import html
import logging
from pyrogram import types
from pyrogram.errors import MessageNotModified

LOGGER = logging.getLogger(__name__)


def build_button(text: str, url: str, style: str = "primary") -> str:
    """Build a single in-body rich button (<tg-button>)."""
    escaped_url = html.escape(url, quote=True)
    escaped_text = html.escape(text)
    return (
        f'<tg-button type="url" style="{style}" '
        f'url="{escaped_url}" data="{escaped_url}">{escaped_text}</tg-button>'
    )


def build_button_row(buttons: list[str], align: str = "center") -> str:
    """Wrap one or more rich buttons in a row container."""
    if not buttons:
        return ""
    joined = " ".join(buttons)
    return f'<tg-button-row align="{align}">{joined}</tg-button-row>'


async def send_rich(
    client,
    chat_id: int | str,
    html_text: str,
    reply_markup=None,
    effect_id: int | None = None,
    reply_parameters: types.ReplyParameters | None = None,
) -> types.Message | None:
    """Send a native Telegram Rich Message via Kurigram.
    Ensures that placeholder messages sent this way can be later edited into rich cards.
    """
    rich = types.InputRichMessage(html=html_text)

    # Try with effect_id and reply_parameters
    kwargs = {}
    if effect_id is not None:
        kwargs["effect_id"] = effect_id
    if reply_parameters is not None:
        kwargs["reply_parameters"] = reply_parameters

    try:
        return await client.send_rich_message(
            chat_id=chat_id,
            rich_message=rich,
            reply_markup=reply_markup,
            **kwargs,
        )
    except Exception as ex:
        LOGGER.warning(f"send_rich with kwargs failed in {chat_id}: {ex!r}, retrying without optional kwargs...")

    # Fallback without effect or reply_parameters
    try:
        return await client.send_rich_message(
            chat_id=chat_id,
            rich_message=rich,
            reply_markup=reply_markup,
        )
    except Exception as ex:
        LOGGER.error(f"send_rich failed in {chat_id}: {ex!r}")
        return None


async def edit_rich(
    client,
    chat_id: int | str,
    message_id: int,
    html_text: str,
    reply_markup=None,
) -> types.Message | None:
    """Edit an existing message into a rich message."""
    try:
        return await client.edit_message_text(
            chat_id=chat_id,
            message_id=message_id,
            rich_message=types.InputRichMessage(html=html_text),
            reply_markup=reply_markup,
        )
    except MessageNotModified:
        return None
    except Exception as ex:
        LOGGER.warning(f"edit_rich failed for {message_id} in {chat_id}: {ex!r}")
        return None
