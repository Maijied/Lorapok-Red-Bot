from datetime import datetime, timezone
from typing import Any

from sqlalchemy import Column, DateTime, Integer, String, Text, or_
from sqlalchemy.orm import Session

from app.database import Base
from app.utils.text import stable_hash


class ModerationDecisionRecord(Base):
    __tablename__ = "moderation_decisions"

    id = Column(Integer, primary_key=True, index=True)
    text_hash = Column(String(64), index=True)
    content = Column(Text)
    action = Column(String(50))
    reason = Column(String(255))
    source = Column(String(50))
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "text_hash": self.text_hash,
            "content": self.content,
            "action": self.action,
            "reason": self.reason,
            "source": self.source,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


def remember_case(db: Session, text: str, action: str, reason: str, source: str) -> None:
    record = ModerationDecisionRecord(
        text_hash=stable_hash(text),
        content=text,
        action=action,
        reason=reason,
        source=source,
    )
    db.add(record)
    db.commit()


def recent_cases(db: Session, limit: int = 20) -> list[dict[str, Any]]:
    records = (
        db.query(ModerationDecisionRecord)
        .order_by(ModerationDecisionRecord.created_at.desc())
        .limit(limit)
        .all()
    )
    return [r.to_dict() for r in records]


def find_similar_cases(db: Session, query_text: str, limit: int = 5) -> list[dict[str, Any]]:
    """Search cases by text content or hash."""
    h = stable_hash(query_text)
    records = (
        db.query(ModerationDecisionRecord)
        .filter(
            or_(
                ModerationDecisionRecord.text_hash == h,
                ModerationDecisionRecord.content.ilike(f"%{query_text}%"),
                ModerationDecisionRecord.reason.ilike(f"%{query_text}%"),
            )
        )
        .order_by(ModerationDecisionRecord.created_at.desc())
        .limit(limit)
        .all()
    )
    return [r.to_dict() for r in records]
