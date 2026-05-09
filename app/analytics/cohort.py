"""Cohort analysis — user retention, power users, and churn prediction."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.dashboard.models import UserReputation

log = logging.getLogger(__name__)


def build_cohort_table(
    db: Session,
    subreddit_name: str,
    tenant_id: str = "default",
    months: int = 6,
) -> dict[str, Any]:
    """Group users by join month and track activity counts."""
    since = datetime.now(timezone.utc) - timedelta(days=months * 30)
    users = (
        db.query(UserReputation)
        .filter(
            UserReputation.tenant_id == tenant_id,
            UserReputation.subreddit_name == subreddit_name,
            UserReputation.created_at >= since,
        )
        .all()
    )

    cohorts: dict[str, dict[str, int]] = {}
    for u in users:
        if not u.created_at:
            continue
        month_key = u.created_at.strftime("%Y-%m")
        if month_key not in cohorts:
            cohorts[month_key] = {"total": 0, "active": 0, "churned": 0}
        cohorts[month_key]["total"] += 1
        cutoff = datetime.now(timezone.utc) - timedelta(days=30)
        if u.last_active_at and u.last_active_at >= cutoff:
            cohorts[month_key]["active"] += 1
        else:
            cohorts[month_key]["churned"] += 1

    return {"cohorts": cohorts, "months": months, "subreddit": subreddit_name}


def get_power_users(
    db: Session,
    subreddit_name: str,
    tenant_id: str = "default",
    limit: int = 50,
) -> list[dict[str, Any]]:
    users = (
        db.query(UserReputation)
        .filter(
            UserReputation.tenant_id == tenant_id,
            UserReputation.subreddit_name == subreddit_name,
        )
        .order_by(UserReputation.reputation_score.desc())
        .limit(limit)
        .all()
    )
    return [
        {
            "username": u.username,
            "reputation_score": u.reputation_score,
            "approved_posts": u.approved_posts,
            "approved_comments": u.approved_comments,
            "is_contributor": u.is_contributor,
            "flair_tier": u.flair_tier,
        }
        for u in users
    ]


def get_churn_risk_users(
    db: Session,
    subreddit_name: str,
    tenant_id: str = "default",
    inactive_days: int = 30,
) -> list[dict[str, Any]]:
    """Return contributors who haven't been active in *inactive_days* days."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=inactive_days)
    users = (
        db.query(UserReputation)
        .filter(
            UserReputation.tenant_id == tenant_id,
            UserReputation.subreddit_name == subreddit_name,
            UserReputation.is_contributor == True,  # noqa: E712
            UserReputation.last_active_at < cutoff,
        )
        .order_by(UserReputation.last_active_at.asc())
        .all()
    )
    return [
        {
            "username": u.username,
            "reputation_score": u.reputation_score,
            "last_active_at": u.last_active_at.isoformat() if u.last_active_at else None,
            "days_inactive": (datetime.now(timezone.utc) - u.last_active_at).days
            if u.last_active_at
            else None,
        }
        for u in users
    ]
