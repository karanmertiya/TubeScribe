"""Gemini provider — wraps google-genai SDK."""
from __future__ import annotations
import logging
from .config import LLMConfig

log = logging.getLogger("tubescribe.llm.gemini")


def call(llm: LLMConfig, prompt: str) -> str:
    try:
        from google import genai
        from google.genai import types

        client   = genai.Client(api_key=llm.api_key)
        response = client.models.generate_content(
            model=llm.model,
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=llm.system_prompt,
                temperature=0.3,
            ),
        )
        return response.text
    except Exception as exc:
        log.error("Gemini error: %s", exc)
        return f"\n\n> ⚠️ **Gemini Error:** {exc}\n\n"


def get_transcript_from_url(llm: LLMConfig, video_url: str) -> tuple[str, str]:
    """
    Use Gemini to extract the title and raw transcript from a YouTube URL.
    Gemini fetches the video internally — no IP blocking, no yt-dlp needed.
    Returns (title, transcript_text).
    """
    try:
        from google import genai
        from google.genai import types

        client = genai.Client(api_key=llm.api_key)

        prompt = (
            "You are a transcript extractor.\n"
            "Given this YouTube video:\n"
            "1. Output the video title on the first line as: TITLE: <title>\n"
            "2. Then output the full verbatim transcript of the video, exactly as spoken, "
            "with no summarization, no formatting, no timestamps — just the raw spoken words.\n"
            "Output nothing else."
        )

        response = client.models.generate_content(
            model=llm.model,
            contents=types.Content(
                parts=[
                    types.Part(file_data=types.FileData(file_uri=video_url)),
                    types.Part(text=prompt),
                ]
            ),
            config=types.GenerateContentConfig(temperature=0.0),
        )

        text = response.text or ""
        lines = text.splitlines()
        title = "Untitled Video"
        if lines and lines[0].startswith("TITLE:"):
            title = lines[0].replace("TITLE:", "").strip()
            transcript = "\n".join(lines[1:]).strip()
        else:
            transcript = text.strip()

        if not transcript:
            raise RuntimeError("Gemini returned empty transcript.")

        log.warning("Gemini transcript extracted: %d words for '%s'", len(transcript.split()), title)
        return title, transcript

    except Exception as exc:
        log.error("Gemini transcript extraction error: %s", exc)
        raise RuntimeError(f"Gemini transcript extraction failed: {exc}") from exc
    """
    Pass a YouTube URL directly to Gemini — no transcript needed.
    Google's API fetches and processes the video internally, no IP blocking.
    Returns (title, notes_markdown).
    """
    try:
        from google import genai
        from google.genai import types

        client = genai.Client(api_key=llm.api_key)

        prompt = (
            "You are an elite academic note-taking assistant.\n"
            "First, state the exact video title on a line starting with 'TITLE: '.\n"
            "Then generate comprehensive, beautifully structured Markdown notes from this video.\n\n"
            + llm.system_prompt +
            "\n\nGenerate the complete notes for this entire video now."
        )

        response = client.models.generate_content(
            model=llm.model,
            contents=types.Content(
                parts=[
                    types.Part(
                        file_data=types.FileData(file_uri=video_url)
                    ),
                    types.Part(text=prompt),
                ]
            ),
            config=types.GenerateContentConfig(temperature=0.3),
        )

        text = response.text or ""

        # Extract title from first line if present
        title = "Untitled Video"
        lines = text.splitlines()
        if lines and lines[0].startswith("TITLE:"):
            title = lines[0].replace("TITLE:", "").strip()
            text  = "\n".join(lines[1:]).strip()

        log.warning("Gemini YouTube URL processing complete for: %s", title)
        return title, text

    except Exception as exc:
        log.error("Gemini YouTube URL error: %s", exc)
        raise RuntimeError(f"Gemini video processing failed: {exc}") from exc
