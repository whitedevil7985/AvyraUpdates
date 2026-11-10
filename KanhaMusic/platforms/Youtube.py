import asyncio
import os
import re
import logging
import hashlib
import json
import random
import time
import traceback
from typing import Union, List, Tuple, Dict
from urllib.parse import urlparse, parse_qs, quote, quote_plus

import aiohttp
import httpx
import yt_dlp
from pyrogram.enums import MessageEntityType
from pyrogram.types import Message
from py_yt import VideosSearch, Playlist

try:
    from py_yt.core.requests import RequestCore
except Exception:
    RequestCore = object

import config
from KanhaMusic.utils.url_guard import check_url as check_stream_url
from KanhaMusic.utils.media_guard import PublicHTTPTransport, get_media_proxy

logger = logging.getLogger("KanhaMusic.youtube")

# ── Directories & Cache ──────────────────────────────────────────────────────────
DOWNLOAD_DIR = "downloads"
_CACHE_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "cache")
os.makedirs(DOWNLOAD_DIR, exist_ok=True)
os.makedirs(_CACHE_DIR, exist_ok=True)

_SEARCH_CACHE: dict = {}  # query -> video_id
_STREAM_CACHE: dict = {}  # (mode, url) -> (stream_url, expire_timestamp)
_MAX_SEARCH_CACHE_SIZE = 5000
_MAX_STREAM_CACHE_SIZE = 3000
_MEM_CACHE: dict = {}

# ── API Configurations (Read directly from config.py) ─────────────────────────
API_URL = getattr(config, "API_URL", None) or getattr(config, "RITESH_API_URL", None)
API_KEY = getattr(config, "API_KEY", None) or getattr(config, "RITESH_API_KEY", None)
YT_API_TOKEN = getattr(config, "YT_API_TOKEN", None) or getattr(config, "YTUBE_API_TOKEN", None)
BASE_URL = getattr(config, "NUB_YT_API_BASE_URL", None) or getattr(config, "YTUBE_API_BASE_URL", None)
INFLEX_API_KEY = getattr(config, "INFLEX_API_KEY", None) or "INFLEX55158228D"
INFLEX_API_URL = (getattr(config, "INFLEX_API_URL", None) or "http://187.127.120.51").rstrip("/")
_RAW_KEYS = getattr(config, "YOUTUBE_API_KEYS", "")
if isinstance(_RAW_KEYS, list):
    YOUTUBE_API_KEYS = _RAW_KEYS
else:
    YOUTUBE_API_KEYS = [k.strip() for k in str(_RAW_KEYS).split(",") if k.strip()]

YT_COOKIES_FILE = getattr(config, "YT_COOKIES_FILE", None)
COOKIES_FROM_BROWSER = getattr(config, "COOKIES_FROM_BROWSER", None)
COOKIES_BOOTSTRAP_URL = getattr(config, "COOKIES_BOOTSTRAP_URL", "https://www.youtube.com/watch?v=jNQXAC9IVRw")
COOKIES_REFRESH_HOURS = getattr(config, "COOKIES_REFRESH_HOURS", 6.0)

SEARCH_URL = "https://www.googleapis.com/youtube/v3/search"
DETAILS_URL = "https://www.googleapis.com/youtube/v3/videos"

# ── Circuit Breaker for NUB API ─────────────────────────────────────────────────
_api_failures = 0
_api_last_failure_time = 0.0
_CIRCUIT_BREAKER_THRESHOLD = 3
_CIRCUIT_BREAKER_COOLDOWN = 120.0


def _api_breaker_open() -> bool:
    global _api_failures, _api_last_failure_time
    if _api_failures >= _CIRCUIT_BREAKER_THRESHOLD:
        if time.time() - _api_last_failure_time > _CIRCUIT_BREAKER_COOLDOWN:
            _api_failures = 0
            return False
        return True
    return False


def _api_record_success():
    global _api_failures
    _api_failures = 0


def _api_record_failure():
    global _api_failures, _api_last_failure_time
    _api_failures += 1
    _api_last_failure_time = time.time()


# ── HTTP Client ─────────────────────────────────────────────────────────────────
_http_client: httpx.AsyncClient | None = None


def get_http_client() -> httpx.AsyncClient:
    global _http_client
    if _http_client is None or _http_client.is_closed:
        try:
            transport = PublicHTTPTransport(allow_private=True)
        except Exception:
            transport = httpx.AsyncHTTPTransport(verify=True)
        _http_client = httpx.AsyncClient(
            timeout=httpx.Timeout(connect=10.0, read=25.0, write=10.0, pool=10.0),
            follow_redirects=True,
            transport=transport,
            limits=httpx.Limits(max_keepalive_connections=20, max_connections=50),
        )
    return _http_client


async def close_http_client():
    global _http_client
    if _http_client is not None and not _http_client.is_closed:
        await _http_client.aclose()
        _http_client = None


# ── Memory Cache ────────────────────────────────────────────────────────────────
def _mem_cache_get(key):
    if isinstance(key, tuple) and len(key) == 2:
        kind, val = key
        if kind == "search":
            return _SEARCH_CACHE.get(val) or _MEM_CACHE.get(key)
        elif kind in ("audio", "video"):
            entry = _STREAM_CACHE.get((kind, val))
            if entry:
                stream_url, expire = entry
                if expire and time.time() < expire - 15:
                    return stream_url
                else:
                    _STREAM_CACHE.pop((kind, val), None)
                    _MEM_CACHE.pop(key, None)
                    return None
            return _MEM_CACHE.get(key)
    return _MEM_CACHE.get(key)


def _mem_cache_set(key, value):
    if isinstance(key, tuple) and len(key) == 2:
        kind, val = key
        if kind == "search":
            if len(_SEARCH_CACHE) >= _MAX_SEARCH_CACHE_SIZE:
                oldest_key = next(iter(_SEARCH_CACHE))
                _SEARCH_CACHE.pop(oldest_key, None)
            _SEARCH_CACHE[val] = value
        elif kind in ("audio", "video"):
            if len(_STREAM_CACHE) >= _MAX_STREAM_CACHE_SIZE:
                oldest_key = next(iter(_STREAM_CACHE))
                _STREAM_CACHE.pop(oldest_key, None)
            expire = _extract_expire(value)
            _STREAM_CACHE[(kind, val)] = (value, expire)
    _MEM_CACHE[key] = value


# ── Disk Cache Helpers ──────────────────────────────────────────────────────────
def _key(url: str, prefix: str = "") -> str:
    return hashlib.md5((prefix + url).encode()).hexdigest()


def _cache_path(url: str, prefix: str = "") -> str:
    return os.path.join(_CACHE_DIR, _key(url, prefix) + ".json")


def _extract_expire(stream_url: str) -> int | None:
    try:
        q = parse_qs(urlparse(stream_url).query)
        expire = int(q.get("expire", [0])[0])
        return expire if expire > int(time.time()) else None
    except Exception:
        return None


def _read_cache_sync(url: str, prefix: str = "") -> str | None:
    path = _cache_path(url, prefix)
    if not os.path.exists(path):
        return None
    try:
        with open(path, "r") as f:
            data = json.load(f)
        expire = data.get("expire", 0)
        if time.time() < expire - 15:
            return data.get("url")
        os.remove(path)
    except Exception:
        try:
            os.remove(path)
        except Exception:
            pass
    return None


def _write_cache_sync(url: str, stream_url: str, prefix: str = ""):
    expire = _extract_expire(stream_url)
    if not expire:
        return
    try:
        fd = os.open(_cache_path(url, prefix), os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(fd, "w") as f:
            json.dump({"url": stream_url, "expire": expire}, f)
    except Exception:
        pass


async def _read_cache(url: str, prefix: str = "") -> str | None:
    return await asyncio.to_thread(_read_cache_sync, url, prefix)


async def _write_cache(url: str, stream_url: str, prefix: str = ""):
    await asyncio.to_thread(_write_cache_sync, url, stream_url, prefix)


def evict_stream_cache(url: str, mode: str = "audio"):
    if not url:
        return
    _STREAM_CACHE.pop((mode, url), None)
    _MEM_CACHE.pop((mode, url), None)
    for pfx in (f"{mode}_", ""):
        path = _cache_path(url, pfx)
        try:
            if os.path.exists(path):
                os.remove(path)
        except OSError:
            pass


# ── String & Format Helpers ────────────────────────────────────────────────────
def time_to_seconds(time):
    if not time or str(time) == "None":
        return 0
    stringt = str(time).strip()
    try:
        return sum(int(x) * 60 ** i for i, x in enumerate(reversed(stringt.split(":"))))
    except Exception:
        return 0


def format_duration(seconds: int) -> str:
    if not seconds:
        return "00:00"
    m, s = divmod(int(seconds), 60)
    h, m = divmod(m, 60)
    if h:
        return f"{h}:{m:02d}:{s:02d}"
    return f"{m:02d}:{s:02d}"


def format_ind(n):
    try:
        n = float(n)
    except (ValueError, TypeError):
        return "0"
    if n >= 10**7:
        return f"{n / 10**7:.1f} Crore"
    if n >= 10**5:
        return f"{n / 10**5:.1f} Lakh"
    if n >= 10**3:
        return f"{n / 10**3:.1f}K"
    return str(int(n))


def _extract_id(link: str) -> str:
    if not link:
        return ""
    if "v=" in link:
        return link.split("v=")[-1].split("&")[0]
    if "youtu.be/" in link:
        return link.split("youtu.be/")[-1].split("?")[0].split("&")[0]
    m = re.search(r"(?:v=|/shorts/|youtu\.be/|/embed/|/v/|/live/)([A-Za-z0-9_-]{11})", link)
    if m:
        return m.group(1)
    if re.fullmatch(r"[A-Za-z0-9_-]{11}", link.strip()):
        return link.strip()
    return link


def extract_video_id(url):
    return _extract_id(url)


def is_direct_stream_url(url: str) -> bool:
    if not isinstance(url, str) or not url.startswith(("http://", "https://")):
        return False
    if re.search(r"spotify\.com", url, re.I):
        return False
    if re.search(r"(youtube\.com/(watch|playlist|shorts|embed)|youtu\.be/)", url, re.I):
        return False
    return True

async def _validate_audio_source(url: str) -> bool:
    """Reject provider URLs that return an HTML/error page instead of audio."""
    url = normalize_media_url(url)
    if not url:
        return False
    timeout = aiohttp.ClientTimeout(total=5, connect=3, sock_read=3)
    headers = {
        "Range": "bytes=0-2047",
        "User-Agent": "Mozilla/5.0 (compatible; KanhaMusic/1.0)",
    }
    try:
        async with aiohttp.ClientSession(timeout=timeout, headers=headers) as session:
            async with session.get(url, allow_redirects=True) as response:
                if response.status not in (200, 206):
                    return False
                content_type = (response.headers.get("Content-Type") or "").lower()
                if any(kind in content_type for kind in ("text/html", "application/json", "text/plain")):
                    return False
                sample = await response.content.read(2048)
                if not sample:
                    return False
                prefix = sample.lstrip()[:32].lower()
                if prefix.startswith((b"<!doctype html", b"<html", b"{", b"[")):
                    return False
                return True
    except Exception:
        return False


def normalize_media_url(value) -> str | None:
    """Extract a real HTTP media URL from provider responses."""
    if not isinstance(value, str):
        return None
    value = value.strip()
    markdown = re.fullmatch(r"\[[^\]]+\]\((https?://[^)]+)\)", value)
    if markdown:
        value = markdown.group(1).strip()
    if value.startswith("<") and value.endswith(">"):
        value = value[1:-1].strip()
    parsed = urlparse(value)
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        return None
    return value


def is_external_path(path) -> bool:
    if not path:
        return True
    path = str(path)
    if path.startswith(("http://", "https://")):
        return True
    base = os.path.normpath(os.path.abspath(DOWNLOAD_DIR))
    full = os.path.normpath(os.path.abspath(path))
    return not full.startswith(base + os.sep)


def get_random_key():
    if not YOUTUBE_API_KEYS:
        return None
    return random.choice(YOUTUBE_API_KEYS)


# ── NUB API & yt-dlp Core Stream Resolution ─────────────────────────────────────
def _provider_stream(data: dict, mode: str) -> str | None:
    if mode == "audio":
        return data.get("stream_url")
    formats = data.get("formats") or []
    if data.get("vcodec") == "none" or data.get("acodec") == "none":
        return None
    available_formats = [item for item in formats if item.get("url")]
    if available_formats and all(item.get("vcodec") == "none" or item.get("acodec") == "none" for item in available_formats):
        return None
    return data.get("stream_url")


async def _run_yt_dlp(url: str, format_selector: str, cookies: str | None) -> str | None:
    cmd = [
        "yt-dlp",
        "--js-runtimes", "node",
        "--remote-components", "ejs:github",
        "-f", format_selector,
        "--no-playlist",
        "-g",
        url,
    ]
    cookies = cookies or YT_COOKIES_FILE
    if cookies and os.path.exists(cookies):
        cmd.extend(["--cookies", cookies])
    try:
        proxy = await get_media_proxy()
        if proxy:
            cmd.extend(["--proxy", proxy])
    except Exception:
        pass

    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=10)
        if proc.returncode == 0 and stdout:
            return stdout.decode().strip().split("\n")[0]
    except Exception:
        pass
    return None


async def _inflex_api_get_stream(link: str, is_video: bool = False, timeout: int = 25) -> str | None:
    key = INFLEX_API_KEY
    base = (INFLEX_API_URL or "").rstrip("/")
    if not key or not base:
        return None

    video_id = _extract_id(link)
    if not video_id or len(video_id) < 3:
        return None

    watch_url = f"https://www.youtube.com/watch?v={video_id}"
    dl_type = "video" if is_video else "audio"
    payload = {"url": watch_url, "type": dl_type}
    headers = {
        "Content-Type": "application/json",
        "X-API-KEY": key,
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    }

    try:
        client = get_http_client()
        resp = await client.post(
            f"{base}/download",
            json=payload,
            headers=headers,
            timeout=timeout,
        )
        if resp.status_code == 200:
            data = resp.json()
            if data.get("status") == "success":
                if is_video:
                    return data.get("video_url") or data.get("stream_url") or data.get("audio_url")
                else:
                    return data.get("audio_url") or data.get("stream_url")
    except Exception:
        pass
    return None


async def _ritesh_api_get_stream(link: str, is_video: bool = False, timeout: int = 15) -> str | None:
    api_url = API_URL
    api_key = API_KEY
    if not api_url or not api_key:
        return None

    video_id = _extract_id(link)
    if not video_id or len(video_id) < 3:
        return None

    query = f"https://www.youtube.com/watch?v={video_id}"
    dl_type = "video" if is_video else "audio"
    params = {"query": query, "dl_type": dl_type, "api_key": api_key}
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    }
    try:
        client = get_http_client()
        resp = await client.get(
            f"{api_url}/download",
            params=params,
            headers=headers,
            timeout=timeout,
            follow_redirects=False,
        )
        if resp.status_code in (301, 302, 303, 307, 308):
            loc = resp.headers.get("location")
            if loc:
                if loc.startswith("http://") or loc.startswith("https://"):
                    return loc
                return f"{api_url.rstrip('/')}/{loc.lstrip('/')}"
        elif resp.status_code == 200:
            ctype = resp.headers.get("Content-Type", "")
            if "application/json" in ctype:
                data = resp.json()
                return (
                    data.get("url")
                    or data.get("download_url")
                    or data.get("link")
                    or (data.get("data") or {}).get("url")
                )
    except Exception:
        pass
    return None


async def get_stream(url: str, cookies: str | None = None, skip_api: bool = False) -> str | None:
    if not skip_api:
        cached = _mem_cache_get(("audio", url))
        if cached:
            cached = normalize_media_url(cached)
            if cached and await _validate_audio_source(cached):
                return cached
            _STREAM_CACHE.pop(("audio", url), None)
            _MEM_CACHE.pop(("audio", url), None)
        cached = await _read_cache(url, prefix="audio_")
        if cached:
            cached = normalize_media_url(cached)
            if cached and await _validate_audio_source(cached):
                _mem_cache_set(("audio", url), cached)
                return cached

    # Resolve configured API providers concurrently. Sequential provider calls
    # made every failed request add its full timeout to the song start delay.
    async def _nub_audio():
        if not (YT_API_TOKEN and BASE_URL) or _api_breaker_open() or skip_api:
            return None
        try:
            resp = await asyncio.wait_for(
                get_http_client().get(
                    f"{BASE_URL}/info",
                    params={"q": url},
                    headers={"Authorization": f"Bearer {YT_API_TOKEN}"},
                ),
                timeout=5,
            )
            if resp.status_code == 200:
                data = resp.json()
                stream_url = normalize_media_url(data.get("stream_url"))
                if stream_url:
                    _api_record_success()
                    return stream_url
            _api_record_failure()
        except Exception:
            _api_record_failure()
        return None

    providers = []
    if INFLEX_API_KEY and INFLEX_API_URL and not skip_api:
        providers.append(_inflex_api_get_stream(url, is_video=False, timeout=5))
    if API_KEY and API_URL and not skip_api:
        providers.append(_ritesh_api_get_stream(url, is_video=False, timeout=5))
    if YT_API_TOKEN and BASE_URL and not skip_api:
        providers.append(_nub_audio())

    if providers:
        tasks = {asyncio.create_task(provider) for provider in providers}
        try:
            while tasks:
                done, tasks = await asyncio.wait(
                    tasks, timeout=5, return_when=asyncio.FIRST_COMPLETED
                )
                if not done:
                    break
                for task in done:
                    try:
                        stream_url = normalize_media_url(task.result())
                    except Exception:
                        stream_url = None
                    if stream_url and await _validate_audio_source(stream_url):
                        for pending in tasks:
                            pending.cancel()
                        await asyncio.gather(*tasks, return_exceptions=True)
                        _mem_cache_set(("audio", url), stream_url)
                        await _write_cache(url, stream_url, prefix="audio_")
                        return stream_url
        finally:
            for pending in tasks:
                pending.cancel()
            if tasks:
                await asyncio.gather(*tasks, return_exceptions=True)

    # [4] Fallback to yt-dlp
    stream = await _run_yt_dlp(url, "bestaudio[ext=m4a]/bestaudio/best", cookies)
    stream = normalize_media_url(stream)
    if stream and await _validate_audio_source(stream):
        _mem_cache_set(("audio", url), stream)
        await _write_cache(url, stream, prefix="audio_")
        return stream
    return None


async def get_video_stream(url: str, cookies: str | None = None, skip_api: bool = False) -> str | None:
    if not skip_api:
        cached = _mem_cache_get(("video", url))
        if cached:
            return cached
        cached = await _read_cache(url, prefix="video_")
        if cached:
            _mem_cache_set(("video", url), cached)
            return cached

    # [1] Primary: Inflex API (@InflexAPIBot)
    if INFLEX_API_KEY and INFLEX_API_URL and not skip_api:
        try:
            stream = await _inflex_api_get_stream(url, is_video=True, timeout=15)
            if stream:
                _mem_cache_set(("video", url), stream)
                await _write_cache(url, stream, prefix="video_")
                return stream
        except Exception:
            pass

    # [2] Secondary: Ritesh API
    if API_KEY and API_URL and not skip_api:
        try:
            stream = await _ritesh_api_get_stream(url, is_video=True, timeout=15)
            if stream:
                _mem_cache_set(("video", url), stream)
                await _write_cache(url, stream, prefix="video_")
                return stream
        except Exception:
            pass

    # [3] Tertiary: NUB API /info
    if YT_API_TOKEN and BASE_URL and not _api_breaker_open() and not skip_api:
        try:
            resp = await get_http_client().get(
                f"{BASE_URL}/info",
                params={"q": url},
                headers={"Authorization": f"Bearer {YT_API_TOKEN}"},
            )
            if resp.status_code == 200:
                data = resp.json()
                stream = _provider_stream(data, "video")
                if stream:
                    _api_record_success()
                    _mem_cache_set(("video", url), stream)
                    await _write_cache(url, stream, prefix="video_")
                    return stream
                if data.get("stream_url"):
                    _api_record_success()
                else:
                    _api_record_failure()
            else:
                _api_record_failure()
        except Exception:
            _api_record_failure()

    # [4] Fallback to yt-dlp
    stream = await _run_yt_dlp(url, "bestvideo[height<=720]+bestaudio/best[height<=720]", cookies)
    if stream:
        _mem_cache_set(("video", url), stream)
        await _write_cache(url, stream, prefix="video_")
        return stream
    return None
    if stream:
        _mem_cache_set(("video", url), stream)
        await _write_cache(url, stream, prefix="video_")
        return stream
    return None


async def get_video_info(query: str, max_results: int = 1, mode: str = "audio") -> Tuple:
    if is_direct_stream_url(query):
        return (
            "Direct Stream",
            extract_video_id(query),
            "N/A",
            query,
            "N/A",
            "0",
            query,
            "N/A",
            "direct",
        )

    # NUB API /info
    if YT_API_TOKEN and BASE_URL and not _api_breaker_open():
        try:
            resp = await get_http_client().get(
                f"{BASE_URL}/info",
                params={"q": query},
                headers={"Authorization": f"Bearer {YT_API_TOKEN}"},
            )
            if resp.status_code == 200:
                data = resp.json()
                stream_url = _provider_stream(data, mode)
                if stream_url and data.get("title"):
                    _api_record_success()
                    return (
                        data.get('title', 'N/A'),
                        data.get('video_id', 'N/A'),
                        data.get('duration', '0'),
                        data.get('youtube_link', 'N/A'),
                        data.get('channel_name', 'N/A'),
                        data.get('views', '0'),
                        stream_url,
                        data.get('thumbnail', 'N/A'),
                        'ytube',
                    )
                if mode == "video" and data.get("stream_url") and data.get("title"):
                    _api_record_success()
                else:
                    _api_record_failure()
            else:
                _api_record_failure()
        except Exception:
            _api_record_failure()

    # Fallback: youtube_search or VideosSearch
    try:
        results = await youtube_search(query, limit=max_results)
        if results:
            video = results[0]
            video_id = video['url'].split('v=')[-1]
            stream_url = await get_stream(video['url']) if mode == "audio" else await get_video_stream(video['url'])
            return (
                video.get('title', 'N/A'),
                video_id,
                video.get('duration', '0'),
                video.get('url', 'N/A'),
                video.get('channel_name', 'N/A'),
                video.get('views', '0'),
                stream_url or 'N/A',
                video.get('thumbnail', 'N/A'),
                'ytdlp',
            )
    except Exception:
        pass

    return (None,) * 9


# ── YouTube Data API v3 Search ──────────────────────────────────────────────────
async def youtube_search(query: str, limit: int = 1):
    if is_direct_stream_url(query) or not YOUTUBE_API_KEYS:
        return []
    api_key = get_random_key()
    if not api_key:
        return []
    client = get_http_client()
    try:
        search_params = {
            "part": "snippet",
            "q": query,
            "maxResults": limit,
            "type": "video",
            "key": api_key,
        }
        search_res = await client.get(SEARCH_URL, params=search_params)
        if search_res.status_code != 200:
            return []
        items = search_res.json().get("items", [])
        video_ids = [item["id"]["videoId"] for item in items if "videoId" in item.get("id", {})]
        if not video_ids:
            return []
        details_params = {
            "part": "contentDetails,statistics",
            "id": ",".join(video_ids),
            "key": get_random_key() or api_key,
        }
        detail_res = await client.get(DETAILS_URL, params=details_params)
        if detail_res.status_code != 200:
            return []
        detail_items = {v["id"]: v for v in detail_res.json().get("items", [])}
        results = []
        for item in items:
            vid = item["id"].get("videoId")
            if not vid or vid not in detail_items:
                continue
            det = detail_items[vid]
            dur = det.get("contentDetails", {}).get("duration", "")
            results.append({
                "title": item["snippet"].get("title", ""),
                "url": f"https://www.youtube.com/watch?v={vid}",
                "duration": dur,
                "channel_name": item["snippet"].get("channelTitle", ""),
                "views": det.get("statistics", {}).get("viewCount", "0"),
                "thumbnail": item["snippet"].get("thumbnails", {}).get("high", {}).get("url", ""),
            })
        return results
    except Exception:
        return []


# ── Cookie Handlers ─────────────────────────────────────────────────────────────
async def export_browser_cookies():
    if not COOKIES_FROM_BROWSER or not YT_COOKIES_FILE:
        return
    browsers = [b for b in re.split(r"[,\s]+", COOKIES_FROM_BROWSER or "") if b]
    for browser in browsers:
        cmd = [
            "yt-dlp",
            "--cookies-from-browser", browser,
            "--cookies", YT_COOKIES_FILE,
            "--skip-download",
            COOKIES_BOOTSTRAP_URL,
        ]
        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
            )
            await asyncio.wait_for(proc.communicate(), timeout=60)
            if os.path.exists(YT_COOKIES_FILE) and os.path.getsize(YT_COOKIES_FILE) > 0:
                return
        except Exception:
            continue


async def refresh_cookies_loop():
    if not COOKIES_FROM_BROWSER or not YT_COOKIES_FILE or COOKIES_REFRESH_HOURS <= 0:
        return
    while True:
        await asyncio.sleep(COOKIES_REFRESH_HOURS * 3600)
        await export_browser_cookies()


# ── Downloader Engine ───────────────────────────────────────────────────────────
async def _download_stream_url(stream_url: str, file_path: str, timeout: int = 90) -> bool:
    tmp_path = file_path + ".part"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "*/*",
        "Accept-Encoding": "identity;q=1, *;q=0",
    }
    try:
        async with aiohttp.ClientSession(headers=headers) as session:
            async with session.get(stream_url, allow_redirects=True, timeout=aiohttp.ClientTimeout(total=timeout)) as resp:
                if resp.status in (200, 206):
                    with open(tmp_path, "wb") as f:
                        async for chunk in resp.content.iter_chunked(131072):
                            f.write(chunk)
                    if os.path.exists(tmp_path) and os.path.getsize(tmp_path) > 10000:
                        os.replace(tmp_path, file_path)
                        return True
    except Exception:
        pass
    finally:
        if os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except Exception:
                pass

    # Secondary fallback: ffmpeg stream download
    try:
        proc = await asyncio.create_subprocess_exec(
            "ffmpeg", "-y", "-reconnect", "1", "-reconnect_streamed", "1",
            "-reconnect_delay_max", "5",
            "-user_agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "-i", stream_url, "-c", "copy", tmp_path,
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
        )
        await asyncio.wait_for(proc.communicate(), timeout=timeout)
        if os.path.exists(tmp_path) and os.path.getsize(tmp_path) > 10000:
            os.replace(tmp_path, file_path)
            return True
    except Exception:
        pass
    finally:
        if os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except Exception:
                pass
    return False


async def _ytdlp_download(link: str, is_video: bool, out_path: str) -> str | None:
    fmt = "bestvideo[height<=720]+bestaudio/best[height<=720]" if is_video else "bestaudio[ext=m4a]/bestaudio/best"
    cmd = [
        "yt-dlp",
        "-f", fmt,
        "--no-playlist",
        "-o", out_path,
        link,
    ]
    if YT_COOKIES_FILE and os.path.exists(YT_COOKIES_FILE):
        cmd.extend(["--cookies", YT_COOKIES_FILE])
    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )
        await asyncio.wait_for(proc.communicate(), timeout=90)
        if os.path.exists(out_path) and os.path.getsize(out_path) > 10000:
            return out_path
    except Exception:
        pass
    return None


async def _api_download(link: str, dl_type: str, ext: str, timeout: int, out_path: str = None):
    video_id = _extract_id(link)
    if not video_id or len(video_id) < 3:
        return None

    os.makedirs(DOWNLOAD_DIR, exist_ok=True)
    file_path = out_path or os.path.join(DOWNLOAD_DIR, f"{video_id}.{ext}")
    tmp_path = file_path + ".part"

    if os.path.exists(file_path) and os.path.getsize(file_path) > 10000:
        return file_path

    query = f"https://www.youtube.com/watch?v={video_id}"
    params = {"query": query, "dl_type": dl_type, "api_key": API_KEY}
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    }

    try:
        async with aiohttp.ClientSession(headers=headers) as session:
            async with session.get(
                f"{API_URL}/download",
                params=params,
                allow_redirects=True,
                timeout=aiohttp.ClientTimeout(total=timeout),
            ) as resp:
                if resp.status != 200:
                    return None

                ctype = resp.headers.get("Content-Type", "")

                if "application/json" in ctype:
                    data = await resp.json()
                    url = (
                        data.get("url")
                        or data.get("download_url")
                        or data.get("link")
                        or (data.get("data") or {}).get("url")
                    )
                    if not url:
                        return None
                    async with session.get(
                        url, allow_redirects=True, timeout=aiohttp.ClientTimeout(total=timeout)
                    ) as r2:
                        if r2.status != 200:
                            return None
                        with open(tmp_path, "wb") as f:
                            async for chunk in r2.content.iter_chunked(131072):
                                f.write(chunk)
                else:
                    with open(tmp_path, "wb") as f:
                        async for chunk in resp.content.iter_chunked(131072):
                            f.write(chunk)

        if os.path.exists(tmp_path) and os.path.getsize(tmp_path) > 10000:
            os.replace(tmp_path, file_path)
            return file_path
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
        return None
    except Exception:
        for p in (tmp_path, file_path):
            if os.path.exists(p) and p == tmp_path:
                try:
                    os.remove(p)
                except Exception:
                    pass
        return None


async def _inflex_api_download(link: str, is_video: bool, ext: str, timeout: int, out_path: str = None) -> str | None:
    video_id = _extract_id(link)
    if not video_id or len(video_id) < 3:
        return None

    os.makedirs(DOWNLOAD_DIR, exist_ok=True)
    file_path = out_path or os.path.join(DOWNLOAD_DIR, f"inflex_{video_id}.{ext}")

    if os.path.exists(file_path) and os.path.getsize(file_path) > 10000:
        return file_path

    try:
        stream_url = await _inflex_api_get_stream(link, is_video=is_video, timeout=min(30, timeout))
        if stream_url:
            if await _download_stream_url(stream_url, file_path, timeout=timeout):
                if os.path.exists(file_path) and os.path.getsize(file_path) > 10000:
                    return file_path
    except Exception:
        pass
    return None


# ── Multi-API Fast Race (INFLEX [Primary] vs RITESH [Secondary] vs NUB [Tertiary]) ──
async def _race_download(link: str, is_video: bool = False) -> str | None:
    video_id = _extract_id(link)
    if not video_id:
        return None

    os.makedirs(DOWNLOAD_DIR, exist_ok=True)
    ext = "mp4" if is_video else "mp3"
    dl_type = "video" if is_video else "audio"
    final_file = os.path.join(DOWNLOAD_DIR, f"{video_id}.{ext}")

    if os.path.exists(final_file) and os.path.getsize(final_file) > 10000:
        return final_file

    watch_url = f"https://www.youtube.com/watch?v={video_id}"
    timeout = 90 if not is_video else 120

    # Worker 1: [Primary] Inflex API (@InflexAPIBot)
    async def _inflex_worker() -> str | None:
        try:
            inflex_file = os.path.join(DOWNLOAD_DIR, f"inflex_{video_id}.{ext}")
            res = await _inflex_api_download(link, is_video=is_video, ext=ext, timeout=timeout, out_path=inflex_file)
            if res and os.path.exists(res) and os.path.getsize(res) > 10000:
                return res
        except Exception:
            pass
        return None

    # Worker 2: [Secondary] Ritesh API
    async def _ritesh_worker() -> str | None:
        try:
            ritesh_file = os.path.join(DOWNLOAD_DIR, f"ritesh_{video_id}.{ext}")
            res = await _api_download(link, dl_type, ext, timeout=timeout, out_path=ritesh_file)
            if res and os.path.exists(res) and os.path.getsize(res) > 10000:
                return res
        except Exception:
            pass
        return None

    # Worker 3: [Tertiary] NUB API
    async def _nub_worker() -> str | None:
        try:
            get_fn = get_video_stream if is_video else get_stream
            stream_url = await get_fn(watch_url)
            if stream_url:
                nub_part = os.path.join(DOWNLOAD_DIR, f"nub_{video_id}.{ext}.part")
                if await _download_stream_url(stream_url, nub_part, timeout=timeout):
                    return nub_part
        except Exception:
            pass
        return None

    # Launch all available APIs simultaneously in parallel:
    tasks = []
    if INFLEX_API_KEY and INFLEX_API_URL:
        tasks.append(asyncio.create_task(_inflex_worker(), name="Inflex_API"))
    if API_KEY and API_URL:
        tasks.append(asyncio.create_task(_ritesh_worker(), name="Ritesh_API"))
    if YT_API_TOKEN and BASE_URL:
        tasks.append(asyncio.create_task(_nub_worker(), name="NUB_API"))

    winner_file = None
    while tasks:
        done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
        tasks = list(pending)
        for completed_task in done:
            try:
                res = completed_task.result()
            except Exception:
                res = None
            if res and os.path.exists(res) and os.path.getsize(res) > 10000:
                winner_file = res
                # Cancel the remaining slower tasks immediately
                for p in tasks:
                    p.cancel()
                tasks.clear()
                break

    if winner_file and os.path.exists(winner_file):
        try:
            os.replace(winner_file, final_file)
            return final_file
        except Exception:
            return winner_file

    # Fallback Tier 3: yt-dlp download if all APIs failed
    try:
        res = await _ytdlp_download(watch_url, is_video=is_video, out_path=final_file)
        if res and os.path.exists(res):
            return res
    except Exception:
        pass

    return None


async def download_song(link: str) -> str:
    return await _race_download(link, is_video=False)


async def download_video(link: str) -> str:
    return await _race_download(link, is_video=True)


# ── YouTubeAPI Class ────────────────────────────────────────────────────────────
class YouTubeAPI:
    def __init__(self):
        self.base = "https://www.youtube.com/watch?v="
        self.regex = r"(?:https?:\/\/)?(?:www\.)?(?:youtu\.be\/|youtube\.com\/(?:embed\/|v\/|shorts\/|playlist\?|watch\?v=|watch\?.+(?:&|&#38;);v=))([a-zA-Z0-9\-_]{11})|(^.*(youtu.be\/|list=)([^#\&\?]*).*)"
        self.status = "https://www.youtube.com/oembed?url="
        self.list = "https://youtube.com/playlist?list="

    async def exists(self, link: str, videoid: Union[bool, str] = None):
        if videoid:
            link = self.base + link
        return bool(re.search(self.regex, link))

    async def url(self, message_1: Message) -> Union[str, None]:
        messages = [message_1]
        if message_1.reply_to_message:
            messages.append(message_1.reply_to_message)
        text = ""
        offset = None
        length = None
        for message in messages:
            if offset:
                break
            if message.entities:
                for entity in message.entities:
                    if entity.type == MessageEntityType.URL:
                        text = message.text or message.caption
                        offset, length = entity.offset, entity.length
                        break
            elif message.caption_entities:
                for entity in message.caption_entities:
                    if entity.type == MessageEntityType.TEXT_LINK:
                        return entity.url
        if offset in (None,):
            return None
        return text[offset : offset + length]

    async def details(self, link: str, videoid: Union[bool, str] = None):
        if videoid:
            link = self.base + link
        if "&" in link:
            link = link.split("&")[0]

        # Fast path 1: NUB API metadata
        try:
            vid = _extract_id(link)
            info = await get_video_info(vid or link, mode="audio")
            if info and info[0] and info[0] != "N/A":
                title = info[0]
                duration_min = info[2]
                duration_sec = time_to_seconds(duration_min)
                thumbnail = info[7]
                vidid = info[1]
                return title, duration_min, duration_sec, thumbnail, vidid
        except Exception:
            pass

        # Fast path 2: VideosSearch
        results = VideosSearch(link, limit=1)
        for result in (await results.next())["result"]:
            title = result["title"]
            duration_min = result["duration"]
            thumbnail = result["thumbnails"][0]["url"].split("?")[0]
            vidid = result["id"]
            duration_sec = int(time_to_seconds(duration_min)) if str(duration_min) != "None" else 0
            return title, duration_min, duration_sec, thumbnail, vidid

    async def title(self, link: str, videoid: Union[bool, str] = None):
        if videoid:
            link = self.base + link
        if "&" in link:
            link = link.split("&")[0]
        try:
            info = await get_video_info(link, mode="audio")
            if info and info[0] and info[0] != "N/A":
                return info[0]
        except Exception:
            pass
        results = VideosSearch(link, limit=1)
        for result in (await results.next())["result"]:
            return result["title"]

    async def duration(self, link: str, videoid: Union[bool, str] = None):
        if videoid:
            link = self.base + link
        if "&" in link:
            link = link.split("&")[0]
        try:
            info = await get_video_info(link, mode="audio")
            if info and info[2] and info[2] != "0":
                return info[2]
        except Exception:
            pass
        results = VideosSearch(link, limit=1)
        for result in (await results.next())["result"]:
            return result["duration"]

    async def thumbnail(self, link: str, videoid: Union[bool, str] = None):
        if videoid:
            link = self.base + link
        if "&" in link:
            link = link.split("&")[0]
        try:
            info = await get_video_info(link, mode="audio")
            if info and info[7] and info[7] != "N/A":
                return info[7]
        except Exception:
            pass
        results = VideosSearch(link, limit=1)
        for result in (await results.next())["result"]:
            return result["thumbnails"][0]["url"].split("?")[0]

    async def video(self, link: str, videoid: Union[bool, str] = None):
        if videoid:
            link = self.base + link
        if "&" in link:
            link = link.split("&")[0]
        # Fast path 1: Stream URL
        try:
            stream_url = await get_video_stream(link)
            if stream_url:
                return 1, stream_url
        except Exception:
            pass
        # Fallback: Download
        try:
            downloaded = await download_video(link)
            if downloaded:
                return 1, downloaded
        except Exception:
            pass
        # Fallback: yt-dlp direct formats
        try:
            ytdl_opts = {"quiet": True}
            ydl = yt_dlp.YoutubeDL(ytdl_opts)
            with ydl:
                r = ydl.extract_info(link, download=False)
                for format in r.get("formats", []):
                    if "dash" not in str(format.get("format", "")).lower():
                        return 1, format.get("url")
        except Exception:
            pass
        return 0, None

    async def playlist(self, link, limit, user_id, videoid: Union[bool, str] = None):
        if videoid:
            link = self.list + link
        if "&" in link:
            link = link.split("&")[0]
        playlist = await Playlist.create(link)
        title = playlist.title
        items = []
        count = 0
        for video in playlist.videos:
            if count >= limit:
                break
            count += 1
            items.append({
                "title": video.title,
                "duration": video.duration,
                "url": video.link,
            })
        return items, title

    async def track(self, link: str, videoid: Union[bool, str] = None):
        if videoid:
            link = self.base + link
        if "&" in link:
            link = link.split("&")[0]

        # Reuse recent search metadata so repeated play requests do not
        # pay the YouTube search round-trip again.
        cache_key = f"track:{link.strip().lower()}"
        cached = _mem_cache_get(("search", cache_key))
        if cached:
            return cached, cached["vidid"]

        results = VideosSearch(link, limit=1)
        data = await asyncio.wait_for(results.next(), timeout=15)
        for result in data.get("result", []):
            title = result["title"]
            duration_min = result["duration"]
            vidid = result["id"]
            yturl = result["link"]
            thumbnail = result["thumbnails"][0]["url"].split("?")[0]
            track_details = {
                "title": title,
                "link": yturl,
                "vidid": vidid,
                "duration_min": duration_min,
                "thumb": thumbnail,
            }
            _mem_cache_set(("search", cache_key), track_details)
            return track_details, vidid
        raise ValueError("No YouTube search result found")

    async def formats(self, link: str, videoid: Union[bool, str] = None):
        if videoid:
            link = self.base + link
        if "&" in link:
            link = link.split("&")[0]
        ytdl_opts = {"quiet": True}
        ydl = yt_dlp.YoutubeDL(ytdl_opts)
        with ydl:
            formats_available = []
            r = ydl.extract_info(link, download=False)
            for format in r.get("formats", []):
                try:
                    if "dash" not in str(format.get("format", "")).lower():
                        formats_available.append({
                            "format": format.get("format"),
                            "filesize": format.get("filesize"),
                            "format_id": format.get("format_id"),
                            "ext": format.get("ext"),
                            "format_note": format.get("format_note"),
                            "yturl": link,
                        })
                except Exception:
                    continue
        return formats_available, link

    async def slider(self, link: str, query_type: int, videoid: Union[bool, str] = None):
        if videoid:
            link = self.base + link
        if "&" in link:
            link = link.split("&")[0]
        a = VideosSearch(link, limit=10)
        result = (await a.next()).get("result")
        title = result[query_type]["title"]
        duration_min = result[query_type]["duration"]
        vidid = result[query_type]["id"]
        thumbnail = result[query_type]["thumbnails"][0]["url"].split("?")[0]
        return title, duration_min, thumbnail, vidid

    async def download(
        self,
        link: str,
        mystic,
        video: Union[bool, str] = None,
        videoid: Union[bool, str] = None,
        songaudio: Union[bool, str] = None,
        songvideo: Union[bool, str] = None,
        format_id: Union[bool, str] = None,
        title: Union[bool, str] = None,
    ) -> str:
        if videoid:
            link = self.base + link
        try:
            if video:
                downloaded_file = await download_video(link)
            else:
                downloaded_file = await download_song(link)
            if downloaded_file:
                return downloaded_file, True
            return None, False
        except Exception:
            return None, False


# ── YouTube Autoplay & Recommendations Fetcher ──────────────────────────────────
class YouTubeAutoplayFetcher(RequestCore):
    def __init__(self, timeout: float = 15.0, max_retries: int = 2):
        if RequestCore is not object:
            super().__init__(timeout=timeout, max_retries=max_retries)
        self.timeout = timeout
        self.max_retries = max_retries

    async def fetch_mix_and_related(self, video_id: str) -> list:
        if RequestCore is object:
            return []
        self.url = self._build_url("next")
        self.data = self._build_payload(
            client_name="WEB",
            client_version="2.20260820.08.00",
            videoId=video_id,
            playlistId=f"RD{video_id}",
        )
        tracks = []
        seen = {video_id}
        try:
            resp = await self.post_request()
            if not resp:
                return tracks
            data = await resp.json()
        except Exception:
            return tracks

        two_col = data.get("contents", {}).get("twoColumnWatchNextResults", {})
        p_items = two_col.get("playlist", {}).get("playlist", {}).get("contents", [])
        for item in p_items:
            vr = item.get("playlistPanelVideoRenderer")
            if not vr:
                continue
            vid = vr.get("videoId")
            if not vid or vid in seen:
                continue
            title = vr.get("title", {}).get("simpleText") or ""
            dur_str = vr.get("lengthText", {}).get("simpleText") or "0"
            seen.add(vid)
            tracks.append({
                "video_id": vid,
                "title": title,
                "duration": time_to_seconds(dur_str),
            })
        return tracks

    async def fetch_simple_related(self, video_id: str) -> list:
        if RequestCore is object:
            return []
        self.url = self._build_url("next")
        self.data = self._build_payload(
            client_name="WEB",
            client_version="2.20260820.08.00",
            videoId=video_id,
        )
        tracks = []
        seen = {video_id}
        try:
            resp = await self.post_request()
            if not resp:
                return tracks
            data = await resp.json()
        except Exception:
            return tracks

        two_col = data.get("contents", {}).get("twoColumnWatchNextResults", {})
        sec = two_col.get("secondaryResults", {}).get("secondaryResults", {}).get("results", [])
        for item in sec:
            if "lockupViewModel" in item:
                lvm = item["lockupViewModel"]
                vid = lvm.get("contentId")
                if not vid or vid in seen:
                    continue
                meta = lvm.get("metadata", {}).get("lockupMetadataViewModel", {})
                title = meta.get("title", {}).get("content") or ""
                dur_str = "0"
                overlays = lvm.get("contentImage", {}).get("thumbnailViewModel", {}).get("overlays", [])
                for o in overlays:
                    badges = o.get("thumbnailBottomOverlayViewModel", {}).get("badges", [])
                    for b in badges:
                        tb = b.get("thumbnailBadgeViewModel", {})
                        if tb.get("text"):
                            dur_str = tb["text"]
                            break
                seen.add(vid)
                tracks.append({
                    "video_id": vid,
                    "title": title,
                    "duration": time_to_seconds(dur_str),
                })
            elif "compactVideoRenderer" in item:
                cvr = item["compactVideoRenderer"]
                vid = cvr.get("videoId")
                if not vid or vid in seen:
                    continue
                title = cvr.get("title", {}).get("simpleText") or ""
                dur_str = cvr.get("lengthText", {}).get("simpleText") or "0"
                seen.add(vid)
                tracks.append({
                    "video_id": vid,
                    "title": title,
                    "duration": time_to_seconds(dur_str),
                })
        return tracks


_EXCLUDE_TERMS = (
    "trailer",
    "teaser",
    "1 hour",
    "10 hour",
    "jukebox",
    "full album",
    "full movie",
    "reaction",
    "interview",
    "review",
    "status video",
    "whatsapp status",
    "ringtone",
    "behind the scenes",
    "making of",
    "karaoke",
    "instrumental",
    "slowed",
    "reverb",
    "bass boosted",
    "8d audio",
    "speed up",
    "sped up",
    "nightcore",
    "shorts",
    "#shorts",
)

_LABELS = {
    "tseries", "t-series", "sony music", "zee music", "tips", "yrf",
    "speed records", "geet mp3", "white hill", "dharma", "vevo",
    "saregama", "eros now", "desi music factory", "aditya music",
    "lahari music", "svf", "dm - desi music factory", "apna punjab"
}


def _extract_music_meta(title: str):
    if not title:
        return {"song": "", "artist": "", "keywords": []}
    clean = re.sub(r"\[.*?\]|\(.*?\)", "", title).strip()
    parts = re.split(r"\s*[|\-–—:]\s*", clean)
    parts = [p.strip() for p in parts if p.strip()]

    song = parts[0] if parts else clean
    song = re.sub(r"\b(official|video|audio|full song|lyrical|lyrics|song|4k|hd|8k)\b", "", song, flags=re.I).strip()

    artist = ""
    keywords = []
    for p in parts[1:]:
        p_clean = re.sub(r"\b(official|video|audio|lyric|lyrics|full song|song|remix|hd|4k|8k|version|full|feat|ft)\b", "", p, flags=re.I).strip()
        p_lower = p_clean.lower()
        if not p_clean or len(p_clean) < 3:
            continue
        if any(lbl in p_lower for lbl in _LABELS):
            continue
        if not artist and not any(ch.isdigit() for ch in p_clean):
            artist = p_clean
        keywords.append(p_clean)

    return {"song": song, "artist": artist, "keywords": keywords}


async def _search_related(title: str, source_id: str, source_meta: dict = None, limit: int = 15) -> list:
    from KanhaMusic.utils.stream.history import clean_song_title, is_same_song

    source_meta = source_meta or _extract_music_meta(title)
    cleaned = clean_song_title(title)
    artist = source_meta.get("artist") or ""

    queries = []
    if artist:
        queries.append(f"{artist} top hit songs")
        queries.append(f"{artist} songs playlist")
    if cleaned:
        queries.append(f"{cleaned} radio mix")

    for kw in source_meta.get("keywords", []):
        if len(kw) >= 3 and kw != artist:
            queries.append(f"{kw} hit songs")
            break

    tracks = []
    seen = {source_id}
    for q in queries:
        try:
            results = VideosSearch(q, limit=limit)
            data = await results.next()
            for item in data.get("result", []):
                vid = item.get("id")
                if not vid or vid in seen:
                    continue
                cand_title = item.get("title") or ""
                if title and is_same_song(title, cand_title):
                    continue
                if any(is_same_song(cand_title, tr.get("title", "")) for tr in tracks):
                    continue
                seen.add(vid)
                tracks.append({
                    "video_id": vid,
                    "title": cand_title,
                    "duration": time_to_seconds(item.get("duration") or 0),
                })
        except Exception:
            continue
        if len(tracks) >= 20:
            break

    return tracks


async def get_autoplay(video_id, timeout=25, retries=3, seed_id=None, source_title=None):
    from KanhaMusic.utils.stream.history import is_same_song

    fetcher = YouTubeAutoplayFetcher(timeout=min(15.0, timeout))
    tracks = []
    seen = {video_id} if video_id else set()
    if seed_id:
        seen.add(seed_id)

    source = video_id or seed_id
    if not source_title and source:
        try:
            source_title = await asyncio.wait_for(
                YouTube.title(source, videoid=True), timeout=4
            )
        except Exception:
            source_title = ""

    source_meta = _extract_music_meta(source_title) if source_title else {"song": "", "artist": "", "keywords": []}

    # 1. Primary: Official YouTube Mix / Radio (RD{video_id})
    # YouTube's genuine recommendation algorithm (identical to YouTube Music / AnupriyaTuneBot)
    if video_id:
        try:
            mix_tracks = await fetcher.fetch_mix_and_related(video_id)
            if mix_tracks:
                for t in mix_tracks:
                    vid = t.get("video_id")
                    title = t.get("title", "")
                    dur = t.get("duration", 0)
                    if not vid or vid in seen:
                        continue
                    if dur and (dur < 60 or dur > 720):
                        continue
                    t_lower = title.lower()
                    if any(term in t_lower for term in _EXCLUDE_TERMS):
                        continue
                    if source_title and is_same_song(source_title, title):
                        continue
                    if any(is_same_song(title, tr.get("title", "")) for tr in tracks):
                        continue
                    seen.add(vid)
                    tracks.append(t)
        except Exception:
            pass

    # 2. Secondary: YouTube Watch Next / Up Next sidebar
    if len(tracks) < 10 and video_id:
        try:
            simple_tracks = await fetcher.fetch_simple_related(video_id)
            if simple_tracks:
                for t in simple_tracks:
                    vid = t.get("video_id")
                    title = t.get("title", "")
                    dur = t.get("duration", 0)
                    if not vid or vid in seen:
                        continue
                    if dur and (dur < 60 or dur > 720):
                        continue
                    t_lower = title.lower()
                    if any(term in t_lower for term in _EXCLUDE_TERMS):
                        continue
                    if source_title and is_same_song(source_title, title):
                        continue
                    if any(is_same_song(title, tr.get("title", "")) for tr in tracks):
                        continue
                    seen.add(vid)
                    tracks.append(t)
        except Exception:
            pass

    # 3. Tertiary fallback: Only if YouTube Mix returned fewer than 5 tracks
    if len(tracks) < 5 and (source_title or source_meta.get("artist")):
        try:
            search_tracks = await _search_related(source_title, source, source_meta)
            if search_tracks:
                for t in search_tracks:
                    vid = t.get("video_id")
                    title = t.get("title", "")
                    dur = t.get("duration", 0)
                    if not vid or vid in seen:
                        continue
                    if dur and (dur < 60 or dur > 720):
                        continue
                    t_lower = title.lower()
                    if any(term in t_lower for term in _EXCLUDE_TERMS):
                        continue
                    if source_title and is_same_song(source_title, title):
                        continue
                    if any(is_same_song(title, tr.get("title", "")) for tr in tracks):
                        continue
                    seen.add(vid)
                    tracks.append(t)
        except Exception:
            pass

    return tracks


YouTube = YouTubeAPI()
