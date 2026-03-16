"""Groq provider — round-robins across up to 3 API keys for 3x rate limit."""
from __future__ import annotations
import itertools
import logging
import os
import time

import requests as _requests

from .config import LLMConfig

log       = logging.getLogger("tubescribe.llm.groq")
MAX_TRIES = int(os.getenv("GROQ_MAX_RETRIES", "6"))

# Build key pool from env: GROQ_API_KEY (primary), GROQ_API_KEY_2, GROQ_API_KEY_3
def _build_pool() -> list[str]:
    keys = []
    for var in ("GROQ_API_KEY", "GROQ_API_KEY_2", "GROQ_API_KEY_3"):
        k = os.getenv(var, "").strip()
        if k:
            keys.append(k)
    return keys or [""]

_key_pool = _build_pool()
_key_cycle = itertools.cycle(range(len(_key_pool)))
_call_count = 0

def _next_key() -> str:
    global _call_count
    idx = next(_key_cycle)
    _call_count += 1
    log.debug("Using key slot %d (call #%d)", idx, _call_count)
    return _key_pool[idx]


def call(llm: LLMConfig, prompt: str) -> str:
    payload = {
        "model": llm.model,
        "messages": [
            {"role": "system", "content": llm.system_prompt},
            {"role": "user",   "content": prompt},
        ],
        "temperature": 0.3,
    }

    tried_keys: set[str] = set()

    for attempt in range(MAX_TRIES):
        api_key = _next_key() or llm.api_key
        headers = {
            "Content-Type":  "application/json",
            "Authorization": f"Bearer {api_key}",
        }
        tried_keys.add(api_key)

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
                # If we have untried keys, switch immediately with no wait
                untried = [k for k in _key_pool if k and k not in tried_keys]
                if untried:
                    log.warning("429 on key slot — switching to next key immediately")
                    continue
                # All keys exhausted, back off
                retry_after = exc.response.headers.get("Retry-After")
                wait = int(retry_after) + 2 if retry_after else min(20 * (attempt + 1), 120)
                log.warning("All keys rate-limited — waiting %ds (attempt %d/%d)", wait, attempt + 1, MAX_TRIES)
                time.sleep(wait)
                tried_keys.clear()  # reset so we retry all keys after wait
                continue
            else:
                log.error("Groq HTTP %s: %s", status, exc.response.text[:200])
                return f"\n\n> \u26a0\ufe0f **Groq Error {status}**\n\n"

        except Exception as exc:
            log.error("Groq error: %s", exc)
            if attempt < MAX_TRIES - 1:
                time.sleep(5)
                continue
            return f"\n\n> \u26a0\ufe0f **Groq Error:** {exc}\n\n"

    return f"\n\n> \u274c **Groq failed after {MAX_TRIES} retries.**\n\n"
