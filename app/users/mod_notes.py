"""Mod notes system — create, fetch, and search moderator notes on users."""

from __future__ import annotations

import logging
from typing import Any

from sqlalchemy.orm import Session

from app.dashboard.models import ModNote

log = logging.getLogger(__name__)

_VALID_LABELS = {"BOT_BAN", "BOT_SPAM", "BOT_REVIEW", "HUMAN_OVERRIDE"}


def add_mod_note(
    reddit: Any,
    subreddit_name: str,
    username: str,
    note: str,
    label: str = "BOT_REVIEW",
    db: Session | None = None,
    tenant_id: str = "default",
    dry_run: bool = True,
) -> bool:
    if label not in _VALID_LABELS:
        label = "BOT_REVIEW"

    reddit_note_id = None
    if not dry_run:
        try:
            redditor = reddit.redditor(username)
            created = reddit.subreddit(subreddit_name).mod.notes.create(
                redditor=redditor, note=note, label=label
            )
            reddit_note_id = getattr(created, "id", None)
        except Exception as exc:
            log.warning("Could not create Reddit mod note for u/%s: %s", username, exc)
    else:
        log.info("DRY_RUN mod note u/%s r/%s [%s]: %s", username, subreddit_name, label, note[:80])

    if db:
        record = ModNote(
            tenant_id=tenant_id,
            username=username,
            subreddit_name=subreddit_name,
            note=note,
            label=label,
            created_by="LorapokRedBot",
            reddit_note_id=str(reddit_note_id) if reddit_note_id else None,
        )
        db.add(record)
        db.commit()

    return True


def get_mod_notes(
    reddit: Any, subreddit_name: str, username: str
) -> list[dict]:
    """Fetch mod notes from Reddit via PRAW."""
    try:
        redditor = reddit.redditor(username)
        notes = reddit.subreddit(subreddit_name).mod.notes.redditors(redditor)
        return [
            {
                "id": getattr(n, "id", ""),
                "note": getattr(n, "note", ""),
                "label": getattr(n, "label", ""),
                "created_at": getattr(n, "created_at", None),
            }
            for n in notes
        ]
    except Exception as exc:
        log.error("Could not fetch mod notes for u/%s: %s", username, exc)
        return []


def search_mod_notes(
    db: Session,
    subreddit_name: str,
    query: str,
    tenant_id: str = "default",
) -> list[dict]:
    records = (
        db.query(ModNote)
        .filter(
            ModNote.tenant_id == tenant_id,
            ModNote.subreddit_name == subreddit_name,
            ModNote.note.ilike(f"%{query}%"),
        )
        .order_by(ModNote.created_at.desc())
        .limit(50)
        .all()
    )
    return [
        {
            "id": r.id,
            "username": r.username,
            "note": r.note,
            "label": r.label,
            "created_by": r.created_by,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in records
    ]


def auto_note_on_action(
    reddit: Any,
    db: Session,
    username: str,
    subreddit_name: str,
    action: str,
    reason: str,
    tenant_id: str = "default",
    dry_run: bool = True,
) -> None:
    """Automatically create a mod note when the bot takes an action."""
    label_map = {
        "remove": "BOT_SPAM",
        "ban": "BOT_BAN",
        "review": "BOT_REVIEW",
        "override": "HUMAN_OVERRIDE",
    }
    label = label_map.get(action, "BOT_REVIEW")
    note = f"[{action.upper()}] {reason[:200]}"
    add_mod_note(reddit, subreddit_name, username, note, label, db, tenant_id, dry_run)
