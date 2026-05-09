"""Subreddit health score — composite 0–100 metric."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.dashboard.models import (
    DailyMetric,
    ModerationDecisionRecord,
    ReviewCaseRecord,
    SpamSignalRecord,
    UserReputation,
)

log = logging.getLogger(__name__)


@dataclass
class SubredditHealthScore:
    total: float       # 0 – 100
    growth: float      # 0 – 25
    engagement: float  # 0 – 25
    moderation: float  # 0 – 25
    spam: float        # 0 – 25

    def __post_init__(self) -> None:
        self.growth = max(0.0, min(25.0, self.growth))
        self.engagement = max(0.0, min(25.0, self.engagement))
        self.moderation = max(0.0, min(25.0, self.moderation))
        self.spam = max(0.0, min(25.0, self.spam))
        self.total = self.growth + self.engagement + self.moderation + self.spam


def compute_health_score(
    db: Session,
    subreddit_name: str,
    tenant_id: str = "default",
    reddit: Any = None,
) -> SubredditHealthScore:
    """Compute a composite health score for *subreddit_name*."""
    growth = _growth_component(db, subreddit_name, tenant_id)
    engagement = _engagement_component(db, subreddit_name, tenant_id)
    moderation = _moderation_component(db, subreddit_name, tenant_id)
    spam = _spam_component(db, subreddit_name, tenant_id)
    return SubredditHealthScore(
        total=growth + engagement + moderation + spam,
        growth=growth,
        engagement=engagement,
        moderation=moderation,
        spam=spam,
    )


# ── Component calculators ─────────────────────────────────────────────────────


def _growth_component(db: Session, subreddit_name: str, tenant_id: str) -> float:
    """Score based on new user registrations in the past 30 days."""
    since = datetime.now(timezone.utc) - timedelta(days=30)
    new_users = (
        db.query(UserReputation)
        .filter(
            UserReputation.tenant_id == tenant_id,
            UserReputation.subreddit_name == subreddit_name,
            UserReputation.created_at >= since,
        )
        .count()
    )
    # 10+ new users/month → full 25 points
    return min(25.0, new_users * 2.5)


def _engagement_component(db: Session, subreddit_name: str, tenant_id: str) -> float:
    """Score based on comments processed in the past 7 days."""
    since = datetime.now(timezone.utc) - timedelta(days=7)
    records = (
        db.query(DailyMetric)
        .filter(
            DailyMetric.metric_name == "comments_processed",
            DailyMetric.metric_date >= since.date(),
        )
        .all()
    )
    total_comments = sum(r.count for r in records)
    avg_per_day = total_comments / 7.0
    # 50+ comments/day → full 25 points
    return min(25.0, (avg_per_day / 50.0) * 25.0)


def _moderation_component(db: Session, subreddit_name: str, tenant_id: str) -> float:
    """Score based on removal rate, override rate, and queue backlog."""
    since = datetime.now(timezone.utc) - timedelta(days=7)
    total_decisions = (
        db.query(ModerationDecisionRecord)
        .filter(
            ModerationDecisionRecord.tenant_id == tenant_id,
            ModerationDecisionRecord.subreddit_name == subreddit_name,
            ModerationDecisionRecord.created_at >= since,
        )
        .count()
    )
    removals = (
        db.query(ModerationDecisionRecord)
        .filter(
            ModerationDecisionRecord.tenant_id == tenant_id,
            ModerationDecisionRecord.subreddit_name == subreddit_name,
            ModerationDecisionRecord.action == "remove",
            ModerationDecisionRecord.created_at >= since,
        )
        .count()
    )
    overrides = (
        db.query(ReviewCaseRecord)
        .filter(
            ReviewCaseRecord.tenant_id == tenant_id,
            ReviewCaseRecord.subreddit_name == subreddit_name,
            ReviewCaseRecord.was_override == True,  # noqa: E712
            ReviewCaseRecord.created_at >= since,
        )
        .count()
    )
    queue_backlog = (
        db.query(ReviewCaseRecord)
        .filter(
            ReviewCaseRecord.tenant_id == tenant_id,
            ReviewCaseRecord.subreddit_name == subreddit_name,
            ReviewCaseRecord.status == "pending",
        )
        .count()
    )

    removal_rate = removals / max(1, total_decisions)
    override_rate = overrides / max(1, total_decisions)

    score = 25.0
    score -= min(10.0, removal_rate * 50)
    score -= min(10.0, override_rate * 50)
    score -= min(5.0, queue_backlog / 10.0)
    return max(0.0, score)


def _spam_component(db: Session, subreddit_name: str, tenant_id: str) -> float:
    """Score based on spam signal volume in the past 7 days."""
    since = datetime.now(timezone.utc) - timedelta(days=7)
    spam_count = (
        db.query(SpamSignalRecord)
        .filter(
            SpamSignalRecord.tenant_id == tenant_id,
            SpamSignalRecord.subreddit_name == subreddit_name,
            SpamSignalRecord.created_at >= since,
        )
        .count()
    )
    # 0 spam → 25, 10+ spam → 0
    return max(0.0, 25.0 - spam_count * 2.5)
