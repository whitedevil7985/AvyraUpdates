# KanhaMusic/plugins/admins/autoplay.py
from pyrogram import filters
from pyrogram.types import InlineKeyboardMarkup, Message

from KanhaMusic import ayush
from KanhaMusic.utils.database import autoplay_off, autoplay_on, is_autoplay
from KanhaMusic.utils.decorators.admins import ActualAdminCB, AdminRightsCheckAnyTime
from KanhaMusic.utils.formatters import with_autoplay_status
from KanhaMusic.utils.inline.play import autoplay_markup
from config import BANNED_USERS


def _autoplay_command_text(mode: bool) -> str:
    status = "ON ✅" if mode else "OFF ❌"
    return (
        "🔁 Autoplay\n\n"
        f"Current status: {status}\n\n"
        "When Autoplay is ON, the bot automatically queues and plays a related track "
        "once the current queue runs out, instead of leaving the voice chat."
    )


@ayush.on_message(filters.command(["autoplay"]) & filters.group & ~BANNED_USERS)
@AdminRightsCheckAnyTime
async def autoplay_command(client, message: Message, _, chat_id):
    mode = await is_autoplay(chat_id)
    markup = InlineKeyboardMarkup([autoplay_markup(chat_id, mode)])
    await message.reply_text(_autoplay_command_text(mode), reply_markup=markup)


@ayush.on_callback_query(filters.regex(r"^autoplay ") & ~BANNED_USERS)
@ActualAdminCB
async def autoplay_toggle(client, CallbackQuery, _):
    chat_id = int(CallbackQuery.data.split(None, 1)[1])
    mode = await is_autoplay(chat_id)

    if mode:
        await autoplay_off(chat_id)
        new_mode = False
        toast = "Autoplay turned OFF"
    else:
        await autoplay_on(chat_id)
        new_mode = True
        toast = "Autoplay turned ON"

    await CallbackQuery.answer(toast, show_alert=False)

    markup = CallbackQuery.message.reply_markup
    if markup:
        rows = []
        for row in markup.inline_keyboard:
            new_row = []
            for button in row:
                if button.callback_data and button.callback_data.startswith("autoplay "):
                    new_row.extend(autoplay_markup(chat_id, new_mode))
                else:
                    new_row.append(button)
            rows.append(new_row)
        markup = InlineKeyboardMarkup(rows)

    if CallbackQuery.message.photo:
        try:
            await CallbackQuery.message.edit_reply_markup(reply_markup=markup)
        except Exception:
            pass
    elif CallbackQuery.message.text and any(
        x in (CallbackQuery.message.text or "") for x in ["𝖲𝗍𝖺𝗋𝗍𝖾𝖽 𝖲𝗍𝗋𝖾𝖺𝗆𝗂𝗇𝗀", "Started Streaming", "❍"]
    ):
        try:
            await CallbackQuery.message.edit_reply_markup(reply_markup=markup)
        except Exception:
            pass
    else:
        try:
            await CallbackQuery.message.edit_text(
                _autoplay_command_text(new_mode), reply_markup=markup
            )
        except Exception:
            pass
