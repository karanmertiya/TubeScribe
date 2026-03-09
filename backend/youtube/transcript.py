"""Download and clean VTT subtitles from a single YouTube video."""
from __future__ import annotations
import logging
import os
import tempfile
from io import StringIO

import webvtt
import yt_dlp

log = logging.getLogger("tubescribe.youtube")

# Path to a cookies.txt file — can be set via env var or a mounted file
_COOKIES_FILE = os.getenv("YOUTUBE_COOKIES_FILE")   # path to file on disk
_COOKIES_TEXT = os.getenv("YOUTUBE_COOKIES")         # raw cookie file content


def _cookies_path() -> str | None:
    """
    Return a usable cookies file path, or None.
    Priority:
      1. YOUTUBE_COOKIES_FILE — direct path to an existing file
      2. YOUTUBE_COOKIES      — raw Netscape cookie file content stored as env var,
                                written to a temp file each call
    """
    if _COOKIES_FILE and os.path.exists(_COOKIES_FILE):
        return _COOKIES_FILE
    if _COOKIES_TEXT:
        # Write cookie content to a temp file (deleted by caller)
        tmp = tempfile.NamedTemporaryFile(
            mode="w", suffix=".txt", delete=False, encoding="utf-8"
        )
        tmp.write(_COOKIES_TEXT)
        tmp.close()
        return tmp.name
    return None


def _base_ydl_opts(extra: dict | None = None) -> dict:
    """Base yt-dlp options, with cookies injected if available."""
    opts: dict = {
        "quiet":         True,
        "skip_download": True,
    }
    cookies = _cookies_path()
    if cookies:
        opts["cookiefile"] = cookies
        log.debug("yt-dlp: using cookies from %s", cookies)
    else:
        log.debug("yt-dlp: no cookies configured")
    if extra:
        opts.update(extra)
    return opts


def extract(video_url: str, temp_dir: str) -> tuple[str, str]:
    """
    Returns (title, clean_transcript).
    Raises FileNotFoundError if no English subtitles exist.
    Raises ValueError if the transcript is empty after cleaning.
    """
    base = os.path.join(temp_dir, "video")
    ydl_opts = _base_ydl_opts({
        "writesubtitles":    True,
        "writeautomaticsub": True,
        "subtitleslangs":    ["en"],
        "subtitlesformat":   "vtt",
        "skip_download":     True,
        "outtmpl":           base,
    })

    cookies_tmp = ydl_opts.get("cookiefile") if _COOKIES_TEXT else None

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info  = ydl.extract_info(video_url, download=False)
            title = info.get("title", "Untitled Video")
    finally:
        # Clean up temp cookie file if we wrote one
        if cookies_tmp and cookies_tmp != _COOKIES_FILE:
            try:
                os.remove(cookies_tmp)
            except OSError:
                pass

    vtt_path = f"{base}.en.vtt"
    if not os.path.exists(vtt_path):
        raise FileNotFoundError(f"No English subtitles for: {title!r}")

    with open(vtt_path, "r", encoding="utf-8") as fh:
        captions = webvtt.read_buffer(StringIO(fh.read()))

    os.remove(vtt_path)

    # Deduplicate caption lines (VTT often repeats lines mid-scroll)
    seen: dict[str, None] = {}
    for c in captions:
        text = c.text.strip().replace("\n", " ")
        if text:
            seen[text] = None

    transcript = " ".join(seen.keys())
    if not transcript:
        raise ValueError(f"Empty transcript for: {title!r}")

    return title, transcript


def chunk(text: str, word_limit: int = 700) -> list[str]:
    """Split text into word-limited chunks."""
    words  = text.split()
    chunks, current = [], []
    for w in words:
        current.append(w)
        if len(current) >= word_limit:
            chunks.append(" ".join(current))
            current = []
    if current:
        chunks.append(" ".join(current))
    return chunks
