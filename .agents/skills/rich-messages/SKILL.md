---
name: rich-messages
description: >-
  Guide and standards for implementing and maintaining Telegram native Rich Messages
  (InputRichMessage, send_rich_message, edit_message_text, in-body <tg-button>, HTML
  tables, and details tags) in the Shruti / KanhaMusic bot codebase.
---

# Telegram Rich Messages in Shruti (KanhaMusic)

This skill provides step-by-step procedures and constraints for building and editing native Telegram Rich Messages using Kurigram (`pyrogram 2.2.26+`).

## Critical Kurigram Constraints

1. **Initial Message Must Be Rich**:
   A message originally sent via `message.reply_text()` (plain text) **cannot** be edited into a rich message later using `edit_text(rich_message=...)`. In this Kurigram build, editing a plain message with a rich message silently falls back to raw plain text or fails.
   **Always send the initial placeholder as a rich message**:
   ```python
   from pyrogram import types

   sent = await client.send_rich_message(
       chat_id=message.chat.id,
       rich_message=types.InputRichMessage(html="ᴘɪηɢɪηɢ… ᴘʟєᴧsє ᴡᴧɪᴛ…"),
       reply_parameters=types.ReplyParameters(message_id=message.id),
   )
   ```

2. **In-Body Buttons vs Inline Keyboards**:
   To render buttons directly attached to the rich message card without an external inline keyboard:
   - Use `<tg-button-row align="center">` and `<tg-button>` tags in the HTML body.
   - Do **NOT** pass `reply_markup` unless falling back.
   - Format:
     ```html
     <tg-button-row align="center">
       <tg-button type="url" style="primary" url="{url}" data="{url}">{label}</tg-button>
     </tg-button-row>
     ```
   - Supported styles: `primary`, `success`, `danger`.

3. **Quoted Anchor Links**:
   Pyrogram's `.mention` outputs unquoted HTML links like `<a href=tg://user?id=123>`.
   In MTProto Rich Message parsers (especially `<summary>` and headings), unquoted or `tg://` links can display as raw unrendered text.
   Always format bot/user links explicitly:
   ```python
   import html

   bot_link = f'<a href="https://t.me/{bot_username}">{html.escape(bot_name)}</a>'
   ```

4. **Supported Rich HTML Tags**:
   - Headers: `<h3>Heading</h3>`
   - Collapsible sections: `<details open><summary>Title</summary>Content</details>`
   - Formatted tables: `<table bordered striped><tr><th>Header</th></tr><tr><td>Row</td></tr></table>`
   - Images/banners: `<img src="https://..."/>`

## Standard Editing Flow

```python
card = (
    f'<img src="{IMG_URL}"/>'
    f"<h3>● Title: <code>{val}</code></h3>"
    f"<details open><summary>{bot_link} Details</summary>"
    f"<table bordered striped>"
    f"<tr><th>Metric</th><th>Value</th></tr>"
    f"<tr><td>Metric 1</td><td><code>Val 1</code></td></tr>"
    f"</table></details>"
)

btn = (
    '<tg-button-row align="center">'
    f'<tg-button type="url" style="primary" url="{support_url}" data="{support_url}">Support</tg-button>'
    "</tg-button-row>"
)

try:
    await sent.edit_text(rich_message=types.InputRichMessage(html=card + btn))
except Exception:
    # Fallback to standard inline markup if in-body buttons fail
    await sent.edit_text(
        rich_message=types.InputRichMessage(html=card),
        reply_markup=fallback_markup,
    )
```

## Helper Utilities

Use `KanhaMusic.utils.rich_message`:
- `send_rich(...)`: Safely sends initial placeholder or message.
- `edit_rich(...)`: Safely edits rich messages with fallback.
- `build_button(...)` / `build_button_row(...)`: Generates valid `<tg-button>` markup.
