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
import tempfile

import requests
import yt_dlp
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api.proxies import GenericProxyConfig
from youtube_transcript_api._errors import (
    NoTranscriptFound,
    TranscriptsDisabled,
    VideoUnavailable,
)
try:
    from youtube_transcript_api._errors import RequestBlocked, IpBlocked
    _BLOCK_ERRORS = (RequestBlocked, IpBlocked)
except ImportError:
    _BLOCK_ERRORS = ()

log = logging.getLogger("tubescribe.youtube")

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


def _video_id(url: str) -> str:
    m = re.search(r"(?:v=|youtu\.be/|embed/|shorts/)([A-Za-z0-9_-]{11})", url)
    if m:
        return m.group(1)
    raise ValueError(f"Cannot extract video ID from URL: {url}")


def _get_title(video_id: str, cookies_file: str | None) -> str:
    """Get title via yt-dlp extract_flat (metadata only, no download)."""
    opts: dict = {"quiet": True, "skip_download": True, "extract_flat": True}
    if cookies_file:
        opts["cookiefile"] = cookies_file
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(
                f"https://www.youtube.com/watch?v={video_id}", download=False
            )
        return info.get("title") or "Untitled Video"
    except Exception as exc:
        log.warning("Could not fetch title via yt-dlp: %s", exc)
        return "Untitled Video"


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
    Returns (title, clean_transcript_text).
    Tries Cloudflare Worker first, then direct youtube-transcript-api.
    Raises FileNotFoundError / ValueError so pipeline.py can fall through to Gemini.
    """
    video_id    = _video_id(video_url)
    cookies     = _cookies_path()
    cookies_tmp = cookies if (_COOKIES_TEXT and cookies != _COOKIES_FILE) else None

    try:
        worker_url = os.getenv("YT_PROXY_WORKER", "").strip()

        # ── Primary: Cloudflare Worker ─────────────────────────────────────
        if worker_url:
            log.info("Fetching transcript via Cloudflare Worker for %s", video_id)
            try:
                title, segments = _fetch_via_worker(worker_url, video_id)
                transcript = " ".join(s["text"] for s in segments if s.get("text"))
                if not transcript.strip():
                    raise FileNotFoundError("Worker returned empty transcript text")
                log.info("Worker success: %d words for '%s'", len(transcript.split()), title)
                return title, transcript
            except FileNotFoundError:
                raise  # no captions → tell pipeline to use Gemini
            except Exception as exc:
                log.warning("Worker failed: %s — trying direct API", exc)
                # Fall through to direct API

        # ── Fallback: direct youtube-transcript-api (local/residential only) ──
        title  = _get_title(video_id, cookies)
        proxy  = os.getenv("PROXY_URL", "").strip()

        if proxy:
            log.info("Using PROXY_URL for transcript fetch")
            ytt = YouTubeTranscriptApi(
                proxy_config=GenericProxyConfig(http_url=proxy, https_url=proxy)
            )
        else:
            ytt = YouTubeTranscriptApi()

        try:
            transcript_list = ytt.list(video_id)
            try:
                t = transcript_list.find_manually_created_transcript(["en"])
            except NoTranscriptFound:
                t = transcript_list.find_generated_transcript(["en"])
            fetched = t.fetch()
        except _BLOCK_ERRORS as exc:
            raise FileNotFoundError(
                f"YouTube is blocking requests from this server IP: {exc}"
            )
        except (NoTranscriptFound, TranscriptsDisabled, VideoUnavailable) as exc:
            raise FileNotFoundError(f"No English transcript for '{title}': {exc}")

        entries = fetched.snippets if hasattr(fetched, "snippets") else fetched
        seen: dict[str, None] = {}
        for e in entries:
            text = (e.text if hasattr(e, "text") else e.get("text", "")).strip().replace("\n", " ")
            if text:
                seen[text] = None

        transcript = " ".join(seen.keys())
        if not transcript:
            raise ValueError(f"Empty transcript for: {title!r}")

        log.info("Direct API OK: %d words for '%s'", len(transcript.split()), title)
        return title, transcript

    finally:
        if cookies_tmp:
            try:
                os.remove(cookies_tmp)
            except OSError:
                pass


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