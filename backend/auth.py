"""
Developer auth via signed session cookie.
No database. Cookie format: dev:{nonce}:{hmac_sha256}
"""
from __future__ import annotations
import hashlib
import hmac
import os
import secrets

from fastapi import Request

ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "")
SESSION_SECRET = os.getenv("SESSION_SECRET", secrets.token_hex(32))


def _sign(value: str) -> str:
    return hmac.new(SESSION_SECRET.encode(), value.encode(), hashlib.sha256).hexdigest()


def make_token() -> str:
    nonce = secrets.token_hex(16)
    return f"dev:{nonce}:{_sign(f'dev:{nonce}')}"


def verify_token(token: str | None) -> bool:
    if not token:
        return False
    try:
        prefix, nonce, sig = token.split(":")
        if prefix != "dev":
            return False
        return hmac.compare_digest(_sign(f"dev:{nonce}"), sig)
    except Exception:
        return False


def is_dev(request: Request) -> bool:
    return verify_token(request.cookies.get("session"))
