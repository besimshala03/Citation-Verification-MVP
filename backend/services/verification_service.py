"""Citation verification helpers."""

from __future__ import annotations

import sqlite3

from backend.db import repository as repo
from backend.services.evaluation import evaluate_support
from backend.services.text_extraction import extract_pdf_pages


def process_citation_local(
    conn: sqlite3.Connection,
    citation: dict,
    project_id: str,
) -> dict:
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

    doc = repo.get_document(project_id, conn=conn)
    document_summary = doc.get("summary") if doc else None
    paper_pages: list[str] = []
    disk_path = ref_paper.get("disk_path")
    if disk_path:
        try:
            with open(disk_path, "rb") as f:
                paper_pages = extract_pdf_pages(f.read())
        except OSError:
            paper_pages = []

    eval_result = evaluate_support(
        citing_paragraph=citation["citing_paragraph"],
        matched_passage=None,
        abstract=None,
        author=citation["author"],
        year=citation["year"],
        paper_title=ref_paper.get("filename", "Unknown"),
        source_type="pdf",
        paper_text=paper_text,
        document_summary=document_summary,
        paper_pages=paper_pages,
    )

    return _build_result(
        citation,
        source_type="pdf",
        passage=eval_result.relevant_passage,
        label=eval_result.label,
        explanation=eval_result.explanation,
        confidence=eval_result.confidence,
        paper_filename=ref_paper.get("filename"),
        evidence_page=eval_result.evidence_page,
        evidence_why=eval_result.evidence_why,
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
        "evidence_page": None,
        "evidence_why": None,
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
    evidence_page: int | None = None,
    evidence_why: str | None = None,
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
        "evidence_page": evidence_page,
        "evidence_why": evidence_why,
        "evaluation": {
            "label": label,
            "explanation": explanation,
            "confidence": confidence,
        },
    }
