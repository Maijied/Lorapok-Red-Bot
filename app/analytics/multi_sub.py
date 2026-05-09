"""Multi-subreddit aggregate analytics — tenant-scoped cross-subreddit metrics."""

from __future__ import annotations

import logging
from typing import Any

from sqlalchemy.orm import Session

from app.dashboard.models import DailyMetric, ReviewCaseRecord, TenantConfig, UserReputation

log = logging.getLogger(__name__)


def get_aggregate_metrics(db: Session, tenant_id: str) -> dict[str, Any]:
    """Combine metrics across all subreddits managed by *tenant_id*."""
    tenant = db.query(TenantConfig).filter(TenantConfig.tenant_id == tenant_id).first()
    if not tenant:
        return {"error": "Tenant not found", "tenant_id": tenant_id}

    subreddits: list[str] = tenant.managed_subreddits or []

    total_users = (
        db.query(UserReputation)
        .filter(
            UserReputation.tenant_id == tenant_id,
            UserReputation.subreddit_name.in_(subreddits),
        )
        .count()
    )
    pending_reviews = (
        db.query(ReviewCaseRecord)
        .filter(
            ReviewCaseRecord.tenant_id == tenant_id,
            ReviewCaseRecord.status == "pending",
        )
        .count()
    )
    total_comments = (
        db.query(DailyMetric)
        .filter(DailyMetric.metric_name == "comments_processed")
        .with_entities(DailyMetric.count)
        .all()
    )
    comments_sum = sum(r.count for r in total_comments)

    return {
        "tenant_id": tenant_id,
        "managed_subreddits": subreddits,
        "subreddit_count": len(subreddits),
        "total_tracked_users": total_users,
        "pending_reviews": pending_reviews,
        "total_comments_processed": comments_sum,
        "tier": tenant.tier,
    }


def get_per_sub_breakdown(db: Session, tenant_id: str) -> list[dict[str, Any]]:
    """Return a summary dict per managed subreddit for *tenant_id*."""
    tenant = db.query(TenantConfig).filter(TenantConfig.tenant_id == tenant_id).first()
    if not tenant:
        return []

    subreddits: list[str] = tenant.managed_subreddits or []
    result = []

    for sub in subreddits:
        user_count = (
            db.query(UserReputation)
            .filter(
                UserReputation.tenant_id == tenant_id,
                UserReputation.subreddit_name == sub,
            )
            .count()
        )
        pending = (
            db.query(ReviewCaseRecord)
            .filter(
                ReviewCaseRecord.tenant_id == tenant_id,
                ReviewCaseRecord.subreddit_name == sub,
                ReviewCaseRecord.status == "pending",
            )
            .count()
        )
        result.append({
            "subreddit": sub,
            "tracked_users": user_count,
            "pending_reviews": pending,
        })

    return result
