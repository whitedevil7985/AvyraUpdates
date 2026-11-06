import html
import random
import time
import psutil

from pyrogram import filters, types
from pyrogram.enums import ChatType
from pyrogram.types import Message

from KanhaMusic import ayush
from KanhaMusic.core.call import Kanha
from KanhaMusic.misc import _boot_
from KanhaMusic.utils.decorators.language import language
from KanhaMusic.utils.inline import supp_markup
from config import BANNED_USERS, PING_IMG_URL, SUPPORT_CHANNEL, SUPPORT_CHAT

MESSAGE_EFFECTS = [
    5107584321108051014,
    5159385139981059251,
    5104841245755180586,
    5046509860389126442,
]


@ayush.on_message(filters.command(["ping", "alive"]) & ~BANNED_USERS)
@language
async def ping_com(client, message: Message, _):
    start = time.time()
    is_private = message.chat.type == ChatType.PRIVATE
    kwargs = {"effect_id": random.choice(MESSAGE_EFFECTS)} if is_private else {}

    # Placeholder must be sent as a rich message too:
    # a message that starts out plain cannot be edited into a rich message later in Kurigram.
    sent = None
    try:
        sent = await client.send_rich_message(
            chat_id=message.chat.id,
            rich_message=types.InputRichMessage(html="ᴘɪηɢɪηɢ… ᴘʟєᴧsє ᴡᴧɪᴛ…"),
            reply_parameters=types.ReplyParameters(message_id=message.id),
            **kwargs,
        )
    except Exception:
        try:
            sent = await client.send_rich_message(
                chat_id=message.chat.id,
                rich_message=types.InputRichMessage(html="ᴘɪηɢɪηɢ… ᴘʟєᴧsє ᴡᴧɪᴛ…"),
                **kwargs,
            )
        except Exception:
            try:
                sent = await client.send_rich_message(
                    chat_id=message.chat.id,
                    rich_message=types.InputRichMessage(html="ᴘɪηɢɪηɢ… ᴘʟєᴧsє ᴡᴧɪᴛ…"),
                )
            except Exception:
                sent = await message.reply_text("ᴘɪηɢɪηɢ… ᴘʟєᴧsє ᴡᴧɪᴛ…")

    get_time = lambda s: (lambda r: (f"{r[-1]}, " if r[-1][:-4] != "0" else "") + ":".join(reversed(r[:-1])))([f"{v}{u}" for v, u in zip([s % 60, (s // 60) % 60, (s // 3600) % 24, s // 86400], ["s", "m", "h", "days"])])
    uptime = get_time(int(time.time() - _boot_))
    latency = round((time.time() - start) * 1000, 2)

    try:
        pytgping = await Kanha.ping()
    except Exception:
        pytgping = 0

    cpu = psutil.cpu_percent(interval=0)
    ram = psutil.virtual_memory().percent
    disk = psutil.disk_usage("/").percent

    bot_username = getattr(client, "username", None) or getattr(ayush, "username", None)
    if not bot_username and hasattr(client, "me") and client.me:
        bot_username = client.me.username

    bot_first_name = (
        client.me.first_name if hasattr(client, "me") and client.me and client.me.first_name
        else (getattr(client, "name", "Bot") or getattr(ayush, "name", "Bot") or "Bot")
    )
    bot_id = getattr(client, "id", None) or (client.me.id if hasattr(client, "me") and client.me else None)
    bot_url = f"https://t.me/{bot_username}" if bot_username else (f"tg://user?id={bot_id}" if bot_id else "#")
    bot_link = f'<a href="{bot_url}">{html.escape(bot_first_name.strip())}</a>'

    img_tag = f'<img src="{PING_IMG_URL}"/>' if PING_IMG_URL else ""
    card = (
        f"{img_tag}"
        f"<h3>● 𝐏σηɢ: <code>{latency}ms</code></h3>"
        f"<details open><summary>{bot_link} 𝐒ᴛᴧᴛɪsᴛɪᴄs</summary>"
        f"<table bordered striped>"
        f"<tr><th>𝐌єᴛꝛɪᴄ</th><th>𝐕ᴧʟυє</th></tr>"
        f"<tr><td>𝐔ᴘᴛɪϻє</td><td><code>{uptime}</code></td></tr>"
        f"<tr><td>𝐂𝐏𝐔</td><td><code>{cpu}%</code></td></tr>"
        f"<tr><td>𝐑𝐀𝐌</td><td><code>{ram}%</code></td></tr>"
        f"<tr><td>𝐃ɪsᴋ</td><td><code>{disk}%</code></td></tr>"
        f"<tr><td>𝐏ʏ𝐓ɢ𝐂ᴧʟʟs</td><td><code>{pytgping}ms</code></td></tr>"
        f"</table></details>"
    )

    btn_support = (
        f'<tg-button type="url" style="primary" url="{SUPPORT_CHAT}" data="{SUPPORT_CHAT}">SUPPORT</tg-button>'
        if SUPPORT_CHAT else ""
    )
    btn_channel = (
        f'<tg-button type="url" style="primary" url="{SUPPORT_CHANNEL}" data="{SUPPORT_CHANNEL}">UPDATES</tg-button>'
        if SUPPORT_CHANNEL else ""
    )
    support_btn = (
        f'<tg-button-row align="center">{btn_support} {btn_channel}</tg-button-row>'
        if (btn_support or btn_channel) else ""
    )

    try:
        await sent.edit_text(
            rich_message=types.InputRichMessage(html=card + support_btn),
        )
    except Exception:
        # Fallback if Telegram rejects in-body button
        try:
            await sent.edit_text(
                rich_message=types.InputRichMessage(html=card),
                reply_markup=supp_markup(_),
            )
        except Exception:
            await sent.edit_text(
                _["ping_2"].format(latency, bot_link, uptime, f"{ram}%", f"{cpu}%", f"{disk}%", pytgping),
                reply_markup=supp_markup(_),
            )
