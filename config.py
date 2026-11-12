import re
from os import getenv

from dotenv import load_dotenv
from pyrogram import filters

load_dotenv()

# Get from my.telegram.org/app
API_ID = int(getenv("API_ID") or 0)
API_HASH = getenv("API_HASH", "")

# Get from @BotFather
BOT_TOKEN = getenv("BOT_TOKEN", "")

# Get from MongoDB Atlas
MONGO_DB_URI = getenv("MONGO_DB_URI", "")

DURATION_LIMIT_MIN = int(getenv("DURATION_LIMIT") or 6000)

LOGGER_ID = int(getenv("LOGGER_ID") or 0)
OWNER_ID = int(getenv("OWNER_ID") or 8617644501)

# Heroku App Name
HEROKU_APP_NAME = getenv("HEROKU_APP_NAME", "")

# Get from dashboard.heroku.com/account
HEROKU_API_KEY = getenv("HEROKU_API_KEY", "")



UPSTREAM_BRANCH = getenv("UPSTREAM_BRANCH", "main")

GIT_TOKEN = getenv("GIT_TOKEN")

# Get API Key from @SHRUTIAPIBOT

# ╔══════════════════════════════════════════════════════════════════════════════╗
# ║                     YOUTUBE API CONFIGURATION                                ║
# ║   Primary: Inflex API (@InflexAPIBot)                                         ║
# ║   Secondary: Ritesh API                                                      ║
# ║   Tertiary: NUB API                                                          ║
# ╚══════════════════════════════════════════════════════════════════════════════╝

# ──────────────────────────────────────────────────────────────────────────────
# [1] INFLEX API SETTINGS (@InflexAPIBot) [PRIMARY]
# ──────────────────────────────────────────────────────────────────────────────
# Inflex API Key:
INFLEX_API_KEY = getenv("INFLEX_API_KEY") or "INFLEX55158228D"

# Inflex API Base URL (Default: http://187.127.120.51):
_raw_inflex = getenv("INFLEX_API_URL") or "http://187.127.120.51"
_raw_inflex_cleaned = _raw_inflex.encode("ascii", "ignore").decode().strip().strip("'\"`")
_m_inflex = re.search(r'(https?://[^\s\'"<>]+|[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}(?::\d+)?[^\s\'"<>]*)', _raw_inflex_cleaned)
_domain_inflex = _m_inflex.group(1).strip() if _m_inflex else _raw_inflex_cleaned.strip()
if _domain_inflex and not _domain_inflex.startswith(("http://", "https://")):
    _domain_inflex = f"http://{_domain_inflex}"
INFLEX_API_URL = _domain_inflex.rstrip("/") if _domain_inflex else "http://187.127.120.51"

# ──────────────────────────────────────────────────────────────────────────────
# [2] RITESH API SETTINGS [SECONDARY]
# ──────────────────────────────────────────────────────────────────────────────
# Ritesh API Key:
RITESH_API_KEY = getenv("RITESH_API_KEY") or getenv("API_KEY") or "riteshfree7a13156394b9c397822c0006"
API_KEY = RITESH_API_KEY

# Ritesh API Base URL (Default: https://api.riteshyt.in):
RITESH_API_URL = getenv("RITESH_API_URL") or getenv("API_URL") or "https://api.riteshyt.in"
API_URL = RITESH_API_URL

# ──────────────────────────────────────────────────────────────────────────────
# [3] NUB API SETTINGS [TERTIARY]
# ──────────────────────────────────────────────────────────────────────────────
# NUB API Token / Key:
YTUBE_API_TOKEN = getenv("YTUBE_API_TOKEN") or getenv("YT_API_TOKEN") or "c8t5JHzIKs"
YT_API_TOKEN = YTUBE_API_TOKEN

# NUB API Base URL (Default: https://api.nubcoders.com):
_raw_base = getenv("YTUBE_API_BASE_URL") or getenv("NUB_YT_API_BASE_URL") or "https://api.nubcoders.com"
_raw_cleaned = _raw_base.encode("ascii", "ignore").decode().strip().strip("'\"`")
_m = re.search(r'(https?://[^\s\'"<>]+|[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}(?::\d+)?[^\s\'"<>]*)', _raw_cleaned)
_domain = _m.group(1).strip() if _m else _raw_cleaned.strip()
if _domain and not _domain.startswith(("http://", "https://")):
    _domain = f"https://{_domain}"
YTUBE_API_BASE_URL = _domain.rstrip("/") if _domain else "https://api.nubcoders.com"
NUB_YT_API_BASE_URL = YTUBE_API_BASE_URL

# ──────────────────────────────────────────────────────────────────────────────
# [4] YOUTUBE DATA API & COOKIES SETTINGS
# ──────────────────────────────────────────────────────────────────────────────
# YouTube Data API v3 Keys (comma-separated, optional):
YOUTUBE_API_KEYS = getenv("YOUTUBE_API_KEYS", "")

# Cookies and Cache:
# Heroku has no logged-in browser profile, so accept an exported Netscape
# cookies file as a base64 config var (recommended) or raw multiline content.
YT_COOKIES_FILE = getenv("YT_COOKIES_FILE", None)
YT_COOKIES_BASE64 = getenv("YT_COOKIES_BASE64", "")
YT_COOKIES_CONTENT = getenv("YT_COOKIES_CONTENT", "")
if YT_COOKIES_BASE64 or YT_COOKIES_CONTENT:
    import base64 as _base64
    import os as _os
    _cookie_path = YT_COOKIES_FILE or "/tmp/kanhamusic-youtube-cookies.txt"
    try:
        _cookie_bytes = (
            _base64.b64decode(YT_COOKIES_BASE64, validate=True)
            if YT_COOKIES_BASE64 else YT_COOKIES_CONTENT.encode("utf-8")
        )
        _cookie_text = _cookie_bytes.decode("utf-8-sig")
        if "Netscape HTTP Cookie File" not in _cookie_text[:256]:
            raise ValueError("YouTube cookies must be in Netscape cookies.txt format")
        _fd = _os.open(_cookie_path, _os.O_WRONLY | _os.O_CREAT | _os.O_TRUNC, 0o600)
        with _os.fdopen(_fd, "w", encoding="utf-8") as _cookie_file:
            _cookie_file.write(_cookie_text)
        YT_COOKIES_FILE = _cookie_path
    except Exception as _cookie_error:
        raise RuntimeError("Invalid YT_COOKIES_BASE64/YT_COOKIES_CONTENT; provide a valid Netscape cookies.txt export") from _cookie_error
COOKIES_FROM_BROWSER = getenv("COOKIES_FROM_BROWSER", None)
if COOKIES_FROM_BROWSER and not YT_COOKIES_FILE:
    import os as _os
    YT_COOKIES_FILE = _os.path.join(_os.getcwd(), "cookies.txt")
COOKIES_BOOTSTRAP_URL = getenv("COOKIES_BOOTSTRAP_URL", "https://www.youtube.com/watch?v=jNQXAC9IVRw")
try:
    COOKIES_REFRESH_HOURS = float(getenv("COOKIES_REFRESH_HOURS") or 6.0)
except ValueError:
    COOKIES_REFRESH_HOURS = 6.0
MAX_FILE_SIZE_BYTES = int(getenv("MAX_FILE_SIZE_BYTES") or (2 * 1024 * 1024 * 1024))

SUPPORT_CHANNEL = getenv(
    "SUPPORT_CHANNEL",
    "https://t.me/MeowCloner"
)

SUPPORT_CHAT = getenv(
    "SUPPORT_CHAT",
    "https://t.me/MeowClone"
)

AUTO_LEAVING_ASSISTANT = (
    getenv("AUTO_LEAVING_ASSISTANT") or "False"
).lower() == "true"

# Get from developer.spotify.com/dashboard
SPOTIFY_CLIENT_ID = getenv("SPOTIFY_CLIENT_ID")
SPOTIFY_CLIENT_SECRET = getenv("SPOTIFY_CLIENT_SECRET")

PLAYLIST_FETCH_LIMIT = int(
    getenv("PLAYLIST_FETCH_LIMIT") or 25
)

TG_AUDIO_FILESIZE_LIMIT = int(
    getenv("TG_AUDIO_FILESIZE_LIMIT") or 104857600
)

TG_VIDEO_FILESIZE_LIMIT = int(
    getenv("TG_VIDEO_FILESIZE_LIMIT") or 1073741824
)

# Get from @Sessionbbbot
STRING1 = getenv("STRING_SESSION")
STRING2 = getenv("STRING_SESSION2")
STRING3 = getenv("STRING_SESSION3")
STRING4 = getenv("STRING_SESSION4")
STRING5 = getenv("STRING_SESSION5")

BANNED_USERS = filters.user()
adminlist = {}
lyrical = {}
votemode = {}
autoclean = []
confirmer = {}

START_IMG_URL = getenv(
    "START_IMG_URL",
    "https://yukiapi.site/file/lLbJqLky"
)

PING_IMG_URL = getenv(
    "PING_IMG_URL",
    "https://yukiapi.site/file/lLbJqLky"
)

PLAYLIST_IMG_URL = "https://yukiapi.site/file/lLbJqLky"
STATS_IMG_URL = "https://yukiapi.site/file/lLbJqLky"
TELEGRAM_AUDIO_URL = "https://yukiapi.site/file/lLbJqLky"
TELEGRAM_VIDEO_URL = "https://yukiapi.site/file/lLbJqLky"
STREAM_IMG_URL = "https://yukiapi.site/file/lLbJqLky"
SOUNCLOUD_IMG_URL = "https://yukiapi.site/file/lLbJqLky"
YOUTUBE_IMG_URL = "https://yukiapi.site/file/lLbJqLky"
SPOTIFY_ARTIST_IMG_URL = "https://yukiapi.site/file/lLbJqLky"
SPOTIFY_ALBUM_IMG_URL = "https://yukiapi.site/file/lLbJqLky"
SPOTIFY_PLAYLIST_IMG_URL = "https://yukiapi.site/file/lLbJqLky"


def time_to_seconds(time):
    stringt = str(time)
    return sum(
        int(x) * 60 ** i
        for i, x in enumerate(reversed(stringt.split(":")))
    )


DURATION_LIMIT = int(
    time_to_seconds(f"{DURATION_LIMIT_MIN}:00")
)


if SUPPORT_CHANNEL:
    if not re.match("(?:http|https)://", SUPPORT_CHANNEL):
        raise SystemExit(
            "[ERROR] SUPPORT_CHANNEL url must start with https://"
        )

if SUPPORT_CHAT:
    if not re.match("(?:http|https)://", SUPPORT_CHAT):
        raise SystemExit(
            "[ERROR] SUPPORT_CHAT url must start with https://"
        )
