# Kurigram Rich Message Reference

## Overview
Kurigram (`pyrogram 2.2.26+`) supports MTProto Native Rich Messages via `types.InputRichMessage` and raw type `raw.types.InputRichMessageHTML`.

### Methods
- `client.send_rich_message(chat_id, rich_message=types.InputRichMessage(html=...), reply_parameters=..., effect_id=..., reply_markup=...)`
- `message.edit_text(rich_message=types.InputRichMessage(html=...), reply_markup=...)`
- `client.edit_message_text(chat_id, message_id, rich_message=types.InputRichMessage(html=...), reply_markup=...)`

### Supported Tags
- `<h3>...</h3>`: Large bold heading.
- `<details open><summary>Title</summary>...</details>`: Collapsible card block with clickable header.
- `<table bordered striped><tr><th>Header</th></tr><tr><td>Data</td></tr></table>`: Data table with striped rows.
- `<img src="https://..."/>`: Top banner image.
- `<tg-button-row align="center">`: Row container for in-body buttons.
- `<tg-button type="url" style="primary|success|danger" url="..." data="...">Label</tg-button>`: Rich button living inside the message card.
