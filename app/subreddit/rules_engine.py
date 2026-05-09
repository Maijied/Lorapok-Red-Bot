"""Rules engine v2 — subreddit rules, removal reasons, and violation tracking."""

from __future__ import annotations

import logging
from typing import Any

from sqlalchemy.orm import Session

from app.dashboard.models import RuleViolationRecord

log = logging.getLogger(__name__)


def list_rules(reddit: Any, subreddit_name: str) -> list[dict]:
    try:
        return [
            {
                "short_name": r.short_name,
                "description": r.description,
                "violation_reason": r.violation_reason,
                "kind": r.kind,
            }
            for r in reddit.subreddit(subreddit_name).rules
        ]
    except Exception as exc:
        log.error("Could not list rules for r/%s: %s", subreddit_name, exc)
        return []


def add_rule(
    reddit: Any,
    subreddit_name: str,
    short_name: str,
    description: str = "",
    violation_reason: str = "",
    dry_run: bool = True,
) -> bool:
    if dry_run:
        log.info("DRY_RUN add_rule r/%s: %s", subreddit_name, short_name)
        return True
    try:
        reddit.subreddit(subreddit_name).rules.mod.add(
            short_name=short_name,
            kind="all",
            description=description,
            violation_reason=violation_reason or short_name,
        )
        return True
    except Exception as exc:
        log.error("Failed to add rule to r/%s: %s", subreddit_name, exc)
        return False


def delete_rule(
    reddit: Any, subreddit_name: str, short_name: str, dry_run: bool = True
) -> bool:
    if dry_run:
        log.info("DRY_RUN delete_rule r/%s: %s", subreddit_name, short_name)
        return True
    try:
        for rule in reddit.subreddit(subreddit_name).rules:
            if rule.short_name == short_name:
                rule.mod.delete()
                return True
        return False
    except Exception as exc:
        log.error("Failed to delete rule from r/%s: %s", subreddit_name, exc)
        return False


def list_removal_reasons(reddit: Any, subreddit_name: str) -> list[dict]:
    try:
        return [
            {"id": rr.id, "title": rr.title, "message": rr.message}
            for rr in reddit.subreddit(subreddit_name).mod.removal_reasons
        ]
    except Exception as exc:
        log.error("Could not list removal reasons for r/%s: %s", subreddit_name, exc)
        return []


def add_removal_reason(
    reddit: Any,
    subreddit_name: str,
    title: str,
    message: str,
    dry_run: bool = True,
) -> str:
    if dry_run:
        log.info("DRY_RUN add_removal_reason r/%s: %s", subreddit_name, title)
        return "dry_run_id"
    try:
        rr = reddit.subreddit(subreddit_name).mod.removal_reasons.add(
            title=title, message=message
        )
        return rr.id
    except Exception as exc:
        log.error("Failed to add removal reason to r/%s: %s", subreddit_name, exc)
        return ""


def delete_removal_reason(
    reddit: Any, subreddit_name: str, reason_id: str, dry_run: bool = True
) -> bool:
    if dry_run:
        log.info("DRY_RUN delete_removal_reason r/%s: %s", subreddit_name, reason_id)
        return True
    try:
        reddit.subreddit(subreddit_name).mod.removal_reasons[reason_id].delete()
        return True
    except Exception as exc:
        log.error("Failed to delete removal reason %s: %s", reason_id, exc)
        return False


def track_rule_violation(
    db: Session,
    username: str,
    subreddit_name: str,
    rule_id: str,
    content_id: str,
    tenant_id: str = "default",
) -> None:
    record = RuleViolationRecord(
        tenant_id=tenant_id,
        username=username,
        subreddit_name=subreddit_name,
        rule_id=rule_id,
        content_id=content_id,
    )
    db.add(record)
    db.commit()


def get_user_violation_history(
    db: Session,
    username: str,
    subreddit_name: str,
    tenant_id: str = "default",
) -> list[dict]:
    records = (
        db.query(RuleViolationRecord)
        .filter(
            RuleViolationRecord.tenant_id == tenant_id,
            RuleViolationRecord.username == username,
            RuleViolationRecord.subreddit_name == subreddit_name,
        )
        .order_by(RuleViolationRecord.created_at.desc())
        .all()
    )
    return [
        {
            "id": r.id,
            "rule_id": r.rule_id,
            "content_id": r.content_id,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in records
    ]
