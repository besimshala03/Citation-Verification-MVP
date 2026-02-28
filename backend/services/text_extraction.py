"""Shared text extraction helpers."""

from __future__ import annotations

import logging
from io import BytesIO

from pypdf import PdfReader

logger = logging.getLogger(__name__)


def extract_pdf_text(pdf_bytes: bytes) -> str:
    """Extract text from PDF bytes with surrogate-safe normalization."""
    try:
        reader = PdfReader(BytesIO(pdf_bytes))
        pages: list[str] = []
        for page in reader.pages:
            text = page.extract_text()
            if text:
                pages.append(text)

        full_text = "\n".join(pages)
        return full_text.encode("utf-8", errors="surrogatepass").decode(
            "utf-8", errors="replace"
        )
    except Exception:
        logger.exception("Failed to extract PDF text")
        return ""
