import random
import re
from urllib.parse import urlsplit

from pyrogram.enums import ButtonStyle
from pyrogram.types import InlineKeyboardButton

import config
from KanhaMusic import ayush

COLORS = (ButtonStyle.PRIMARY, ButtonStyle.SUCCESS, ButtonStyle.DANGER)


def _random_styles(count):
    while True:
        picks = [random.choice(COLORS) for _ in range(count)]
        if count < 3 or len(set(picks)) > 1:
            return picks


def _valid_button_url(value):
    """Normalize common Telegram link formats and validate the result."""
    if not isinstance(value, str):
        return None

    value = value.strip().strip("<>").strip()
    if not value or any(char.isspace() for char in value):
        return None

    # Accept @username and bare Telegram usernames as Telegram profile links.
    if value.startswith("@"):
        username = value[1:]
        if re.fullmatch(r"[A-Za-z0-9_]{5,32}", username):
            return f"https://t.me/{username}"
        return None

    # Normalize t.me links with or without a scheme.
    if value.startswith("t.me/"):
        value = f"https://{value}"
    elif value.startswith("www.t.me/"):
        value = f"https://{value}"
    elif "://" not in value and re.fullmatch(r"[A-Za-z0-9_]{5,32}", value):
        return f"https://t.me/{value}"

    # Add HTTPS to ordinary domains that were entered without a scheme.
    if "://" not in value:
        value = f"https://{value}"

    try:
        parsed = urlsplit(value)
        if parsed.scheme not in ("http", "https") or not parsed.hostname:
            return None
        if parsed.username or parsed.password:
            return None
        _ = parsed.port
    except (TypeError, ValueError):
        return None

    # Telegram button URLs must not contain control characters.
    if any(ord(char) < 32 for char in value):
        return None
    return value


def _bot_startgroup_url():
    username = getattr(ayush, "username", None)
    if not isinstance(username, str) or not username.strip():
        return None
    username = username.strip().lstrip("@")
    if not re.fullmatch(r"[A-Za-z0-9_]{5,32}", username):
        return None
    return f"https://t.me/{username}?startgroup=true"


def start_panel(_):
    buttons = []
    row = []
    start_url = _valid_button_url(_bot_startgroup_url())
    support_url = _valid_button_url(config.SUPPORT_CHAT)

    if start_url:
        row.append(
            InlineKeyboardButton(
                text=_["S_B_1"],
                url=start_url,
                style=random.choice(COLORS),
            )
        )
    if support_url:
        row.append(
            InlineKeyboardButton(
                text=_["S_B_2"],
                url=support_url,
                style=random.choice(COLORS),
            )
        )
    if row:
        buttons.append(row)
    return buttons


def private_panel(_):
    buttons = []
    start_url = _valid_button_url(_bot_startgroup_url())
    channel_url = _valid_button_url(config.SUPPORT_CHANNEL)
    chat_url = _valid_button_url(config.SUPPORT_CHAT)

    if start_url:
        buttons.append([
            InlineKeyboardButton(
                text=_["S_B_3"],
                url=start_url,
                style=random.choice(COLORS),
            )
        ])

    buttons.append([
        InlineKeyboardButton(
            text=_["S_B_4"],
            callback_data="settings_back_helper",
            style=random.choice(COLORS),
        )
    ])

    support_row = []
    if channel_url:
        support_row.append(
            InlineKeyboardButton(
                text=_["S_B_6"],
                url=channel_url,
                style=random.choice(COLORS),
            )
        )
    if chat_url:
        support_row.append(
            InlineKeyboardButton(
                text=_["S_B_2"],
                url=chat_url,
                style=random.choice(COLORS),
            )
        )
    if support_row:
        buttons.append(support_row)

    buttons.append([
        InlineKeyboardButton(
            text=_["S_B_5"],
            user_id=config.OWNER_ID,
            style=random.choice(COLORS),
        ),
    ])
    return buttons
