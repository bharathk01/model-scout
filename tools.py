"""Tools for the ModelScout agent.

The Hugging Face calls are real and need no API key. `send_digest` emails the
digest when SMTP is configured (env vars below), and always keeps a local copy
as a fallback.

Email is enabled by setting these env vars (see .env.example):
    SMTP_HOST, SMTP_PORT (default 587), SMTP_USER, SMTP_PASSWORD,
    EMAIL_FROM, EMAIL_TO
If any required one is missing, the digest is saved to disk only.
"""

import os
import smtplib
from datetime import datetime, timedelta, timezone
from email.message import EmailMessage
from pathlib import Path

from huggingface_hub import list_models
from langchain_core.tools import tool


@tool
def get_recent_models(pipeline_tag: str = "text-generation", since_hours: int = 24, limit: int = 15) -> str:
    """List models newly published on the Hugging Face Hub.

    Args:
        pipeline_tag: Task filter, e.g. "text-generation", "text-to-image",
            "automatic-speech-recognition".
        since_hours: Only include models created within this many hours.
        limit: Max number of models to scan (newest first).
    """
    cutoff = datetime.now(timezone.utc) - timedelta(hours=since_hours)
    models = list_models(sort="createdAt", pipeline_tag=pipeline_tag, limit=limit, full=True)

    rows = []
    for m in models:
        created = getattr(m, "created_at", None)
        if created is None or created < cutoff:
            continue
        rows.append(
            f"- {m.id} | created {created:%Y-%m-%d %H:%M UTC} "
            f"| downloads={getattr(m, 'downloads', 0)} likes={getattr(m, 'likes', 0)}"
        )

    if not rows:
        return f"No new '{pipeline_tag}' models in the last {since_hours}h."
    return f"New '{pipeline_tag}' models (last {since_hours}h):\n" + "\n".join(rows)


@tool
def get_trending_models(pipeline_tag: str = "text-generation", limit: int = 10) -> str:
    """List currently trending models on the Hugging Face Hub for a task."""
    models = list_models(sort="trendingScore", pipeline_tag=pipeline_tag, limit=limit, full=True)
    rows = [
        f"- {m.id} | downloads={getattr(m, 'downloads', 0)} likes={getattr(m, 'likes', 0)}"
        for m in models
    ]
    return f"Trending '{pipeline_tag}' models:\n" + "\n".join(rows)


def _email_config() -> dict | None:
    """Return SMTP config from env, or None if it isn't fully set."""
    required = {
        "host": os.getenv("SMTP_HOST"),
        "user": os.getenv("SMTP_USER"),
        "password": os.getenv("SMTP_PASSWORD"),
        "sender": os.getenv("EMAIL_FROM"),
        "recipient": os.getenv("EMAIL_TO"),
    }
    if not all(required.values()):
        return None
    required["port"] = int(os.getenv("SMTP_PORT", "587"))
    return required


def _send_email(cfg: dict, subject: str, body: str) -> None:
    """Send one plain-text email over STARTTLS. Raises on failure."""
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = cfg["sender"]
    msg["To"] = cfg["recipient"]
    msg.set_content(body)

    with smtplib.SMTP(cfg["host"], cfg["port"], timeout=30) as smtp:
        smtp.starttls()
        smtp.login(cfg["user"], cfg["password"])
        smtp.send_message(msg)


@tool
def send_digest(title: str, body_markdown: str) -> str:
    """Deliver a finished digest by email (if SMTP is configured) and always
    save a local copy as a fallback. Returns a short status line."""
    if not title.strip() or not body_markdown.strip():
        return "Nothing to send: title and body must both be non-empty."

    # Always keep a local copy — cheap, and the fallback when email is off.
    out_dir = Path(__file__).parent / "digests"
    out_dir.mkdir(exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    path = out_dir / f"{stamp}.md"
    path.write_text(f"# {title}\n\n{body_markdown}\n", encoding="utf-8")

    cfg = _email_config()
    if cfg is None:
        return f"Saved locally → {path} (email not configured; set SMTP_* env vars to enable)."

    try:
        _send_email(cfg, subject=title, body=body_markdown)
    except (smtplib.SMTPException, OSError) as exc:
        # Surface the failure but don't lose the digest — it's on disk.
        return f"Saved locally → {path}, but email failed: {type(exc).__name__}: {exc}"

    return f"Emailed to {cfg['recipient']} and saved locally → {path}."
