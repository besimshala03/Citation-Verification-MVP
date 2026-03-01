"""Prompt templates/builders for citation verification."""

from __future__ import annotations

SYSTEM_PROMPT = """\
You are an academic citation verification assistant.

You will receive:
1) A citing context block
2) Source text from the cited paper

Important:
- The claim to verify is ONLY the sentence wrapped with [CLAIM_SENTENCE]...[/CLAIM_SENTENCE].
- Any surrounding sentences are context only and must not be treated as the claim.
- If tags are missing, use only the sentence that contains the citation mention as the claim.
- First, extract and internally restate the exact claim from the claim sentence.
- Then search the source text for evidence addressing that exact claim (same variable, relation, direction, and conditions).
- Do NOT classify as SUPPORTS based on loose topical similarity.
- Prefer precise evidence over generic background statements.
- If the source only partially matches or is ambiguous about the specific claim, return UNCERTAIN.

Return ONLY valid JSON with this exact shape:
{
  "label": "SUPPORTS" | "CONTRADICTS" | "NOT_RELEVANT" | "UNCERTAIN",
  "explanation": "1-3 sentence explanation focused on the exact claim and evidence",
  "confidence": <float between 0.0 and 1.0>,
  "relevant_passage": "<verbatim passage up to 500 chars>" | null,
  "evidence_page": <1-based page number integer> | null,
  "evidence_why": "1 sentence why the snippet supports/contradicts the claim" | null
}

Do not add markdown, code fences, or extra keys.
"""


def build_user_prompt(
    citing_paragraph: str,
    source_text: str,
    source_label: str,
    author: str,
    year: str,
    paper_title: str | None,
    document_summary: str | None,
) -> str:
    title_str = paper_title or "Unknown"
    claim_hint = (
        "The citing context below contains the claim sentence wrapped in "
        "[CLAIM_SENTENCE] tags. Only that sentence should be evaluated."
    )
    return (
        f"Citation: ({author}, {year})\n"
        f"Paper title: {title_str}\n\n"
        f"{claim_hint}\n\n"
        f"Citing context:\n{citing_paragraph}\n\n"
        f"Document-level background context (secondary only):\n"
        f"{document_summary or 'N/A'}\n\n"
        "Important: The background context is only for domain understanding. "
        "Do not use it as evidence and do not let it override the claim sentence.\n\n"
        f"Source ({source_label}):\n{source_text}"
    )

