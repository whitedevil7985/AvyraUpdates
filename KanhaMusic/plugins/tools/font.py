import math

from pyrogram import filters
from pyrogram.enums import ButtonStyle
from pyrogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message

from config import BANNED_USERS
from KanhaMusic import ayush
from KanhaMusic.utils.fonts_data import Fonts

FONT_STYLES = {
    "typewriter": Fonts.typewriter,
    "outline": Fonts.outline,
    "serif": Fonts.serief,
    "bold_cool": Fonts.bold_cool,
    "cool": Fonts.cool,
    "small_cap": Fonts.smallcap,
    "script": Fonts.script,
    "script_bolt": Fonts.bold_script,
    "tiny": Fonts.tiny,
    "comic": Fonts.comic,
    "sans": Fonts.san,
    "slant_sans": Fonts.slant_san,
    "slant": Fonts.slant,
    "sim": Fonts.sim,
    "circles": Fonts.circles,
    "circle_dark": Fonts.dark_circle,
    "gothic": Fonts.gothic,
    "gothic_bolt": Fonts.bold_gothic,
    "cloud": Fonts.cloud,
    "happy": Fonts.happy,
    "sad": Fonts.sad,
    "special": Fonts.special,
    "squares": Fonts.square,
    "squares_bold": Fonts.dark_square,
    "andalucia": Fonts.andalucia,
    "manga": Fonts.manga,
    "stinky": Fonts.stinky,
    "bubbles": Fonts.bubbles,
    "underline": Fonts.underline,
    "ladybug": Fonts.ladybug,
    "rays": Fonts.rays,
    "birds": Fonts.birds,
    "slash": Fonts.slash,
    "stop": Fonts.stop,
    "skyline": Fonts.skyline,
    "arrows": Fonts.arrows,
    "qvnes": Fonts.rvnes,
    "strike": Fonts.strike,
    "frozen": Fonts.frozen,
}

PER_PAGE = 6
# Telegram limits callback_data to 64 bytes; keep the text part within this budget.
CB_TEXT_BYTES = 40


def _fit(text, budget=CB_TEXT_BYTES):
    raw = text.encode("utf-8")
    if len(raw) <= budget:
        return text
    return raw[:budget].decode("utf-8", errors="ignore")


@ayush.on_message(filters.command(["font"]) & ~BANNED_USERS)
async def font_command(c, message: Message):
    if message.reply_to_message:
        text = message.reply_to_message.text
    else:
        if len(message.command) < 2:
            return await message.reply("Please provide some text to style.")
        text = message.text.split(None, 1)[1]

    if not text:
        return await message.reply("Please provide some text to style.")

    keyboard = get_font_keyboard(0, text)
    await message.reply("Select a font style to apply:", reply_markup=keyboard)


def get_font_keyboard(page: int, text: str) -> InlineKeyboardMarkup:
    styles = list(FONT_STYLES.keys())
    total_pages = math.ceil(len(styles) / PER_PAGE)
    page = max(0, min(page, total_pages - 1))
    start = page * PER_PAGE
    end = start + PER_PAGE
    style_buttons = []

    short = _fit(text)
    preview_text = text.split()[0] if text.split() else text
    preview_text = preview_text[:8] if len(preview_text) > 8 else preview_text

    for i in range(start, min(end, len(styles)), 2):
        row = []
        for j in range(2):
            if i + j < len(styles):
                style = styles[i + j]
                callback_data = f"font+{style}+{page}+{short}"

                try:
                    styled_preview = FONT_STYLES[style](preview_text)
                    button_text = f"{styled_preview}"
                except Exception:
                    button_text = style.replace("_", " ").title()

                row.append(
                    InlineKeyboardButton(
                        button_text,
                        callback_data=callback_data,
                        style=ButtonStyle.PRIMARY,
                    )
                )
        if row:
            style_buttons.append(row)

    nav_buttons = []
    if total_pages > 1:
        nav_row = []
        if page > 0:
            nav_row.append(
                InlineKeyboardButton(
                    "⬅️ Back",
                    callback_data=f"font_nav+{page - 1}+{short}",
                    style=ButtonStyle.PRIMARY,
                )
            )
        if page < total_pages - 1:
            nav_row.append(
                InlineKeyboardButton(
                    "➡️ Next",
                    callback_data=f"font_nav+{page + 1}+{short}",
                    style=ButtonStyle.PRIMARY,
                )
            )

        if nav_row:
            nav_buttons.append(nav_row)

    nav_buttons.append(
        [
            InlineKeyboardButton(
                "❌ Close",
                callback_data="font_close",
                style=ButtonStyle.DANGER,
            )
        ]
    )

    style_buttons.extend(nav_buttons)
    return InlineKeyboardMarkup(style_buttons)


@ayush.on_callback_query(filters.regex(r"^font\+") & ~BANNED_USERS)
async def apply_font_style(c, query: CallbackQuery):
    try:
        parts = query.data.split("+", 3)
        if len(parts) < 4:
            await query.answer("Invalid data format!", show_alert=True)
            return

        style = parts[1]
        text = parts[3]

        if style in FONT_STYLES:
            styled = FONT_STYLES[style](text)
            await query.edit_message_text(styled)
        else:
            await query.answer("Unknown style!", show_alert=True)
    except Exception:
        await query.answer("Error applying style!", show_alert=True)


@ayush.on_callback_query(filters.regex(r"^font_nav\+") & ~BANNED_USERS)
async def paginate_fonts(c, query: CallbackQuery):
    try:
        parts = query.data.split("+", 2)
        if len(parts) < 3:
            await query.answer("Invalid navigation data!", show_alert=True)
            return

        page = int(parts[1])
        text = parts[2]

        keyboard = get_font_keyboard(page, text)
        await query.edit_message_reply_markup(reply_markup=keyboard)
        await query.answer()
    except Exception:
        await query.answer("Unable to paginate.", show_alert=True)


@ayush.on_callback_query(filters.regex(r"^font_close$") & ~BANNED_USERS)
async def close_fonts(c, query: CallbackQuery):
    try:
        await query.message.delete()
    except Exception:
        await query.message.edit_text("Font selector closed.")
        await query.answer()
