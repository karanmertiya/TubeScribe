"""Groq provider — OpenAI-compatible REST with exponential back-off on 429."""
from __future__ import annotations
import logging
import os
import time

import requests as _requests

from .config import LLMConfig

log        = logging.getLogger("tubescribe.llm.groq")
MAX_TRIES  = int(os.getenv("GROQ_MAX_RETRIES", "6"))


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

    for attempt in range(MAX_TRIES):
        try:
            r = _requests.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers=headers, json=payload, timeout=120,
            )
            r.raise_for_status()
            return r.json()["choices"][0]["message"]["content"]

        except _requests.HTTPError as exc:
            status = exc.response.status_code
            if status == 429:
                # Try to read Retry-After header first, then use exponential backoff
                retry_after = exc.response.headers.get("Retry-After")
                if retry_after:
                    wait = int(retry_after) + 2
                else:
                    # Exponential: 20, 40, 60, 80, 100, 120
                    wait = min(20 * (attempt + 1), 120)
                log.warning("Rate-limit 429 — waiting %ds (attempt %d/%d)", wait, attempt + 1, MAX_TRIES)
                time.sleep(wait)
                continue
            else:
                log.error("Groq HTTP %s: %s", status, exc.response.text[:200])
                return f"\n\n> \u26a0\ufe0f **Groq Error {status}**\n\n"

        except Exception as exc:
            log.error("Groq error: %s", exc)
            if attempt < MAX_TRIES - 1:
                time.sleep(10)
                continue
            return f"\n\n> \u26a0\ufe0f **Groq Error:** {exc}\n\n"

    return f"\n\n> \u274c **Groq failed after {MAX_TRIES} retries. Try again in a minute.**\n\n"
