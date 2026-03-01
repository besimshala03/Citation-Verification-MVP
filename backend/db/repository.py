"""SQLite persistence for projects, documents, references, citations, verification."""

from __future__ import annotations

import shutil
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

from backend.config import settings
from backend.db.connection import create_connection


@contextmanager
def _conn_scope(conn: sqlite3.Connection | None):
    if conn is not None:
        yield conn, False
        return

    local = create_connection()
    try:
        yield local, True
    finally:
        local.close()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def init_db(conn: sqlite3.Connection | None = None) -> None:
    with _conn_scope(conn) as (c, close_after):
        c.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
                id TEXT PRIMARY KEY,
                email TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                is_verified INTEGER NOT NULL DEFAULT 0,
                verification_code_hash TEXT,
                verification_expires_at TEXT,
                verified_at TEXT,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS projects (
                id TEXT PRIMARY KEY,
                owner_id TEXT REFERENCES users(id) ON DELETE CASCADE,
                name TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS documents (
                id TEXT PRIMARY KEY,
                project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
                filename TEXT NOT NULL,
                disk_path TEXT NOT NULL,
                full_text TEXT,
                main_text TEXT,
                bibliography_text TEXT,
                summary TEXT,
                uploaded_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS reference_entries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
                document_id TEXT NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
                entry_text TEXT NOT NULL,
                parsed_author TEXT,
                parsed_year TEXT,
                parsed_title TEXT,
                status TEXT NOT NULL DEFAULT 'pending'
            );

            CREATE TABLE IF NOT EXISTS reference_papers (
                id TEXT PRIMARY KEY,
                reference_entry_id INTEGER NOT NULL UNIQUE REFERENCES reference_entries(id) ON DELETE CASCADE,
                project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
                filename TEXT NOT NULL,
                disk_path TEXT NOT NULL,
                extracted_text TEXT,
                uploaded_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS citations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
                document_id TEXT NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
                citation_index INTEGER NOT NULL,
                citation_text TEXT NOT NULL,
                author TEXT NOT NULL,
                year TEXT NOT NULL,
                citing_paragraph TEXT NOT NULL,
                reference_entry_id INTEGER REFERENCES reference_entries(id)
            );

            CREATE TABLE IF NOT EXISTS verification_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                citation_id INTEGER NOT NULL REFERENCES citations(id) ON DELETE CASCADE,
                project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
                source_type TEXT NOT NULL,
                matched_passage TEXT,
                label TEXT NOT NULL,
                explanation TEXT NOT NULL,
                confidence REAL NOT NULL,
                verified_at TEXT NOT NULL
            );
            """
        )
        _ensure_documents_summary_column(c)
        _ensure_projects_owner_column(c)
        _ensure_users_verification_columns(c)
        c.commit()
        if close_after:
            return


def _ensure_documents_summary_column(conn: sqlite3.Connection) -> None:
    cols = conn.execute("PRAGMA table_info(documents)").fetchall()
    names = {row[1] for row in cols}
    if "summary" not in names:
        conn.execute("ALTER TABLE documents ADD COLUMN summary TEXT")


def _ensure_projects_owner_column(conn: sqlite3.Connection) -> None:
    cols = conn.execute("PRAGMA table_info(projects)").fetchall()
    names = {row[1] for row in cols}
    if "owner_id" not in names:
        conn.execute("ALTER TABLE projects ADD COLUMN owner_id TEXT")


def _ensure_users_verification_columns(conn: sqlite3.Connection) -> None:
    cols = conn.execute("PRAGMA table_info(users)").fetchall()
    names = {row[1] for row in cols}
    if "is_verified" not in names:
        conn.execute("ALTER TABLE users ADD COLUMN is_verified INTEGER NOT NULL DEFAULT 0")
    if "verification_code_hash" not in names:
        conn.execute("ALTER TABLE users ADD COLUMN verification_code_hash TEXT")
    if "verification_expires_at" not in names:
        conn.execute("ALTER TABLE users ADD COLUMN verification_expires_at TEXT")
    if "verified_at" not in names:
        conn.execute("ALTER TABLE users ADD COLUMN verified_at TEXT")


def _touch_project(conn: sqlite3.Connection, project_id: str) -> None:
    conn.execute("UPDATE projects SET updated_at = ? WHERE id = ?", (_now(), project_id))


def create_project(
    name: str, owner_id: str, conn: sqlite3.Connection | None = None
) -> dict:
    project_id = str(uuid.uuid4())
    now = _now()
    with _conn_scope(conn) as (c, close_after):
        c.execute(
            "INSERT INTO projects (id, owner_id, name, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
            (project_id, owner_id, name, now, now),
        )
        c.commit()
    return {
        "id": project_id,
        "owner_id": owner_id,
        "name": name,
        "created_at": now,
        "updated_at": now,
    }


def list_projects(owner_id: str, conn: sqlite3.Connection | None = None) -> list[dict]:
    with _conn_scope(conn) as (c, _):
        rows = c.execute(
            """
            SELECT
                p.id, p.name, p.created_at, p.updated_at,
                CASE WHEN d.id IS NOT NULL THEN 1 ELSE 0 END AS has_document,
                COALESCE(ref_stats.reference_count, 0) AS reference_count,
                COALESCE(ref_stats.references_uploaded, 0) AS references_uploaded,
                COALESCE(cit_stats.citation_count, 0) AS citation_count
            FROM projects p
            LEFT JOIN documents d ON d.project_id = p.id
            LEFT JOIN (
                SELECT project_id,
                       COUNT(*) AS reference_count,
                       SUM(CASE WHEN status = 'uploaded' THEN 1 ELSE 0 END) AS references_uploaded
                FROM reference_entries
                GROUP BY project_id
            ) ref_stats ON ref_stats.project_id = p.id
            LEFT JOIN (
                SELECT project_id, COUNT(*) AS citation_count
                FROM citations
                GROUP BY project_id
            ) cit_stats ON cit_stats.project_id = p.id
            WHERE p.owner_id = ?
            ORDER BY p.updated_at DESC
            """
            ,
            (owner_id,),
        ).fetchall()
    return [dict(row) for row in rows]


def get_project(
    project_id: str, owner_id: str, conn: sqlite3.Connection | None = None
) -> dict | None:
    with _conn_scope(conn) as (c, _):
        row = c.execute(
            "SELECT * FROM projects WHERE id = ? AND owner_id = ?",
            (project_id, owner_id),
        ).fetchone()
    return dict(row) if row else None


def delete_project(
    project_id: str, owner_id: str, conn: sqlite3.Connection | None = None
) -> bool:
    with _conn_scope(conn) as (c, _):
        row = c.execute(
            "SELECT id FROM projects WHERE id = ? AND owner_id = ?",
            (project_id, owner_id),
        ).fetchone()
        if not row:
            return False
        c.execute("DELETE FROM projects WHERE id = ? AND owner_id = ?", (project_id, owner_id))
        c.commit()

    project_dir = settings.storage_root / project_id
    if project_dir.exists():
        shutil.rmtree(project_dir, ignore_errors=True)

    return True


def save_document(
    project_id: str,
    filename: str,
    file_bytes: bytes,
    full_text: str,
    main_text: str,
    bibliography_text: str | None,
    summary: str | None = None,
    conn: sqlite3.Connection | None = None,
) -> dict:
    doc_id = str(uuid.uuid4())
    now = _now()

    doc_dir = settings.storage_root / project_id / "document"
    doc_dir.mkdir(parents=True, exist_ok=True)
    for existing in doc_dir.iterdir():
        if existing.is_file():
            existing.unlink()
    disk_path = doc_dir / filename
    disk_path.write_bytes(file_bytes)

    with _conn_scope(conn) as (c, _):
        c.execute("DELETE FROM documents WHERE project_id = ?", (project_id,))
        c.execute(
            """INSERT INTO documents (id, project_id, filename, disk_path, full_text, main_text, bibliography_text, summary, uploaded_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                doc_id,
                project_id,
                filename,
                str(disk_path),
                full_text,
                main_text,
                bibliography_text,
                summary,
                now,
            ),
        )
        _touch_project(c, project_id)
        c.commit()

    return {
        "id": doc_id,
        "project_id": project_id,
        "filename": filename,
        "disk_path": str(disk_path),
        "uploaded_at": now,
    }


def get_document(project_id: str, conn: sqlite3.Connection | None = None) -> dict | None:
    with _conn_scope(conn) as (c, _):
        row = c.execute("SELECT * FROM documents WHERE project_id = ?", (project_id,)).fetchone()
    return dict(row) if row else None


def create_reference_entries(
    project_id: str,
    document_id: str,
    entries: list[dict],
    conn: sqlite3.Connection | None = None,
) -> list[dict]:
    with _conn_scope(conn) as (c, _):
        c.execute("DELETE FROM reference_entries WHERE project_id = ?", (project_id,))
        created = []
        for entry in entries:
            cursor = c.execute(
                """INSERT INTO reference_entries
                   (project_id, document_id, entry_text, parsed_author, parsed_year, parsed_title, status)
                   VALUES (?, ?, ?, ?, ?, ?, 'pending')""",
                (
                    project_id,
                    document_id,
                    entry["entry_text"],
                    entry.get("parsed_author"),
                    entry.get("parsed_year"),
                    entry.get("parsed_title"),
                ),
            )
            created.append(
                {
                    "id": cursor.lastrowid,
                    "entry_text": entry["entry_text"],
                    "parsed_author": entry.get("parsed_author"),
                    "parsed_year": entry.get("parsed_year"),
                    "parsed_title": entry.get("parsed_title"),
                    "status": "pending",
                    "paper_filename": None,
                }
            )

        _touch_project(c, project_id)
        c.commit()

    return created


def list_reference_entries(project_id: str, conn: sqlite3.Connection | None = None) -> list[dict]:
    with _conn_scope(conn) as (c, _):
        rows = c.execute(
            """
            SELECT
                re.id, re.entry_text, re.parsed_author, re.parsed_year, re.parsed_title, re.status,
                rp.filename AS paper_filename
            FROM reference_entries re
            LEFT JOIN reference_papers rp ON rp.reference_entry_id = re.id
            WHERE re.project_id = ?
            ORDER BY re.id
            """,
            (project_id,),
        ).fetchall()
    return [dict(row) for row in rows]


def get_reference_entry(entry_id: int, conn: sqlite3.Connection | None = None) -> dict | None:
    with _conn_scope(conn) as (c, _):
        row = c.execute("SELECT * FROM reference_entries WHERE id = ?", (entry_id,)).fetchone()
    return dict(row) if row else None


def save_reference_paper(
    reference_entry_id: int,
    project_id: str,
    filename: str,
    file_bytes: bytes,
    extracted_text: str,
    conn: sqlite3.Connection | None = None,
) -> dict:
    paper_id = str(uuid.uuid4())
    now = _now()

    ref_dir = settings.storage_root / project_id / "references" / str(reference_entry_id)
    ref_dir.mkdir(parents=True, exist_ok=True)
    for existing in ref_dir.iterdir():
        if existing.is_file():
            existing.unlink()
    disk_path = ref_dir / filename
    disk_path.write_bytes(file_bytes)

    with _conn_scope(conn) as (c, _):
        c.execute("DELETE FROM reference_papers WHERE reference_entry_id = ?", (reference_entry_id,))
        c.execute(
            """INSERT INTO reference_papers
               (id, reference_entry_id, project_id, filename, disk_path, extracted_text, uploaded_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (paper_id, reference_entry_id, project_id, filename, str(disk_path), extracted_text, now),
        )
        c.execute("UPDATE reference_entries SET status = 'uploaded' WHERE id = ?", (reference_entry_id,))
        c.execute(
            """
            DELETE FROM verification_results
            WHERE citation_id IN (
                SELECT id FROM citations WHERE reference_entry_id = ?
            )
            """,
            (reference_entry_id,),
        )
        _touch_project(c, project_id)
        c.commit()

    return {
        "paper_id": paper_id,
        "reference_entry_id": reference_entry_id,
        "filename": filename,
        "text_length": len(extracted_text),
        "status": "uploaded",
    }


def get_reference_paper(reference_entry_id: int, conn: sqlite3.Connection | None = None) -> dict | None:
    with _conn_scope(conn) as (c, _):
        row = c.execute(
            "SELECT * FROM reference_papers WHERE reference_entry_id = ?",
            (reference_entry_id,),
        ).fetchone()
    return dict(row) if row else None


def delete_reference_paper(reference_entry_id: int, conn: sqlite3.Connection | None = None) -> bool:
    with _conn_scope(conn) as (c, _):
        paper = c.execute(
            "SELECT * FROM reference_papers WHERE reference_entry_id = ?",
            (reference_entry_id,),
        ).fetchone()
        if not paper:
            return False

        paper = dict(paper)
        c.execute("DELETE FROM reference_papers WHERE reference_entry_id = ?", (reference_entry_id,))
        c.execute("UPDATE reference_entries SET status = 'pending' WHERE id = ?", (reference_entry_id,))
        c.execute(
            """
            DELETE FROM verification_results
            WHERE citation_id IN (
                SELECT id FROM citations WHERE reference_entry_id = ?
            )
            """,
            (reference_entry_id,),
        )
        _touch_project(c, paper["project_id"])
        c.commit()

    disk_path = Path(paper["disk_path"])
    if disk_path.exists():
        disk_path.unlink()

    return True


def save_citations(
    project_id: str,
    document_id: str,
    citations: list[dict],
    conn: sqlite3.Connection | None = None,
) -> list[dict]:
    with _conn_scope(conn) as (c, _):
        c.execute("DELETE FROM citations WHERE project_id = ?", (project_id,))

        created = []
        for i, cit in enumerate(citations):
            cursor = c.execute(
                """INSERT INTO citations
                   (project_id, document_id, citation_index, citation_text, author, year,
                    citing_paragraph, reference_entry_id)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    project_id,
                    document_id,
                    i,
                    cit["citation_text"],
                    cit["author"],
                    cit["year"],
                    cit["citing_paragraph"],
                    cit.get("reference_entry_id"),
                ),
            )
            created.append(
                {
                    "id": cursor.lastrowid,
                    "citation_index": i,
                    "citation_text": cit["citation_text"],
                    "author": cit["author"],
                    "year": cit["year"],
                    "citing_paragraph": cit["citing_paragraph"],
                    "reference_entry_id": cit.get("reference_entry_id"),
                    "bibliography_match": cit.get("bibliography_match"),
                }
            )
        c.commit()

    return created


def list_citations(project_id: str, conn: sqlite3.Connection | None = None) -> list[dict]:
    with _conn_scope(conn) as (c, _):
        rows = c.execute(
            """
            SELECT
                c.id, c.citation_index, c.citation_text, c.author, c.year,
                c.citing_paragraph, c.reference_entry_id,
                re.entry_text AS bibliography_match,
                vr.label AS verification_label
            FROM citations c
            LEFT JOIN reference_entries re ON re.id = c.reference_entry_id
            LEFT JOIN verification_results vr ON vr.citation_id = c.id
            WHERE c.project_id = ?
            ORDER BY c.citation_index
            """,
            (project_id,),
        ).fetchall()
    return [dict(row) for row in rows]


def save_verification_result(
    citation_id: int,
    project_id: str,
    result: dict,
    conn: sqlite3.Connection | None = None,
) -> dict:
    now = _now()
    with _conn_scope(conn) as (c, _):
        c.execute("DELETE FROM verification_results WHERE citation_id = ?", (citation_id,))
        c.execute(
            """INSERT INTO verification_results
               (citation_id, project_id, source_type, matched_passage, label, explanation, confidence, verified_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                citation_id,
                project_id,
                result["source_type"],
                result.get("matched_passage"),
                result["label"],
                result["explanation"],
                result["confidence"],
                now,
            ),
        )
        _touch_project(c, project_id)
        c.commit()

    return {
        "citation_id": citation_id,
        "source_type": result["source_type"],
        "matched_passage": result.get("matched_passage"),
        "label": result["label"],
        "explanation": result["explanation"],
        "confidence": result["confidence"],
        "verified_at": now,
    }


def get_verification_result(citation_id: int, conn: sqlite3.Connection | None = None) -> dict | None:
    with _conn_scope(conn) as (c, _):
        row = c.execute("SELECT * FROM verification_results WHERE citation_id = ?", (citation_id,)).fetchone()
    return dict(row) if row else None
