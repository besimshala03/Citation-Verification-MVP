"""Citation Verification MVP backend application."""

from __future__ import annotations

from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.api.routes import auth, citations, documents, projects, references
from backend.config import settings
from backend.db import repository as repo
from backend.logging_config import configure_logging

load_dotenv()
configure_logging()


@asynccontextmanager
async def lifespan(application: FastAPI):
    if settings.jwt_secret_key in {"change-me-in-production", "change-this-to-a-long-random-secret"}:
        raise RuntimeError("JWT_SECRET_KEY must be set to a strong random value.")
    repo.init_db()
    yield


app = FastAPI(title="Citation Verification MVP", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(projects.router)
app.include_router(documents.router)
app.include_router(references.router)
app.include_router(citations.router)
app.include_router(auth.router)
