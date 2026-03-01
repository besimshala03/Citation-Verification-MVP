"""Authentication routes."""

from __future__ import annotations

import sqlite3
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status

from backend.auth import create_access_token, get_current_user, hash_password, verify_password
from backend.db.connection import get_db_connection
from backend.models.schemas import AuthResponse, LoginRequest, RegisterRequest

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=AuthResponse)
async def register(
    req: RegisterRequest,
    conn: sqlite3.Connection = Depends(get_db_connection),
):
    email = req.email.strip().lower()
    password = req.password

    existing = conn.execute("SELECT id FROM users WHERE email = ?", (email,)).fetchone()
    if existing:
        raise HTTPException(status_code=409, detail="Email already registered")

    user_id = str(uuid.uuid4())

    password_hash = hash_password(password)
    now = datetime.now(timezone.utc).isoformat()
    conn.execute(
        "INSERT INTO users (id, email, password_hash, created_at) VALUES (?, ?, ?, ?)",
        (user_id, email, password_hash, now),
    )
    conn.commit()

    token = create_access_token(user_id, email)
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {"id": user_id, "email": email, "created_at": now},
    }


@router.post("/login", response_model=AuthResponse)
async def login(
    req: LoginRequest,
    conn: sqlite3.Connection = Depends(get_db_connection),
):
    email = req.email.strip().lower()
    row = conn.execute(
        "SELECT id, email, password_hash, created_at FROM users WHERE email = ?",
        (email,),
    ).fetchone()
    if not row:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")

    user = dict(row)
    if not verify_password(req.password, user["password_hash"]):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")

    token = create_access_token(user["id"], user["email"])
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {"id": user["id"], "email": user["email"], "created_at": user["created_at"]},
    }


@router.get("/me")
async def me(current_user: dict = Depends(get_current_user)):
    return {"user": current_user}
