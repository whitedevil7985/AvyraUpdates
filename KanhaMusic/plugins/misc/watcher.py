from pyrogram import filters
from pyrogram.types import Message

from KanhaMusic import ayush
from KanhaMusic.core.call import Kanha

welcome = 20
close = 30


@ayush.on_message(filters.video_chat_started, group=welcome)
@ayush.on_message(filters.video_chat_ended, group=close)
async def welcome(_, message: Message):
    await Kanha.stop_stream_force(message.chat.id)
