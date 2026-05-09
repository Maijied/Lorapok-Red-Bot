"""Append-only audit trail of every moderation decision.

Records are never deleted — this is the full history used for similarity
search and the learning-loop signal extraction.  All queries are scoped to
``tenant_id`` for multi-tenant isolation.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.dashboard.models import ModerationDecisionRecord
from app.utils.text import stable_hash


def remember_case(
    db: Session,
    text: str,
    action: str,
    reason: str,
    source: str,
    tenant_id: str = "default",
    subreddit_name: str = "",
) -> None:
    """Persist a moderation decision to the audit trail.  Never raises."""
    try:
        record = ModerationDecisionRecord(
            tenant_id=tenant_id,
            subreddit_name=subreddit_name,
            text_hash=stable_hash(text),
            content=text,
            action=action,
            reason=reason,
            source=source,
        )
        db.add(record)
        db.commit()
    except Exception:
        db.rollback()


def recent_cases(
    db: Session,
    limit: int = 20,
    tenant_id: str = "default",
    subreddit_name: str | None = None,
) -> list[dict[str, Any]]:
    """Return the most recent *limit* decisions for a tenant."""
    query = (
        db.query(ModerationDecisionRecord)
        .filter(ModerationDecisionRecord.tenant_id == tenant_id)
    )
    if subreddit_name:
        query = query.filter(ModerationDecisionRecord.subreddit_name == subreddit_name)
    records = query.order_by(ModerationDecisionRecord.created_at.desc()).limit(limit).all()
    return [_to_dict(r) for r in records]


def find_similar_cases(
    db: Session,
    query_text: str,
    limit: int = 5,
    tenant_id: str = "default",
) -> list[dict[str, Any]]:
    """Find decisions with the same content hash or a substring match."""
    h = stable_hash(query_text)
    # Exact hash match first
    exact = (
        db.query(ModerationDecisionRecord)
        .filter(
            ModerationDecisionRecord.tenant_id == tenant_id,
            ModerationDecisionRecord.text_hash == h,
        )
        .order_by(ModerationDecisionRecord.created_at.desc())
        .limit(limit)
        .all()
    )
    if exact:
        return [_to_dict(r) for r in exact]

    # Fallback: substring search on content
    snippet = query_text[:100]
    fuzzy = (
        db.query(ModerationDecisionRecord)
        .filter(
            ModerationDecisionRecord.tenant_id == tenant_id,
            ModerationDecisionRecord.content.ilike(f"%{snippet}%"),
        )
        .order_by(ModerationDecisionRecord.created_at.desc())
        .limit(limit)
        .all()
    )
    return [_to_dict(r) for r in fuzzy]


def _to_dict(record: ModerationDecisionRecord) -> dict[str, Any]:
    return {
        "id": record.id,
        "tenant_id": record.tenant_id,
        "subreddit_name": record.subreddit_name,
        "text_hash": record.text_hash,
        "content": record.content,
        "action": record.action,
        "reason": record.reason,
        "source": record.source,
        "created_at": record.created_at.isoformat() if record.created_at else None,
    }
