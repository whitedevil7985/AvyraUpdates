# Shruti Bot Agent Guidelines

## Telegram Rich Message Rules
When writing or modifying bot responses that use rich formatting:
1. **Always Use `types.InputRichMessage` with HTML**:
   - For commands using rich cards (`/ping`, `/alive`, `/stats`, etc.), use `types.InputRichMessage(html=...)`.
   - Never send a plain text placeholder (`reply_text`) if the message will subsequently be edited into a rich message. In Kurigram (`pyrogram 2.2.26`), plain messages cannot be transitioned to rich messages via `edit_text`. Send the initial message with `client.send_rich_message()`.

2. **In-Body Buttons**:
   - Use native in-body buttons `<tg-button-row align="center"><tg-button ...>Label</tg-button></tg-button-row>` inside the rich HTML.
   - Do not pass external `reply_markup` inline keyboards simultaneously unless explicitly handling an edit fallback.

3. **URL & Scheme Sanitization**:
   - Never use unquoted or raw `tg://user?id=...` schemes in rich message headings or `<summary>`.
   - Format user/bot links with standard quotes and HTTPS: `<a href="https://t.me/{username}">{name}</a>`.

4. **Multi-Source Audio Streaming Architecture**:
   - Primary: Inflex API (`http://187.127.120.51`, key: `INFLEX55158228D`)
   - Secondary: Ritesh API
   - Tertiary: NUB API / yt-dlp fallback
   - Do not alter this fallback sequence without explicit instruction.
