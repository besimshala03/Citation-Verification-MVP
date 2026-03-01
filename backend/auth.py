"""Authentication and authorization helpers."""

from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from passlib.context import CryptContext

from backend.config import settings
from backend.db.connection import get_db_connection

# Use pbkdf2_sha256 for stable, secure password hashing without native backend
# compatibility issues.
pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")
bearer_scheme = HTTPBearer(auto_error=False)


class AuthError(HTTPException):
    def __init__(self, detail: str = "Invalid authentication credentials"):
        super().__init__(status_code=status.HTTP_401_UNAUTHORIZED, detail=detail)


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(user_id: str, email: str) -> str:
    now = datetime.now(timezone.utc)
    expire = now + timedelta(minutes=settings.jwt_access_token_expire_minutes)
    payload: dict[str, Any] = {
        "sub": user_id,
        "email": email,
        "iat": int(now.timestamp()),
        "exp": int(expire.timestamp()),
        "type": "access",
    }
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> dict[str, Any]:
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
        )
        if payload.get("type") != "access":
            raise AuthError()
        return payload
    except JWTError as exc:
        raise AuthError() from exc


def get_user_from_token_string(token: str, conn: sqlite3.Connection) -> dict:
    payload = decode_access_token(token)
    user_id = payload.get("sub")
    if not user_id:
        raise AuthError()
    row = conn.execute(
        "SELECT id, email, created_at FROM users WHERE id = ?",
        (user_id,),
    ).fetchone()
    if not row:
        raise AuthError()
    return dict(row)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    conn: sqlite3.Connection = Depends(get_db_connection),
) -> dict:
    if not credentials or credentials.scheme.lower() != "bearer":
        raise AuthError("Not authenticated")

    return get_user_from_token_string(credentials.credentials, conn)


def get_current_user_optional(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    conn: sqlite3.Connection = Depends(get_db_connection),
) -> dict | None:
    if not credentials or credentials.scheme.lower() != "bearer":
        return None
    try:
        return get_user_from_token_string(credentials.credentials, conn)
    except AuthError:
        return None
