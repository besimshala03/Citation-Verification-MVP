"""File processing module: PDF/DOCX text extraction and section splitting."""

import re
from io import BytesIO

from pypdf import PdfReader
from docx import Document


def extract_text(file_bytes: bytes, filename: str) -> str:
    """Extract full text from a PDF or DOCX file.

    Args:
        file_bytes: Raw bytes of the uploaded file.
        filename: Original filename (used to determine format).

    Returns:
        Full extracted text as a single string. Empty string on failure.

    Raises:
        ValueError: If file format is not .pdf or .docx.
    """
    lower = filename.lower()
    if lower.endswith(".pdf"):
        return _extract_pdf(file_bytes)
    elif lower.endswith(".docx"):
        return _extract_docx(file_bytes)
    else:
        raise ValueError(f"Unsupported file format: {filename}")


def _extract_pdf(file_bytes: bytes) -> str:
    """Extract text from PDF bytes using pypdf."""
    try:
        reader = PdfReader(BytesIO(file_bytes))
        pages = []
        for page in reader.pages:
            text = page.extract_text()
            if text:
                pages.append(text)
        return "\n".join(pages)
    except Exception:
        return ""


def _extract_docx(file_bytes: bytes) -> str:
    """Extract text from DOCX bytes using python-docx."""
    try:
        doc = Document(BytesIO(file_bytes))
        paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
        return "\n".join(paragraphs)
    except Exception:
        return ""


# Strategy 1: heading on its own line (well-formatted DOCX or PDF).
# Matches "References", "6. Bibliography", "1 Literaturverzeichnis", etc.
_BIBLIOGRAPHY_HEADING_STRICT_RE = re.compile(
    r"(?im)^\s*(?:\d+[\.\)\s]\s*)?"
    r"(?:references|bibliography|literature|works\s+cited"
    r"|literaturverzeichnis|literatur|quellenverzeichnis|quellen)"
    r"\s*$"
)

# Strategy 2: heading appearing inline in the text.
# pypdf often loses newlines around headings, producing text like:
#   "...last sentence.   1 Literaturverzeichnis Firstname, L. (2020)..."
# This regex finds the heading as a word boundary without requiring line start.
# Restricted to unambiguous long keywords to avoid false positives.
_BIBLIOGRAPHY_HEADING_INLINE_RE = re.compile(
    r"(?i)"
    r"(?<!\w)"                          # not preceded by a word character
    r"(?:\d+\s+)?"                      # optional section number like "1 "
    r"(?:references|bibliography|works\s+cited"
    r"|literaturverzeichnis|quellenverzeichnis)"
    r"(?!\w)"                           # not followed by a word character
)


def split_sections(full_text: str) -> tuple[str, str | None]:
    """Split document text into main text and bibliography section.

    Uses two strategies:
    1. Strict: heading on its own line (handles well-formatted documents).
    2. Inline: heading embedded in text (handles PDF-extracted text where
       pypdf drops newlines around section headings).

    In both cases the LAST match is used to avoid false positives from the
    heading word appearing earlier in body text.

    Args:
        full_text: Complete document text.

    Returns:
        Tuple of (main_text, bibliography_text).
        bibliography_text is None if no heading was found.
    """
    # Strategy 1: strict line-based detection
    strict_matches = list(_BIBLIOGRAPHY_HEADING_STRICT_RE.finditer(full_text))
    if strict_matches:
        last_match = strict_matches[-1]
        main_text = full_text[:last_match.start()].strip()
        bibliography_text = full_text[last_match.end():].strip()
        if bibliography_text:
            return main_text, bibliography_text

    # Strategy 2: inline detection for PDF-extracted text
    inline_matches = list(_BIBLIOGRAPHY_HEADING_INLINE_RE.finditer(full_text))
    if inline_matches:
        last_match = inline_matches[-1]
        main_text = full_text[:last_match.start()].rstrip()
        bibliography_text = full_text[last_match.end():].strip()
        if bibliography_text:
            return main_text, bibliography_text

    return full_text, None
