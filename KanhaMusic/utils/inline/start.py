import random

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


def start_panel(_):
    s = _random_styles(2)
    buttons = [
        [
            InlineKeyboardButton(
                text=_["S_B_1"],
                url=f"https://t.me/{ayush.username}?startgroup=true",
                style=s[0],
            ),
            InlineKeyboardButton(
                text=_["S_B_2"],
                url=config.SUPPORT_CHAT,
                style=s[1],
            ),
        ],
    ]
    return buttons


def private_panel(_):
    s = _random_styles(5)
    buttons = [
        [
            InlineKeyboardButton(
                text=_["S_B_3"],
                url=f"https://t.me/{ayush.username}?startgroup=true",
                style=s[0],
            )
        ],
        [
            InlineKeyboardButton(
                text=_["S_B_4"],
                callback_data="settings_back_helper",
                style=s[1],
            )
        ],
        [
            InlineKeyboardButton(
                text=_["S_B_6"],
                url=config.SUPPORT_CHANNEL,
                style=s[2],
            ),
            InlineKeyboardButton(
                text=_["S_B_2"],
                url=config.SUPPORT_CHAT,
                style=s[3],
            ),
        ],
        [
            InlineKeyboardButton(
                text="sσυꝛᴄє",
                url="https://github.com/Oyekanhaa/KanhaMusic/fork",
                style=random.choice(COLORS),
            ),
            InlineKeyboardButton(
                text=_["S_B_5"],
                user_id=config.OWNER_ID,
                style=s[4],
            ),
        ],
    ]
    return buttons
