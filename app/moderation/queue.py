from datetime import datetime, timezone
from typing import Any

from sqlalchemy import Boolean, Column, DateTime, Integer, String, Text
from sqlalchemy.orm import Session

from app.database import Base


class ReviewCaseRecord(Base):
    __tablename__ = "review_cases"

    id = Column(Integer, primary_key=True, index=True)
    text = Column(Text)
    reason = Column(String(255))
    source = Column(String(50))
    recommended_action = Column(String(50), default="review")
    status = Column(String(50), default="pending")  # pending, approved, rejected, escalated
    reviewer_note = Column(Text, default="")
    was_override = Column(Boolean, default=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict[str, Any]:
        return {
            "case_id": str(self.id),
            "text": self.text,
            "reason": self.reason,
            "source": self.source,
            "recommended_action": self.recommended_action,
            "status": self.status,
            "reviewer_note": self.reviewer_note,
            "was_override": self.was_override,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


def queue_case(
    db: Session, text: str, reason: str, source: str, recommended_action: str = "review"
) -> str:
    case = ReviewCaseRecord(
        text=text, reason=reason, source=source, recommended_action=recommended_action
    )
    db.add(case)
    db.commit()
    db.refresh(case)
    return str(case.id)


def list_queue(db: Session, status: str | None = None) -> list[dict[str, Any]]:
    query = db.query(ReviewCaseRecord)
    if status:
        query = query.filter(ReviewCaseRecord.status == status)
    records = query.order_by(ReviewCaseRecord.created_at.desc()).all()
    return [r.to_dict() for r in records]


def resolve_case(db: Session, case_id: str, status: str, reviewer_note: str = "") -> bool:
    if status not in {"approved", "rejected", "escalated"}:
        return False
    try:
        cid = int(case_id)
    except ValueError:
        return False

    case = db.query(ReviewCaseRecord).filter(ReviewCaseRecord.id == cid).first()
    if not case:
        return False

    # Learning loop logic: detect override
    is_override = False
    if status == "approved" and case.recommended_action == "remove":
        is_override = True
    elif status == "rejected" and case.recommended_action == "allow":
        is_override = True

    case.status = status
    case.reviewer_note = reviewer_note
    case.was_override = is_override
    db.commit()
    return True
