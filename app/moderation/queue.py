"""Human-in-the-loop review queue backed by PostgreSQL.

Uncertain moderation cases are stored here for moderator approval, rejection,
or escalation.  All queries are scoped to a ``tenant_id`` to enforce
multi-tenant isolation.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.dashboard.models import ReviewCaseRecord

_VALID_STATUSES = {"approved", "rejected", "escalated"}


def queue_case(
    db: Session,
    text: str,
    reason: str,
    source: str,
    recommended_action: str = "review",
    tenant_id: str = "default",
    subreddit_name: str = "",
) -> str:
    """Insert a new pending review case and return its string ID."""
    if recommended_action not in {"allow", "review", "remove"}:
        recommended_action = "review"

    case = ReviewCaseRecord(
        tenant_id=tenant_id,
        subreddit_name=subreddit_name,
        text=text,
        reason=reason[:255] if reason else "",
        source=source[:50] if source else "",
        recommended_action=recommended_action,
        status="pending",
        reviewer_note="",
        was_override=False,
    )
    db.add(case)
    db.commit()
    db.refresh(case)
    return str(case.id)


def list_queue(
    db: Session,
    status: str | None = None,
    tenant_id: str = "default",
    subreddit_name: str | None = None,
) -> list[dict[str, Any]]:
    """Return review cases, optionally filtered by status and subreddit."""
    query = db.query(ReviewCaseRecord).filter(ReviewCaseRecord.tenant_id == tenant_id)
    if status:
        query = query.filter(ReviewCaseRecord.status == status)
    if subreddit_name:
        query = query.filter(ReviewCaseRecord.subreddit_name == subreddit_name)
    records = query.order_by(ReviewCaseRecord.created_at.desc()).all()
    return [_to_dict(r) for r in records]


def resolve_case(
    db: Session,
    case_id: str,
    status: str,
    reviewer_note: str = "",
    tenant_id: str = "default",
) -> bool:
    """Transition a case to *status*.  Returns False on invalid input."""
    if status not in _VALID_STATUSES:
        return False
    try:
        cid = int(case_id)
    except (ValueError, TypeError):
        return False

    case = (
        db.query(ReviewCaseRecord)
        .filter(ReviewCaseRecord.id == cid, ReviewCaseRecord.tenant_id == tenant_id)
        .first()
    )
    if not case:
        return False

    # Detect moderator override (learning-loop signal)
    was_override = (
        (status == "approved" and case.recommended_action == "remove")
        or (status == "rejected" and case.recommended_action == "allow")
    )

    case.status = status
    case.reviewer_note = reviewer_note
    case.was_override = was_override
    db.commit()
    return True


def _to_dict(case: ReviewCaseRecord) -> dict[str, Any]:
    return {
        "case_id": str(case.id),
        "tenant_id": case.tenant_id,
        "subreddit_name": case.subreddit_name,
        "text": case.text,
        "reason": case.reason,
        "source": case.source,
        "recommended_action": case.recommended_action,
        "status": case.status,
        "reviewer_note": case.reviewer_note,
        "was_override": case.was_override,
        "created_at": case.created_at.isoformat() if case.created_at else None,
    }
