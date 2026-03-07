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
