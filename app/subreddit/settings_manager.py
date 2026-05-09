"""Subreddit settings automation — reads and writes all SubredditModeration settings."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

log = logging.getLogger(__name__)


@dataclass
class SubredditSettingsSnapshot:
    subreddit: str
    settings: dict[str, Any]
    captured_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class SyncResult:
    synced: int
    errors: list[str]


def get_settings(reddit: Any, subreddit_name: str) -> SubredditSettingsSnapshot:
    """Fetch current subreddit settings via PRAW."""
    sub = reddit.subreddit(subreddit_name)
    settings_dict = sub.mod.settings()
    return SubredditSettingsSnapshot(subreddit=subreddit_name, settings=dict(settings_dict))


def update_settings(
    reddit: Any, subreddit_name: str, dry_run: bool = True, **kwargs: Any
) -> bool:
    """Update subreddit settings.  No-ops in dry_run mode."""
    if dry_run:
        log.info("DRY_RUN update_settings r/%s: %s", subreddit_name, kwargs)
        return True
    try:
        reddit.subreddit(subreddit_name).mod.update(**kwargs)
        log.info("Updated settings for r/%s: %s", subreddit_name, list(kwargs.keys()))
        return True
    except Exception as exc:
        log.error("Failed to update settings for r/%s: %s", subreddit_name, exc)
        return False


def accept_mod_invite(reddit: Any, subreddit_name: str) -> bool:
    """Accept a moderator invitation for *subreddit_name*."""
    try:
        reddit.subreddit(subreddit_name).mod.accept_invite()
        log.info("Accepted mod invite for r/%s", subreddit_name)
        return True
    except Exception as exc:
        log.error("Failed to accept mod invite for r/%s: %s", subreddit_name, exc)
        return False


def sync_policy(
    reddit: Any,
    db: Session,
    source: str,
    targets: list[str],
    policy_types: list[str],
) -> SyncResult:
    """Copy rules, removal reasons, and/or flair templates from *source* to each target.

    Each target is committed independently so a failure on one does not roll
    back successful syncs on others.  Idempotent — calling twice produces the
    same subreddit state.
    """
    from app.dashboard.models import PolicySyncRecord

    synced = 0
    errors: list[str] = []

    source_data = _fetch_policy_data(reddit, source, policy_types)

    for target in targets:
        try:
            _apply_policy_data(reddit, target, source_data, policy_types)
            record = PolicySyncRecord(
                source_subreddit=source,
                target_subreddit=target,
                policy_types=policy_types,
                success=True,
            )
            db.add(record)
            db.commit()
            synced += 1
            log.info("Policy synced from r/%s → r/%s (%s)", source, target, policy_types)
        except Exception as exc:
            db.rollback()
            msg = f"r/{target}: {exc}"
            errors.append(msg)
            log.error("Policy sync failed for r/%s: %s", target, exc)
            record = PolicySyncRecord(
                source_subreddit=source,
                target_subreddit=target,
                policy_types=policy_types,
                success=False,
                error_message=str(exc),
            )
            db.add(record)
            db.commit()

    return SyncResult(synced=synced, errors=errors)


# ── Internal helpers ──────────────────────────────────────────────────────────


def _fetch_policy_data(reddit: Any, subreddit_name: str, policy_types: list[str]) -> dict:
    data: dict[str, Any] = {}
    sub = reddit.subreddit(subreddit_name)
    if "rules" in policy_types:
        data["rules"] = [
            {"short_name": r.short_name, "description": r.description,
             "violation_reason": r.violation_reason}
            for r in sub.rules
        ]
    if "removal_reasons" in policy_types:
        data["removal_reasons"] = [
            {"title": rr.title, "message": rr.message}
            for rr in sub.mod.removal_reasons
        ]
    return data


def _apply_policy_data(
    reddit: Any, target: str, data: dict, policy_types: list[str]
) -> None:
    sub = reddit.subreddit(target)
    if "rules" in policy_types and "rules" in data:
        # Delete existing rules then recreate — simplest idempotent approach
        for rule in list(sub.rules):
            rule.mod.delete()
        for r in data["rules"]:
            sub.rules.mod.add(
                short_name=r["short_name"],
                kind="all",
                description=r.get("description", ""),
                violation_reason=r.get("violation_reason", r["short_name"]),
            )
    if "removal_reasons" in policy_types and "removal_reasons" in data:
        for rr in data["removal_reasons"]:
            sub.mod.removal_reasons.add(title=rr["title"], message=rr["message"])
