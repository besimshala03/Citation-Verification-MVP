"""Document ingestion workflow helpers."""

from __future__ import annotations

import sqlite3

from fastapi import HTTPException, UploadFile

from backend.config import settings
from backend.db import repository as repo
from backend.services.bibliography_parser import (
    match_citation,
    parse_entries,
    parse_entry_metadata,
)
from backend.services.citation_detection import detect_citations
from backend.services.document_summary import generate_document_summary
from backend.services.file_processing import extract_text, split_sections

_ALLOWED_MAIN_MIME = {
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}


def _validate_document_upload(file: UploadFile, file_bytes: bytes) -> str:
    filename = file.filename or ""
    lower = filename.lower()
    if not lower.endswith((".pdf", ".docx")):
        raise HTTPException(
            status_code=400,
            detail="Unsupported file format. Only PDF and DOCX files are accepted.",
        )

    if len(file_bytes) > settings.max_main_document_bytes:
        raise HTTPException(
            status_code=400,
            detail=f"Main document exceeds max size of {settings.max_main_document_bytes} bytes.",
        )

    if file.content_type and file.content_type not in _ALLOWED_MAIN_MIME:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported MIME type: {file.content_type}",
        )

    return filename


def _save_document(
    conn: sqlite3.Connection,
    project_id: str,
    filename: str,
    file_bytes: bytes,
    full_text: str,
    main_text: str,
    bibliography_text: str | None,
    summary: str | None,
) -> dict:
    return repo.save_document(
        project_id=project_id,
        filename=filename,
        file_bytes=file_bytes,
        full_text=full_text,
        main_text=main_text,
        bibliography_text=bibliography_text,
        summary=summary,
        conn=conn,
    )


def _process_bibliography(
    conn: sqlite3.Connection,
    project_id: str,
    document_id: str,
    bibliography_text: str | None,
) -> tuple[list[dict], str | None]:
    warning = None
    ref_entries_created: list[dict] = []

    if bibliography_text:
        raw_entries = parse_entries(bibliography_text)
        entries_with_metadata = []
        for entry_text in raw_entries:
            meta = parse_entry_metadata(entry_text)
            entries_with_metadata.append({"entry_text": entry_text, **meta})

        ref_entries_created = repo.create_reference_entries(
            project_id,
            document_id,
            entries_with_metadata,
            conn=conn,
        )
    else:
        warning = "No bibliography/references section found in the document."

    return ref_entries_created, warning


def _process_citations(
    conn: sqlite3.Connection,
    project_id: str,
    document_id: str,
    main_text: str,
    ref_entries_created: list[dict],
) -> list[dict]:
    citations = detect_citations(main_text)
    citation_dicts = []
    for cit in citations:
        matched_entry_id = None
        matched_entry_text = None
        for ref_entry in ref_entries_created:
            bib_match = match_citation(cit.author, cit.year, ref_entry["entry_text"])
            if bib_match:
                matched_entry_id = ref_entry["id"]
                matched_entry_text = ref_entry["entry_text"]
                break

        citation_dicts.append(
            {
                "citation_text": cit.citation_text,
                "author": cit.author,
                "year": cit.year,
                "citing_paragraph": cit.citing_paragraph,
                "reference_entry_id": matched_entry_id,
                "bibliography_match": matched_entry_text,
            }
        )

    return repo.save_citations(project_id, document_id, citation_dicts, conn=conn)


async def ingest_document(
    conn: sqlite3.Connection,
    project_id: str,
    file: UploadFile,
) -> dict:
    file_bytes = await file.read()
    filename = _validate_document_upload(file, file_bytes)

    full_text = extract_text(file_bytes, filename)
    if not full_text.strip():
        raise HTTPException(
            status_code=400,
            detail="Could not extract text from the document.",
        )

    main_text, bibliography_text = split_sections(full_text)
    document_summary = generate_document_summary(main_text)

    doc = _save_document(
        conn,
        project_id,
        filename,
        file_bytes,
        full_text,
        main_text,
        bibliography_text,
        document_summary,
    )

    ref_entries_created, warning = _process_bibliography(
        conn,
        project_id,
        doc["id"],
        bibliography_text,
    )

    saved_citations = _process_citations(
        conn,
        project_id,
        doc["id"],
        main_text,
        ref_entries_created,
    )

    return {
        "document_id": doc["id"],
        "filename": filename,
        "citation_count": len(saved_citations),
        "reference_entries": ref_entries_created,
        "document_summary": document_summary,
        "warning": warning,
    }
