"""Evaluation module: LLM-based citation support classification."""

import json
import os
from dataclasses import dataclass

from openai import OpenAI


@dataclass
class EvaluationResult:
    """Result of the LLM evaluation for a single citation."""

    label: str  # SUPPORTS, CONTRADICTS, NOT_RELEVANT, UNCERTAIN
    explanation: str
    confidence: float  # 0.0 to 1.0


_VALID_LABELS = {"SUPPORTS", "CONTRADICTS", "NOT_RELEVANT", "UNCERTAIN"}

_SYSTEM_PROMPT = """You are an academic citation verification assistant. Your task is to \
determine whether a cited source supports the claim made in the citing paragraph.

Respond ONLY with valid JSON in exactly this format:
{
    "label": "SUPPORTS" | "CONTRADICTS" | "NOT_RELEVANT" | "UNCERTAIN",
    "explanation": "1-3 sentence explanation of your reasoning",
    "confidence": <float between 0.0 and 1.0>
}

Classification guidelines:
- SUPPORTS: The source text provides evidence that aligns with the claim.
- CONTRADICTS: The source text provides evidence that opposes the claim.
- NOT_RELEVANT: The source text does not address the topic of the claim.
- UNCERTAIN: There is not enough information to make a determination.

Do not include any text outside the JSON object."""


def evaluate_support(
    citing_paragraph: str,
    matched_passage: str | None,
    abstract: str | None,
    author: str,
    year: str,
    paper_title: str | None,
    source_type: str,
) -> EvaluationResult:
    """Use the LLM to evaluate whether the source supports the cited claim.

    If source_type is "not_found", skips the LLM call and returns UNCERTAIN.

    Args:
        citing_paragraph: The paragraph containing the citation.
        matched_passage: Best-matching passage from the paper, or None.
        abstract: Paper abstract, or None.
        author: Citation author string.
        year: Citation year string.
        paper_title: Paper title from OpenAlex, or None.
        source_type: "pdf", "abstract_only", or "not_found".

    Returns:
        EvaluationResult with label, explanation, and confidence.
    """
    if source_type == "not_found":
        return EvaluationResult(
            label="UNCERTAIN",
            explanation="No source text available for verification.",
            confidence=0.0,
        )

    # Determine the source text to send to the LLM
    if matched_passage:
        source_text = matched_passage
        source_label = "full text passage"
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
    """Build the user prompt for the LLM."""
    title_str = paper_title or "Unknown"
    return (
        f"Citation: ({author}, {year})\n"
        f"Paper title: {title_str}\n\n"
        f"Citing paragraph:\n{citing_paragraph}\n\n"
        f"Source passage ({source_label}):\n{source_text}"
    )


def _call_llm(user_prompt: str) -> str | None:
    """Call the OpenAI API and return the response content.

    Returns None on any failure.
    """
    try:
        client = OpenAI()
        model = os.getenv("MODEL_NAME", "gpt-5.2")

        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0,
            max_tokens=500,
        )

        return response.choices[0].message.content
    except Exception:
        return None


def _parse_llm_response(response_text: str | None) -> EvaluationResult:
    """Parse the LLM's JSON response into an EvaluationResult.

    Returns a fallback UNCERTAIN result if parsing fails.
    """
    if not response_text:
        return EvaluationResult(
            label="UNCERTAIN",
            explanation="LLM response could not be parsed.",
            confidence=0.0,
        )

    try:
        data = json.loads(response_text)

        label = data.get("label", "UNCERTAIN")
        if label not in _VALID_LABELS:
            label = "UNCERTAIN"

        explanation = str(data.get("explanation", "No explanation provided."))

        confidence = float(data.get("confidence", 0.0))
        # Clamp to valid range
        confidence = max(0.0, min(1.0, confidence))

        return EvaluationResult(
            label=label,
            explanation=explanation,
            confidence=confidence,
        )
    except (json.JSONDecodeError, ValueError, TypeError, KeyError):
        return EvaluationResult(
            label="UNCERTAIN",
            explanation="LLM response could not be parsed.",
            confidence=0.0,
        )
