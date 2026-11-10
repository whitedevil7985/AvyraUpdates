import logging
from html import escape
from pathlib import Path

from pyrogram.enums import ButtonStyle
from pyrogram.handlers import ChatJoinRequestHandler
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup

import config
from KanhaMusic import ayush

LOGGER = logging.getLogger(__name__)
REQUEST_BANNER = Path(__file__).resolve().parents[2] / "assets" / "join_request.jpg"


async def send_join_request_dm(client, request):
    """DM users who have already opened the bot at least once."""
    user = request.from_user
    chat = request.chat

    group_name = escape(chat.title or "the group")
    first_name = escape(user.first_name or "there")

    text = (
        f"✨ <b>Hey {first_name}!</b>\n\n"
        f"Your request to join <b>{group_name}</b> has been received. 💫\n\n"
        "The group admins will review your request. "
        "You'll be able to join once they approve it.\n\n"
        "Thanks for your interest! ❤️"
    )

    keyboard = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "🆘 Support",
                    url=config.SUPPORT_CHAT,
                    style=ButtonStyle.PRIMARY,
                ),
                InlineKeyboardButton(
                    "📢 Updates",
                    url=config.SUPPORT_CHANNEL,
                    style=ButtonStyle.SUCCESS,
                ),
            ]
        ]
    )

    try:
        await client.send_photo(
            chat_id=user.id,
            photo=str(REQUEST_BANNER),
            caption=text,
            reply_markup=keyboard,
        )
        LOGGER.info(
            "Join-request DM sent to user_id=%s for chat_id=%s",
            user.id,
            chat.id,
        )
    except Exception as exc:
        # Telegram may reject the DM if the user has never started the bot
        # or has blocked it. Log only the exception type, not private data.
        LOGGER.info(
            "Could not DM join requester user_id=%s chat_id=%s (%s)",
            user.id,
            chat.id,
            type(exc).__name__,
        )


ayush.add_handler(
    ChatJoinRequestHandler(send_join_request_dm),
    group=0,
)
