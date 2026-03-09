"""
Fetch transcripts from YouTube.
Primary: Cloudflare Worker API (YT_PROXY_WORKER env var) — not IP-blocked.
Fallback: direct youtube-transcript-api (works locally, blocked on cloud IPs).
yt-dlp used only for video title via extract_flat (no format/download).
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
        log.warning("Could not fetch title: %s", exc)
        return "Untitled Video"


def _fetch_via_worker(worker_url: str, video_id: str) -> list:
    """
    Fetch transcript by calling the Cloudflare Worker as a fetch API.
    Worker proxies the YouTube page + timedtext URL, returns raw content.
    """
    WORKER = worker_url.rstrip("/") + "?url="
    yt_page = f"https://www.youtube.com/watch?v={video_id}"

    # Step 1: fetch YouTube page via Worker
    resp = requests.get(WORKER + requests.utils.quote(yt_page, safe=""), timeout=15)
    if not resp.ok:
        raise FileNotFoundError(f"Worker failed to fetch YouTube page: {resp.status_code}")
    html = resp.text

    # Step 2: extract caption tracks
    match = re.search(r'"captionTracks":(\[.*?\])', html)
    if not match:
        raise FileNotFoundError("No captions found for this video (no captionTracks in page).")

    import json
    tracks = json.loads(match.group(1))
    track = (
        next((t for t in tracks if t.get("languageCode") == "en" and not t.get("kind")), None)
        or next((t for t in tracks if t.get("languageCode") == "en"), None)
        or (tracks[0] if tracks else None)
    )
    if not track:
        raise FileNotFoundError("No English captions found for this video.")

    # Step 3: fetch transcript JSON via Worker
    timedtext_url = track["baseUrl"] + "&fmt=json3"
    tresp = requests.get(WORKER + requests.utils.quote(timedtext_url, safe=""), timeout=15)
    if not tresp.ok:
        raise FileNotFoundError(f"Worker failed to fetch transcript: {tresp.status_code}")

    data   = tresp.json()
    events = data.get("events", [])

    # Convert to list of dicts like youtube-transcript-api returns
    result = []
    for ev in events:
        if not ev.get("segs"):
            continue
        text = "".join(s.get("utf8", "") for s in ev["segs"]).replace("\n", " ").strip()
        if text:
            result.append({"text": text})
    return result


def extract(video_url: str, temp_dir: str) -> tuple[str, str]:
    """Returns (title, clean_transcript)."""
    video_id    = _video_id(video_url)
    cookies     = _cookies_path()
    cookies_tmp = cookies if (_COOKIES_TEXT and cookies != _COOKIES_FILE) else None

    try:
        title      = _get_title(video_id, cookies)
        worker_url = os.getenv("YT_PROXY_WORKER", "").strip()
        proxy_url  = os.getenv("PROXY_URL", "").strip()

        if worker_url:
            log.warning("Fetching transcript via Cloudflare Worker for %s", video_id)
            raw_entries = _fetch_via_worker(worker_url, video_id)
        else:
            if proxy_url:
                log.warning("Using PROXY_URL for transcript fetch")
                ytt = YouTubeTranscriptApi(
                    proxy_config=GenericProxyConfig(http_url=proxy_url, https_url=proxy_url)
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
            except _BLOCK_ERRORS as exc:  # type: ignore
                raise FileNotFoundError(
                    "YouTube is blocking transcript requests from this server IP. "
                    f"Details: {exc}"
                )
            except (NoTranscriptFound, TranscriptsDisabled, VideoUnavailable) as exc:
                raise FileNotFoundError(f"No English transcript for '{title}': {exc}")

            entries = fetched.snippets if hasattr(fetched, "snippets") else fetched
            raw_entries = [
                {"text": (e.text if hasattr(e, "text") else e.get("text", ""))}
                for e in entries
            ]

        # Deduplicate
        seen: dict[str, None] = {}
        for entry in raw_entries:
            text = entry.get("text", "").strip().replace("\n", " ")
            if text:
                seen[text] = None

        transcript_text = " ".join(seen.keys())
        if not transcript_text:
            raise ValueError(f"Empty transcript for: {title!r}")

        log.warning("Transcript OK: %d words for '%s'", len(transcript_text.split()), title)
        return title, transcript_text

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
