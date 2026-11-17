import random
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
    """Return a Telegram-safe absolute HTTP(S) URL, or None."""
    if not isinstance(value, str):
        return None
    value = value.strip()
    if not value or any(char.isspace() for char in value):
        return None
    try:
        parsed = urlsplit(value)
        if parsed.scheme not in ("http", "https") or not parsed.hostname:
            return None
        # Accessing port also validates malformed port values.
        _ = parsed.port
    except (TypeError, ValueError):
        return None
    return value


def _bot_startgroup_url():
    username = getattr(ayush, "username", None)
    if not isinstance(username, str) or not username.strip():
        return None
    username = username.strip().lstrip("@")
    if not username or any(char.isspace() for char in username):
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
