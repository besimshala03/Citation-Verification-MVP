"""Citation verification helpers."""

from __future__ import annotations

import sqlite3

from backend.db import repository as repo
from backend.services.evaluation import evaluate_support


def process_citation_local(conn: sqlite3.Connection, citation: dict) -> dict:
    ref_entry_id = citation.get("reference_entry_id")
    if not ref_entry_id:
        return _build_result(
            citation,
            source_type="not_uploaded",
            passage=None,
            label="UNCERTAIN",
            explanation="No bibliography match found for this citation.",
            confidence=0.0,
        )

    ref_paper = repo.get_reference_paper(ref_entry_id, conn=conn)
    if not ref_paper:
        return _build_result(
            citation,
            source_type="not_uploaded",
            passage=None,
            label="UNCERTAIN",
            explanation="Reference paper not yet uploaded. Upload the PDF for this reference to enable verification.",
            confidence=0.0,
        )

    paper_text = ref_paper.get("extracted_text", "")
    if not paper_text or not paper_text.strip():
        return _build_result(
            citation,
            source_type="pdf",
            passage=None,
            label="UNCERTAIN",
            explanation="Could not extract readable text from the uploaded PDF.",
            confidence=0.0,
        )

    eval_result = evaluate_support(
        citing_paragraph=citation["citing_paragraph"],
        matched_passage=None,
        abstract=None,
        author=citation["author"],
        year=citation["year"],
        paper_title=ref_paper.get("filename", "Unknown"),
        source_type="pdf",
        paper_text=paper_text,
    )

    return _build_result(
        citation,
        source_type="pdf",
        passage=eval_result.relevant_passage,
        label=eval_result.label,
        explanation=eval_result.explanation,
        confidence=eval_result.confidence,
        paper_filename=ref_paper.get("filename"),
    )


def build_error_result(citation: dict, error_msg: str) -> dict:
    return {
        "citation_text": citation["citation_text"],
        "author": citation["author"],
        "year": citation["year"],
        "citing_paragraph": citation["citing_paragraph"],
        "bibliography_match": citation.get("bibliography_match"),
        "paper_found": False,
        "paper_metadata": None,
        "source_type": "not_uploaded",
        "matched_passage": None,
        "evaluation": {
            "label": "UNCERTAIN",
            "explanation": f"Processing error: {error_msg}",
            "confidence": 0.0,
        },
    }


def _build_result(
    citation: dict,
    source_type: str,
    passage: str | None,
    label: str,
    explanation: str,
    confidence: float,
    paper_filename: str | None = None,
) -> dict:
    return {
        "citation_text": citation["citation_text"],
        "author": citation["author"],
        "year": citation["year"],
        "citing_paragraph": citation["citing_paragraph"],
        "bibliography_match": citation.get("bibliography_match"),
        "paper_found": source_type == "pdf",
        "paper_metadata": (
            {
                "title": paper_filename or "Uploaded Paper",
                "authors": [],
                "year": int(citation["year"]) if citation["year"].isdigit() else None,
            }
            if source_type == "pdf"
            else None
        ),
        "source_type": source_type,
        "matched_passage": passage,
        "evaluation": {
            "label": label,
            "explanation": explanation,
            "confidence": confidence,
        },
    }
