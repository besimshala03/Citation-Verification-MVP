"""Authentication routes."""

from __future__ import annotations

import sqlite3
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status

from backend.auth import (
    create_access_token,
    generate_verification_code,
    get_current_user,
    hash_password,
    hash_verification_code,
    verification_expiry_iso,
    verify_password,
)
from backend.db.connection import get_db_connection
from backend.models.schemas import (
    AuthResponse,
    LoginRequest,
    MessageResponse,
    RegisterRequest,
    RegisterResponse,
    ResendVerificationRequest,
    VerifyEmailRequest,
)
from backend.services.email_service import EmailDeliveryError, send_verification_email

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=RegisterResponse)
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

    code = generate_verification_code()
    code_hash = hash_verification_code(code)
    expires_at = verification_expiry_iso()
    password_hash = hash_password(password)
    now = datetime.now(timezone.utc).isoformat()
    try:
        conn.execute(
            """
            INSERT INTO users
            (id, email, password_hash, is_verified, verification_code_hash, verification_expires_at, created_at)
            VALUES (?, ?, ?, 0, ?, ?, ?)
            """,
            (user_id, email, password_hash, code_hash, expires_at, now),
        )
        conn.commit()
        send_verification_email(email, code)
    except EmailDeliveryError as exc:
        conn.execute("DELETE FROM users WHERE id = ?", (user_id,))
        conn.commit()
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    return {"message": "Verification code sent to your email.", "email": email}


@router.post("/login", response_model=AuthResponse)
async def login(
    req: LoginRequest,
    conn: sqlite3.Connection = Depends(get_db_connection),
):
    email = req.email.strip().lower()
    row = conn.execute(
        "SELECT id, email, password_hash, is_verified, created_at FROM users WHERE email = ?",
        (email,),
    ).fetchone()
    if not row:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")

    user = dict(row)
    if not verify_password(req.password, user["password_hash"]):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")
    if not bool(user["is_verified"]):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Email not verified")

    token = create_access_token(user["id"], user["email"])
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "id": user["id"],
            "email": user["email"],
            "is_verified": bool(user["is_verified"]),
            "created_at": user["created_at"],
        },
    }


@router.post("/verify-email", response_model=AuthResponse)
async def verify_email(
    req: VerifyEmailRequest,
    conn: sqlite3.Connection = Depends(get_db_connection),
):
    email = req.email.strip().lower()
    code_hash = hash_verification_code(req.code.strip())

    row = conn.execute(
        """
        SELECT id, email, is_verified, verification_code_hash, verification_expires_at, created_at
        FROM users WHERE email = ?
        """,
        (email,),
    ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="User not found")

    user = dict(row)
    if bool(user["is_verified"]):
        token = create_access_token(user["id"], user["email"])
        return {
            "access_token": token,
            "token_type": "bearer",
            "user": {
                "id": user["id"],
                "email": user["email"],
                "is_verified": True,
                "created_at": user["created_at"],
            },
        }

    exp = user.get("verification_expires_at")
    if not user.get("verification_code_hash") or not exp:
        raise HTTPException(status_code=400, detail="No active verification code")

    expires_dt = datetime.fromisoformat(exp)
    if datetime.now(timezone.utc) > expires_dt:
        raise HTTPException(status_code=400, detail="Verification code expired")
    if code_hash != user["verification_code_hash"]:
        raise HTTPException(status_code=400, detail="Invalid verification code")

    now = datetime.now(timezone.utc).isoformat()
    conn.execute(
        """
        UPDATE users
        SET is_verified = 1,
            verification_code_hash = NULL,
            verification_expires_at = NULL,
            verified_at = ?
        WHERE id = ?
        """,
        (now, user["id"]),
    )
    conn.commit()

    token = create_access_token(user["id"], user["email"])
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "id": user["id"],
            "email": user["email"],
            "is_verified": True,
            "created_at": user["created_at"],
        },
    }


@router.post("/resend-verification", response_model=MessageResponse)
async def resend_verification(
    req: ResendVerificationRequest,
    conn: sqlite3.Connection = Depends(get_db_connection),
):
    email = req.email.strip().lower()
    row = conn.execute(
        "SELECT id, is_verified FROM users WHERE email = ?",
        (email,),
    ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="User not found")
    user = dict(row)
    if bool(user["is_verified"]):
        return {"message": "Email is already verified."}

    code = generate_verification_code()
    code_hash = hash_verification_code(code)
    expires_at = verification_expiry_iso()
    try:
        conn.execute(
            """
            UPDATE users
            SET verification_code_hash = ?, verification_expires_at = ?
            WHERE id = ?
            """,
            (code_hash, expires_at, user["id"]),
        )
        conn.commit()
        send_verification_email(email, code)
    except EmailDeliveryError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return {"message": "Verification code resent."}


@router.get("/me")
async def me(current_user: dict = Depends(get_current_user)):
    return {"user": current_user}
