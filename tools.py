"""Tools for the ModelScout agent.

The Hugging Face calls are real and need no API key. `send_digest` emails the
digest when SMTP is configured (env vars below), and always keeps a local copy
as a fallback.

Email is enabled by setting these env vars:
    SMTP_HOST, SMTP_PORT (default 587), SMTP_USER, SMTP_PASSWORD,
    EMAIL_FROM, EMAIL_TO
If any required one is missing, the digest is saved to disk only.
"""

import json
import logging
import os
import smtplib
from datetime import datetime, timedelta, timezone
from email.headerregistry import Address
from email.message import EmailMessage
from pathlib import Path

import markdown
from huggingface_hub import list_models
from langchain_core.tools import tool

LOGGER = logging.getLogger(__name__)
SENDER_DISPLAY_NAME = "Model Scout"

# Models we've already reported once, so re-running the agent (e.g. a daily
# cron) never re-notifies about the same release twice. Gitignored, local
# state — see README for how to persist it across CI runs.
SEEN_MODELS_FILE = Path(__file__).parent / "seen_models.json"


# A third-party variant (quantization/fine-tune/adapter, not from the base
# model's own org) still gets surfaced if it already has real traction —
# otherwise a genuinely popular release (e.g. a well-known quantizer's GGUF)
# would be indistinguishable from noise.
POPULAR_LIKES_THRESHOLD = 20
POPULAR_DOWNLOADS_THRESHOLD = 1000


def _variant_base(model) -> str | None:
    """Return the base model id this model derives from, or None if it's original.

    HF auto-adds tags like `base_model:quantized:<id>`, `base_model:adapter:<id>`,
    or `base_model:finetune:<id>` whenever a model card declares a base model —
    a reliable signal for "this is a fine-tune/quantization/adapter of
    something else", as opposed to a first-party, from-scratch release.
    """
    tags = getattr(model, "tags", None) or []
    for t in tags:
        if t.startswith("base_model:"):
            return t.split(":", 2)[-1]
    return None


def _worth_keeping_variant(model, base_id: str) -> bool:
    """Keep a variant only if it's official (same org as the base model) or popular."""
    own_org = model.id.split("/", 1)[0].lower()
    base_org = base_id.split("/", 1)[0].lower()
    if own_org == base_org:
        return True  # official release from the base model's own org/lab
    likes = getattr(model, "likes", 0) or 0
    downloads = getattr(model, "downloads", 0) or 0
    return likes >= POPULAR_LIKES_THRESHOLD or downloads >= POPULAR_DOWNLOADS_THRESHOLD


def _load_seen() -> set[str]:
    if not SEEN_MODELS_FILE.exists():
        return set()
    try:
        return set(json.loads(SEEN_MODELS_FILE.read_text(encoding="utf-8")))
    except (json.JSONDecodeError, OSError):
        LOGGER.warning("Could not read %s; starting with empty seen-model state.", SEEN_MODELS_FILE)
        return set()


def _mark_seen(model_ids: list[str]) -> None:
    if not model_ids:
        return
    seen = _load_seen() | set(model_ids)
    SEEN_MODELS_FILE.write_text(json.dumps(sorted(seen)), encoding="utf-8")


@tool
def get_recent_models(pipeline_tag: str = "text-generation", since_hours: int = 24, limit: int = 25) -> str:
    """Return newly published, worth-reporting Hugging Face models for a task.

    Excludes low-signal fine-tunes/quantizations/adapters of another model
    (third-party, no real traction) and models already reported in a previous
    call. Official variants (released by the base model's own org, e.g. the
    official GGUF build) and popular community variants are still included,
    labeled "variant of <base>" so they read as a release of an existing
    model rather than a brand-new one. The Hub API needs no authentication.
    """
    LOGGER.info("get_recent_models pipeline_tag=%s since_hours=%d limit=%d", pipeline_tag, since_hours, limit)
    cutoff = datetime.now(timezone.utc) - timedelta(hours=since_hours)
    seen = _load_seen()

    model_rows = []
    new_ids = []
    try:
        for model in list_models(sort="createdAt", pipeline_tag=pipeline_tag, limit=limit, full=True):
            created = getattr(model, "created_at", None)
            if created is None or created < cutoff:
                continue
            if model.id in seen:
                continue

            base_id = _variant_base(model)
            if base_id and not _worth_keeping_variant(model, base_id):
                continue

            new_ids.append(model.id)
            summary = (
                f"- {model.id}"
                f" | created {created:%Y-%m-%d %H:%M UTC}"
                f" | downloads={getattr(model, 'downloads', 0)}"
                f" | likes={getattr(model, 'likes', 0)}"
            )
            if base_id:
                summary += f" | variant of {base_id}"
            model_rows.append(summary)
    except Exception as exc:
        LOGGER.exception("Hugging Face lookup failed for pipeline_tag=%s", pipeline_tag)
        return f"Could not reach the Hugging Face Hub: {exc}"

    _mark_seen(new_ids)

    if not model_rows:
        return f"No new, worth-reporting '{pipeline_tag}' models in the last {since_hours}h."
    return f"New '{pipeline_tag}' models (last {since_hours}h) — entries marked 'variant of X' are a release of an existing model, not a new one:\n" + "\n".join(
        model_rows
    )


@tool
def get_trending_models(pipeline_tag: str = "text-generation", limit: int = 10) -> str:
    """Return currently trending Hugging Face models for a task."""
    LOGGER.info("get_trending_models pipeline_tag=%s limit=%d", pipeline_tag, limit)
    try:
        model_rows = [
            f"- {model.id} | downloads={getattr(model, 'downloads', 0)} likes={getattr(model, 'likes', 0)}"
            for model in list_models(sort="trendingScore", pipeline_tag=pipeline_tag, limit=limit, full=True)
        ]
    except Exception as exc:
        LOGGER.exception("Hugging Face lookup failed for pipeline_tag=%s", pipeline_tag)
        return f"Could not reach the Hugging Face Hub: {exc}"
    return f"Trending '{pipeline_tag}' models:\n" + "\n".join(model_rows)


def _email_config() -> dict | None:
    """Return SMTP config from env, or None if it is incomplete."""
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


def _send_email(cfg: dict, subject: str, body_markdown: str) -> None:
    """Send a digest email over STARTTLS: plain-text fallback + a rendered HTML part."""
    # Header values must not contain raw newlines (CRLF header injection).
    safe_subject = " ".join(subject.splitlines()).strip()

    msg = EmailMessage()
    msg["Subject"] = safe_subject
    msg["From"] = Address(SENDER_DISPLAY_NAME, addr_spec=cfg["sender"])
    msg["To"] = cfg["recipient"]
    msg.set_content(body_markdown)

    html_body = markdown.markdown(body_markdown, extensions=["extra", "sane_lists"])
    msg.add_alternative(
        f"""\
<html><body style="font-family: -apple-system, Segoe UI, Roboto, sans-serif; max-width: 640px; margin: auto; color: #1a1a1a; line-height: 1.5;">
<h2 style="border-bottom: 2px solid #eee; padding-bottom: 8px;">{safe_subject}</h2>
{html_body}
<hr style="border: none; border-top: 1px solid #eee; margin-top: 24px;">
<p style="color: #888; font-size: 12px;">Sent by Model Scout</p>
</body></html>
""",
        subtype="html",
    )

    with smtplib.SMTP(cfg["host"], cfg["port"], timeout=30) as smtp:
        smtp.starttls()
        smtp.login(cfg["user"], cfg["password"])
        smtp.send_message(msg)


@tool
def send_digest(title: str, body_markdown: str) -> str:
    """Deliver a digest by email when SMTP is configured and always save a local copy."""
    if not title.strip() or not body_markdown.strip():
        return "Nothing to send: title and body must both be non-empty."

    # Always keep a local copy — cheap, and the fallback when email is off.
    out_dir = Path(__file__).parent / "digests"
    out_dir.mkdir(exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    path = out_dir / f"{stamp}.md"
    path.write_text(f"# {title}\n\n{body_markdown}\n", encoding="utf-8")
    LOGGER.info("Saved digest %r -> %s", title, path)

    cfg = _email_config()
    if cfg is None:
        return f"Saved locally → {path} (email not configured; set SMTP_* env vars to enable)."

    try:
        _send_email(cfg, subject=title, body_markdown=body_markdown)
    except (smtplib.SMTPException, OSError) as exc:
        LOGGER.exception("Failed sending digest email.")
        return f"Saved locally → {path}, but email failed: {type(exc).__name__}: {exc}"

    LOGGER.info("Emailed digest %r to %s", title, cfg["recipient"])
    return f"Emailed to {cfg['recipient']} and saved locally → {path}."
