"""Generate short document-level summaries for context."""

from __future__ import annotations

import logging
import re

from openai import OpenAI

from backend.config import settings

logger = logging.getLogger(__name__)

_SUMMARY_SYSTEM_PROMPT = """\
You summarize academic documents in 2-3 concise sentences.
Focus on the main topic, core claim types, and scope.
Do not include bullet points or markdown.
"""


def generate_document_summary(main_text: str) -> str | None:
    text = (main_text or "").strip()
    if not text:
        return None

    truncated = text[: settings.max_summary_input_chars]
    summary = _summarize_with_llm(truncated)
    if summary:
        return summary

    return _heuristic_summary(truncated)


def _summarize_with_llm(text: str) -> str | None:
    try:
        client = OpenAI()
        response = client.chat.completions.create(
            model=settings.model_name,
            messages=[
                {"role": "system", "content": _SUMMARY_SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": (
                        "Summarize this document in exactly 2-3 sentences:\n\n"
                        f"{text}"
                    ),
                },
            ],
            temperature=0.2,
            max_completion_tokens=180,
        )
        content = (response.choices[0].message.content or "").strip()
        return content or None
    except Exception:
        logger.exception("Failed to generate LLM summary for document")
        return None


def _heuristic_summary(text: str) -> str | None:
    # fallback: first 2-3 sentence-like chunks
    sentences = [
        s.strip()
        for s in re.split(r"(?<=[.!?])\s+", text)
        if s and s.strip()
    ]
    if not sentences:
        return None
    return " ".join(sentences[:3])

