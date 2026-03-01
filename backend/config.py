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
    log_level=os.getenv("LOG_LEVEL", "INFO"),
)
