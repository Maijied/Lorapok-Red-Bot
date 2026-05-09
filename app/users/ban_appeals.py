"""Ban appeal workflow — create, auto-review, escalate, and resolve appeals."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.dashboard.models import BanAppeal

log = logging.getLogger(__name__)


def create_ban_appeal(
    db: Session,
    username: str,
    subreddit_name: str,
    modmail_id: str,
    appeal_text: str,
    tenant_id: str = "default",
) -> BanAppeal:
    appeal = BanAppeal(
        tenant_id=tenant_id,
        username=username,
        subreddit_name=subreddit_name,
        modmail_id=modmail_id,
        appeal_text=appeal_text,
        status="pending",
    )
    db.add(appeal)
    db.commit()
    db.refresh(appeal)
    return appeal


def auto_review_appeal(
    db: Session,
    appeal: BanAppeal,
    reputation: Any,  # UserReputation
    settings: Any,
) -> str:
    """Apply auto-approve / auto-reject / escalate logic.

    Returns the decision string: "approve" | "reject" | "escalate".
    """
    bans = getattr(reputation, "bans", 0)
    score = getattr(reputation, "reputation_score", 0.0)

    # Auto-reject: 3+ prior bans
    if bans >= 3:
        decision = "reject"
        reason = "3 or more prior bans on record."
    # Auto-approve: high reputation, no recent bans
    elif score > 50 and bans == 0:
        decision = "approve"
        reason = "High reputation score and no prior bans."
    else:
        decision = "escalate"
        reason = "Requires human moderator review."

    appeal.auto_decision = decision
    appeal.auto_reason = reason
    db.commit()
    return decision


def escalate_appeal(db: Session, appeal_id: int, reason: str, tenant_id: str = "default") -> bool:
    appeal = (
        db.query(BanAppeal)
        .filter(BanAppeal.id == appeal_id, BanAppeal.tenant_id == tenant_id)
        .first()
    )
    if not appeal:
        return False
    appeal.status = "escalated"
    appeal.auto_reason = reason
    db.commit()
    return True


def resolve_appeal(
    db: Session,
    appeal_id: int,
    decision: str,
    reviewer_note: str = "",
    tenant_id: str = "default",
) -> bool:
    if decision not in {"approved", "rejected"}:
        return False
    appeal = (
        db.query(BanAppeal)
        .filter(BanAppeal.id == appeal_id, BanAppeal.tenant_id == tenant_id)
        .first()
    )
    if not appeal:
        return False
    appeal.final_decision = decision
    appeal.reviewer_note = reviewer_note
    appeal.status = decision
    appeal.resolved_at = datetime.now(timezone.utc)
    db.commit()
    return True


def get_pending_appeals(
    db: Session, subreddit_name: str, tenant_id: str = "default"
) -> list[BanAppeal]:
    return (
        db.query(BanAppeal)
        .filter(
            BanAppeal.tenant_id == tenant_id,
            BanAppeal.subreddit_name == subreddit_name,
            BanAppeal.status == "pending",
        )
        .order_by(BanAppeal.created_at.asc())
        .all()
    )
