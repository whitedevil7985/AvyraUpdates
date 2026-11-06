"""
Reference implementation for /ping rich message in Shruti
"""
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
from config import BANNED_USERS, PING_IMG_URL, SUPPORT_CHAT

MESSAGE_EFFECTS = [
    5107584321108051014,
    5159385139981059251,
    5104841245755180586,
    5046509860389126442,
]


@ayush.on_message(filters.command(["ping", "alive"]) & ~BANNED_USERS)
@language
async def ping_example(client, message: Message, _):
    start = time.time()
    is_private = message.chat.type == ChatType.PRIVATE
    kwargs = {"effect_id": random.choice(MESSAGE_EFFECTS)} if is_private else {}

    # Placeholder MUST be sent as a rich message
    sent = None
    try:
        sent = await client.send_rich_message(
            chat_id=message.chat.id,
            rich_message=types.InputRichMessage(html="ᴘɪηɢɪηɢ… ᴘʟєᴧsє ᴡᴧɪᴛ…"),
            reply_parameters=types.ReplyParameters(message_id=message.id),
            **kwargs,
        )
    except Exception:
        sent = await client.send_rich_message(
            chat_id=message.chat.id,
            rich_message=types.InputRichMessage(html="ᴘɪηɢɪηɢ… ᴘʟєᴧsє ᴡᴧɪᴛ…"),
        )

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
    bot_first_name = client.me.first_name if hasattr(client, "me") and client.me else (getattr(client, "name", "Bot") or "Bot")
    bot_link = f'<a href="https://t.me/{bot_username}">{html.escape(bot_first_name.strip())}</a>' if bot_username else f"<b>{html.escape(bot_first_name.strip())}</b>"

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

    support_btn = ""
    if SUPPORT_CHAT:
        support_url = html.escape(SUPPORT_CHAT, quote=True)
        support_btn = (
            '<tg-button-row align="center">'
            f'<tg-button type="url" style="primary" url="{support_url}" data="{support_url}">'
            "sυᴘᴘσʀᴛ ☏︎</tg-button>"
            "</tg-button-row>"
        )

    try:
        await sent.edit_text(
            rich_message=types.InputRichMessage(html=card + support_btn),
        )
    except Exception:
        await sent.edit_text(
            rich_message=types.InputRichMessage(html=card),
            reply_markup=supp_markup(_),
        )
