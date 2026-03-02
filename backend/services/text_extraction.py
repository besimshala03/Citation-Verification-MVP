"""Shared text extraction helpers with OCR fallback for scanned PDFs."""

from __future__ import annotations

import logging
from io import BytesIO

from pypdf import PdfReader

from backend.config import settings

logger = logging.getLogger(__name__)

# Lazy imports for OCR — only loaded when needed
_ocr_available: bool | None = None


def _check_ocr_available() -> bool:
    """Check if pytesseract and PIL are installed."""
    global _ocr_available
    if _ocr_available is not None:
        return _ocr_available
    try:
        import pytesseract  # noqa: F401
        from PIL import Image  # noqa: F401

        # Also check that the tesseract binary is accessible
        pytesseract.get_tesseract_version()
        _ocr_available = True
    except Exception:
        _ocr_available = False
        logger.info("OCR not available (pytesseract/tesseract not installed). Scanned PDFs will return empty text.")
    return _ocr_available


def _ocr_pdf_pages(pdf_bytes: bytes) -> list[str]:
    """Extract text from a scanned PDF using OCR (pytesseract + pdf2image or PIL)."""
    try:
        import pytesseract
        from pdf2image import convert_from_bytes

        lang = settings.ocr_language
        images = convert_from_bytes(pdf_bytes)
        pages: list[str] = []
        for img in images:
            text = pytesseract.image_to_string(img, lang=lang)
            normalized = text.encode("utf-8", errors="surrogatepass").decode(
                "utf-8", errors="replace"
            )
            pages.append(normalized)
        return pages
    except ImportError:
        # Fallback: try rendering pages using pypdf + PIL directly
        try:
            import pytesseract
            from PIL import Image

            reader = PdfReader(BytesIO(pdf_bytes))
            pages: list[str] = []
            for page in reader.pages:
                page_images = []
                for image_obj in page.images:
                    try:
                        img = Image.open(BytesIO(image_obj.data))
                        page_images.append(img)
                    except Exception:
                        continue

                if page_images:
                    texts = []
                    for img in page_images:
                        text = pytesseract.image_to_string(img, lang=settings.ocr_language)
                        texts.append(text)
                    combined = "\n".join(texts)
                    normalized = combined.encode("utf-8", errors="surrogatepass").decode(
                        "utf-8", errors="replace"
                    )
                    pages.append(normalized)
                else:
                    pages.append("")
            return pages
        except Exception:
            logger.exception("OCR fallback with embedded images failed")
            return []
    except Exception:
        logger.exception("OCR extraction failed")
        return []


def _needs_ocr(pages: list[str]) -> bool:
    """Determine if the extracted text is too sparse and OCR should be attempted."""
    total_chars = sum(len(p.strip()) for p in pages)
    return total_chars < settings.ocr_min_chars_threshold


def extract_pdf_text(pdf_bytes: bytes) -> str:
    """Extract text from PDF bytes with surrogate-safe normalization.

    Falls back to OCR when regular text extraction yields too little content.
    """
    try:
        pages = extract_pdf_pages(pdf_bytes)
        full_text = "\n".join(pages)
        return full_text.encode("utf-8", errors="surrogatepass").decode(
            "utf-8", errors="replace"
        )
    except Exception:
        logger.exception("Failed to extract PDF text")
        return ""


def extract_pdf_pages(pdf_bytes: bytes) -> list[str]:
    """Extract PDF text page-by-page with surrogate-safe normalization.

    If regular extraction yields fewer than OCR_MIN_CHARS_THRESHOLD characters
    and OCR is enabled/available, falls back to OCR.
    """
    try:
        reader = PdfReader(BytesIO(pdf_bytes))
        pages: list[str] = []
        for page in reader.pages:
            text = page.extract_text() or ""
            normalized = text.encode("utf-8", errors="surrogatepass").decode(
                "utf-8", errors="replace"
            )
            pages.append(normalized)

        # Check if we need OCR fallback
        if _needs_ocr(pages) and settings.ocr_enabled and _check_ocr_available():
            logger.info(
                "PDF text extraction yielded < %d chars, attempting OCR fallback.",
                settings.ocr_min_chars_threshold,
            )
            ocr_pages = _ocr_pdf_pages(pdf_bytes)
            if ocr_pages and sum(len(p.strip()) for p in ocr_pages) > sum(len(p.strip()) for p in pages):
                logger.info("OCR produced more text (%d chars vs %d chars), using OCR result.",
                    sum(len(p.strip()) for p in ocr_pages),
                    sum(len(p.strip()) for p in pages),
                )
                return ocr_pages

        return pages
    except Exception:
        logger.exception("Failed to extract PDF pages")
        return []
