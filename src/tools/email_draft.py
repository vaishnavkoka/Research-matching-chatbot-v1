"""Draft (and optionally send) a collaboration / match summary email.
Draft-only works with no config; SMTP send activates when SMTP_* env vars exist.
This is gated behind Human-in-the-Loop confirmation.
"""
from __future__ import annotations

import os
import smtplib
from datetime import datetime
from email.mime.text import MIMEText
from pathlib import Path

from src.config import (SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD, SMTP_FROM,
                        EMAIL_DRAFTS_DIR)


def draft_email(to_name: str, to_email: str, subject: str, body: str) -> dict:
    """Compose a structured email and persist it as a draft file. Returns the draft."""
    draft = {
        "to_name": to_name,
        "to_email": to_email,
        "subject": subject,
        "body": body,
        "created_at": datetime.now().isoformat(timespec="seconds"),
    }
    Path(EMAIL_DRAFTS_DIR).mkdir(parents=True, exist_ok=True)
    fname = f"draft_{to_email.split('@')[0]}_{int(datetime.now().timestamp())}.txt"
    path = Path(EMAIL_DRAFTS_DIR) / fname
    path.write_text(
        f"To: {to_name} <{to_email}>\nSubject: {subject}\n\n{body}\n", encoding="utf-8"
    )
    draft["saved_to"] = str(path)
    return draft


def send_email(draft: dict) -> str:
    """Send a previously composed draft via SMTP if configured; else stay draft-only."""
    if not (SMTP_HOST and SMTP_USER and SMTP_PASSWORD):
        return f"SMTP not configured — draft saved to {draft.get('saved_to')} (not sent)."
    try:
        msg = MIMEText(draft["body"], "plain", "utf-8")
        msg["Subject"] = draft["subject"]
        msg["From"] = SMTP_FROM or SMTP_USER
        msg["To"] = draft["to_email"]
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.sendmail(msg["From"], [draft["to_email"]], msg.as_string())
        return f"Email sent to {draft['to_email']}."
    except Exception as exc:
        return f"SMTP send failed ({exc}); draft preserved at {draft.get('saved_to')}."
