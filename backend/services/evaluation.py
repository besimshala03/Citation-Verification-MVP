"""Evaluation module: LLM-based citation support classification."""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass

from openai import OpenAI

from backend.config import settings
from backend.services.prompts.verification import SYSTEM_PROMPT, build_user_prompt

logger = logging.getLogger(__name__)


@dataclass
class EvaluationResult:
    label: str
    explanation: str
    confidence: float
    relevant_passage: str | None = None
    evidence_page: int | None = None
    evidence_why: str | None = None


_VALID_LABELS = {"SUPPORTS", "CONTRADICTS", "NOT_RELEVANT", "UNCERTAIN"}

def evaluate_support(
    citing_paragraph: str,
    matched_passage: str | None,
    abstract: str | None,
    author: str,
    year: str,
    paper_title: str | None,
    source_type: str,
    paper_text: str | None = None,
    document_summary: str | None = None,
    paper_pages: list[str] | None = None,
) -> EvaluationResult:
    if source_type == "not_found":
        return EvaluationResult(
            label="UNCERTAIN",
            explanation="No source text available for verification.",
            confidence=0.0,
        )

    if paper_pages:
        joined_with_tags = _build_tagged_page_source(paper_pages)
        truncated = joined_with_tags[: settings.max_paper_chars]
        if len(joined_with_tags) > settings.max_paper_chars:
            truncated += "\n\n[...text truncated...]"
        source_text = truncated
        source_label = "full paper text with page markers"
    elif paper_text and paper_text.strip():
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

    user_prompt = build_user_prompt(
        citing_paragraph,
        source_text,
        source_label,
        author,
        year,
        paper_title,
        document_summary,
    )
    response_text = _call_llm(user_prompt)
    return _parse_llm_response(response_text, paper_pages or [])


def _build_tagged_page_source(pages: list[str]) -> str:
    chunks: list[str] = []
    for i, page in enumerate(pages, start=1):
        chunks.append(f"[PAGE {i}]\n{page}\n[/PAGE {i}]")
    return "\n\n".join(chunks)


def _call_llm(user_prompt: str) -> str | None:
    try:
        client = OpenAI()
        try:
            response = client.chat.completions.create(
                model=settings.model_name,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
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
                    {"role": "system", "content": SYSTEM_PROMPT},
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


def _parse_llm_response(
    response_text: str | None, paper_pages: list[str] | None = None
) -> EvaluationResult:
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

        evidence_page = data.get("evidence_page")
        if isinstance(evidence_page, int):
            if evidence_page <= 0:
                evidence_page = None
        elif isinstance(evidence_page, str) and evidence_page.strip().isdigit():
            evidence_page = int(evidence_page.strip())
            if evidence_page <= 0:
                evidence_page = None
        else:
            evidence_page = None

        evidence_why = data.get("evidence_why")
        if not isinstance(evidence_why, str) or not evidence_why.strip() or evidence_why.lower() == "null":
            evidence_why = None

        if evidence_page is None and relevant_passage and paper_pages:
            evidence_page = _infer_page_number(relevant_passage, paper_pages)

        return EvaluationResult(
            label=label,
            explanation=str(data.get("explanation", "No explanation provided.")),
            confidence=confidence,
            relevant_passage=relevant_passage.strip() if relevant_passage else None,
            evidence_page=evidence_page,
            evidence_why=evidence_why.strip() if evidence_why else None,
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


def _infer_page_number(snippet: str, paper_pages: list[str]) -> int | None:
    # Try exact-ish containment first.
    candidate = snippet.strip()
    if not candidate:
        return None
    for idx, page in enumerate(paper_pages, start=1):
        if candidate in page:
            return idx

    # Fallback: fuzzy token overlap.
    words = [w for w in re.findall(r"\w+", candidate.lower()) if len(w) > 3]
    if not words:
        return None
    best_idx = None
    best_score = 0
    for idx, page in enumerate(paper_pages, start=1):
        lower = page.lower()
        score = sum(1 for w in words if w in lower)
        if score > best_score:
            best_score = score
            best_idx = idx
    return best_idx if best_score >= max(2, len(words) // 3) else None
