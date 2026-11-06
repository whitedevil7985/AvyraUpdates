from pyrogram.enums import ParseMode

from KanhaMusic import ayush
from KanhaMusic.utils.database import is_on_off
from config import LOGGER_ID


async def play_logs(message, streamtype):
    if not LOGGER_ID:
        return
    if await is_on_off(2):
        if message.chat.id == LOGGER_ID:
            return

        chat_members = getattr(message.chat, "members_count", None)
        if not chat_members:
            try:
                chat_members = await ayush.get_chat_members_count(message.chat.id)
            except Exception:
                chat_members = "N/A"

        chat_title = message.chat.title or "Unknown Chat"
        chat_username = f"@{message.chat.username}" if message.chat.username else "Private Group"
        user_mention = message.from_user.mention if message.from_user else "Unknown User"
        user_id = message.from_user.id if message.from_user else "N/A"
        user_username = f"@{message.from_user.username}" if (message.from_user and message.from_user.username) else "No Username"

        try:
            query = message.text.split(None, 1)[1]
        except Exception:
            query = getattr(message, "text", "Direct / Inline Stream")

        logger_text = f"""
<b>{ayush.mention} ᴘʟᴀʏ ʟᴏɢ</b>

<b>ᴄʜᴀᴛ ɪᴅ :</b> <code>{message.chat.id}</code>
<b>ᴄʜᴀᴛ ɴᴀᴍᴇ :</b> {chat_title}
<b>ᴄʜᴀᴛ ᴜsᴇʀɴᴀᴍᴇ :</b> {chat_username}
<b>ᴄʜᴀᴛ ᴍᴇᴍʙᴇʀs :</b> <code>{chat_members}</code>

<b>ᴜsᴇʀ ɪᴅ :</b> <code>{user_id}</code>
<b>ɴᴀᴍᴇ :</b> {user_mention}
<b>ᴜsᴇʀɴᴀᴍᴇ :</b> {user_username}

<b>ǫᴜᴇʀʏ :</b> {query}
<b>sᴛʀᴇᴀᴍᴛʏᴘᴇ :</b> {streamtype}"""
        try:
            await ayush.send_message(
                chat_id=LOGGER_ID,
                text=logger_text,
                parse_mode=ParseMode.HTML,
                disable_web_page_preview=True,
            )
        except Exception:
            pass
        return


async def autoplay_logs(chat_id, title, video_id, previous_title, video=False):
    if not LOGGER_ID or not chat_id or chat_id == LOGGER_ID:
        return
    if not await is_on_off(2):
        return

    chat_title = "Unknown Chat"
    chat_username = "Private Group"
    chat_members = "N/A"
    try:
        chat = await ayush.get_chat(chat_id)
        if chat:
            chat_title = chat.title or "Unknown Chat"
            chat_username = f"@{chat.username}" if chat.username else "Private Group"
            chat_members = getattr(chat, "members_count", None)
            if not chat_members:
                try:
                    chat_members = await ayush.get_chat_members_count(chat_id)
                except Exception:
                    chat_members = "N/A"
    except Exception:
        try:
            chat_members = await ayush.get_chat_members_count(chat_id)
        except Exception:
            chat_members = "N/A"

    streamtype = "Autoplay Video" if video else "Autoplay Audio"
    logger_text = f"""
<b>{ayush.mention} ᴀᴜᴛᴏᴘʟᴀʏ ʟᴏɢ</b>

<b>ᴄʜᴀᴛ ɪᴅ :</b> <code>{chat_id}</code>
<b>ᴄʜᴀᴛ ɴᴀᴍᴇ :</b> {chat_title}
<b>ᴄʜᴀᴛ ᴜsᴇʀɴᴀᴍᴇ :</b> {chat_username}
<b>ᴄʜᴀᴛ ᴍᴇᴍʙᴇʀs :</b> <code>{chat_members}</code>

<b>ᴘʀᴇᴠɪᴏᴜs ᴛʀᴀᴄᴋ :</b> {previous_title or 'N/A'}
<b>ǫᴜᴇʀʏ :</b> <a href="https://www.youtube.com/watch?v={video_id}">{title}</a>
<b>sᴛʀᴇᴀᴍᴛʏᴘᴇ :</b> {streamtype}"""
    try:
        await ayush.send_message(
            chat_id=LOGGER_ID,
            text=logger_text,
            parse_mode=ParseMode.HTML,
            disable_web_page_preview=True,
        )
    except Exception:
        pass
