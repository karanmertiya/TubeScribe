"""Resolve a YouTube URL (single video or playlist) to a list of entries."""
from __future__ import annotations
import yt_dlp


def resolve(url: str) -> list[dict]:
    """
    Returns [{"url": str, "title": str}, …].
    Works for playlists, channels, and single videos.
    """
    ydl_opts = {"quiet": True, "extract_flat": True, "skip_download": True}
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)

    entries = info.get("entries") or [info]
    return [
        {
            "url":   f"https://www.youtube.com/watch?v={e['id']}",
            "title": e.get("title") or f"Video {i + 1}",
        }
        for i, e in enumerate(entries)
        if e and e.get("id")
    ]
