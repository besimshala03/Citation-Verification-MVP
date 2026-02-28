"""File processing module: PDF/DOCX text extraction and section splitting."""

from __future__ import annotations

import logging
import re
from io import BytesIO

from docx import Document

from backend.services.text_extraction import extract_pdf_text

logger = logging.getLogger(__name__)


def extract_text(file_bytes: bytes, filename: str) -> str:
    lower = filename.lower()
    if lower.endswith(".pdf"):
        return extract_pdf_text(file_bytes)
    if lower.endswith(".docx"):
        return _extract_docx(file_bytes)
    raise ValueError(f"Unsupported file format: {filename}")


def _extract_docx(file_bytes: bytes) -> str:
    try:
        doc = Document(BytesIO(file_bytes))
        paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
        return "\n".join(paragraphs)
    except Exception:
        logger.exception("Failed to extract DOCX text")
        return ""


_BIBLIOGRAPHY_HEADING_STRICT_RE = re.compile(
    r"(?im)^\s*(?:\d+[\.\)\s]\s*)?"
    r"(?:references|bibliography|literature|works\s+cited"
    r"|literaturverzeichnis|literatur|quellenverzeichnis|quellen)"
    r"\s*$"
)

_BIBLIOGRAPHY_HEADING_INLINE_RE = re.compile(
    r"(?i)"
    r"(?<!\w)"
    r"(?:\d+\s+)?"
    r"(?:references|bibliography|works\s+cited"
    r"|literaturverzeichnis|quellenverzeichnis)"
    r"(?!\w)"
)


def split_sections(full_text: str) -> tuple[str, str | None]:
    strict_matches = list(_BIBLIOGRAPHY_HEADING_STRICT_RE.finditer(full_text))
    if strict_matches:
        last_match = strict_matches[-1]
        main_text = full_text[: last_match.start()].strip()
        bibliography_text = full_text[last_match.end() :].strip()
        if bibliography_text:
            return main_text, bibliography_text

    inline_matches = list(_BIBLIOGRAPHY_HEADING_INLINE_RE.finditer(full_text))
    if inline_matches:
        last_match = inline_matches[-1]
        main_text = full_text[: last_match.start()].rstrip()
        bibliography_text = full_text[last_match.end() :].strip()
        if bibliography_text:
            return main_text, bibliography_text

    return full_text, None
