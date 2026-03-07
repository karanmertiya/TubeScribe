"""Groq provider — OpenAI-compatible REST with exponential back-off on 429."""
from __future__ import annotations
import logging
import os
import time

import requests as _requests

from .config import LLMConfig

log       = logging.getLogger("tubescribe.llm.groq")
RETRY_WAIT = int(os.getenv("GROQ_RETRY_WAIT", "15"))


def call(llm: LLMConfig, prompt: str) -> str:
    headers = {
        "Content-Type":  "application/json",
        "Authorization": f"Bearer {llm.api_key}",
    }
    payload = {
        "model": llm.model,
        "messages": [
            {"role": "system", "content": llm.system_prompt},
            {"role": "user",   "content": prompt},
        ],
        "temperature": 0.3,
    }

    for attempt in range(3):
        try:
            r = _requests.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers=headers, json=payload, timeout=120,
            )
            r.raise_for_status()
            return r.json()["choices"][0]["message"]["content"]

        except _requests.HTTPError as exc:
            if exc.response.status_code == 429:
                wait = RETRY_WAIT * (attempt + 1)
                log.warning("Rate-limit — waiting %ds (attempt %d/3)", wait, attempt + 1)
                time.sleep(wait)
            else:
                log.error("Groq HTTP %s: %s", exc.response.status_code, exc.response.text[:200])
                return f"\n\n> ⚠️ **Groq Error {exc.response.status_code}**\n\n"

        except Exception as exc:
            log.error("Groq error: %s", exc)
            return f"\n\n> ⚠️ **Groq Error:** {exc}\n\n"

    return "\n\n> ❌ **Groq failed after 3 retries.**\n\n"
