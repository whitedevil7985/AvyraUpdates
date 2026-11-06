import re

MAX_HISTORY = 150

_history = {}

_BUZZWORDS_REGEX = re.compile(
    r"\b(official|video|audio|lyric|lyrics|lyrical|full song|song|songs|remix|lofi|slowed|reverb|teaser|trailer|4k|hd|8k|version|full|visualizer|prod|original|soundtrack|ost|theme|clean|edit|music|chapter|part|exclusive|promo|motion poster|cover|mashup|unplugged|acoustic|instrumental|special|extended|hd video)\b",
    re.IGNORECASE,
)

_LABELS = {
    "tseries", "t-series", "sony music", "zee music", "tips", "yrf",
    "speed records", "geet mp3", "white hill", "dharma", "vevo",
    "saregama", "eros now", "desi music factory", "aditya music",
    "lahari music", "svf", "dm - desi music factory", "apna punjab",
    "shemaroo", "venus", "times music", "bongo", "svf music"
}


def extract_core_song(title: str) -> str:
    """Extracts the pure primary song name from any YouTube title."""
    if not title:
        return ""
    # Strip brackets & parentheses content: (Lyrical Video), [Official 4K], etc.
    t = re.sub(r"\[.*?\]|\(.*?\)", " ", title).strip()

    # Split by common delimiters used in song titles
    parts = re.split(r"\s*[|\-–—:/•~]\s*", t)

    for p in parts:
        p_clean = _BUZZWORDS_REGEX.sub(" ", p)
        p_clean = re.sub(r"[^a-zA-Z0-9\s]", " ", p_clean)
        words = [w.lower() for w in p_clean.split() if len(w) >= 2]
        # Ignore if segment is just a music label
        if words and not any(lbl in " ".join(words) for lbl in _LABELS):
            return " ".join(words)

    # Fallback to general cleaned title
    t_clean = _BUZZWORDS_REGEX.sub(" ", t)
    t_clean = re.sub(r"[^a-zA-Z0-9\s]", " ", t_clean)
    return " ".join([w.lower() for w in t_clean.split() if len(w) >= 2])


def clean_song_title(title: str) -> str:
    return extract_core_song(title)


def is_same_song(title1: str, title2: str) -> bool:
    """Checks if two titles represent the same song (including remixes, lyrics, 4K, etc.)."""
    if not title1 or not title2:
        return False
    c1 = extract_core_song(title1)
    c2 = extract_core_song(title2)
    if not c1 or not c2:
        return False
    if c1 == c2:
        return True
    # Substring match for compound titles
    if len(c1) >= 4 and len(c2) >= 4:
        if c1 in c2 or c2 in c1:
            return True
    # Word set overlap: e.g. "apna bana le" vs "apna bana"
    w1 = set(c1.split())
    w2 = set(c2.split())
    if w1 and w2 and len(w1 & w2) >= 2 and (w1.issubset(w2) or w2.issubset(w1)):
        return True
    return False


def record_played(chat_id, video_id, title=None):
    if not video_id and not title:
        return
    data = _history.setdefault(chat_id, {"ids": [], "titles": []})
    if video_id:
        video_id = str(video_id)
        if video_id in data["ids"]:
            data["ids"].remove(video_id)
        data["ids"].append(video_id)
        if len(data["ids"]) > MAX_HISTORY:
            del data["ids"][: len(data["ids"]) - MAX_HISTORY]

    if title:
        if title in data["titles"]:
            data["titles"].remove(title)
        data["titles"].append(title)
        if len(data["titles"]) > MAX_HISTORY:
            del data["titles"][: len(data["titles"]) - MAX_HISTORY]


def was_recently_played(chat_id, video_id, title=None) -> bool:
    data = _history.get(chat_id)
    if not data:
        return False

    if video_id and str(video_id) in data.get("ids", []):
        return True

    if title:
        for past in data.get("titles", []):
            if is_same_song(title, past):
                return True

    return False


def clear_history(chat_id):
    _history.pop(chat_id, None)
