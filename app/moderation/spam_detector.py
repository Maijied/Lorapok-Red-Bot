"""Cross-subreddit spam detector — detects coordinated posting across subreddits."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.dashboard.models import SpamSignalRecord

log = logging.getLogger(__name__)

_MIN_SUBREDDITS = 3


@dataclass
class SpamSignal:
    username: str
    content_hash: str
    subreddits: list[str]
    occurrences: int
    score: float  # 0.0 – 1.0


def record_submission(
    db: Session,
    username: str,
    subreddit_name: str,
    content_hash: str,
    url: str = "",
    tenant_id: str = "default",
) -> None:
    """Record a submission for cross-subreddit spam tracking."""
    record = SpamSignalRecord(
        tenant_id=tenant_id,
        username=username,
        subreddit_name=subreddit_name,
        content_hash=content_hash,
        url=url,
    )
    db.add(record)
    db.commit()


def detect_cross_sub_spam(
    db: Session,
    username: str,
    content_hash: str,
    window_hours: int = 24,
    tenant_id: str = "default",
) -> SpamSignal | None:
    """Return a SpamSignal if the same content appears in 3+ subreddits within the window."""
    window_start = datetime.now(timezone.utc) - timedelta(hours=window_hours)
    records = (
        db.query(SpamSignalRecord)
        .filter(
            SpamSignalRecord.tenant_id == tenant_id,
            SpamSignalRecord.username == username,
            SpamSignalRecord.content_hash == content_hash,
            SpamSignalRecord.created_at >= window_start,
        )
        .all()
    )

    subreddits = list({r.subreddit_name for r in records})
    if len(subreddits) < _MIN_SUBREDDITS:
        return None

    score = min(1.0, len(subreddits) / 10.0)
    return SpamSignal(
        username=username,
        content_hash=content_hash,
        subreddits=subreddits,
        occurrences=len(records),
        score=score,
    )


def get_spam_signals(
    db: Session,
    subreddit_name: str,
    min_score: float = 0.7,
    tenant_id: str = "default",
    window_hours: int = 24,
) -> list[dict[str, Any]]:
    """Return recent spam signals above *min_score* for a subreddit."""
    window_start = datetime.now(timezone.utc) - timedelta(hours=window_hours)
    records = (
        db.query(SpamSignalRecord)
        .filter(
            SpamSignalRecord.tenant_id == tenant_id,
            SpamSignalRecord.subreddit_name == subreddit_name,
            SpamSignalRecord.created_at >= window_start,
        )
        .all()
    )

    # Group by (username, content_hash)
    groups: dict[tuple, list] = {}
    for r in records:
        key = (r.username, r.content_hash)
        groups.setdefault(key, []).append(r)

    results = []
    for (username, content_hash), group_records in groups.items():
        subs = list({r.subreddit_name for r in group_records})
        if len(subs) < _MIN_SUBREDDITS:
            continue
        score = min(1.0, len(subs) / 10.0)
        if score >= min_score:
            results.append({
                "username": username,
                "content_hash": content_hash,
                "subreddits": subs,
                "occurrences": len(group_records),
                "score": score,
            })

    return sorted(results, key=lambda x: x["score"], reverse=True)
