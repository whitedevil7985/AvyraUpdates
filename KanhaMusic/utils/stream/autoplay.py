import asyncio
import os
import random
import re

from KanhaMusic import YouTube, ayush
from KanhaMusic.misc import db
from KanhaMusic.platforms.Youtube import get_autoplay, is_external_path
from KanhaMusic.utils.database import get_lang, is_autoplay
from KanhaMusic.utils.formatters import seconds_to_min
from KanhaMusic.utils.logger import autoplay_logs
from KanhaMusic.utils.rich_stream import send_now_playing_rich
from KanhaMusic.utils.stream.history import (
    is_same_song,
    record_played,
    was_recently_played,
)
from KanhaMusic.utils.stream.queue import put_queue
from KanhaMusic.utils.stream.seed import get_seed
from KanhaMusic.utils.thumbnails import get_thumb
from strings import get_string

PREFETCH_AFTER = 5
DOWNLOAD_TIMEOUT = 90
FALLBACK_TIMEOUT = 40
READY_WAIT = 45
API_TIMEOUT = 25
API_RETRIES = 3

_ID_RE = re.compile(r"^[A-Za-z0-9_-]{11}$")
_cache = {}


def _new_entry(source_id, carry=None, video=False, failed=None, source_title=""):
    return {
        "source_id": source_id,
        "source_title": source_title,
        "video": video,
        "tracks": [],
        "carry": carry or [],
        "failed": set(failed or ()),
        "ready": None,
        "inflight": None,
        "task": None,
    }


def _in_any_queue(path):
    for queue in db.values():
        for item in queue or []:
            if item.get("file") == path:
                return True
    return False


def _release_file(path):
    if not path or is_external_path(path) or _in_any_queue(path):
        return
    try:
        if os.path.exists(path):
            os.remove(path)
    except Exception:
        pass


def _discard_entry(entry):
    picked = entry.get("ready")
    entry["ready"] = None
    if picked:
        _release_file(picked[3])


def discard_prefetch(chat_id):
    entry = _cache.pop(chat_id, None)
    if entry:
        _discard_entry(entry)


_UNWANTED_WORDS = (
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
)


def _clean(chat_id, entry, tracks):
    out = []
    seen = {entry["source_id"]} | entry["failed"]
    src_title = entry.get("source_title") or ""
    for track in tracks or []:
        video_id = track.get("video_id")
        title = track.get("title") or ""
        duration = track.get("duration") or 0
        if not video_id or video_id in seen:
            continue
        if duration and (duration < 45 or duration > 900):
            continue
        t_lower = title.lower()
        if any(w in t_lower for w in _UNWANTED_WORDS):
            continue
        if src_title and is_same_song(src_title, title):
            continue
        if was_recently_played(chat_id, video_id, title):
            continue
        if any(is_same_song(title, t.get("title")) for t in out):
            continue
        seen.add(video_id)
        out.append(track)
    return out


async def _download(next_id, video, timeout):
    task = asyncio.ensure_future(
        YouTube.download(next_id, None, video=video, videoid=True)
    )
    try:
        return await asyncio.wait_for(asyncio.shield(task), timeout)
    except Exception:
        return None, False


async def _pick(chat_id, entry, video, timeout):
    src_title = entry.get("source_title") or ""
    while _cache.get(chat_id) is entry and entry["tracks"]:
        track = entry["tracks"].pop(0)
        next_id = track.get("video_id")
        title = track.get("title") or ""
        if not next_id or was_recently_played(chat_id, next_id, title):
            continue
        if src_title and is_same_song(src_title, title):
            continue
        entry["inflight"] = next_id
        thumb = asyncio.ensure_future(get_thumb(next_id))
        file_path, direct = await _download(next_id, video, timeout)
        entry["inflight"] = None
        if not file_path or not os.path.exists(file_path):
            entry["failed"].add(next_id)
            continue
        title = (title or "Autoplay Track").title()
        duration_min = seconds_to_min(track.get("duration") or 0)
        img = await thumb
        record_played(chat_id, next_id, title)
        return next_id, title, duration_min, file_path, direct, img
    return None


async def _fetch_tracks(chat_id, entry):
    try:
        fresh = await get_autoplay(
            entry["source_id"],
            timeout=API_TIMEOUT,
            retries=API_RETRIES,
            seed_id=get_seed(chat_id),
            source_title=entry.get("source_title") or "",
        )
    except Exception:
        fresh = []
    tracks = _clean(chat_id, entry, fresh)
    if not tracks:
        tracks = _clean(chat_id, entry, entry["carry"])
    entry["tracks"] = tracks


async def _prefetch(chat_id, entry):
    try:
        await _fetch_tracks(chat_id, entry)
        if _cache.get(chat_id) is not entry:
            return
        picked = await _pick(chat_id, entry, entry["video"], DOWNLOAD_TIMEOUT)
    except Exception:
        picked = None
    if picked and _cache.get(chat_id) is not entry:
        _release_file(picked[3])
        picked = None
    entry["ready"] = picked


def _is_youtube_id(value):
    return bool(value) and bool(_ID_RE.match(str(value)))


async def schedule_prefetch(chat_id, playing):
    if not playing or len(playing) != 1:
        return
    item = playing[0]
    if item.get("played", 0) < PREFETCH_AFTER:
        return
    source_id = item.get("vidid")
    if not _is_youtube_id(source_id):
        return
    queued = str(item.get("file"))
    if queued.startswith("live_") or queued == "index_url":
        return
    entry = _cache.get(chat_id)
    if entry and entry["source_id"] == source_id:
        return
    if not await is_autoplay(chat_id):
        return
    carry = list(entry["tracks"]) if entry else []
    if entry:
        _discard_entry(entry)
    video = str(item.get("streamtype")) == "video"
    source_title = item.get("title") or ""
    fresh = _new_entry(source_id, carry, video, source_title=source_title)
    _cache[chat_id] = fresh
    fresh["task"] = asyncio.ensure_future(_prefetch(chat_id, fresh))


async def try_autoplay(chat_id, popped) -> bool:
    if not popped:
        return False

    if not await is_autoplay(chat_id):
        return False

    source_id = popped.get("vidid")
    if not source_id or source_id in ("telegram", "soundcloud"):
        return False

    source_title = popped.get("title") or ""
    record_played(chat_id, source_id, source_title)
    original_chat_id = popped.get("chat_id") or chat_id
    if original_chat_id != chat_id:
        record_played(original_chat_id, source_id, source_title)
    video = str(popped.get("streamtype")) == "video"

    fetching_msg = None
    try:
        fetching_msg = await ayush.send_message(
            original_chat_id, "» <b>ᴀᴜᴛᴏᴩʟᴀʏ ғᴇᴛᴄʜɪɴɢ ɴᴇxᴛ sᴏɴɢ...</b>"
        )
    except Exception:
        fetching_msg = None

    entry = _cache.get(chat_id)
    picked = None
    leftover = []
    failed = set()

    if entry and entry["source_id"] == source_id:
        task = entry.get("task")
        if task is not None and not task.done():
            try:
                await asyncio.wait_for(asyncio.shield(task), READY_WAIT)
            except Exception:
                pass
        picked = entry.get("ready")
        entry["ready"] = None
        if picked and not os.path.exists(picked[3]):
            picked = None
        leftover = list(entry["tracks"])
        failed = set(entry["failed"])
        if entry.get("inflight"):
            failed.add(entry["inflight"])
    elif entry:
        _discard_entry(entry)
        leftover = list(entry["tracks"])

    if not picked:
        same_source = bool(entry) and entry["source_id"] == source_id
        entry = _new_entry(source_id, leftover, video, failed, source_title=source_title)
        _cache[chat_id] = entry
        if same_source:
            entry["tracks"] = _clean(chat_id, entry, leftover)
        if not entry["tracks"]:
            await _fetch_tracks(chat_id, entry)
        picked = await _pick(chat_id, entry, video, FALLBACK_TIMEOUT)

    if not picked:
        if fetching_msg:
            try:
                await fetching_msg.delete()
            except Exception:
                pass
        return False

    next_id, title, duration_min, file_path, direct, img = picked

    from KanhaMusic.core.call import Kanha

    try:
        await Kanha.skip_stream(chat_id, file_path, video=video)
    except Exception:
        if fetching_msg:
            try:
                await fetching_msg.delete()
            except Exception:
                pass
        return False

    if fetching_msg:
        try:
            await fetching_msg.delete()
        except Exception:
            pass

    record_played(chat_id, next_id, title)
    if original_chat_id != chat_id:
        record_played(original_chat_id, next_id, title)

    from KanhaMusic.utils.stream.seed import set_seed
    set_seed(chat_id, next_id)

    await put_queue(
        chat_id,
        original_chat_id,
        file_path if direct else f"vid_{next_id}",
        title,
        duration_min,
        "Autoplay",
        next_id,
        ayush.id,
        "video" if video else "audio",
    )

    language = await get_lang(original_chat_id)
    _ = get_string(language)

    run = await send_now_playing_rich(
        ayush,
        chat_id,
        original_chat_id,
        img,
        _["stream_1"].format(
            f"https://t.me/{ayush.username}?start=info_{next_id}",
            title[:23],
            duration_min,
            "Autoplay",
        ),
    )
    if db.get(chat_id):
        db[chat_id][0]["mystic"] = run
        db[chat_id][0]["markup"] = "stream"
    await autoplay_logs(
        original_chat_id,
        title,
        next_id,
        popped.get("title"),
        video,
    )
    return True