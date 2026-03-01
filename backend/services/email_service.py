"""SMTP email delivery service."""

from __future__ import annotations

import logging
import smtplib
from email.message import EmailMessage

from backend.config import settings

logger = logging.getLogger(__name__)


class EmailDeliveryError(RuntimeError):
    pass


def send_verification_email(to_email: str, code: str) -> None:
    if not settings.smtp_host or not settings.smtp_from_email:
        raise EmailDeliveryError("SMTP is not configured (SMTP_HOST/SMTP_FROM_EMAIL missing)")

    msg = EmailMessage()
    msg["Subject"] = "Verify your Citation Verifier account"
    msg["From"] = settings.smtp_from_email
    msg["To"] = to_email
    msg.set_content(
        "Your verification code is: "
        f"{code}\n\n"
        f"This code expires in {settings.email_verification_code_expire_minutes} minutes."
    )

    try:
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=20) as server:
            if settings.smtp_use_tls:
                server.starttls()
            if settings.smtp_username and settings.smtp_password:
                server.login(settings.smtp_username, settings.smtp_password)
            server.send_message(msg)
    except Exception as exc:
        logger.exception("Failed to send verification email")
        raise EmailDeliveryError("Failed to send verification email") from exc
