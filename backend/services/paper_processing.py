"""Paper processing module: extract text from locally uploaded PDFs."""

from __future__ import annotations

from backend.services.text_extraction import extract_pdf_text as _extract_pdf_text


def extract_pdf_text(pdf_bytes: bytes) -> str:
    """Backward-compatible wrapper around shared PDF extraction."""
    return _extract_pdf_text(pdf_bytes)
