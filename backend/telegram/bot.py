"""
Telegram bot webhook handler.
DEVELOPER ONLY — only responds to the owner's chat ID.

Supported commands:
  /topdf <markdown>   — converts pasted markdown to a PDF and returns it immediately
"""
from __future__ import annotations
import datetime
import logging
import os

from backend.pdf import to_pdf
from .sender import send_document, send_message

log      = logging.getLogger("tubescribe.bot")
DEV_CHAT = os.getenv("TELEGRAM_CHAT_ID")


async def handle_update(update: dict) -> None:
    msg = update.get("message") or update.get("edited_message")
    if not msg:
        return

    chat_id = str(msg["chat"]["id"])
    text    = msg.get("text", "")

    # Hard gate: only respond to developer's own chat
    if chat_id != DEV_CHAT:
        send_message("⛔ This bot is private.", chat_id=chat_id)
        return

    if not text.startswith("/topdf"):
        # Ignore all other messages silently
        return

    md = text[len("/topdf"):].strip()

    if not md:
        send_message(
            "📝 <b>/topdf usage:</b>\n"
            "<code>/topdf ## My Notes\n- bullet one\n- bullet two</code>\n\n"
            "Paste any Markdown after the command — you'll get a PDF back instantly.",
            chat_id=chat_id,
        )
        return

    send_message("⏳ Rendering PDF…", chat_id=chat_id)

    try:
        pdf_bytes = to_pdf("Telegram Notes", md)
        ts        = datetime.datetime.now().strftime("%Y%m%d_%H%M")
        send_document("📄 Here's your PDF!", pdf_bytes, f"notes_{ts}.pdf", chat_id=chat_id)
    except Exception as exc:
        log.error("/topdf render failed: %s", exc)
        send_message(f"❌ PDF generation failed:\n<code>{exc}</code>", chat_id=chat_id)
