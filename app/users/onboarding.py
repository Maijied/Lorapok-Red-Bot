"""User onboarding — welcome DM and flair assignment for new subscribers."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.dashboard.models import OnboardingRecord

log = logging.getLogger(__name__)

_DEFAULT_WELCOME = (
    "Welcome to the community! 👋\n\n"
    "Please read the rules before posting. "
    "If you have any questions, feel free to reach out via modmail."
)


def is_welcomed(
    db: Session, username: str, subreddit_name: str, tenant_id: str = "default"
) -> bool:
    return (
        db.query(OnboardingRecord)
        .filter(
            OnboardingRecord.tenant_id == tenant_id,
            OnboardingRecord.username == username,
            OnboardingRecord.subreddit_name == subreddit_name,
        )
        .first()
    ) is not None


def send_welcome_dm(
    reddit: Any,
    username: str,
    subreddit_name: str,
    template: str = _DEFAULT_WELCOME,
    dry_run: bool = True,
) -> bool:
    if dry_run:
        log.info("DRY_RUN welcome DM → u/%s (r/%s)", username, subreddit_name)
        return True
    try:
        reddit.redditor(username).message(
            subject=f"Welcome to r/{subreddit_name}!",
            message=template,
        )
        return True
    except Exception as exc:
        log.warning("Could not send welcome DM to u/%s: %s", username, exc)
        return False


def mark_welcomed(
    db: Session, username: str, subreddit_name: str, tenant_id: str = "default"
) -> None:
    record = OnboardingRecord(
        tenant_id=tenant_id,
        username=username,
        subreddit_name=subreddit_name,
        status="welcomed",
        welcomed_at=datetime.now(timezone.utc),
    )
    db.add(record)
    db.commit()


def handle_new_subscriber(
    reddit: Any,
    db: Session,
    username: str,
    subreddit_name: str,
    settings: Any,
) -> None:
    """Orchestrate the full onboarding flow for a new subscriber."""
    tenant_id = getattr(settings, "tenant_id", "default")
    dry_run = getattr(settings, "dry_run", True)

    if is_welcomed(db, username, subreddit_name, tenant_id):
        return

    sent = send_welcome_dm(reddit, username, subreddit_name, dry_run=dry_run)
    if sent:
        mark_welcomed(db, username, subreddit_name, tenant_id)
        log.info("Welcomed u/%s to r/%s", username, subreddit_name)
    else:
        log.warning("Skipping mark_welcomed for u/%s — DM failed", username)
