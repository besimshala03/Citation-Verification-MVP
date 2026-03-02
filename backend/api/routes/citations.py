"""Citation and verification routes."""

from __future__ import annotations

import logging
import sqlite3

from fastapi import APIRouter, Depends, HTTPException

from backend.auth import get_current_user
from backend.db import repository as repo
from backend.db.connection import get_db_connection
from backend.models.schemas import (
    BatchVerificationResponse,
    VerificationResultSchema,
    VerifyCitationRequest,
)
from backend.services.verification_service import process_citation_local

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/projects/{project_id}/citations")
async def get_citations(
    project_id: str,
    conn: sqlite3.Connection = Depends(get_db_connection),
    current_user: dict = Depends(get_current_user),
):
    project = repo.get_project(project_id, owner_id=current_user["id"], conn=conn)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found.")

    citations = repo.list_citations(project_id, conn=conn)
    return {"citations": citations}


@router.post(
    "/projects/{project_id}/verify-citation",
    response_model=VerificationResultSchema,
)
async def verify_citation(
    project_id: str,
    req: VerifyCitationRequest,
    conn: sqlite3.Connection = Depends(get_db_connection),
    current_user: dict = Depends(get_current_user),
):
    project = repo.get_project(project_id, owner_id=current_user["id"], conn=conn)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found.")

    citations = repo.list_citations(project_id, conn=conn)
    citation = next((c for c in citations if c["id"] == req.citation_id), None)
    if not citation:
        raise HTTPException(status_code=404, detail="Citation not found.")

    result = process_citation_local(conn, citation, project_id)
    repo.save_verification_result(
        citation_id=citation["id"],
        project_id=project_id,
        result={
            "source_type": result["source_type"],
            "matched_passage": result["matched_passage"],
            "label": result["evaluation"]["label"],
            "explanation": result["evaluation"]["explanation"],
            "confidence": result["evaluation"]["confidence"],
        },
        conn=conn,
    )
    return result


@router.post(
    "/projects/{project_id}/verify-all",
    response_model=BatchVerificationResponse,
)
async def verify_all_citations(
    project_id: str,
    conn: sqlite3.Connection = Depends(get_db_connection),
    current_user: dict = Depends(get_current_user),
):
    project = repo.get_project(project_id, owner_id=current_user["id"], conn=conn)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found.")

    citations = repo.list_citations(project_id, conn=conn)
    if not citations:
        raise HTTPException(status_code=400, detail="No citations found for this project.")

    results = []
    errors = 0
    for citation in citations:
        try:
            result = process_citation_local(conn, citation, project_id)
            repo.save_verification_result(
                citation_id=citation["id"],
                project_id=project_id,
                result={
                    "source_type": result["source_type"],
                    "matched_passage": result["matched_passage"],
                    "label": result["evaluation"]["label"],
                    "explanation": result["evaluation"]["explanation"],
                    "confidence": result["evaluation"]["confidence"],
                },
                conn=conn,
            )
            results.append({"citation_id": citation["id"], "result": result})
        except Exception:
            logger.exception("Error verifying citation %s", citation["id"])
            errors += 1

    return {
        "results": results,
        "total": len(citations),
        "verified": len(results),
        "errors": errors,
    }
