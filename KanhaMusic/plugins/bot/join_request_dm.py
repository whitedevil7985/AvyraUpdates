import logging
from html import escape

from pyrogram import filters
from pyrogram.handlers import ChatJoinRequestHandler
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from KanhaMusic import ayush

LOGGER = logging.getLogger(__name__)


async def send_join_request_dm(client, request):
    """DM users who have already opened the bot at least once."""
    user = request.from_user
    chat = request.chat

    # Telegram does not allow bots to start a private conversation.
    # If the user has never pressed /start, send_message will be rejected.
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
        [[InlineKeyboardButton("🤖 Open Bot", url=start_url)]]
    )

    try:
        await client.send_message(
            chat_id=user.id,
            text=text,
            reply_markup=keyboard,
            disable_web_page_preview=True,
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
