"""Shared upload validation helpers."""

from __future__ import annotations

from backend.config import settings
from backend.errors import AppValidationError

ALLOWED_MAIN_EXTENSIONS = (".pdf", ".docx")
ALLOWED_MAIN_MIME = {
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}
ALLOWED_REFERENCE_MIME = {"application/pdf"}


def validate_main_document_upload(
    filename: str,
    content_type: str | None,
    file_size: int,
) -> str:
    normalized = filename.strip()
    lower = normalized.lower()
    if not lower.endswith(ALLOWED_MAIN_EXTENSIONS):
        raise AppValidationError(
            "Unsupported file format. Only PDF and DOCX files are accepted."
        )

    if file_size > settings.max_main_document_bytes:
        raise AppValidationError(
            f"Main document exceeds max size of {settings.max_main_document_bytes} bytes."
        )

    if content_type and content_type not in ALLOWED_MAIN_MIME:
        raise AppValidationError(f"Unsupported MIME type: {content_type}")

    return normalized


def validate_reference_pdf_upload(
    filename: str,
    content_type: str | None,
    file_size: int,
) -> str:
    normalized = filename.strip()
    if not normalized.lower().endswith(".pdf"):
        raise AppValidationError("Only PDF files are accepted for reference papers.")
    if content_type and content_type not in ALLOWED_REFERENCE_MIME:
        raise AppValidationError(f"Unsupported MIME type: {content_type}")
    if file_size > settings.max_reference_pdf_bytes:
        raise AppValidationError(
            f"Reference PDF exceeds max size of {settings.max_reference_pdf_bytes} bytes."
        )
    return normalized

