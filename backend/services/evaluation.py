"""Evaluation module: LLM-based citation support classification."""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass

from openai import OpenAI

from backend.config import settings

logger = logging.getLogger(__name__)


@dataclass
class EvaluationResult:
    label: str
    explanation: str
    confidence: float
    relevant_passage: str | None = None


_VALID_LABELS = {"SUPPORTS", "CONTRADICTS", "NOT_RELEVANT", "UNCERTAIN"}

_SYSTEM_PROMPT = """\
You are an academic citation verification assistant.

You will receive:
1) A citing paragraph
2) Source text from the cited paper

Return ONLY valid JSON with this exact shape:
{
  "label": "SUPPORTS" | "CONTRADICTS" | "NOT_RELEVANT" | "UNCERTAIN",
  "explanation": "1-3 sentence explanation",
  "confidence": <float between 0.0 and 1.0>,
  "relevant_passage": "<verbatim passage up to 500 chars>" | null
}

Do not add markdown, code fences, or extra keys.
"""


def evaluate_support(
    citing_paragraph: str,
    matched_passage: str | None,
    abstract: str | None,
    author: str,
    year: str,
    paper_title: str | None,
    source_type: str,
    paper_text: str | None = None,
) -> EvaluationResult:
    if source_type == "not_found":
        return EvaluationResult(
            label="UNCERTAIN",
            explanation="No source text available for verification.",
            confidence=0.0,
        )

    if paper_text and paper_text.strip():
        truncated = paper_text[: settings.max_paper_chars]
        if len(paper_text) > settings.max_paper_chars:
            truncated += "\n\n[...text truncated...]"
        source_text = truncated
        source_label = "full paper text"
    elif matched_passage:
        source_text = matched_passage
        source_label = "extracted passage"
    elif abstract:
        source_text = abstract
        source_label = "abstract only"
    else:
        return EvaluationResult(
            label="UNCERTAIN",
            explanation="No source text available for verification.",
            confidence=0.0,
        )

    user_prompt = _build_user_prompt(
        citing_paragraph, source_text, source_label, author, year, paper_title
    )
    response_text = _call_llm(user_prompt)
    return _parse_llm_response(response_text)


def _build_user_prompt(
    citing_paragraph: str,
    source_text: str,
    source_label: str,
    author: str,
    year: str,
    paper_title: str | None,
) -> str:
    title_str = paper_title or "Unknown"
    return (
        f"Citation: ({author}, {year})\n"
        f"Paper title: {title_str}\n\n"
        f"Citing paragraph:\n{citing_paragraph}\n\n"
        f"Source ({source_label}):\n{source_text}"
    )


def _call_llm(user_prompt: str) -> str | None:
    try:
        client = OpenAI()
        try:
            response = client.chat.completions.create(
                model=settings.model_name,
                messages=[
                    {"role": "system", "content": _SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0,
                max_completion_tokens=800,
                response_format={"type": "json_object"},
            )
        except Exception:
            # Fallback for models/providers that do not support response_format.
            logger.warning(
                "Falling back to plain completion call without JSON response_format."
            )
            response = client.chat.completions.create(
                model=settings.model_name,
                messages=[
                    {"role": "system", "content": _SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0,
                max_completion_tokens=800,
            )
        return response.choices[0].message.content
    except Exception:
        logger.exception("LLM call failed")
        return None


def _extract_json_candidate(text: str) -> str:
    stripped = text.strip()
    if stripped.startswith("{") and stripped.endswith("}"):
        return stripped

    fence_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, flags=re.DOTALL)
    if fence_match:
        return fence_match.group(1).strip()

    start = text.find("{")
    if start == -1:
        return stripped

    depth = 0
    in_string = False
    escaped = False
    for idx in range(start, len(text)):
        ch = text[idx]
        if in_string:
            if escaped:
                escaped = False
            elif ch == "\\":
                escaped = True
            elif ch == '"':
                in_string = False
            continue

        if ch == '"':
            in_string = True
        elif ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return text[start : idx + 1].strip()

    return stripped


def _parse_llm_response(response_text: str | None) -> EvaluationResult:
    if not response_text:
        return EvaluationResult(
            label="UNCERTAIN",
            explanation="LLM response could not be parsed.",
            confidence=0.0,
        )

    try:
        candidate = _extract_json_candidate(response_text)
        data = json.loads(candidate)
        label = data.get("label", "UNCERTAIN")
        if label not in _VALID_LABELS:
            label = "UNCERTAIN"

        confidence = float(data.get("confidence", 0.0))
        confidence = max(0.0, min(1.0, confidence))

        relevant_passage = data.get("relevant_passage")
        if not isinstance(relevant_passage, str) or not relevant_passage.strip() or relevant_passage.lower() == "null":
            relevant_passage = None

        return EvaluationResult(
            label=label,
            explanation=str(data.get("explanation", "No explanation provided.")),
            confidence=confidence,
            relevant_passage=relevant_passage.strip() if relevant_passage else None,
        )
    except (json.JSONDecodeError, ValueError, TypeError, KeyError):
        logger.warning(
            "Failed to parse LLM response as JSON. Raw response prefix: %r",
            (response_text[:500] if response_text else ""),
        )
        return EvaluationResult(
            label="UNCERTAIN",
            explanation="LLM response could not be parsed.",
            confidence=0.0,
        )
