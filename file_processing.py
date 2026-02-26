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


# Regex to detect bibliography/references section headings.
# Matches lines like "References", "6. Bibliography", "Works Cited", etc.
_BIBLIOGRAPHY_HEADING_RE = re.compile(
    r"(?im)^\s*(?:\d+[\.\)]\s*)?(?:references|bibliography|literature|works\s+cited)\s*$"
)


def split_sections(full_text: str) -> tuple[str, str | None]:
    """Split document text into main text and bibliography section.

    Searches for the LAST occurrence of a bibliography heading
    (References, Bibliography, Literature, Works Cited) to avoid
    false positives from the word appearing in body text.

    Args:
        full_text: Complete document text.

    Returns:
        Tuple of (main_text, bibliography_text).
        bibliography_text is None if no heading was found.
    """
    matches = list(_BIBLIOGRAPHY_HEADING_RE.finditer(full_text))
    if not matches:
        return full_text, None

    last_match = matches[-1]
    split_pos = last_match.end()

    main_text = full_text[:last_match.start()].strip()
    bibliography_text = full_text[split_pos:].strip()

    if not bibliography_text:
        return full_text, None

    return main_text, bibliography_text
