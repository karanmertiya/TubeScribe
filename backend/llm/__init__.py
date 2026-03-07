"""LLM package — import from here, not from sub-modules."""
from .config import LLMConfig, DEFAULT_SYSTEM_PROMPT
from . import gemini, groq as _groq


def call_llm(llm: LLMConfig, chunk: str) -> str:
    """Route a transcript chunk to the active provider and return markdown notes."""
    prompt = (
        "**Transcript Excerpt:**\n---\n"
        f"{chunk}\n"
        "---\n**Detailed Markdown Notes:**\n"
    )
    return gemini.call(llm, prompt) if llm.provider == "gemini" else _groq.call(llm, prompt)


__all__ = ["LLMConfig", "DEFAULT_SYSTEM_PROMPT", "call_llm"]
