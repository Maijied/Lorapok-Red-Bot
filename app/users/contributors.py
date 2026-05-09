"""Contributor management — auto-promote and demote approved contributors."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.dashboard.models import UserReputation

log = logging.getLogger(__name__)

_PROMOTION_MIN_SCORE = 30.0
_PROMOTION_MIN_AGE_DAYS = 30
_DEMOTION_INACTIVE_DAYS = 180


def add_contributor(reddit: Any, subreddit_name: str, username: str, dry_run: bool = True) -> bool:
    if dry_run:
        log.info("DRY_RUN add_contributor r/%s ← u/%s", subreddit_name, username)
        return True
    try:
        reddit.subreddit(subreddit_name).contributor.add(username)
        return True
    except Exception as exc:
        log.error("Failed to add contributor u/%s to r/%s: %s", username, subreddit_name, exc)
        return False


def remove_contributor(
    reddit: Any, subreddit_name: str, username: str, dry_run: bool = True
) -> bool:
    if dry_run:
        log.info("DRY_RUN remove_contributor r/%s ← u/%s", subreddit_name, username)
        return True
    try:
        reddit.subreddit(subreddit_name).contributor.remove(username)
        return True
    except Exception as exc:
        log.error("Failed to remove contributor u/%s from r/%s: %s", username, subreddit_name, exc)
        return False


def run_contributor_promotion_batch(
    reddit: Any, db: Session, subreddit_name: str, settings: Any
) -> int:
    """Promote eligible users to approved contributor status."""
    tenant_id = getattr(settings, "tenant_id", "default")
    dry_run = getattr(settings, "dry_run", True)

    candidates = (
        db.query(UserReputation)
        .filter(
            UserReputation.tenant_id == tenant_id,
            UserReputation.subreddit_name == subreddit_name,
            UserReputation.is_contributor == False,  # noqa: E712
            UserReputation.is_suspicious == False,  # noqa: E712
            UserReputation.reputation_score >= _PROMOTION_MIN_SCORE,
            UserReputation.account_age_days >= _PROMOTION_MIN_AGE_DAYS,
            UserReputation.bans == 0,
        )
        .all()
    )

    promoted = 0
    for rep in candidates:
        if add_contributor(reddit, subreddit_name, rep.username, dry_run):
            rep.is_contributor = True
            db.commit()
            promoted += 1
            log.info("Promoted u/%s to contributor in r/%s", rep.username, subreddit_name)

    return promoted


def run_contributor_demotion_batch(
    reddit: Any, db: Session, subreddit_name: str, settings: Any
) -> int:
    """Demote contributors who have been inactive for 180+ days."""
    tenant_id = getattr(settings, "tenant_id", "default")
    dry_run = getattr(settings, "dry_run", True)
    cutoff = datetime.now(timezone.utc) - timedelta(days=_DEMOTION_INACTIVE_DAYS)

    candidates = (
        db.query(UserReputation)
        .filter(
            UserReputation.tenant_id == tenant_id,
            UserReputation.subreddit_name == subreddit_name,
            UserReputation.is_contributor == True,  # noqa: E712
            UserReputation.last_active_at < cutoff,
        )
        .all()
    )

    demoted = 0
    for rep in candidates:
        if remove_contributor(reddit, subreddit_name, rep.username, dry_run):
            rep.is_contributor = False
            db.commit()
            demoted += 1
            log.info(
                "Demoted u/%s from contributor in r/%s (inactive)",
                rep.username, subreddit_name,
            )

    return demoted
