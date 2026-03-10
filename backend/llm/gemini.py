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
    Use Gemini to generate notes directly from a YouTube URL.
    Gemini fetches the video internally — no IP blocking, no yt-dlp needed.
    Returns (title, '__GEMINI_NOTES__\\n<markdown_notes>').

    Uses gemini-2.0-flash (2M token context) to handle videos up to ~4-5 hours.
    If the video exceeds the context window, falls back to a summary-only prompt.
    """
    from google import genai
    from google.genai import types

    client = genai.Client(api_key=llm.api_key)

    prompt = (
        "You are an elite academic note-taking assistant.\n"
        "Given this YouTube video:\n"
        "1. Output the video title on the first line as: TITLE: <title>\n"
        "2. Then generate comprehensive, beautifully structured Markdown notes.\n\n"
        + llm.system_prompt
        + "\n\nGenerate the complete notes now."
    )

    try:
        response = client.models.generate_content(
            model=llm.model,
            contents=types.Content(
                parts=[
                    types.Part(file_data=types.FileData(file_uri=video_url)),
                    types.Part(text=prompt),
                ]
            ),
            config=types.GenerateContentConfig(temperature=0.3),
        )
    except Exception as exc:
        err_str = str(exc)
        # If token limit exceeded, retry with a condensed prompt asking for key points only
        if "1048576" in err_str or "token" in err_str.lower():
            log.warning("Token limit hit for %s — retrying with condensed prompt", video_url)
            condensed_prompt = (
                "You are a note-taking assistant. This is a very long video.\n"
                "1. Output the video title on the first line as: TITLE: <title>\n"
                "2. Generate a concise but complete summary covering:\n"
                "   - The main topic and goal\n"
                "   - Key concepts, definitions, and algorithms explained\n"
                "   - Important examples with their outcomes\n"
                "   - Core takeaways and conclusions\n"
                "Use ## headers, bullet points, and code blocks where appropriate.\n"
                "Output ONLY Markdown — no preamble."
            )
            response = client.models.generate_content(
                model=llm.model,
                contents=types.Content(
                    parts=[
                        types.Part(file_data=types.FileData(file_uri=video_url)),
                        types.Part(text=condensed_prompt),
                    ]
                ),
                config=types.GenerateContentConfig(temperature=0.3),
            )
        else:
            log.error("Gemini transcript extraction error: %s", exc)
            raise RuntimeError(f"Gemini transcript extraction failed: {exc}") from exc

    text  = response.text or ""
    lines = text.splitlines()
    title = "Untitled Video"

    if lines and lines[0].startswith("TITLE:"):
        title = lines[0].replace("TITLE:", "").strip()
        notes = "\n".join(lines[1:]).strip()
    else:
        notes = text.strip()

    if not notes:
        raise RuntimeError("Gemini returned empty response.")

    log.warning("Gemini notes generated for '%s'", title)
    return title, f"__GEMINI_NOTES__\n{notes}"
