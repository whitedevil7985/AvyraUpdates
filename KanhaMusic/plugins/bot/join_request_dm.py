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


async def _join_request_keyboard(client):
    me = await client.get_me()
    bot_url = f"https://t.me/{me.username}?start=join_request"

    return InlineKeyboardMarkup(
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
                    url=bot_url,
                    style=ButtonStyle.PRIMARY,
                )
            ],
        ]
    )


async def send_join_request_dm(client, request):
    """Send the join-request confirmation as a photo with action buttons."""
    user = request.from_user
    chat = request.chat

    group_name = escape(chat.title or "the group")
    first_name = escape(user.first_name or "there")

    message = (
        f"✨ <b>Welcome, {first_name}!</b>\n\n"
        f"Your request to join <b>{group_name}</b> has been received. 💫\n\n"
        "While you wait, tap <b>Open Bot</b> below to start the bot "
        "and explore more. ❤️"
    )

    try:
        keyboard = await _join_request_keyboard(client)

        if not REQUEST_BANNER.is_file():
            raise FileNotFoundError(f"Join request banner not found: {REQUEST_BANNER}")

        try:
            # This is a real JPEG optimized for Telegram photo uploads.
            await client.send_photo(
                chat_id=user.id,
                photo=str(REQUEST_BANNER),
                caption=message,
                reply_markup=keyboard,
            )
        except Exception as photo_error:
            LOGGER.warning(
                "Join-request photo failed for user_id=%s (%s: %s); "
                "sending text fallback",
                user.id,
                type(photo_error).__name__,
                photo_error,
            )
            await client.send_message(
                chat_id=user.id,
                text=message,
                reply_markup=keyboard,
            )

        LOGGER.info(
            "Join-request DM sent to user_id=%s for chat_id=%s",
            user.id,
            chat.id,
        )
    except Exception as exc:
        # Telegram may reject a DM if the user has never started the bot
        # or has blocked it. Do not let a failed DM stop the update handler.
        LOGGER.warning(
            "Could not DM join requester user_id=%s chat_id=%s (%s: %s)",
            user.id,
            chat.id,
            type(exc).__name__,
            exc,
        )


ayush.add_handler(
    ChatJoinRequestHandler(send_join_request_dm),
    group=0,
)
