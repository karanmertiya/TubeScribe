"""
Transcript utilities.
extract() is kept for compatibility but not used in the main pipeline
(transcripts come from the browser bookmarklet).
chunk() is used by pipeline.py to split text into LLM-sized pieces.
"""
from __future__ import annotations
import re


def chunk(text: str, word_limit: int = 700) -> list[str]:
    words = text.split()
    chunks, current = [], []
    for w in words:
        current.append(w)
        if len(current) >= word_limit:
            chunks.append(" ".join(current))
            current = []
    if current:
        chunks.append(" ".join(current))
    return chunks


def extract(video_url: str, temp_dir: str) -> tuple[str, str]:
    """Not used — transcripts come from browser bookmarklet."""
    raise NotImplementedError("Transcript fetch via server is disabled. Use the bookmarklet.")
