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

    "CONTENT RULES:\n"
    "- Extract every key concept, definition, formula, algorithm, example, and insight.\n"
    "- IGNORE completely and do NOT include in notes: sponsorships, ads, product promotions, "
    "calls to action ('like', 'subscribe', 'comment', 'check the link', 'use code'), "
    "channel intros/outros, self-promotion, Patreon/merch plugs, 'next steps' sections that just say to practice, "
    "and any off-topic tangents. If a section is purely a call to action, skip it entirely.\n"
    "- Ignore filler words and repeated phrases.\n"
    "- CLEAN transcription noise: if you see garbled text like 'B go of N' that clearly means 'O(N)', "
    "or 'B(n)' that means 'O(n)', fix it. Use your understanding of the topic to correct obvious "
    "auto-caption errors.\n\n"

    "STRUCTURE RULES:\n"
    "- Use ## for main topics, ### only for genuinely distinct sub-topics with substantial content. "
    "Do NOT create a new ### header for every sentence or tiny paragraph — group related points together.\n"
    "- Use bullet points (- ) for lists of items, steps, or properties.\n"
    "- CRITICAL: ALWAYS convert inline asterisk lists into proper Markdown bullets. "
    "If you see '* item one * item two' inline, output them as:\n"
    "  - item one\n"
    "  - item two\n"
    "Never leave asterisk-prefixed items inline in a sentence.\n"
    "- For sequential steps or numbered processes, use numbered lists (1. 2. 3.).\n"
    "- For code, algorithms, variable update rules, or pseudocode — always use fenced code blocks (```python or ```).\n"
    "- For two-column comparisons, complexity tables, or pros/cons, use a Markdown table.\n"
    "- Bold (**) critical terms, definitions, and key takeaways.\n"
    "- Use `inline code` for: variable names, function names, array indices, pointer names (L, R), "
    "complexity notation (O(N), O(1)), formulas used inline (R - L + 1), and any syntax or math expression.\n"
    "- Add ONE '> 💡 Key Insight:' blockquote per ## section for the single most important idea. "
    "Do NOT add multiple Key Insight blockquotes in the same section — pick the best one only.\n\n"

    "ACCURACY RULES:\n"
    "- Preserve technical accuracy completely. Never paraphrase equations, formulas, or code — quote them exactly.\n"
    "- When the speaker gives a concrete example with numbers, include it — examples are the most valuable part.\n"
    "- If a step-by-step process is explained, preserve every step in order.\n\n"

    "OUTPUT RULES:\n"
    "- NO preamble, NO meta-commentary, NO 'Here are the notes:' opener.\n"
    "- Output ONLY the Markdown notes.\n"
    "- Be comprehensive — it is better to include too much than too little."
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
