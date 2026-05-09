"""Wiki manager — CRUD and auto-update for subreddit wiki pages."""

from __future__ import annotations

import logging
from typing import Any

from sqlalchemy.orm import Session

from app.dashboard.models import WikiPage

log = logging.getLogger(__name__)


def get_wiki_page(reddit: Any, subreddit_name: str, page_name: str) -> dict:
    page = reddit.subreddit(subreddit_name).wiki[page_name]
    return {"name": page_name, "content": page.content_md, "revision_by": str(page.revision_by)}


def update_wiki_page(
    reddit: Any,
    subreddit_name: str,
    page_name: str,
    content: str,
    reason: str = "Bot update",
    dry_run: bool = True,
    db: Session | None = None,
    tenant_id: str = "default",
) -> bool:
    if dry_run:
        log.info("DRY_RUN wiki update r/%s/%s", subreddit_name, page_name)
        return True
    try:
        reddit.subreddit(subreddit_name).wiki[page_name].edit(content=content, reason=reason)
        if db:
            _sync_local(db, tenant_id, subreddit_name, page_name, content)
        return True
    except Exception as exc:
        log.error("Wiki update failed r/%s/%s: %s", subreddit_name, page_name, exc)
        return False


def list_wiki_pages(reddit: Any, subreddit_name: str) -> list[str]:
    try:
        return [p.name for p in reddit.subreddit(subreddit_name).wiki.pages()]
    except Exception as exc:
        log.error("Could not list wiki pages for r/%s: %s", subreddit_name, exc)
        return []


def get_wiki_revision_history(reddit: Any, subreddit_name: str, page_name: str) -> list[dict]:
    try:
        page = reddit.subreddit(subreddit_name).wiki[page_name]
        return [
            {
                "id": str(rev.id),
                "author": str(rev.author),
                "timestamp": rev.timestamp,
                "reason": rev.reason,
            }
            for rev in page.revisions(limit=20)
        ]
    except Exception as exc:
        log.error("Could not fetch wiki revisions r/%s/%s: %s", subreddit_name, page_name, exc)
        return []


def auto_update_faq(
    reddit: Any,
    subreddit_name: str,
    db: Session,
    settings: Any,
) -> bool:
    """Regenerate the FAQ wiki page from the most common modmail questions."""
    from app.dashboard.models import ModmailRecord

    tenant_id = getattr(settings, "tenant_id", "default")
    questions = (
        db.query(ModmailRecord)
        .filter(
            ModmailRecord.tenant_id == tenant_id,
            ModmailRecord.subreddit_name == subreddit_name,
            ModmailRecord.category == "question",
        )
        .order_by(ModmailRecord.created_at.desc())
        .limit(20)
        .all()
    )
    if not questions:
        return False

    lines = ["# Frequently Asked Questions\n"]
    for q in questions:
        lines.append(f"## {q.subject}\n\n*Auto-generated from community questions.*\n")
    content = "\n".join(lines)
    return update_wiki_page(
        reddit, subreddit_name, "faq", content,
        reason="Auto-update FAQ", dry_run=getattr(settings, "dry_run", True),
        db=db, tenant_id=tenant_id,
    )


def auto_update_changelog(
    reddit: Any,
    subreddit_name: str,
    db: Session,
    settings: Any,
) -> bool:
    """Append latest GitHub release notes to the changelog wiki page."""
    from app.dashboard.models import PendingPost

    tenant_id = getattr(settings, "tenant_id", "default")
    releases = (
        db.query(PendingPost)
        .filter(PendingPost.status == "approved")
        .order_by(PendingPost.created_at.desc())
        .limit(10)
        .all()
    )
    if not releases:
        return False

    lines = ["# Changelog\n"]
    for r in releases:
        lines.append(f"## {r.title}\n\n{r.body[:500]}\n\n[Source]({r.source_url})\n")
    content = "\n".join(lines)
    return update_wiki_page(
        reddit, subreddit_name, "changelog", content,
        reason="Auto-update changelog", dry_run=getattr(settings, "dry_run", True),
        db=db, tenant_id=tenant_id,
    )


def _sync_local(db: Session, tenant_id: str, subreddit_name: str, page_name: str, content: str) -> None:
    from datetime import datetime, timezone

    record = (
        db.query(WikiPage)
        .filter(WikiPage.tenant_id == tenant_id, WikiPage.subreddit_name == subreddit_name, WikiPage.page_name == page_name)
        .first()
    )
    if record:
        record.content = content
        record.last_synced_at = datetime.now(timezone.utc)
    else:
        db.add(WikiPage(tenant_id=tenant_id, subreddit_name=subreddit_name, page_name=page_name, content=content))
    db.commit()
