"""Centralized application configuration loaded from environment variables."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

# Ensure .env is loaded before any settings are read.
load_dotenv()


@dataclass(frozen=True)
class Settings:
    model_name: str
    max_paper_chars: int
    max_summary_input_chars: int
    db_path: Path
    storage_root: Path
    citation_chunk_size: int
    citation_chunk_overlap: int
    citation_context_max_chars: int
    project_name_max_length: int
    max_main_document_bytes: int
    max_reference_pdf_bytes: int
    jwt_secret_key: str
    jwt_algorithm: str
    jwt_access_token_expire_minutes: int
    email_verification_code_expire_minutes: int
    smtp_host: str | None
    smtp_port: int
    smtp_username: str | None
    smtp_password: str | None
    smtp_from_email: str | None
    smtp_use_tls: bool
    log_level: str


_ROOT = Path(__file__).resolve().parent.parent


def _int_env(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


def _bool_env(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


settings = Settings(
    model_name=os.getenv("MODEL_NAME", "gpt-4o"),
    max_paper_chars=_int_env("MAX_PAPER_CHARS", 100_000),
    max_summary_input_chars=_int_env("MAX_SUMMARY_INPUT_CHARS", 20_000),
    db_path=Path(os.getenv("DB_PATH", str(_ROOT / "citation_verifier.db"))),
    storage_root=Path(os.getenv("STORAGE_ROOT", str(_ROOT / "storage" / "projects"))),
    citation_chunk_size=_int_env("CITATION_CHUNK_SIZE", 700),
    citation_chunk_overlap=_int_env("CITATION_CHUNK_OVERLAP", 150),
    citation_context_max_chars=_int_env("CITATION_CONTEXT_MAX_CHARS", 1200),
    project_name_max_length=_int_env("PROJECT_NAME_MAX_LENGTH", 120),
    max_main_document_bytes=_int_env("MAX_MAIN_DOCUMENT_BYTES", 20 * 1024 * 1024),
    max_reference_pdf_bytes=_int_env("MAX_REFERENCE_PDF_BYTES", 50 * 1024 * 1024),
    jwt_secret_key=os.getenv("JWT_SECRET_KEY", "change-me-in-production"),
    jwt_algorithm=os.getenv("JWT_ALGORITHM", "HS256"),
    jwt_access_token_expire_minutes=_int_env("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", 60 * 24),
    email_verification_code_expire_minutes=_int_env(
        "EMAIL_VERIFICATION_CODE_EXPIRE_MINUTES", 15
    ),
    smtp_host=os.getenv("SMTP_HOST"),
    smtp_port=_int_env("SMTP_PORT", 587),
    smtp_username=os.getenv("SMTP_USERNAME"),
    smtp_password=os.getenv("SMTP_PASSWORD"),
    smtp_from_email=os.getenv("SMTP_FROM_EMAIL"),
    smtp_use_tls=_bool_env("SMTP_USE_TLS", True),
    log_level=os.getenv("LOG_LEVEL", "INFO"),
)
