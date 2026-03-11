"""Gemini provider — wraps google-genai SDK."""
from __future__ import annotations
import logging
from .config import LLMConfig

log = logging.getLogger("tubescribe.llm.gemini")

# ── Free-tier daily quotas (as of early 2026) ─────────────────────────────────
# Model                   RPD   RPM   Context   Notes
# gemini-2.5-flash        250   10    1M        Best quality — use first
# gemini-2.5-flash-lite  1000   30    1M        4× quota, still good
# gemini-1.5-flash       1500   15    1M        Legacy but highest free RPD
#
# gemini-2.0-flash was retired March 3 2026 — do NOT use it.
# All models share the same 1M token context window on free tier.
# Quota resets midnight Pacific Time.

_FALLBACK_CHAIN = [
    "gemini-2.5-flash",       # 250 RPD  — primary, best notes quality
    "gemini-2.5-flash-lite",  # 1000 RPD — 4× quota, still good
    "gemini-1.5-flash",       # 1500 RPD — legacy, highest free quota
]

_FULL_PROMPT = (
    "You are an elite academic note-taking assistant.\n"
    "Given this YouTube video:\n"
    "1. Output the video title on the first line as: TITLE: <title>\n"
    "2. Then generate comprehensive, beautifully structured Markdown notes.\n\n"
    "{system_prompt}\n\n"
    "Generate the complete notes now."
)

_CONDENSED_PROMPT = (
    "You are a note-taking assistant. This video is very long — focus on the essentials.\n"
    "1. Output the video title on the first line as: TITLE: <title>\n"
    "2. Generate a focused summary covering:\n"
    "   - Main topic and goal of the video\n"
    "   - Every key concept, definition, and algorithm explained\n"
    "   - Important examples and their outcomes\n"
    "   - Core takeaways and conclusions\n"
    "Use ## headers, bullet points, and fenced code blocks where appropriate.\n"
    "Output ONLY Markdown — no preamble, no meta-commentary."
)


def _is_quota_error(err: str) -> bool:
    return "429" in err or "RESOURCE_EXHAUSTED" in err or "quota" in err.lower()


def _is_token_error(err: str) -> bool:
    return (
        "1048576" in err
        or "token count exceeds" in err.lower()
        or ("token" in err.lower() and "maximum" in err.lower())
    )


def call(llm: LLMConfig, prompt: str) -> str:
    """Route a plain prompt to Gemini — used for note generation from transcript chunks."""
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


def get_transcript_from_url(llm: LLMConfig, video_url: str) -> tuple[str, str, str]:
    """
    Generate notes directly from a YouTube URL via Gemini.
    Google fetches the video internally — no IP blocking, no yt-dlp needed.
    Returns (title, '__GEMINI_NOTES__\\n<markdown>', model_used).

    Two-axis fallback strategy:
      QUOTA errors (429)  → try next model in fallback chain (more daily quota)
      TOKEN errors (>1M)  → switch to condensed prompt on same model first,
                            then move to next model if still failing
    """
    from google import genai
    from google.genai import types

    client = genai.Client(api_key=llm.api_key)

    # Build model chain: configured model first, then fallbacks (deduplicated)
    primary = llm.model
    chain   = [primary] + [m for m in _FALLBACK_CHAIN if m != primary]

    def _call(model: str, condensed: bool) -> object:
        prompt_text = (
            _CONDENSED_PROMPT if condensed
            else _FULL_PROMPT.format(system_prompt=llm.system_prompt)
        )
        return client.models.generate_content(
            model=model,
            contents=types.Content(parts=[
                types.Part(file_data=types.FileData(file_uri=video_url)),
                types.Part(text=prompt_text),
            ]),
            config=types.GenerateContentConfig(temperature=0.3),
        )

    last_exc   = None
    condensed  = False
    active_model = None

    for model in chain:
        try:
            log.info("Gemini attempting %s (condensed=%s)", model, condensed)
            response = _call(model, condensed)
            active_model = model
            break

        except Exception as exc:
            err_str  = str(exc)
            last_exc = exc

            if _is_token_error(err_str):
                # Video too long — try condensed prompt on same model first
                if not condensed:
                    log.warning("Token limit on %s — retrying with condensed prompt", model)
                    condensed = True
                    try:
                        response = _call(model, condensed=True)
                        active_model = model
                        break
                    except Exception as exc2:
                        err_str  = str(exc2)
                        last_exc = exc2
                        if not (_is_quota_error(err_str) or _is_token_error(err_str)):
                            raise RuntimeError(f"Gemini {model} failed: {exc2}") from exc2
                log.warning("Condensed also failed on %s — trying next model", model)
                continue

            elif _is_quota_error(err_str):
                log.warning("Quota exhausted on %s — trying next model", model)
                continue

            else:
                # Unexpected error (network, bad URL, etc.) — don't keep retrying
                log.error("Gemini unexpected error on %s: %s", model, exc)
                raise RuntimeError(f"Gemini failed: {exc}") from exc
    else:
        # All models exhausted
        raise RuntimeError(
            "All Gemini free-tier quotas are exhausted for today "
            f"(tried: {', '.join(chain)}). "
            "Quotas reset at midnight Pacific Time. "
            "You can also add your own Gemini API key in ⚙️ Settings."
        ) from last_exc

    # Parse title + notes from response
    text  = response.text or ""
    lines = text.splitlines()
    title = "Untitled Video"

    if lines and lines[0].startswith("TITLE:"):
        title = lines[0].replace("TITLE:", "").strip()
        notes = "\n".join(lines[1:]).strip()
    else:
        notes = text.strip()

    if not notes:
        raise RuntimeError("Gemini returned an empty response.")

    log.info("Gemini notes ready via %s for '%s'", active_model, title)
    return title, f"__GEMINI_NOTES__\n{notes}", active_model