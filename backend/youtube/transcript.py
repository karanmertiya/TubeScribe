"""
Fetch transcripts from YouTube.

Strategy (in order):
  1. Cloudflare Worker (YT_PROXY_WORKER env var)
     — Custom worker that dynamically extracts INNERTUBE_API_KEY from the
       YouTube page and calls the Android player API. Cloudflare edge IPs
       are not blocked by YouTube unlike AWS/GCP datacenter IPs.
     — Returns title + full transcript text in ~1-2s.

  2. Direct youtube-transcript-api (works only locally / residential IPs)
     — Included as fallback for local dev. Will fail on Railway.

  If both fail, pipeline.py falls through to Gemini which processes the
  YouTube URL directly — always works but uses daily quota.
"""
from __future__ import annotations
import logging
import os
import re

import requests
import yt_dlp

log = logging.getLogger("tubescribe.youtube")


def _video_id(url: str) -> str:
    m = re.search(r"(?:v=|youtu\.be/|embed/|shorts/)([A-Za-z0-9_-]{11})", url)
    if m:
        return m.group(1)
    raise ValueError(f"Cannot extract video ID from URL: {url}")


def _fetch_via_worker(worker_url: str, video_id: str) -> tuple[str, list]:
    """
    Call our Cloudflare Worker which:
      1. Fetches the YouTube page to extract the dynamic INNERTUBE_API_KEY
      2. Calls YouTube's Android player API with that key + visitor data
      3. Fetches caption JSON and returns clean segments

    Returns (title, segments) where segments is [{text, offset, duration}]
    Raises FileNotFoundError if no captions available.
    Raises requests.HTTPError for other failures.
    """
    base = worker_url.rstrip("/")

    # New worker endpoint: GET /?video_id=XXXX
    resp = requests.get(
        f"{base}/?video_id={video_id}",
        timeout=30,
    )

    if resp.status_code == 404:
        raise FileNotFoundError(f"No captions available for video {video_id}")
    if resp.status_code == 400:
        data = resp.json()
        raise ValueError(data.get("error", f"Bad request: {resp.text[:200]}"))
    if resp.status_code == 500:
        try:
            msg = resp.json().get("error", resp.text[:300])
        except Exception:
            msg = resp.text[:300]
        raise FileNotFoundError(f"Worker error: {msg}")
    resp.raise_for_status()

    data = resp.json()

    if "error" in data:
        raise FileNotFoundError(data["error"])

    segments = data.get("segments") or []
    title    = data.get("title") or "Untitled Video"

    if not segments:
        raise FileNotFoundError("Worker returned empty transcript")

    log.info(
        "Worker transcript OK: %d words, title=%r",
        data.get("word_count", 0), title
    )
    return title, segments


def extract(video_url: str, temp_dir: str) -> tuple[str, str]:
    """
    Returns (title, clean_transcript_text) via Cloudflare Worker.
    Raises on failure — pipeline.py handles the error.
    """
    video_id   = _video_id(video_url)
    worker_url = os.getenv("YT_PROXY_WORKER", "").strip()

    if not worker_url:
        raise RuntimeError("YT_PROXY_WORKER env var not set.")

    title, segments = _fetch_via_worker(worker_url, video_id)
    transcript = " ".join(s["text"] for s in segments if s.get("text"))
    if not transcript.strip():
        raise FileNotFoundError("Worker returned empty transcript")

    log.info("Worker OK: %d words for '%s'", len(transcript.split()), title)
    return title, transcript


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
