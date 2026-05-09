"""Modmail triage bot — categorises conversations, auto-replies, tracks SLA."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.dashboard.models import ModmailRecord, ModmailTemplate

log = logging.getLogger(__name__)

_SLA_HOURS: dict[str, int | None] = {
    "free": None,
    "starter": 48,
    "pro": 24,
    "agency": 4,
    "enterprise": 4,
}

_CATEGORY_KEYWORDS: dict[str, list[str]] = {
    "ban_appeal": ["ban appeal", "banned", "unban", "appeal", "wrongly banned"],
    "spam_report": ["spam", "report", "scam", "fake", "bot account"],
    "question": ["how do i", "how to", "what is", "can i", "help", "question", "?"],
    "feedback": ["suggestion", "feedback", "improve", "feature request", "idea"],
}


@dataclass
class ModmailTriageResult:
    conversation_id: str
    category: str
    confidence: float
    auto_replied: bool
    sla_deadline: datetime | None


def triage_conversation(
    conversation: Any,
    settings: Any,
    db: Session,
) -> ModmailTriageResult:
    """Categorise a modmail conversation and optionally auto-reply."""
    conv_id = str(conversation.id)

    # Guard: don't insert duplicate records
    existing = (
        db.query(ModmailRecord)
        .filter(ModmailRecord.conversation_id == conv_id)
        .first()
    )
    if existing:
        return ModmailTriageResult(
            conversation_id=conv_id,
            category=existing.category,
            confidence=existing.confidence,
            auto_replied=existing.auto_replied,
            sla_deadline=existing.sla_deadline,
        )

    subject = getattr(conversation, "subject", "") or ""
    first_msg = ""
    try:
        msgs = list(conversation.messages)
        if msgs:
            first_msg = getattr(msgs[0], "body", "") or ""
    except Exception:
        pass

    text = f"{subject} {first_msg}"
    category, confidence = _classify_modmail(text)

    tier = (
        getattr(settings, "tier", None)
        or _get_tenant_tier(db, getattr(settings, "tenant_id", "default"))
    )
    sla_hours = _SLA_HOURS.get(tier)
    sla_deadline = (
        datetime.now(timezone.utc) + timedelta(hours=sla_hours) if sla_hours else None
    )

    subreddit_name = ""
    try:
        subreddit_name = str(conversation.owner)
    except Exception:
        pass

    record = ModmailRecord(
        tenant_id=getattr(settings, "tenant_id", "default"),
        conversation_id=conv_id,
        subreddit_name=subreddit_name,
        subject=subject[:255],
        author=str(
            getattr(conversation, "authors", [{}])[0]
        ) if getattr(conversation, "authors", None) else "",
        category=category,
        confidence=confidence,
        status="open",
        sla_deadline=sla_deadline,
        auto_replied=False,
    )
    db.add(record)
    db.commit()

    auto_replied = False

    if category == "ban_appeal":
        _create_ban_appeal_record(db, conversation, settings, conv_id, subreddit_name, first_msg)
        auto_replied = _send_auto_reply(conversation, "ban_appeal", settings, db)
        record.auto_replied = auto_replied
        db.commit()

    elif category == "question" and confidence >= 0.85:
        auto_replied = _send_auto_reply(conversation, "question", settings, db)
        if auto_replied:
            record.status = "auto_replied"
            record.auto_replied = True
            db.commit()
            try:
                conversation.archive()
            except Exception:
                pass

    elif category == "unknown" or confidence < 0.60:
        record.status = "needs_human"
        db.commit()

    return ModmailTriageResult(
        conversation_id=conv_id,
        category=category,
        confidence=confidence,
        auto_replied=auto_replied,
        sla_deadline=sla_deadline,
    )


def reply_to_conversation(reddit: Any, conversation_id: str, message: str) -> bool:
    try:
        conv = reddit.subreddit("mod").modmail(conversation_id)
        conv.reply(body=message)
        return True
    except Exception as exc:
        log.error("Failed to reply to modmail %s: %s", conversation_id, exc)
        return False


def archive_conversation(reddit: Any, conversation_id: str) -> bool:
    try:
        reddit.subreddit("mod").modmail(conversation_id).archive()
        return True
    except Exception as exc:
        log.error("Failed to archive modmail %s: %s", conversation_id, exc)
        return False


def get_modmail_analytics(
    db: Session,
    subreddit_name: str,
    tenant_id: str = "default",
    days: int = 30,
) -> dict:
    from datetime import datetime, timedelta, timezone

    since = datetime.now(timezone.utc) - timedelta(days=days)
    records = (
        db.query(ModmailRecord)
        .filter(
            ModmailRecord.tenant_id == tenant_id,
            ModmailRecord.subreddit_name == subreddit_name,
            ModmailRecord.created_at >= since,
        )
        .all()
    )
    category_counts: dict[str, int] = {}
    for r in records:
        category_counts[r.category] = category_counts.get(r.category, 0) + 1

    resolved = [r for r in records if r.resolved_at]
    avg_response_hours = 0.0
    if resolved:
        total_hours = sum(
            (r.resolved_at - r.created_at).total_seconds() / 3600
            for r in resolved
            if r.resolved_at and r.created_at
        )
        avg_response_hours = total_hours / len(resolved)

    return {
        "total": len(records),
        "category_breakdown": category_counts,
        "auto_replied": sum(1 for r in records if r.auto_replied),
        "avg_response_hours": round(avg_response_hours, 2),
    }


def list_modmail_templates(db: Session, tenant_id: str) -> list[dict]:
    records = db.query(ModmailTemplate).filter(ModmailTemplate.tenant_id == tenant_id).all()
    return [
        {
            "id": r.id, "name": r.name, "category": r.category,
            "body": r.body, "language": r.language,
        }
        for r in records
    ]


def create_modmail_template(
    db: Session, tenant_id: str, name: str, category: str, body: str, language: str = "en"
) -> str:
    record = ModmailTemplate(
        tenant_id=tenant_id, name=name, category=category,
        body=body, language=language,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return str(record.id)


def render_template(template_body: str, **variables: str) -> str:
    """Substitute {{variable}} placeholders in a template body."""
    result = template_body
    for key, value in variables.items():
        result = result.replace(f"{{{{{key}}}}}", value)
    return result


# ── Internal helpers ──────────────────────────────────────────────────────────


def _classify_modmail(text: str) -> tuple[str, float]:
    lowered = text.lower()
    scores: dict[str, int] = {}
    for category, keywords in _CATEGORY_KEYWORDS.items():
        scores[category] = sum(1 for kw in keywords if kw in lowered)
    best = max(scores, key=lambda k: scores[k])
    total = sum(scores.values())
    if total == 0:
        return "unknown", 0.3
    confidence = min(0.95, scores[best] / max(1, len(_CATEGORY_KEYWORDS[best])))
    return best, confidence


def _send_auto_reply(conversation: Any, category: str, settings: Any, db: Session) -> bool:
    tenant_id = getattr(settings, "tenant_id", "default")
    templates = (
        db.query(ModmailTemplate)
        .filter(ModmailTemplate.tenant_id == tenant_id, ModmailTemplate.category == category)
        .first()
    )
    if not templates:
        return False
    try:
        conversation.reply(body=templates.body)
        return True
    except Exception as exc:
        log.warning("Auto-reply failed for category %s: %s", category, exc)
        return False


def _create_ban_appeal_record(
    db: Session,
    conversation: Any,
    settings: Any,
    conv_id: str,
    subreddit_name: str,
    appeal_text: str,
) -> None:
    from app.users.ban_appeals import create_ban_appeal

    author = ""
    try:
        authors = list(getattr(conversation, "authors", []))
        if authors:
            author = str(authors[0])
    except Exception:
        pass
    if author:
        create_ban_appeal(
            db,
            username=author,
            subreddit_name=subreddit_name,
            modmail_id=conv_id,
            appeal_text=appeal_text,
            tenant_id=getattr(settings, "tenant_id", "default"),
        )


def _get_tenant_tier(db: Session, tenant_id: str) -> str:
    from app.dashboard.models import TenantConfig

    tenant = db.query(TenantConfig).filter(TenantConfig.tenant_id == tenant_id).first()
    return tenant.tier if tenant else "free"
