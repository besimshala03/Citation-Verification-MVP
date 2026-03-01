"""Pydantic request/response schemas."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class CreateProjectRequest(BaseModel):
    name: str = Field(min_length=1, max_length=120)


class VerifyCitationRequest(BaseModel):
    citation_id: int


class RegisterRequest(BaseModel):
    email: str = Field(min_length=3, max_length=320)
    password: str = Field(min_length=8, max_length=256)


class LoginRequest(BaseModel):
    email: str = Field(min_length=3, max_length=320)
    password: str = Field(min_length=8, max_length=256)


class UserSchema(BaseModel):
    id: str
    email: str
    is_verified: bool
    created_at: str


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserSchema


class RegisterResponse(BaseModel):
    message: str
    email: str


class VerifyEmailRequest(BaseModel):
    email: str = Field(min_length=3, max_length=320)
    code: str = Field(min_length=4, max_length=12)


class ResendVerificationRequest(BaseModel):
    email: str = Field(min_length=3, max_length=320)


class MessageResponse(BaseModel):
    message: str


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
    evidence_page: int | None = None
    evidence_why: str | None = None
    evaluation: EvaluationSchema
