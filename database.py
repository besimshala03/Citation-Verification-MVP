"""Database module: SQLite persistence for projects, documents, references, and citations."""

import os
import shutil
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path

_DB_PATH = Path(__file__).parent / "citation_verifier.db"
_STORAGE_ROOT = Path(__file__).parent / "storage" / "projects"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def get_connection() -> sqlite3.Connection:
    """Return a connection with row_factory = sqlite3.Row."""
    conn = sqlite3.connect(str(_DB_PATH), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db() -> None:
    """Create tables if they don't exist. Called at app startup."""
    conn = get_connection()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS projects (
            id TEXT PRIMARY KEY,
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
    """)
    conn.commit()
    conn.close()


# ---------------------------------------------------------------------------
# Projects
# ---------------------------------------------------------------------------

def create_project(name: str) -> dict:
    """Insert a new project. Returns the created project dict."""
    project_id = str(uuid.uuid4())
    now = _now()
    conn = get_connection()
    conn.execute(
        "INSERT INTO projects (id, name, created_at, updated_at) VALUES (?, ?, ?, ?)",
        (project_id, name, now, now),
    )
    conn.commit()
    conn.close()
    return {"id": project_id, "name": name, "created_at": now, "updated_at": now}


def list_projects() -> list[dict]:
    """Return all projects with summary stats, ordered by updated_at desc."""
    conn = get_connection()
    rows = conn.execute("""
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
        ORDER BY p.updated_at DESC
    """).fetchall()
    conn.close()
    return [dict(row) for row in rows]


def get_project(project_id: str) -> dict | None:
    """Get a single project by ID."""
    conn = get_connection()
    row = conn.execute("SELECT * FROM projects WHERE id = ?", (project_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def delete_project(project_id: str) -> bool:
    """Delete project and all associated data, including disk files."""
    conn = get_connection()
    row = conn.execute("SELECT id FROM projects WHERE id = ?", (project_id,)).fetchone()
    if not row:
        conn.close()
        return False

    conn.execute("DELETE FROM projects WHERE id = ?", (project_id,))
    conn.commit()
    conn.close()

    # Clean up disk storage
    project_dir = _STORAGE_ROOT / project_id
    if project_dir.exists():
        shutil.rmtree(project_dir, ignore_errors=True)

    return True


def _touch_project(conn: sqlite3.Connection, project_id: str) -> None:
    """Update the updated_at timestamp for a project."""
    conn.execute(
        "UPDATE projects SET updated_at = ? WHERE id = ?", (_now(), project_id)
    )


# ---------------------------------------------------------------------------
# Documents
# ---------------------------------------------------------------------------

def save_document(
    project_id: str,
    filename: str,
    file_bytes: bytes,
    full_text: str,
    main_text: str,
    bibliography_text: str | None,
) -> dict:
    """Save the main document for a project. Stores file on disk, metadata in DB.

    If a document already exists for this project, it is replaced.
    """
    doc_id = str(uuid.uuid4())
    now = _now()

    # Save file to disk
    doc_dir = _STORAGE_ROOT / project_id / "document"
    doc_dir.mkdir(parents=True, exist_ok=True)
    # Remove any existing document files
    for existing in doc_dir.iterdir():
        existing.unlink()
    disk_path = doc_dir / filename
    disk_path.write_bytes(file_bytes)

    conn = get_connection()
    # Remove existing document (cascade deletes refs, citations, etc.)
    conn.execute("DELETE FROM documents WHERE project_id = ?", (project_id,))

    conn.execute(
        """INSERT INTO documents (id, project_id, filename, disk_path, full_text, main_text, bibliography_text, uploaded_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (doc_id, project_id, filename, str(disk_path), full_text, main_text, bibliography_text, now),
    )
    _touch_project(conn, project_id)
    conn.commit()
    conn.close()

    return {
        "id": doc_id,
        "project_id": project_id,
        "filename": filename,
        "disk_path": str(disk_path),
        "uploaded_at": now,
    }


def get_document(project_id: str) -> dict | None:
    """Get the document for a project."""
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM documents WHERE project_id = ?", (project_id,)
    ).fetchone()
    conn.close()
    return dict(row) if row else None


# ---------------------------------------------------------------------------
# Reference Entries
# ---------------------------------------------------------------------------

def create_reference_entries(
    project_id: str, document_id: str, entries: list[dict]
) -> list[dict]:
    """Bulk-insert parsed reference entries.

    Each entry dict should have: entry_text, parsed_author, parsed_year, parsed_title.
    """
    conn = get_connection()
    # Clear existing entries for this project
    conn.execute("DELETE FROM reference_entries WHERE project_id = ?", (project_id,))

    created = []
    for entry in entries:
        cursor = conn.execute(
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
        created.append({
            "id": cursor.lastrowid,
            "entry_text": entry["entry_text"],
            "parsed_author": entry.get("parsed_author"),
            "parsed_year": entry.get("parsed_year"),
            "parsed_title": entry.get("parsed_title"),
            "status": "pending",
            "paper_filename": None,
        })

    _touch_project(conn, project_id)
    conn.commit()
    conn.close()
    return created


def list_reference_entries(project_id: str) -> list[dict]:
    """List all reference entries for a project, including paper upload info."""
    conn = get_connection()
    rows = conn.execute("""
        SELECT
            re.id, re.entry_text, re.parsed_author, re.parsed_year, re.parsed_title, re.status,
            rp.filename AS paper_filename
        FROM reference_entries re
        LEFT JOIN reference_papers rp ON rp.reference_entry_id = re.id
        WHERE re.project_id = ?
        ORDER BY re.id
    """, (project_id,)).fetchall()
    conn.close()
    return [dict(row) for row in rows]


def get_reference_entry(entry_id: int) -> dict | None:
    """Get a single reference entry by ID."""
    conn = get_connection()
    row = conn.execute("SELECT * FROM reference_entries WHERE id = ?", (entry_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


# ---------------------------------------------------------------------------
# Reference Papers
# ---------------------------------------------------------------------------

def save_reference_paper(
    reference_entry_id: int,
    project_id: str,
    filename: str,
    file_bytes: bytes,
    extracted_text: str,
) -> dict:
    """Save an uploaded reference paper. Also clears old verification results."""
    paper_id = str(uuid.uuid4())
    now = _now()

    # Save file to disk
    ref_dir = _STORAGE_ROOT / project_id / "references" / str(reference_entry_id)
    ref_dir.mkdir(parents=True, exist_ok=True)
    for existing in ref_dir.iterdir():
        existing.unlink()
    disk_path = ref_dir / filename
    disk_path.write_bytes(file_bytes)

    conn = get_connection()
    # Remove existing paper for this entry if any
    conn.execute("DELETE FROM reference_papers WHERE reference_entry_id = ?", (reference_entry_id,))

    conn.execute(
        """INSERT INTO reference_papers
           (id, reference_entry_id, project_id, filename, disk_path, extracted_text, uploaded_at)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (paper_id, reference_entry_id, project_id, filename, str(disk_path), extracted_text, now),
    )

    # Update entry status
    conn.execute(
        "UPDATE reference_entries SET status = 'uploaded' WHERE id = ?",
        (reference_entry_id,),
    )

    # Clear verification results for citations matched to this reference entry
    conn.execute("""
        DELETE FROM verification_results
        WHERE citation_id IN (
            SELECT id FROM citations WHERE reference_entry_id = ?
        )
    """, (reference_entry_id,))

    _touch_project(conn, project_id)
    conn.commit()
    conn.close()

    return {
        "paper_id": paper_id,
        "reference_entry_id": reference_entry_id,
        "filename": filename,
        "text_length": len(extracted_text),
        "status": "uploaded",
    }


def get_reference_paper(reference_entry_id: int) -> dict | None:
    """Get the uploaded paper for a reference entry."""
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM reference_papers WHERE reference_entry_id = ?",
        (reference_entry_id,),
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def delete_reference_paper(reference_entry_id: int) -> bool:
    """Delete paper row and disk file, reset entry status to 'pending'."""
    conn = get_connection()
    paper = conn.execute(
        "SELECT * FROM reference_papers WHERE reference_entry_id = ?",
        (reference_entry_id,),
    ).fetchone()
    if not paper:
        conn.close()
        return False

    paper = dict(paper)
    conn.execute("DELETE FROM reference_papers WHERE reference_entry_id = ?", (reference_entry_id,))
    conn.execute(
        "UPDATE reference_entries SET status = 'pending' WHERE id = ?",
        (reference_entry_id,),
    )

    # Clear verification results for citations matched to this entry
    conn.execute("""
        DELETE FROM verification_results
        WHERE citation_id IN (
            SELECT id FROM citations WHERE reference_entry_id = ?
        )
    """, (reference_entry_id,))

    _touch_project(conn, paper["project_id"])
    conn.commit()
    conn.close()

    # Remove file from disk
    disk_path = Path(paper["disk_path"])
    if disk_path.exists():
        disk_path.unlink()

    return True


# ---------------------------------------------------------------------------
# Citations
# ---------------------------------------------------------------------------

def save_citations(
    project_id: str, document_id: str, citations: list[dict]
) -> list[dict]:
    """Bulk-insert detected citations with their reference_entry_id matches."""
    conn = get_connection()
    # Clear existing citations for this project
    conn.execute("DELETE FROM citations WHERE project_id = ?", (project_id,))

    created = []
    for i, cit in enumerate(citations):
        cursor = conn.execute(
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
        created.append({
            "id": cursor.lastrowid,
            "citation_index": i,
            "citation_text": cit["citation_text"],
            "author": cit["author"],
            "year": cit["year"],
            "citing_paragraph": cit["citing_paragraph"],
            "reference_entry_id": cit.get("reference_entry_id"),
            "bibliography_match": cit.get("bibliography_match"),
        })

    conn.commit()
    conn.close()
    return created


def list_citations(project_id: str) -> list[dict]:
    """List all citations for a project, including verification status."""
    conn = get_connection()
    rows = conn.execute("""
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
    """, (project_id,)).fetchall()
    conn.close()
    return [dict(row) for row in rows]


# ---------------------------------------------------------------------------
# Verification Results
# ---------------------------------------------------------------------------

def save_verification_result(
    citation_id: int, project_id: str, result: dict
) -> dict:
    """Insert or replace a verification result for a citation."""
    now = _now()
    conn = get_connection()
    # Remove existing result for this citation
    conn.execute("DELETE FROM verification_results WHERE citation_id = ?", (citation_id,))

    conn.execute(
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
    _touch_project(conn, project_id)
    conn.commit()
    conn.close()

    return {
        "citation_id": citation_id,
        "source_type": result["source_type"],
        "matched_passage": result.get("matched_passage"),
        "label": result["label"],
        "explanation": result["explanation"],
        "confidence": result["confidence"],
        "verified_at": now,
    }


def get_verification_result(citation_id: int) -> dict | None:
    """Get the verification result for a citation."""
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM verification_results WHERE citation_id = ?",
        (citation_id,),
    ).fetchone()
    conn.close()
    return dict(row) if row else None
