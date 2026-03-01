"""Document routes."""

from __future__ import annotations

import sqlite3
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import Response

from backend.auth import get_current_user
from backend.db import repository as repo
from backend.db.connection import get_db_connection
from backend.services.document_ingestion import ingest_document

router = APIRouter()


@router.post("/projects/{project_id}/document")
async def upload_document(
    project_id: str,
    file: UploadFile = File(...),
    conn: sqlite3.Connection = Depends(get_db_connection),
    current_user: dict = Depends(get_current_user),
):
    project = repo.get_project(project_id, owner_id=current_user["id"], conn=conn)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found.")

    return await ingest_document(conn, project_id, file)


@router.get("/projects/{project_id}/document/file")
async def serve_document(
    project_id: str,
    conn: sqlite3.Connection = Depends(get_db_connection),
    current_user: dict = Depends(get_current_user),
):
    project = repo.get_project(project_id, owner_id=current_user["id"], conn=conn)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found.")

    doc = repo.get_document(project_id, conn=conn)
    if not doc:
        raise HTTPException(status_code=404, detail="No document uploaded.")

    disk_path = Path(doc["disk_path"])
    if not disk_path.exists():
        raise HTTPException(status_code=404, detail="Document file missing from disk.")

    file_bytes = disk_path.read_bytes()
    filename = doc["filename"]
    media_type = (
        "application/pdf"
        if filename.lower().endswith(".pdf")
        else "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    )
    return Response(content=file_bytes, media_type=media_type)
