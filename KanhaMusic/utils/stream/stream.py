import asyncio
import os
from random import randint
from typing import Union
from uuid import uuid4

import config
from KanhaMusic import Carbon, YouTube, ayush
from KanhaMusic.platforms.Youtube import get_stream, normalize_media_url
from KanhaMusic.core.call import Kanha
from KanhaMusic.misc import db
from KanhaMusic.utils.database import add_active_video_chat, is_active_chat
from KanhaMusic.utils.exceptions import AssistantErr
from KanhaMusic.utils.inline import close_markup
from KanhaMusic.utils.pastebin import KanhaBin
from KanhaMusic.utils.rich_stream import (
    release_mystic,
    send_now_playing_rich,
    send_queue_rich,
)
from KanhaMusic.utils.stream.queue import put_queue, put_queue_index
from KanhaMusic.utils.thumbnails import get_thumb


async def _fetch(_, chat_id, vidid, mystic, video):
    # Prepare a complete local media file before joining the voice chat.
    # Remote provider URLs can pass an HTTP probe but still be rejected later
    # by PyTgCalls with NoAudioSourceFound, which cannot be caught by join_call.
    try:
        file_path, _downloaded = await YouTube.download(
            vidid, mystic, videoid=True, video=True if video else None
        )
    except Exception:
        file_path = None

    if (
        not file_path
        or str(file_path).startswith(("http://", "https://"))
        or not os.path.isfile(file_path)
        or os.path.getsize(file_path) <= 10000
    ):
        raise AssistantErr(_["play_14"])

    # True means this exact prepared source can be retained in the queue.
    return file_path, True


async def _join_with_local_fallback(
    chat_id, original_chat_id, source, vidid, video, thumbnail=None
):
    """Try the fastest remote stream first, then fall back to a real local file."""
    try:
        await Kanha.join_call(
            chat_id, original_chat_id, source, video=video, image=thumbnail
        )
        return source, True
    except Exception:
        if not isinstance(source, str) or not source.startswith(("http://", "https://")):
            raise

    # The provider URL may pass probing but still fail when Telegram/FFmpeg
    # opens it. Download the track locally and retry instead of leaving the VC.
    local_path, _ = await YouTube.download(
        vidid, None, videoid=True, video=True if video else None
    )
    if (
        not local_path
        or str(local_path).startswith(("http://", "https://"))
        or not os.path.isfile(local_path)
    ):
        raise AssistantErr("Audio stream failed and local fallback download was unavailable.")

    await Kanha.join_call(
        chat_id, original_chat_id, local_path, video=video, image=thumbnail
    )
    return local_path, True


async def _announce_queue(_, chat_id, original_chat_id, mystic, title, duration_min, user_name):
    check = db.get(chat_id) or []
    position = len(check) - 1 if check else 0
    qid = uuid4().hex[:8]
    if check:
        check[-1]["qid"] = qid
    await send_queue_rich(
        ayush,
        chat_id,
        original_chat_id,
        _["queue_4"].format(position, title[:27], duration_min, user_name),
        qid,
        replace=mystic,
    )
    return position


async def stream(
    _,
    mystic,
    user_id,
    result,
    chat_id,
    user_name,
    original_chat_id,
    video: Union[bool, str] = None,
    streamtype: Union[bool, str] = None,
    spotify: Union[bool, str] = None,
    forceplay: Union[bool, str] = None,
):
    outcome = await _stream(
        _,
        mystic,
        user_id,
        result,
        chat_id,
        user_name,
        original_chat_id,
        video,
        streamtype,
        spotify,
        forceplay,
    )
    await release_mystic(mystic)
    return outcome


async def _stream(
    _,
    mystic,
    user_id,
    result,
    chat_id,
    user_name,
    original_chat_id,
    video: Union[bool, str] = None,
    streamtype: Union[bool, str] = None,
    spotify: Union[bool, str] = None,
    forceplay: Union[bool, str] = None,
):
    if not result:
        return
    if forceplay:
        await Kanha.force_stop_stream(chat_id)
    if streamtype == "playlist":
        msg = f"{_['play_19']}\n\n"
        count = 0
        for search in result:
            if int(count) == config.PLAYLIST_FETCH_LIMIT:
                continue
            try:
                (
                    title,
                    duration_min,
                    duration_sec,
                    thumbnail,
                    vidid,
                ) = await YouTube.details(search, False if spotify else True)
            except:
                continue
            if str(duration_min) == "None":
                continue
            if duration_sec > config.DURATION_LIMIT:
                continue
            if await is_active_chat(chat_id):
                await put_queue(
                    chat_id,
                    original_chat_id,
                    f"vid_{vidid}",
                    title,
                    duration_min,
                    user_name,
                    vidid,
                    user_id,
                    "video" if video else "audio",
                )
                position = len(db.get(chat_id) or []) - 1
                count += 1
                msg += f"{count}. {title[:70]}\n"
                msg += f"{_['play_20']} {position}\n\n"
            else:
                if not forceplay:
                    db[chat_id] = []
                status = True if video else None
                thumb_task = asyncio.ensure_future(get_thumb(vidid))
                file_path, direct = await _fetch(_, chat_id, vidid, mystic, video)
                file_path, direct = await _join_with_local_fallback(
                    chat_id, original_chat_id, file_path, vidid, status, thumbnail
                )
                await put_queue(
                    chat_id,
                    original_chat_id,
                    file_path if direct else f"vid_{vidid}",
                    title,
                    duration_min,
                    user_name,
                    vidid,
                    user_id,
                    "video" if video else "audio",
                    forceplay=forceplay,
                )
                img = await thumb_task
                run = await send_now_playing_rich(
                    ayush,
                    chat_id,
                    original_chat_id,
                    img,
                    _["stream_1"].format(
                        f"https://t.me/{ayush.username}?start=info_{vidid}",
                        title[:23],
                        duration_min,
                        user_name,
                    ),
                    replace=mystic,
                )
                if db.get(chat_id):
                    db[chat_id][0]["mystic"] = run
                    db[chat_id][0]["markup"] = "stream"
        if count == 0:
            return
        else:
            link = await KanhaBin(msg)
            lines = msg.count("\n")
            if lines >= 17:
                car = os.linesep.join(msg.split(os.linesep)[:17])
            else:
                car = msg
            carbon = await Carbon.generate(car, randint(100, 10000000))
            upl = close_markup(_)
            return await ayush.send_photo(
                original_chat_id,
                photo=carbon,
                caption=_["play_21"].format(position, link),
                reply_markup=upl,
            )
    elif streamtype == "youtube":
        link = result["link"]
        vidid = result["vidid"]
        title = (result["title"]).title()
        duration_min = result["duration_min"]
        thumbnail = result["thumb"]
        status = True if video else None
        thumb_task = (
            None
            if await is_active_chat(chat_id)
            else asyncio.ensure_future(get_thumb(vidid))
        )
        file_path, direct = await _fetch(_, chat_id, vidid, mystic, video)
        async with Kanha.chat_lock(chat_id):
            if await is_active_chat(chat_id):
                await put_queue(
                    chat_id,
                    original_chat_id,
                    file_path if direct else f"vid_{vidid}",
                    title,
                    duration_min,
                    user_name,
                    vidid,
                    user_id,
                    "video" if video else "audio",
                )
                await _announce_queue(
                    _, chat_id, original_chat_id, mystic, title, duration_min, user_name
                )
            else:
                if not forceplay:
                    db[chat_id] = []
                file_path, direct = await _join_with_local_fallback(
                    chat_id, original_chat_id, file_path, vidid, status, thumbnail
                )
                await put_queue(
                    chat_id,
                    original_chat_id,
                    file_path if direct else f"vid_{vidid}",
                    title,
                    duration_min,
                    user_name,
                    vidid,
                    user_id,
                    "video" if video else "audio",
                    forceplay=forceplay,
                )
                img = await (thumb_task if thumb_task else get_thumb(vidid))
                run = await send_now_playing_rich(
                    ayush,
                    chat_id,
                    original_chat_id,
                    img,
                    _["stream_1"].format(
                        f"https://t.me/{ayush.username}?start=info_{vidid}",
                        title[:23],
                        duration_min,
                        user_name,
                    ),
                    replace=mystic,
                )
                if db.get(chat_id):
                    db[chat_id][0]["mystic"] = run
                    db[chat_id][0]["markup"] = "stream"
    elif streamtype == "soundcloud":
        file_path = result["filepath"]
        title = result["title"]
        duration_min = result["duration_min"]
        if await is_active_chat(chat_id):
            await put_queue(
                chat_id,
                original_chat_id,
                file_path,
                title,
                duration_min,
                user_name,
                streamtype,
                user_id,
                "audio",
            )
            await _announce_queue(
                _, chat_id, original_chat_id, mystic, title, duration_min, user_name
            )
        else:
            if not forceplay:
                db[chat_id] = []
            await Kanha.join_call(chat_id, original_chat_id, file_path, video=None)
            await put_queue(
                chat_id,
                original_chat_id,
                file_path,
                title,
                duration_min,
                user_name,
                streamtype,
                user_id,
                "audio",
                forceplay=forceplay,
            )
            run = await send_now_playing_rich(
                ayush,
                chat_id,
                original_chat_id,
                config.SOUNCLOUD_IMG_URL,
                _["stream_1"].format(
                    config.SUPPORT_CHAT, title[:23], duration_min, user_name
                ),
                replace=mystic,
            )
            if db.get(chat_id):
                db[chat_id][0]["mystic"] = run
                db[chat_id][0]["markup"] = "tg"
    elif streamtype == "telegram":
        file_path = result["path"]
        link = result["link"]
        title = (result["title"]).title()
        duration_min = result["dur"]
        status = True if video else None
        if await is_active_chat(chat_id):
            await put_queue(
                chat_id,
                original_chat_id,
                file_path,
                title,
                duration_min,
                user_name,
                streamtype,
                user_id,
                "video" if video else "audio",
            )
            await _announce_queue(
                _, chat_id, original_chat_id, mystic, title, duration_min, user_name
            )
        else:
            if not forceplay:
                db[chat_id] = []
            await Kanha.join_call(chat_id, original_chat_id, file_path, video=status)
            await put_queue(
                chat_id,
                original_chat_id,
                file_path,
                title,
                duration_min,
                user_name,
                streamtype,
                user_id,
                "video" if video else "audio",
                forceplay=forceplay,
            )
            if video:
                await add_active_video_chat(chat_id)
            run = await send_now_playing_rich(
                ayush,
                chat_id,
                original_chat_id,
                config.TELEGRAM_VIDEO_URL if video else config.TELEGRAM_AUDIO_URL,
                _["stream_1"].format(link, title[:23], duration_min, user_name),
                replace=mystic,
            )
            if db.get(chat_id):
                db[chat_id][0]["mystic"] = run
                db[chat_id][0]["markup"] = "tg"
    elif streamtype == "live":
        link = result["link"]
        vidid = result["vidid"]
        title = (result["title"]).title()
        thumbnail = result["thumb"]
        duration_min = "Live Track"
        status = True if video else None
        if await is_active_chat(chat_id):
            await put_queue(
                chat_id,
                original_chat_id,
                f"live_{vidid}",
                title,
                duration_min,
                user_name,
                vidid,
                user_id,
                "video" if video else "audio",
            )
            await _announce_queue(
                _, chat_id, original_chat_id, mystic, title, duration_min, user_name
            )
        else:
            if not forceplay:
                db[chat_id] = []
            n, file_path = await YouTube.video(link)
            if n == 0:
                raise AssistantErr(_["str_3"])
            await Kanha.join_call(
                chat_id,
                original_chat_id,
                file_path,
                video=status,
                image=thumbnail if thumbnail else None,
            )
            await put_queue(
                chat_id,
                original_chat_id,
                f"live_{vidid}",
                title,
                duration_min,
                user_name,
                vidid,
                user_id,
                "video" if video else "audio",
                forceplay=forceplay,
            )
            img = await get_thumb(vidid)
            run = await send_now_playing_rich(
                ayush,
                chat_id,
                original_chat_id,
                img,
                _["stream_1"].format(
                    f"https://t.me/{ayush.username}?start=info_{vidid}",
                    title[:23],
                    duration_min,
                    user_name,
                ),
                replace=mystic,
            )
            if db.get(chat_id):
                db[chat_id][0]["mystic"] = run
                db[chat_id][0]["markup"] = "tg"
    elif streamtype == "index":
        link = result
        title = "ɪɴᴅᴇx ᴏʀ ᴍ3ᴜ8 ʟɪɴᴋ"
        duration_min = "00:00"
        if await is_active_chat(chat_id):
            await put_queue_index(
                chat_id,
                original_chat_id,
                "index_url",
                title,
                duration_min,
                user_name,
                link,
                "video" if video else "audio",
            )
            await _announce_queue(
                _, chat_id, original_chat_id, mystic, title, duration_min, user_name
            )
        else:
            if not forceplay:
                db[chat_id] = []
            await Kanha.join_call(
                chat_id,
                original_chat_id,
                link,
                video=True if video else None,
            )
            await put_queue_index(
                chat_id,
                original_chat_id,
                "index_url",
                title,
                duration_min,
                user_name,
                link,
                "video" if video else "audio",
                forceplay=forceplay,
            )
            run = await send_now_playing_rich(
                ayush,
                chat_id,
                original_chat_id,
                config.STREAM_IMG_URL,
                _["stream_2"].format(user_name),
                replace=mystic,
            )
            if db.get(chat_id):
                db[chat_id][0]["mystic"] = run
                db[chat_id][0]["markup"] = "tg"
