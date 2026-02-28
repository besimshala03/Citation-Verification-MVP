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
    relevant_passage: str | None = None  # LLM-identified relevant passage


_VALID_LABELS = {"SUPPORTS", "CONTRADICTS", "NOT_RELEVANT", "UNCERTAIN"}

# Maximum characters of paper text to send to the LLM (~25K tokens).
_MAX_PAPER_CHARS = 100_000

_SYSTEM_PROMPT = """\
You are an academic citation verification assistant. Your task is to \
determine whether a cited source paper supports the claim made in the \
citing paragraph.

You will receive:
1. A citing paragraph from a document that references a specific paper
2. The full text (or a large excerpt) of the cited paper

Your job:
1. Search through the provided paper text to find the passage(s) most \
relevant to the claim being made in the citing paragraph.
2. Determine whether the paper supports, contradicts, or is not relevant \
to the claim.
3. Extract the single most relevant passage you found.

IMPORTANT: The citing paragraph may be in a different language than the \
paper. Evaluate the semantic meaning regardless of language differences.

Respond ONLY with valid JSON in exactly this format:
{
    "label": "SUPPORTS" | "CONTRADICTS" | "NOT_RELEVANT" | "UNCERTAIN",
    "explanation": "1-3 sentence explanation of your reasoning",
    "confidence": <float between 0.0 and 1.0>,
    "relevant_passage": "The most relevant passage from the paper (verbatim, max 500 characters). null if no relevant passage found."
}

Classification guidelines:
- SUPPORTS: The paper provides evidence that aligns with the claim.
- CONTRADICTS: The paper provides evidence that opposes the claim.
- NOT_RELEVANT: The paper does not address the topic of the claim at all.
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
    paper_text: str | None = None,
) -> EvaluationResult:
    """Use the LLM to evaluate whether the source supports the cited claim.

    When paper_text is provided, sends the full paper text to the LLM so it
    can search for the most relevant passage itself (much more accurate than
    embedding-based chunk matching, especially for cross-language scenarios).

    Falls back to matched_passage/abstract when paper_text is not available.

    Args:
        citing_paragraph: The paragraph containing the citation.
        matched_passage: Best-matching passage from embeddings, or None.
        abstract: Paper abstract, or None.
        author: Citation author string.
        year: Citation year string.
        paper_title: Paper title, or None.
        source_type: "pdf" or "not_uploaded".
        paper_text: Full extracted text of the reference paper, or None.

    Returns:
        EvaluationResult with label, explanation, confidence, and
        the LLM-identified relevant_passage.
    """
    if source_type == "not_found":
        return EvaluationResult(
            label="UNCERTAIN",
            explanation="No source text available for verification.",
            confidence=0.0,
        )

    # Determine the source text to send to the LLM.
    # Prefer full paper text (LLM searches it), fall back to passage/abstract.
    if paper_text and paper_text.strip():
        # Truncate if very long
        truncated = paper_text[:_MAX_PAPER_CHARS]
        if len(paper_text) > _MAX_PAPER_CHARS:
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
    """Build the user prompt for the LLM."""
    title_str = paper_title or "Unknown"
    return (
        f"Citation: ({author}, {year})\n"
        f"Paper title: {title_str}\n\n"
        f"Citing paragraph:\n{citing_paragraph}\n\n"
        f"Source ({source_label}):\n{source_text}"
    )


def _call_llm(user_prompt: str) -> str | None:
    """Call the OpenAI API and return the response content.

    Returns None on any failure, printing the error for debugging.
    """
    try:
        client = OpenAI()
        model = os.getenv("MODEL_NAME", "gpt-4o")

        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0,
            max_completion_tokens=800,
        )

        return response.choices[0].message.content
    except Exception as e:
        print(f"[evaluation] LLM call failed: {e}")
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

        relevant_passage = data.get("relevant_passage")
        if relevant_passage and isinstance(relevant_passage, str):
            relevant_passage = relevant_passage.strip()
            if not relevant_passage or relevant_passage.lower() == "null":
                relevant_passage = None
        else:
            relevant_passage = None

        return EvaluationResult(
            label=label,
            explanation=explanation,
            confidence=confidence,
            relevant_passage=relevant_passage,
        )
    except (json.JSONDecodeError, ValueError, TypeError, KeyError):
        return EvaluationResult(
            label="UNCERTAIN",
            explanation="LLM response could not be parsed.",
            confidence=0.0,
        )
