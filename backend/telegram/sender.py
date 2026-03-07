"""
Telegram delivery helpers.
All functions accept optional token/chat_id overrides so they work for
both the developer's bot and user-supplied bots.
"""
from __future__ import annotations
import logging
import os

import requests

log    = logging.getLogger("tubescribe.telegram")
MAX_MB = float(os.getenv("TG_MAX_MB", "49"))

# Developer credentials (server-side only)
_DEV_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
_DEV_CHAT  = os.getenv("TELEGRAM_CHAT_ID")


def _api(method: str, token: str) -> str:
    return f"https://api.telegram.org/bot{token}/{method}"


def send_message(
    text:    str,
    token:   str | None = None,
    chat_id: str | None = None,
) -> None:
    t  = token   or _DEV_TOKEN
    ch = chat_id or _DEV_CHAT
    if not t or not ch:
        log.debug("Telegram not configured — skipping message.")
        return
    try:
        requests.post(
            _api("sendMessage", t),
            data={"chat_id": ch, "text": text[:4096], "parse_mode": "HTML"},
            timeout=30,
        )
    except Exception as exc:
        log.warning("sendMessage failed: %s", exc)


def send_document(
    caption:   str,
    pdf_bytes: bytes,
    filename:  str,
    token:     str | None = None,
    chat_id:   str | None = None,
) -> None:
    """Send raw PDF bytes as a Telegram document."""
    t  = token   or _DEV_TOKEN
    ch = chat_id or _DEV_CHAT
    if not t or not ch:
        log.debug("Telegram not configured — skipping document.")
        return

    size_mb = len(pdf_bytes) / (1024 * 1024)
    if size_mb > MAX_MB:
        send_message(
            f"⚠️ <b>PDF too large to send</b> ({size_mb:.1f} MB)\n"
            f"<code>{filename}</code>",
            token=t, chat_id=ch,
        )
        log.warning("PDF %s is %.1f MB — skipped (over limit).", filename, size_mb)
        return

    try:
        requests.post(
            _api("sendDocument", t),
            data={"chat_id": ch, "caption": caption[:1024]},
            files={"document": (filename, pdf_bytes, "application/pdf")},
            timeout=120,
        )
        log.info("TG ✓  %s  (%.1f MB)", filename, size_mb)
    except Exception as exc:
        log.error("sendDocument failed: %s", exc)
