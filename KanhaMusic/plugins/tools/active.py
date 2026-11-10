import asyncio
import html
import logging
import time

from pyrogram import filters
from pyrogram.enums import ParseMode
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message

from KanhaMusic import ayush
from KanhaMusic.misc import SUDOERS
from KanhaMusic.utils.database import get_active_chats, get_active_video_chats

LOGGER = logging.getLogger(__name__)
REFRESH_COOLDOWN = 5
_last_refresh = {}


async def _active_ids(kind):
    # Read the tracker directly. Chat metadata is optional and must never
    # decide whether a currently tracked voice chat is counted.
    ids = await (get_active_chats() if kind == "vc" else get_active_video_chats())
    return sorted(set(int(chat_id) for chat_id in (ids or [])))


async def _chat_line(index, chat_id):
    try:
        chat = await ayush.get_chat(chat_id)
        title = html.escape((getattr(chat, "title", None) or str(chat_id)).strip())
        username = getattr(chat, "username", None)
        if username:
            title = f'<a href="https://t.me/{html.escape(username)}">{title}</a>'
    except Exception as exc:
        LOGGER.warning("Active chat title lookup failed for %s: %s", chat_id, exc)
        title = f"Chat {chat_id}"
    return f"{index}. {title} <code>{chat_id}</code>"


async def _render(kind, message):
    started = time.monotonic()
    chat_ids = await _active_ids(kind)
    label = "voice chats" if kind == "vc" else "video chats"

    if not chat_ids:
        text = f"<b>Active {label}: 0</b>\n\nNo sessions are currently tracked by this bot process."
    else:
        lines = await asyncio.gather(
            *(_chat_line(i, chat_id) for i, chat_id in enumerate(chat_ids, 1))
        )
        text = (
            f"<b>Active {label}: {len(chat_ids)}</b>\n\n"
            + "\n".join(lines[:60])
        )
        if len(lines) > 60:
            text += f"\n\nAnd {len(lines) - 60} more chats."

    text += f"\n\n<code>Fetched in {time.monotonic() - started:.2f}s</code>"
    keyboard = InlineKeyboardMarkup(
        [[
            InlineKeyboardButton("🔄 Refresh", callback_data=f"ACTIVE r|{kind}"),
            InlineKeyboardButton("✖️ Close", callback_data="ACTIVE x"),
        ]]
    )
    return await message.edit_text(
        text,
        reply_markup=keyboard,
        parse_mode=ParseMode.HTML,
    )


async def _launch(message: Message, kind):
    loading = await message.reply_text("⏳ Fetching active voice chats...")
    try:
        await _render(kind, loading)
    except Exception as exc:
        LOGGER.exception("Active %s chat report failed", kind)
        # Show the actual failure to the authorized operator instead of
        # masking every exception behind the same generic message.
        detail = html.escape(f"{type(exc).__name__}: {exc}")[:700]
        try:
            await loading.edit_text(
                f"<b>Active chat report failed.</b>\n<code>{detail}</code>",
                parse_mode=ParseMode.HTML,
            )
        except Exception:
            pass


@ayush.on_message(
    filters.command(["activevc", "activevoice", "activechats", "avc", "ac"])
    & SUDOERS
)
async def activevc(client, message: Message):
    await _launch(message, "vc")


@ayush.on_message(
    filters.command(["activev", "activevideo", "activevideos", "avideo", "av"])
    & SUDOERS
)
async def activevi_(client, message: Message):
    await _launch(message, "video")


@ayush.on_callback_query(filters.regex(r"^ACTIVE ") & SUDOERS)
async def active_callback(client, cq):
    action, _, kind = cq.data.split(" ", 1)[1].partition("|")
    if action == "x":
        await cq.answer()
        return await cq.message.delete()
    if action != "r" or kind not in ("vc", "video"):
        return await cq.answer("Invalid refresh request.", show_alert=True)

    key = (cq.message.chat.id, cq.message.id)
    now = time.monotonic()
    if now - _last_refresh.get(key, 0) < REFRESH_COOLDOWN:
        return await cq.answer("Please wait a few seconds before refreshing.", show_alert=False)
    _last_refresh[key] = now
    await cq.answer("Refreshing...")
    try:
        await _render(kind, cq.message)
    except Exception as exc:
        LOGGER.exception("Active %s chat refresh failed", kind)
        detail = html.escape(f"{type(exc).__name__}: {exc}")[:700]
        try:
            await cq.message.edit_text(
                f"<b>Active chat refresh failed.</b>\n<code>{detail}</code>",
                parse_mode=ParseMode.HTML,
            )
        except Exception:
            pass
