"""Download and clean VTT subtitles from a single YouTube video."""
from __future__ import annotations
import logging
import os
from io import StringIO

import webvtt
import yt_dlp

log = logging.getLogger("tubescribe.youtube")


def extract(video_url: str, temp_dir: str) -> tuple[str, str]:
    """
    Returns (title, clean_transcript).
    Raises FileNotFoundError if no English subtitles exist.
    Raises ValueError if the transcript is empty after cleaning.
    """
    base     = os.path.join(temp_dir, "video")
    ydl_opts = {
        "writesubtitles":    True,
        "writeautomaticsub": True,
        "subtitleslangs":    ["en"],
        "subtitlesformat":   "vtt",
        "skip_download":     True,
        "quiet":             True,
        "outtmpl":           base,
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info  = ydl.extract_info(video_url, download=True)
        title = info.get("title", "Untitled Video")

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
