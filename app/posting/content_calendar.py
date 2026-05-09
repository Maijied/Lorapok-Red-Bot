"""Content calendar — schedule posts for future publication with optimal timing."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.dashboard.models import DailyMetric, ScheduledPost

log = logging.getLogger(__name__)


def schedule_post(
    db: Session,
    subreddit_name: str,
    title: str,
    body: str,
    post_at: datetime,
    flair_id: str | None = None,
    tenant_id: str = "default",
) -> str:
    """Create a scheduled post.  Raises ValueError if post_at is in the past."""
    if post_at.tzinfo is None:
        post_at = post_at.replace(tzinfo=timezone.utc)
    if post_at <= datetime.now(timezone.utc):
        raise ValueError(f"post_at must be in the future, got {post_at}")

    record = ScheduledPost(
        tenant_id=tenant_id,
        subreddit_name=subreddit_name,
        title=title[:255],
        body=body,
        flair_id=flair_id,
        post_at=post_at,
        status="scheduled",
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return str(record.id)


def get_scheduled_posts(
    db: Session, subreddit_name: str, tenant_id: str = "default"
) -> list[dict]:
    records = (
        db.query(ScheduledPost)
        .filter(
            ScheduledPost.tenant_id == tenant_id,
            ScheduledPost.subreddit_name == subreddit_name,
        )
        .order_by(ScheduledPost.post_at.asc())
        .all()
    )
    return [_to_dict(r) for r in records]


def cancel_scheduled_post(
    db: Session, post_id: str, tenant_id: str = "default"
) -> bool:
    try:
        pid = int(post_id)
    except (ValueError, TypeError):
        return False
    record = (
        db.query(ScheduledPost)
        .filter(ScheduledPost.id == pid, ScheduledPost.tenant_id == tenant_id)
        .first()
    )
    if not record or record.status != "scheduled":
        return False
    record.status = "cancelled"
    db.commit()
    return True


def publish_due_posts(reddit: Any, db: Session, settings: Any) -> int:
    """Submit all due scheduled posts to Reddit.  Idempotent — never re-publishes."""
    tenant_id = getattr(settings, "tenant_id", "default")
    dry_run = getattr(settings, "dry_run", True)
    now = datetime.now(timezone.utc)

    due = (
        db.query(ScheduledPost)
        .filter(
            ScheduledPost.tenant_id == tenant_id,
            ScheduledPost.status == "scheduled",
            ScheduledPost.post_at <= now,
        )
        .all()
    )

    published = 0
    for post in due:
        if dry_run:
            log.info("DRY_RUN publish scheduled post %d: %s", post.id, post.title)
            post.status = "published"
            db.commit()
            published += 1
            continue
        try:
            submission = reddit.subreddit(post.subreddit_name).submit(
                post.title, selftext=post.body
            )
            if post.flair_id:
                try:
                    submission.flair.select(post.flair_id)
                except Exception:
                    pass
            post.status = "published"
            post.reddit_post_id = submission.id
            db.commit()
            published += 1
            log.info("Published scheduled post %d → %s", post.id, submission.id)
        except Exception as exc:
            post.status = "failed"
            post.error_message = str(exc)[:500]
            db.commit()
            log.error("Failed to publish scheduled post %d: %s", post.id, exc)

    return published


def get_optimal_post_times(
    db: Session, subreddit_name: str, tenant_id: str = "default"
) -> list[datetime]:
    """Analyse DailyMetric data to suggest optimal posting hours (UTC)."""
    from collections import defaultdict

    records = (
        db.query(DailyMetric)
        .filter(DailyMetric.metric_name == "comments_processed")
        .order_by(DailyMetric.metric_date.desc())
        .limit(30)
        .all()
    )

    if not records:
        # Default: Monday 14:00 and Wednesday 10:00 UTC
        now = datetime.now(timezone.utc)
        return [now.replace(hour=14, minute=0, second=0, microsecond=0)]

    # Find the day-of-week with highest average engagement
    day_totals: dict[int, list[int]] = defaultdict(list)
    for r in records:
        if r.metric_date:
            dow = r.metric_date.weekday()
            day_totals[dow].append(r.count)

    best_dow = max(day_totals, key=lambda d: sum(day_totals[d]) / len(day_totals[d]))
    now = datetime.now(timezone.utc)
    days_ahead = (best_dow - now.weekday()) % 7 or 7
    optimal = now.replace(hour=14, minute=0, second=0, microsecond=0)
    from datetime import timedelta
    optimal = optimal + timedelta(days=days_ahead)
    return [optimal]


def _to_dict(post: ScheduledPost) -> dict:
    return {
        "id": post.id,
        "subreddit_name": post.subreddit_name,
        "title": post.title,
        "body": post.body,
        "flair_id": post.flair_id,
        "post_at": post.post_at.isoformat() if post.post_at else None,
        "status": post.status,
        "reddit_post_id": post.reddit_post_id,
        "error_message": post.error_message,
        "created_at": post.created_at.isoformat() if post.created_at else None,
    }
