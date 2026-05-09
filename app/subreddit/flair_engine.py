"""Flair automation engine — auto-assigns post and user flair."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from sqlalchemy.orm import Session

from app.dashboard.models import FlairAssignmentRecord, FlairTemplate, UserReputation

log = logging.getLogger(__name__)


@dataclass
class FlairAssignment:
    template_id: str
    text: str
    css_class: str
    source: str  # "auto_content" | "auto_karma" | "manual"


def auto_assign_post_flair(
    submission: Any,
    subreddit_name: str,
    db: Session,
    tenant_id: str = "default",
) -> FlairAssignment | None:
    """Match submission title+body against FlairTemplate keyword rules."""
    templates = (
        db.query(FlairTemplate)
        .filter(
            FlairTemplate.tenant_id == tenant_id,
            FlairTemplate.subreddit_name == subreddit_name,
            FlairTemplate.flair_type == "link",
        )
        .all()
    )
    text = f"{getattr(submission, 'title', '')} {getattr(submission, 'selftext', '')}".lower()
    for tmpl in templates:
        keywords: list[str] = tmpl.auto_assign_keywords or []
        if any(kw.lower() in text for kw in keywords if kw):
            return FlairAssignment(
                template_id=tmpl.reddit_template_id,
                text=tmpl.text,
                css_class=tmpl.css_class,
                source="auto_content",
            )
    return None


def auto_assign_user_flair(
    reddit: Any,
    subreddit_name: str,
    username: str,
    reputation: UserReputation,
    db: Session,
    tenant_id: str = "default",
    dry_run: bool = True,
) -> bool:
    """Assign user flair based on reputation tier."""
    tier = _compute_flair_tier(reputation.reputation_score)
    if tier == reputation.flair_tier:
        return False  # no change needed

    if dry_run:
        log.info("DRY_RUN user flair: u/%s → %s", username, tier)
        return True

    try:
        reddit.subreddit(subreddit_name).flair.set(username, text=tier)
        reputation.flair_tier = tier
        db.commit()
        _record_assignment(db, tenant_id, subreddit_name, username, tier, "user", "auto_karma")
        return True
    except Exception as exc:
        log.warning("Could not set user flair for u/%s: %s", username, exc)
        return False


def run_user_flair_batch(
    reddit: Any,
    subreddit_name: str,
    db: Session,
    settings: Any,
) -> int:
    """Update user flair for all tracked users whose tier has changed."""
    tenant_id = getattr(settings, "tenant_id", "default")
    dry_run = getattr(settings, "dry_run", True)
    users = (
        db.query(UserReputation)
        .filter(
            UserReputation.tenant_id == tenant_id,
            UserReputation.subreddit_name == subreddit_name,
        )
        .all()
    )
    updated = 0
    for rep in users:
        if auto_assign_user_flair(
            reddit, subreddit_name, rep.username, rep, db, tenant_id, dry_run
        ):
            updated += 1
    log.info("User flair batch: %d updated in r/%s", updated, subreddit_name)
    return updated


def create_flair_template(
    reddit: Any,
    subreddit_name: str,
    text: str,
    css_class: str = "",
    flair_type: str = "link",
    db: Session | None = None,
    tenant_id: str = "default",
) -> str:
    """Create a flair template on Reddit and persist it to DB."""
    sub = reddit.subreddit(subreddit_name)
    if flair_type == "link":
        tmpl = sub.flair.link_templates.add(text=text, css_class=css_class)
    else:
        tmpl = sub.flair.templates.add(text=text, css_class=css_class)
    template_id = tmpl.get("id", "") if isinstance(tmpl, dict) else ""
    if db and template_id:
        record = FlairTemplate(
            tenant_id=tenant_id,
            subreddit_name=subreddit_name,
            reddit_template_id=template_id,
            text=text,
            css_class=css_class,
            flair_type=flair_type,
            auto_assign_keywords=[],
        )
        db.add(record)
        db.commit()
    return template_id


def delete_flair_template(
    reddit: Any,
    subreddit_name: str,
    template_id: str,
    db: Session | None = None,
    tenant_id: str = "default",
) -> bool:
    """Delete a flair template from Reddit and DB."""
    try:
        sub = reddit.subreddit(subreddit_name)
        sub.flair.link_templates.delete(template_id)
        if db:
            db.query(FlairTemplate).filter(
                FlairTemplate.tenant_id == tenant_id,
                FlairTemplate.reddit_template_id == template_id,
            ).delete()
            db.commit()
        return True
    except Exception as exc:
        log.error("Failed to delete flair template %s: %s", template_id, exc)
        return False


def list_flair_templates(
    db: Session,
    subreddit_name: str,
    tenant_id: str = "default",
    flair_type: str = "link",
) -> list[dict]:
    records = (
        db.query(FlairTemplate)
        .filter(
            FlairTemplate.tenant_id == tenant_id,
            FlairTemplate.subreddit_name == subreddit_name,
            FlairTemplate.flair_type == flair_type,
        )
        .all()
    )
    return [
        {
            "id": r.id,
            "reddit_template_id": r.reddit_template_id,
            "text": r.text,
            "css_class": r.css_class,
            "flair_type": r.flair_type,
            "auto_assign_keywords": r.auto_assign_keywords or [],
        }
        for r in records
    ]


# ── Helpers ───────────────────────────────────────────────────────────────────


def _compute_flair_tier(score: float) -> str:
    if score >= 50:
        return "⭐ Top Contributor"
    if score >= 20:
        return "🔥 Active Member"
    if score >= 0:
        return "Member"
    return "New"


def _record_assignment(
    db: Session,
    tenant_id: str,
    subreddit_name: str,
    target: str,
    flair_text: str,
    flair_type: str,
    source: str,
) -> None:
    record = FlairAssignmentRecord(
        tenant_id=tenant_id,
        subreddit_name=subreddit_name,
        target=target,
        flair_text=flair_text,
        flair_type=flair_type,
        source=source,
    )
    db.add(record)
    db.commit()
