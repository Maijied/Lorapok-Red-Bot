"""Lorapok Red Bot — worker entrypoint.

Bootstraps the system, starts the APScheduler background jobs, and runs
the infinite comment + submission stream loop across all configured subreddits.

Design principles:
- No business logic here — only orchestration.
- Settings and DB session are injected into every domain call (no globals).
- One bad comment/submission never kills the stream (per-item try/except).
- All Reddit write operations are guarded by ``settings.dry_run``.
"""

from __future__ import annotations

import logging
import time
from typing import Any

import praw
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from app.config import Settings
from app.database import get_engine, get_session_factory, init_db
from app.moderation.classifier import _to_decision, classify_text
from app.moderation.memory import remember_case
from app.moderation.queue import queue_case
from app.moderation.rules import ModerationDecision, apply_light_rules
from app.dashboard.metrics import metrics_store
from app.posting.scheduler import create_scheduler, register_all_jobs
from app.utils.logging import setup_logging
from app.utils.notify import send_alert_sync
from app.utils.rate_limit import RateLimiter

log = logging.getLogger(__name__)

REMOVAL_NOTICE = (
    "Your comment was removed by Lorapok Red Bot because it appears to violate "
    "community rules. If you think this was a mistake, please contact the moderators."
)
HELP_PROMPT = (
    "Hi! Please include the code, error message, and what you expected. "
    "That makes it easier for the community to help."
)


# ── Public entrypoint ─────────────────────────────────────────────────────────


def main() -> None:
    settings = Settings.from_env()
    setup_logging(settings.log_level)
    log.info("Lorapok Red Bot starting (dry_run=%s).", settings.dry_run)

    # Database
    init_db(settings.database_url)
    engine = get_engine(settings.database_url)
    session_factory = get_session_factory(engine)

    # Reddit client
    reddit = _build_reddit(settings)
    me = reddit.user.me()
    log.info("Authenticated as u/%s", me)

    # Scheduler
    scheduler = create_scheduler()
    register_all_jobs(scheduler, settings, session_factory)
    scheduler.start()

    send_alert_sync(
        f"🤖 Lorapok Red Bot started as u/{me} "
        f"(subreddits: {', '.join(settings.subreddit_names)}, dry_run={settings.dry_run})",
        settings,
    )

    rate_limiter = RateLimiter(min_interval=2.0)

    try:
        _run_stream(reddit, settings, session_factory, rate_limiter)
    finally:
        scheduler.shutdown(wait=False)
        log.info("Lorapok Red Bot stopped.")


# ── Stream loop ───────────────────────────────────────────────────────────────


def _run_stream(
    reddit: praw.Reddit,
    settings: Settings,
    session_factory: Any,
    rate_limiter: RateLimiter,
) -> None:
    """Stream comments and submissions from all configured subreddits."""
    sub_str = "+".join(settings.subreddit_names)
    subreddit = reddit.subreddit(sub_str)

    import prawcore

    for item in subreddit.stream.comments(skip_existing=True):
        db = session_factory()
        try:
            process_comment(db, item, settings)
            rate_limiter.wait()
        except OperationalError as exc:
            log.error("DB error processing comment: %s", exc)
            db.rollback()
            send_alert_sync(f"DB error: {exc}", settings)
            time.sleep(5)
        except prawcore.exceptions.PrawcoreException as exc:
            log.error("Reddit API error: %s", exc)
            send_alert_sync(f"Reddit API error: {exc}", settings)
            time.sleep(10)
        except Exception as exc:
            log.error("Unexpected error processing comment: %s", exc)
            send_alert_sync(f"Bot error: {exc}", settings)
            time.sleep(5)
        finally:
            db.close()


# ── Comment processing ────────────────────────────────────────────────────────


def process_comment(db: Session, comment: Any, settings: Settings) -> None:
    """Route a single comment through the moderation pipeline."""
    text = getattr(comment, "body", "") or ""
    if not text.strip():
        return

    rule_decision = apply_light_rules(text)

    if (
        rule_decision.action == "remove"
        and rule_decision.confidence >= settings.review_confidence_threshold
    ):
        _apply_decision(db, comment, rule_decision, settings)
        metrics_store.increment("comments_processed")
        return

    if (
        rule_decision.action == "review"
        or rule_decision.confidence < settings.review_confidence_threshold
    ):
        ai_payload = classify_text(text, model=settings.ai_model)
        ai_decision = _to_decision(ai_payload)

        if (
            ai_decision.action == "review"
            or ai_decision.confidence < settings.review_confidence_threshold
        ):
            recommended = (
                ai_decision.action if ai_decision.action != "review" else rule_decision.action
            )
            queue_case(
                db,
                text,
                ai_decision.reason,
                "rules+ai",
                recommended,
                tenant_id=settings.tenant_id,
                subreddit_name=getattr(comment, "subreddit_name_prefixed", ""),
            )
            metrics_store.increment("queued_reviews")
            metrics_store.increment("comments_processed")
            return

        _apply_decision(db, comment, ai_decision, settings)
        metrics_store.increment("comments_processed")
        return

    _apply_decision(db, comment, rule_decision, settings)
    metrics_store.increment("comments_processed")


def process_submission(db: Session, submission: Any, settings: Settings) -> None:
    """Route a single submission through the moderation pipeline."""
    title = getattr(submission, "title", "") or ""
    selftext = getattr(submission, "selftext", "") or ""
    text = f"{title}\n{selftext}".strip()
    if not text:
        return

    rule_decision = apply_light_rules(text)

    if (
        rule_decision.action == "remove"
        and rule_decision.confidence >= settings.review_confidence_threshold
    ):
        _apply_submission_decision(db, submission, rule_decision, settings)
        metrics_store.increment("comments_processed")
        return

    if (
        rule_decision.action == "review"
        or rule_decision.confidence < settings.review_confidence_threshold
    ):
        ai_payload = classify_text(text, model=settings.ai_model)
        ai_decision = _to_decision(ai_payload)

        if (
            ai_decision.action == "review"
            or ai_decision.confidence < settings.review_confidence_threshold
        ):
            recommended = (
                ai_decision.action if ai_decision.action != "review" else rule_decision.action
            )
            queue_case(
                db,
                text,
                ai_decision.reason,
                "rules+ai",
                recommended,
                tenant_id=settings.tenant_id,
                subreddit_name=getattr(submission, "subreddit_name_prefixed", ""),
            )
            metrics_store.increment("queued_reviews")
            metrics_store.increment("comments_processed")
            return

        _apply_submission_decision(db, submission, ai_decision, settings)
        metrics_store.increment("comments_processed")
        return

    _apply_submission_decision(db, submission, rule_decision, settings)
    metrics_store.increment("comments_processed")


# ── Decision application ──────────────────────────────────────────────────────


def _apply_decision(
    db: Session, comment: Any, decision: ModerationDecision, settings: Settings
) -> None:
    subreddit_name = getattr(comment, "subreddit_name_prefixed", "")
    remember_case(
        db,
        getattr(comment, "body", ""),
        decision.action,
        decision.reason,
        "rules+ai",
        tenant_id=settings.tenant_id,
        subreddit_name=subreddit_name,
    )

    if decision.action == "remove":
        if settings.dry_run:
            log.info("DRY_RUN remove comment %s: %s", getattr(comment, "id", "?"), decision.reason)
        else:
            try:
                comment.mod.remove()
                comment.reply(REMOVAL_NOTICE)
            except Exception as exc:
                log.warning("Could not remove comment: %s", exc)
        metrics_store.increment("actions_taken")

    elif decision.action == "allow" and _should_offer_help(getattr(comment, "body", "")):
        if not settings.dry_run:
            try:
                comment.reply(HELP_PROMPT)
            except Exception as exc:
                log.warning("Could not reply to comment: %s", exc)


def _apply_submission_decision(
    db: Session, submission: Any, decision: ModerationDecision, settings: Settings
) -> None:
    text = f"{getattr(submission, 'title', '')} {getattr(submission, 'selftext', '')}".strip()
    subreddit_name = getattr(submission, "subreddit_name_prefixed", "")
    remember_case(
        db,
        text,
        decision.action,
        decision.reason,
        "rules+ai",
        tenant_id=settings.tenant_id,
        subreddit_name=subreddit_name,
    )

    if decision.action == "remove":
        if settings.dry_run:
            log.info(
                "DRY_RUN remove submission %s: %s",
                getattr(submission, "id", "?"),
                decision.reason,
            )
        else:
            try:
                submission.mod.remove()
            except Exception as exc:
                log.warning("Could not remove submission: %s", exc)
        metrics_store.increment("actions_taken")


# ── Helpers ───────────────────────────────────────────────────────────────────


def _should_offer_help(text: str) -> bool:
    help_signals = ["help", "error", "how do i", "how to", "not working", "broken", "issue"]
    lowered = text.lower()
    return any(signal in lowered for signal in help_signals)


def _build_reddit(settings: Settings) -> praw.Reddit:
    return praw.Reddit(
        client_id=settings.reddit_client_id,
        client_secret=settings.reddit_client_secret,
        username=settings.reddit_username,
        password=settings.reddit_password,
        user_agent=settings.reddit_user_agent,
    )


if __name__ == "__main__":
    main()
