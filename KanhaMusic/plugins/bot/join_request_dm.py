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


def _join_request_keyboard():
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
            ]
        ]
    )


async def send_join_request_dm(client, request):
    """Send a join-request confirmation DM with a safe fallback."""
    user = request.from_user
    chat = request.chat

    group_name = escape(chat.title or "the group")
    first_name = escape(user.first_name or "there")

    message = (
        f"✨ <b>Hey {first_name}!</b>\n\n"
        f"Your request to join <b>{group_name}</b> has been received. 💫\n\n"
        "The group admins will review your request. "
        "You'll be able to join once they approve it.\n\n"
        "Thanks for your interest! ❤️"
    )
    keyboard = _join_request_keyboard()

    try:
        if not REQUEST_BANNER.is_file():
            raise FileNotFoundError(f"Join request banner not found: {REQUEST_BANNER}")

        # Upload as a document first only if photo processing fails. This avoids
        # Pyrogram/Pillow's ImageProcessFailed from preventing the DM entirely.
        try:
            await client.send_photo(
                chat_id=user.id,
                photo=str(REQUEST_BANNER),
                caption=message,
                reply_markup=keyboard,
            )
        except Exception as photo_error:
            LOGGER.warning(
                "Join-request photo failed for user_id=%s (%s: %s); "
                "trying document fallback",
                user.id,
                type(photo_error).__name__,
                photo_error,
            )
            try:
                await client.send_document(
                    chat_id=user.id,
                    document=str(REQUEST_BANNER),
                    caption=message,
                    reply_markup=keyboard,
                )
            except Exception as document_error:
                LOGGER.warning(
                    "Join-request banner upload also failed for user_id=%s "
                    "(%s: %s); sending text fallback",
                    user.id,
                    type(document_error).__name__,
                    document_error,
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
        # Telegram can reject DMs if the user has never started the bot
        # or has blocked it. Keep the handler alive and log the real reason.
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
