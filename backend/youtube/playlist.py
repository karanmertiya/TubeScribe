"""Resolve a YouTube URL (single video or playlist) to a list of entries."""
from __future__ import annotations
import os
import tempfile
import yt_dlp

_COOKIES_FILE = os.getenv("YOUTUBE_COOKIES_FILE")
_COOKIES_TEXT = os.getenv("YOUTUBE_COOKIES")


def _cookies_path() -> str | None:
    if _COOKIES_FILE and os.path.exists(_COOKIES_FILE):
        return _COOKIES_FILE
    if _COOKIES_TEXT:
        tmp = tempfile.NamedTemporaryFile(
            mode="w", suffix=".txt", delete=False, encoding="utf-8"
        )
        tmp.write(_COOKIES_TEXT)
        tmp.close()
        return tmp.name
    return None


def resolve(url: str) -> list[dict]:
    """
    Returns [{"url": str, "title": str}, …].
    Works for playlists, channels, and single videos.
    """
    opts: dict = {
        "quiet":        True,
        "extract_flat": True,
        "skip_download": True,
    }
    cookies = _cookies_path()
    if cookies:
        opts["cookiefile"] = cookies

    cookies_tmp = cookies if (_COOKIES_TEXT and cookies != _COOKIES_FILE) else None
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=False)
    finally:
        if cookies_tmp:
            try:
                os.remove(cookies_tmp)
            except OSError:
                pass

    entries = info.get("entries") or [info]
    return [
        {
            "url":   f"https://www.youtube.com/watch?v={e['id']}",
            "title": e.get("title") or f"Video {i + 1}",
        }
        for i, e in enumerate(entries)
        if e and e.get("id")
    ]
