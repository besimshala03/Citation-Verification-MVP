"""Citation Verification MVP backend application."""

from __future__ import annotations

from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.api.routes import citations, documents, projects, references
from backend.db import repository as repo
from backend.logging_config import configure_logging

load_dotenv()
configure_logging()


@asynccontextmanager
async def lifespan(application: FastAPI):
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
