"""Paper processing module: extract text from locally uploaded PDFs."""

from io import BytesIO

from pypdf import PdfReader


def extract_pdf_text(pdf_bytes: bytes) -> str:
    """Extract text from PDF bytes using pypdf.

    Args:
        pdf_bytes: Raw PDF file content.

    Returns:
        Extracted text as a single string, or empty string on failure.
    """
    try:
        reader = PdfReader(BytesIO(pdf_bytes))
        pages = []
        for page in reader.pages:
            text = page.extract_text()
            if text:
                pages.append(text)
        full_text = "\n".join(pages)
        # Remove Unicode surrogate characters that some PDFs produce
        # (surrogates U+D800–U+DFFF are invalid in UTF-8 and crash SQLite)
        return full_text.encode("utf-8", errors="surrogatepass").decode(
            "utf-8", errors="replace"
        )
    except Exception:
        return ""
