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
    "- Write in direct, factual language. NEVER use phrases like 'the speaker says', 'the instructor explains', "
    "'the presenter mentions', 'the author covers', or any meta-commentary about who is speaking. "
    "Write the knowledge directly as if it were a textbook.\n"
    "- IGNORE completely: sponsorships, ads, product promotions, calls to action ('like', 'subscribe', "
    "'comment', 'check the link', 'use code'), channel intros/outros, self-promotion, Patreon/merch plugs, "
    "'next steps' sections that just say to practice, viewer engagement requests, series announcements, "
    "and any off-topic tangents. If a section is purely meta or promotional, skip it entirely.\n"
    "- Ignore filler words and repeated phrases.\n"
    "- CLEAN transcription noise: fix obvious auto-caption errors using context (e.g. 'B go of N' → 'O(N)').\n\n"

    "STRUCTURE RULES:\n"
    "- Use ## for main topics, ### only for genuinely distinct sub-topics with substantial content.\n"
    "- Use bullet points (- ) for lists of items, steps, or properties.\n"
    "- CRITICAL — NEVER write lists inline. ALWAYS put each item on its own line:\n"
    "  WRONG: 'Topics: - Recursion - Tabulation - Space Optimization'\n"
    "  RIGHT:\n"
    "  Topics:\n"
    "  - Recursion\n"
    "  - Tabulation\n"
    "  - Space Optimization\n"
    "- For sequential steps or numbered processes, use numbered lists (1. 2. 3.).\n"
    "- For code, algorithms, or pseudocode — always use fenced code blocks (```python or ```).\n"
    "- For comparisons, complexity tables, or pros/cons, use a Markdown table.\n"
    "- Bold (**) critical terms, definitions, and key takeaways.\n"
    "- Use `inline code` for variable names, function names, complexity notation (O(N)), formulas.\n"
    "- Add ONE '> 💡 Key Insight:' blockquote per ## section for the single most important idea only.\n\n"

    "ACCURACY RULES:\n"
    "- Preserve technical accuracy completely. Never paraphrase equations or code — quote them exactly.\n"
    "- When a concrete example with numbers is given, include it.\n"
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
