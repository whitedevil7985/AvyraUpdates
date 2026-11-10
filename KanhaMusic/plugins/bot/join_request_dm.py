import logging
from html import escape
from pathlib import Path

from pyrogram import filters
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

    # Telegram does not allow bots to start a private conversation.
    # If the user has never pressed /start, sending a DM will be rejected.
    bot_username = client.me.username
    start_url = f"https://t.me/{bot_username}?start=join_request"

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
            ],
            [
                InlineKeyboardButton(
                    "🤖 Open Bot",
                    url=start_url,
                    style=ButtonStyle.PRIMARY,
                )
            ],
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
        # Most commonly PeerIdInvalid / ChatWriteForbidden when the user
        # has not started the bot, blocked it, or has privacy restrictions.
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
