"""Reference entry and paper routes."""

from __future__ import annotations

import sqlite3
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import Response

from backend.auth import get_current_user
from backend.config import settings
from backend.db import repository as repo
from backend.db.connection import get_db_connection
from backend.services.paper_processing import extract_pdf_text

router = APIRouter()


@router.get("/projects/{project_id}/references")
async def list_references(
    project_id: str,
    conn: sqlite3.Connection = Depends(get_db_connection),
    current_user: dict = Depends(get_current_user),
):
    project = repo.get_project(project_id, owner_id=current_user["id"], conn=conn)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found.")

    references = repo.list_reference_entries(project_id, conn=conn)
    return {"references": references}


@router.post("/projects/{project_id}/references/{entry_id}/paper")
async def upload_reference_paper(
    project_id: str,
    entry_id: int,
    file: UploadFile = File(...),
    conn: sqlite3.Connection = Depends(get_db_connection),
    current_user: dict = Depends(get_current_user),
):
    project = repo.get_project(project_id, owner_id=current_user["id"], conn=conn)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found.")

    entry = repo.get_reference_entry(entry_id, conn=conn)
    if not entry or entry["project_id"] != project_id:
        raise HTTPException(status_code=404, detail="Reference entry not found.")

    filename = (file.filename or "").strip()
    if not filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=400, detail="Only PDF files are accepted for reference papers."
        )

    if file.content_type and file.content_type != "application/pdf":
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported MIME type: {file.content_type}",
        )

    file_bytes = await file.read()
    if len(file_bytes) > settings.max_reference_pdf_bytes:
        raise HTTPException(
            status_code=400,
            detail=f"Reference PDF exceeds max size of {settings.max_reference_pdf_bytes} bytes.",
        )

    extracted_text = extract_pdf_text(file_bytes)

    return repo.save_reference_paper(
        reference_entry_id=entry_id,
        project_id=project_id,
        filename=filename,
        file_bytes=file_bytes,
        extracted_text=extracted_text,
        conn=conn,
    )


@router.delete("/projects/{project_id}/references/{entry_id}/paper")
async def delete_reference_paper(
    project_id: str,
    entry_id: int,
    conn: sqlite3.Connection = Depends(get_db_connection),
    current_user: dict = Depends(get_current_user),
):
    project = repo.get_project(project_id, owner_id=current_user["id"], conn=conn)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found.")

    entry = repo.get_reference_entry(entry_id, conn=conn)
    if not entry or entry["project_id"] != project_id:
        raise HTTPException(status_code=404, detail="Reference entry not found.")

    deleted = repo.delete_reference_paper(entry_id, conn=conn)
    if not deleted:
        raise HTTPException(status_code=404, detail="No paper uploaded for this reference.")
    return {"deleted": True}


@router.get("/projects/{project_id}/references/{entry_id}/paper/file")
async def serve_reference_paper(
    project_id: str,
    entry_id: int,
    conn: sqlite3.Connection = Depends(get_db_connection),
    current_user: dict = Depends(get_current_user),
):
    project = repo.get_project(project_id, owner_id=current_user["id"], conn=conn)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found.")

    paper = repo.get_reference_paper(entry_id, conn=conn)
    if not paper or paper["project_id"] != project_id:
        raise HTTPException(status_code=404, detail="Reference paper not found.")

    disk_path = Path(paper["disk_path"])
    if not disk_path.exists():
        raise HTTPException(status_code=404, detail="Paper file missing from disk.")

    file_bytes = disk_path.read_bytes()
    return Response(content=file_bytes, media_type="application/pdf")
