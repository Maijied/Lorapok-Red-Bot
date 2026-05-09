"""User reputation system — scoring, flair tier assignment, and contributor tracking."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.dashboard.models import UserReputation

log = logging.getLogger(__name__)


@dataclass
class ReputationDelta:
    approved_posts: int = 0
    approved_comments: int = 0
    removed_posts: int = 0
    removed_comments: int = 0
    bans: int = 0


def compute_reputation_score(reputation: UserReputation) -> float:
    """Compute reputation score from counts.  Pure function — no I/O.

    Formula: (approved_posts*2 + approved_comments - removed_posts*5 - bans*20)
             / max(1, account_age_days)
    Clamped to [-100.0, 100.0].
    """
    raw = (
        reputation.approved_posts * 2
        + reputation.approved_comments * 1
        - reputation.removed_posts * 5
        - reputation.bans * 20
    ) / max(1, reputation.account_age_days)
    return max(-100.0, min(100.0, raw))


def get_or_create_reputation(
    db: Session,
    username: str,
    subreddit_name: str,
    tenant_id: str = "default",
) -> UserReputation:
    """Fetch or create a UserReputation record (upsert on UNIQUE constraint)."""
    record = (
        db.query(UserReputation)
        .filter(
            UserReputation.tenant_id == tenant_id,
            UserReputation.username == username,
            UserReputation.subreddit_name == subreddit_name,
        )
        .first()
    )
    if record:
        return record
    record = UserReputation(
        tenant_id=tenant_id,
        username=username,
        subreddit_name=subreddit_name,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


def update_reputation(
    db: Session,
    username: str,
    subreddit_name: str,
    delta: ReputationDelta,
    tenant_id: str = "default",
) -> UserReputation:
    """Apply *delta* to a user's reputation and recompute the score."""
    record = get_or_create_reputation(db, username, subreddit_name, tenant_id)
    record.approved_posts += delta.approved_posts
    record.approved_comments += delta.approved_comments
    record.removed_posts += delta.removed_posts
    record.removed_comments += delta.removed_comments
    record.bans += delta.bans
    record.reputation_score = compute_reputation_score(record)
    record.last_active_at = datetime.now(timezone.utc)
    record.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(record)
    return record


def get_top_contributors(
    db: Session,
    subreddit_name: str,
    tenant_id: str = "default",
    limit: int = 20,
) -> list[UserReputation]:
    return (
        db.query(UserReputation)
        .filter(
            UserReputation.tenant_id == tenant_id,
            UserReputation.subreddit_name == subreddit_name,
        )
        .order_by(UserReputation.reputation_score.desc())
        .limit(limit)
        .all()
    )


def flag_suspicious_user(
    db: Session,
    username: str,
    subreddit_name: str,
    reason: str,
    tenant_id: str = "default",
) -> None:
    record = get_or_create_reputation(db, username, subreddit_name, tenant_id)
    record.is_suspicious = True
    db.commit()
    log.info("Flagged u/%s as suspicious in r/%s: %s", username, subreddit_name, reason)
