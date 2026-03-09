"""
Fetch transcripts via YouTube's timedtext API (youtube-transcript-api).
yt-dlp is used only to resolve the video title — no format/download involved.
"""
from __future__ import annotations
import logging
import os
import re
import tempfile

import yt_dlp
from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api._errors import (
    NoTranscriptFound,
    TranscriptsDisabled,
    VideoUnavailable,
)
# These were added in newer versions — import safely
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
    """Extract YouTube video ID from any URL format."""
    m = re.search(r"(?:v=|youtu\.be/|embed/|shorts/)([A-Za-z0-9_-]{11})", url)
    if m:
        return m.group(1)
    raise ValueError(f"Cannot extract video ID from URL: {url}")


def _get_title(video_id: str, cookies_file: str | None) -> str:
    """Use yt-dlp metadata-only fetch to get the video title."""
    opts: dict = {
        "quiet":         True,
        "skip_download": True,
        "extract_flat":  True,
    }
    if cookies_file:
        opts["cookiefile"] = cookies_file
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(
                f"https://www.youtube.com/watch?v={video_id}",
                download=False,
            )
        return info.get("title") or "Untitled Video"
    except Exception as exc:
        log.warning("Could not fetch title via yt-dlp: %s", exc)
        return "Untitled Video"


def extract(video_url: str, temp_dir: str) -> tuple[str, str]:
    """
    Returns (title, clean_transcript).
    Uses youtube-transcript-api for transcript, yt-dlp for title only.
    """
    video_id    = _video_id(video_url)
    cookies     = _cookies_path()
    cookies_tmp = cookies if (_COOKIES_TEXT and cookies != _COOKIES_FILE) else None

    try:
        title = _get_title(video_id, cookies)

        log.warning("Fetching transcript for video_id=%s", video_id)

        # Build proxy config if PROXY_URL is set
        proxy_url = os.getenv("PROXY_URL")
        proxies   = {"https": proxy_url, "http": proxy_url} if proxy_url else None
        if proxies:
            log.warning("Using proxy for transcript fetch")

        # New API: instantiate the class, then use list_transcripts
        ytt = YouTubeTranscriptApi()
        try:
            transcript_list = ytt.list(video_id, proxies=proxies)
            # Prefer manually created English, then auto-generated
            try:
                transcript = transcript_list.find_manually_created_transcript(["en"])
            except NoTranscriptFound:
                transcript = transcript_list.find_generated_transcript(["en"])
            fetched = transcript.fetch()
        except _BLOCK_ERRORS as exc:  # type: ignore
            raise FileNotFoundError(
                "YouTube is blocking transcript requests from this server IP. "
                "This is a YouTube restriction on cloud/datacenter IPs. "
                f"Details: {exc}"
            )
        except (NoTranscriptFound, TranscriptsDisabled, VideoUnavailable) as exc:
            raise FileNotFoundError(
                f"No English transcript available for '{title}': {exc}"
            )

        # Clean and deduplicate — new API returns FetchedTranscript with .snippets
        seen: dict[str, None] = {}
        # Handle both old dict format and new FetchedTranscriptSnippet format
        entries = fetched.snippets if hasattr(fetched, "snippets") else fetched
        for entry in entries:
            if hasattr(entry, "text"):
                text = entry.text.strip().replace("\n", " ")
            else:
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
    """Split text into word-limited chunks."""
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
