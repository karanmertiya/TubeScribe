"""
LLM configuration resolved per-request.
Dev mode uses server-side keys; user mode uses whatever arrives in the request body.
"""
from __future__ import annotations
import os


# ── Server-side defaults (dev mode) ───────────────────────────────────────────
DEFAULT_PROVIDER  = os.getenv("LLM_PROVIDER",  "gemini" if os.getenv("GEMINI_API_KEY") else "groq")
DEFAULT_GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
DEFAULT_GROQ_MODEL   = os.getenv("GROQ_MODEL",   "llama-3.3-70b-versatile")
SERVER_GEMINI_KEY    = os.getenv("GEMINI_API_KEY")
SERVER_GROQ_KEY      = os.getenv("GROQ_API_KEY")

DEFAULT_SYSTEM_PROMPT = (
    "You are an elite academic note-taking assistant.\n"
    "Transform the transcript excerpt into comprehensive, beautifully structured Markdown notes.\n\n"
    "RULES:\n"
    "- Extract every key concept, definition, formula, example, and insight.\n"
    "- Use ## for main topics, ### for sub-topics, bullet points for detail.\n"
    "- Bold (**) critical terms and takeaways.\n"
    "- Add a '> 💡 Key Insight:' blockquote for the single most important idea per section.\n"
    "- Preserve technical accuracy. Never paraphrase equations or code — quote them exactly.\n"
    "- Ignore filler words, repeated phrases, transcription noise.\n"
    "- NO preamble, NO meta-commentary. Output ONLY the Markdown notes."
)


class LLMConfig:
    """Resolved LLM configuration for one request. Stateless, immutable."""

    def __init__(
        self,
        provider:      str | None = None,
        model:         str | None = None,
        api_key:       str | None = None,
        system_prompt: str | None = None,
    ):
        self.provider      = (provider or DEFAULT_PROVIDER).lower()
        self.system_prompt = system_prompt or DEFAULT_SYSTEM_PROMPT

        if self.provider == "gemini":
            self.model   = model   or DEFAULT_GEMINI_MODEL
            self.api_key = api_key or SERVER_GEMINI_KEY
        else:
            self.provider = "groq"
            self.model    = model   or DEFAULT_GROQ_MODEL
            self.api_key  = api_key or SERVER_GROQ_KEY

    def validate(self) -> str | None:
        """Return an error string if the config is unusable, else None."""
        if not self.api_key:
            return f"No API key for provider '{self.provider}'. Set it in Settings."
        return None

    @property
    def label(self) -> str:
        return f"{self.provider.upper()} / {self.model}"
