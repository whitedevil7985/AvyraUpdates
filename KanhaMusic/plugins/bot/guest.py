import re
import random

from pyrogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    InlineQueryResultArticle,
    InputTextMessageContent,
)
from pyrogram.enums import ButtonStyle

from KanhaMusic import ayush
from KanhaMusic.utils.fonts_data import Fonts

_STYLES = [ButtonStyle.PRIMARY, ButtonStyle.SUCCESS, ButtonStyle.DANGER]


def _rs():
    """Random style — har button alag colour."""
    return random.choice(_STYLES)


def font(text: str) -> str:
    if not text:
        return ""

    segments = re.split(r"(<[^>]+>)", text)
    styled_segments = []
    for segment in segments:
        if segment.startswith("<") and segment.endswith(">"):
            styled_segments.append(segment)
        else:
            styled_text = ""
            for char in segment:
                try:
                    if char.isupper():
                        styled_text += Fonts.serief(char)
                    elif char.islower():
                        styled_text += Fonts.smallcap(char)
                    else:
                        styled_text += char
                except Exception:
                    styled_text += char
            styled_segments.append(styled_text)

    return "".join(styled_segments)


@ayush.on_guest_message()
async def clone_guest_handler(c, m):
    bot_name_html = f'<a href="https://t.me/{c.me.username}">{font(c.me.first_name)}</a>'

    caption = (
        f"🎧 {bot_name_html} {font('is one of the best')}\n"
        f"{font('music + video streaming bots')}\n"
        f"{font('on telegram for your groups and channels')} ✨\n\n"
        f"➤ {font('just tap on the button below and')}\n"
        f"{font('add this bot to your group to play')}\n"
        f"{font('any of your favorite songs')} ❄️\n\n"
        f"✦ {font('your group')} • {font('your music')} • {font('your vibe')} 🚀"
    )

    keyboard = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    font("☊₊ Add me Baby ☊₊"),
                    url=f"https://t.me/{c.me.username}?startgroup=true",
                    style=_rs(),
                )
            ]
        ]
    )

    await c.answer_guest_query(
        m.guest_query_id,
        result=InlineQueryResultArticle(
            title=font("Lord Kanha"),
            input_message_content=InputTextMessageContent(caption),
            reply_markup=keyboard,
        ),
    )
