"""Database connection utilities and FastAPI dependency."""

from __future__ import annotations

import sqlite3
from collections.abc import Iterator

from backend.config import settings


def create_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(str(settings.db_path), check_same_thread=False, timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute("PRAGMA busy_timeout=10000")
    return conn


def get_db_connection() -> Iterator[sqlite3.Connection]:
    conn = create_connection()
    try:
        yield conn
    finally:
        conn.close()
