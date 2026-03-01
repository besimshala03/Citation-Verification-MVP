"""Project routes."""

from __future__ import annotations

import sqlite3

from fastapi import APIRouter, Depends, HTTPException

from backend.auth import get_current_user
from backend.db.connection import get_db_connection
from backend.db import repository as repo
from backend.models.schemas import CreateProjectRequest

router = APIRouter()


@router.post("/projects")
async def create_project(
    req: CreateProjectRequest,
    conn: sqlite3.Connection = Depends(get_db_connection),
    current_user: dict = Depends(get_current_user),
):
    return repo.create_project(req.name, owner_id=current_user["id"], conn=conn)


@router.get("/projects")
async def list_projects(
    conn: sqlite3.Connection = Depends(get_db_connection),
    current_user: dict = Depends(get_current_user),
):
    return {"projects": repo.list_projects(owner_id=current_user["id"], conn=conn)}


@router.get("/projects/{project_id}")
async def get_project(
    project_id: str,
    conn: sqlite3.Connection = Depends(get_db_connection),
    current_user: dict = Depends(get_current_user),
):
    project = repo.get_project(project_id, owner_id=current_user["id"], conn=conn)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found.")

    document = repo.get_document(project_id, conn=conn)
    references = repo.list_reference_entries(project_id, conn=conn)
    citations = repo.list_citations(project_id, conn=conn)

    return {
        "id": project["id"],
        "name": project["name"],
        "created_at": project["created_at"],
        "updated_at": project["updated_at"],
        "document": (
            {"id": document["id"], "filename": document["filename"]}
            if document
            else None
        ),
        "reference_entries": references,
        "citation_count": len(citations),
        "document_summary": (document.get("summary") if document else None),
        "warning": None,
    }


@router.delete("/projects/{project_id}")
async def delete_project(
    project_id: str,
    conn: sqlite3.Connection = Depends(get_db_connection),
    current_user: dict = Depends(get_current_user),
):
    deleted = repo.delete_project(project_id, owner_id=current_user["id"], conn=conn)
    if not deleted:
        raise HTTPException(status_code=404, detail="Project not found.")
    return {"deleted": True}
