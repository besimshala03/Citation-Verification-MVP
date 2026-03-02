"""Pydantic request/response schemas."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator

from backend.config import settings


class CreateProjectRequest(BaseModel):
    name: str = Field(min_length=1, max_length=255)

    @field_validator("name")
    @classmethod
    def _validate_name(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("Project name cannot be empty.")
        if len(normalized) > settings.project_name_max_length:
            raise ValueError(
                f"Project name must be <= {settings.project_name_max_length} characters."
            )
        return normalized


class VerifyCitationRequest(BaseModel):
    citation_id: int


class RegisterRequest(BaseModel):
    email: str = Field(min_length=3, max_length=320)
    password: str = Field(min_length=8, max_length=256)

    @field_validator("email")
    @classmethod
    def _validate_email(cls, value: str) -> str:
        normalized = value.strip().lower()
        if "@" not in normalized or "." not in normalized.split("@")[-1]:
            raise ValueError("Invalid email address")
        return normalized


class LoginRequest(BaseModel):
    email: str = Field(min_length=3, max_length=320)
    password: str = Field(min_length=8, max_length=256)

    @field_validator("email")
    @classmethod
    def _validate_email(cls, value: str) -> str:
        normalized = value.strip().lower()
        if "@" not in normalized or "." not in normalized.split("@")[-1]:
            raise ValueError("Invalid email address")
        return normalized


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

    @field_validator("email")
    @classmethod
    def _validate_email(cls, value: str) -> str:
        normalized = value.strip().lower()
        if "@" not in normalized or "." not in normalized.split("@")[-1]:
            raise ValueError("Invalid email address")
        return normalized


class ResendVerificationRequest(BaseModel):
    email: str = Field(min_length=3, max_length=320)

    @field_validator("email")
    @classmethod
    def _validate_email(cls, value: str) -> str:
        normalized = value.strip().lower()
        if "@" not in normalized or "." not in normalized.split("@")[-1]:
            raise ValueError("Invalid email address")
        return normalized


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


class BatchVerificationItemSchema(BaseModel):
    citation_id: int
    result: VerificationResultSchema


class BatchVerificationResponse(BaseModel):
    results: list[BatchVerificationItemSchema]
    total: int
    verified: int
    errors: int
