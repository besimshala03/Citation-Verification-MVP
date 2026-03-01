"""Application-level exceptions and FastAPI exception handlers."""

from __future__ import annotations

import logging
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)


class AppValidationError(ValueError):
    """Raised for domain validation errors that should return HTTP 400."""


def install_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppValidationError)
    async def _validation_error_handler(
        request: Request, exc: AppValidationError
    ) -> JSONResponse:
        request_id = request.headers.get("X-Request-ID") or str(uuid4())
        return JSONResponse(
            status_code=400,
            content={"detail": str(exc), "request_id": request_id},
        )

    @app.exception_handler(Exception)
    async def _unhandled_error_handler(request: Request, exc: Exception) -> JSONResponse:
        request_id = request.headers.get("X-Request-ID") or str(uuid4())
        logger.exception("Unhandled backend error [request_id=%s]", request_id)
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal server error", "request_id": request_id},
        )

