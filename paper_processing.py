"""Paper processing module: download open-access PDFs and extract text."""

from io import BytesIO

import requests
from pypdf import PdfReader


_TIMEOUT = 15  # seconds
_MAX_SIZE = 20 * 1024 * 1024  # 20 MB


def retrieve_paper_text(
    oa_pdf_url: str | None, abstract: str | None
) -> tuple[str | None, str]:
    """Attempt to retrieve the full text of a paper.

    Fallback chain: PDF download -> abstract only -> not found.

    Args:
        oa_pdf_url: Open access PDF URL from OpenAlex, or None.
        abstract: Abstract text from OpenAlex, or None.

    Returns:
        Tuple of (text, source_type) where source_type is one of:
        "pdf", "abstract_only", "not_found".
    """
    if oa_pdf_url:
        pdf_bytes = _download_pdf(oa_pdf_url)
        if pdf_bytes:
            text = _extract_pdf_text(pdf_bytes)
            if text.strip():
                return text, "pdf"

    if abstract:
        return abstract, "abstract_only"

    return None, "not_found"


def _download_pdf(url: str) -> bytes | None:
    """Download a PDF with safety limits.

    Applies a 15-second timeout and 20 MB maximum size.
    Uses streaming to enforce the size limit without loading
    the entire response into memory at once.

    Returns:
        Raw PDF bytes, or None on any failure.
    """
    try:
        response = requests.get(url, timeout=_TIMEOUT, stream=True)
        if response.status_code != 200:
            return None

        # Check Content-Length header if available
        content_length = response.headers.get("Content-Length")
        if content_length and int(content_length) > _MAX_SIZE:
            return None

        # Stream and accumulate chunks, abort if over size limit
        chunks: list[bytes] = []
        total = 0
        for chunk in response.iter_content(chunk_size=8192):
            total += len(chunk)
            if total > _MAX_SIZE:
                return None
            chunks.append(chunk)

        return b"".join(chunks)
    except Exception:
        return None


def _extract_pdf_text(pdf_bytes: bytes) -> str:
    """Extract text from PDF bytes using pypdf."""
    try:
        reader = PdfReader(BytesIO(pdf_bytes))
        pages = []
        for page in reader.pages:
            text = page.extract_text()
            if text:
                pages.append(text)
        return "\n".join(pages)
    except Exception:
        return ""
