"""Citation and verification routes."""

from __future__ import annotations

import logging
import sqlite3

from fastapi import APIRouter, Depends, HTTPException

from backend.db import repository as repo
from backend.db.connection import get_db_connection
from backend.models.schemas import VerificationResultSchema, VerifyCitationRequest
from backend.services.verification_service import build_error_result, process_citation_local

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/projects/{project_id}/citations")
async def get_citations(
    project_id: str,
    conn: sqlite3.Connection = Depends(get_db_connection),
):
    project = repo.get_project(project_id, conn=conn)
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
):
    project = repo.get_project(project_id, conn=conn)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found.")

    citations = repo.list_citations(project_id, conn=conn)
    citation = next((c for c in citations if c["id"] == req.citation_id), None)
    if not citation:
        raise HTTPException(status_code=404, detail="Citation not found.")

    try:
        result = process_citation_local(conn, citation)
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
    except Exception:
        logger.exception("Citation verification failed")
        return build_error_result(citation, "verification failed")
