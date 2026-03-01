"""Shared text extraction helpers."""

from __future__ import annotations

import logging
from io import BytesIO

from pypdf import PdfReader

logger = logging.getLogger(__name__)


def extract_pdf_text(pdf_bytes: bytes) -> str:
    """Extract text from PDF bytes with surrogate-safe normalization."""
    try:
        full_text = "\n".join(extract_pdf_pages(pdf_bytes))
        return full_text.encode("utf-8", errors="surrogatepass").decode(
            "utf-8", errors="replace"
        )
    except Exception:
        logger.exception("Failed to extract PDF text")
        return ""


def extract_pdf_pages(pdf_bytes: bytes) -> list[str]:
    """Extract PDF text page-by-page with surrogate-safe normalization."""
    try:
        reader = PdfReader(BytesIO(pdf_bytes))
        pages: list[str] = []
        for page in reader.pages:
            text = page.extract_text() or ""
            normalized = text.encode("utf-8", errors="surrogatepass").decode(
                "utf-8", errors="replace"
            )
            pages.append(normalized)
        return pages
    except Exception:
        logger.exception("Failed to extract PDF pages")
        return []
