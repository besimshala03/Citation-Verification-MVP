"""Citation Verification MVP backend application."""

from __future__ import annotations

from contextlib import asynccontextmanager
from uuid import uuid4

from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response

from backend.api.routes import auth, citations, documents, exports, projects, references
from backend.config import settings
from backend.db import repository as repo
from backend.errors import install_exception_handlers
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
install_exception_handlers(app)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def request_id_middleware(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID") or str(uuid4())
    response: Response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response


app.include_router(projects.router)
app.include_router(documents.router)
app.include_router(references.router)
app.include_router(citations.router)
app.include_router(exports.router)
app.include_router(auth.router)
