"""Pydantic request/response schemas."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class CreateProjectRequest(BaseModel):
    name: str = Field(min_length=1, max_length=120)


class VerifyCitationRequest(BaseModel):
    citation_id: int


class EvaluationSchema(BaseModel):
    label: Literal["SUPPORTS", "CONTRADICTS", "NOT_RELEVANT", "UNCERTAIN"]
    explanation: str
    confidence: float


class PaperMetadataSchema(BaseModel):
    title: str
    authors: list[str]
    year: int | None


class VerificationResultSchema(BaseModel):
    citation_text: str
    author: str
    year: str
    citing_paragraph: str
    bibliography_match: str | None
    paper_found: bool
    paper_metadata: PaperMetadataSchema | None
    source_type: Literal["pdf", "not_uploaded", "not_found"]
    matched_passage: str | None
    evaluation: EvaluationSchema
