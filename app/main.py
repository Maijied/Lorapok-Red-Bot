"""Lorapok Red Bot — worker entrypoint.

Bootstraps the system, starts APScheduler background jobs, and runs the
infinite comment stream loop across all configured subreddits.

Design principles:
- No business logic here — only orchestration.
- Settings and DB session injected into every domain call (no globals).
- One bad item never kills the stream (per-item try/except).
- All Reddit write operations guarded by ``settings.dry_run``.
"""

from __future__ import annotations

import logging
import threading
import time
from typing import Any

import praw
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from app.config import Settings
from app.dashboard.metrics import metrics_store
from app.database import get_engine, get_session_factory, init_db
from app.moderation.classifier import _to_decision, classify_text
from app.moderation.memory import remember_case
from app.moderation.queue import queue_case
from app.moderation.rules import ModerationDecision, apply_light_rules
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

    init_db(settings.database_url)
    engine = get_engine(settings.database_url)
    session_factory = get_session_factory(engine)

    reddit = _build_reddit(settings)
    me = reddit.user.me()
    log.info("Authenticated as u/%s", me)

    scheduler = create_scheduler()
    register_all_jobs(scheduler, settings, session_factory)
    scheduler.start()

    send_alert_sync(
        f"🤖 Lorapok Red Bot started as u/{me} "
        f"(subreddits: {', '.join(settings.subreddit_names)}, "
        f"dry_run={settings.dry_run})",
        settings,
    )

    rate_limiter = RateLimiter(min_interval=2.0)

    # Modmail stream in a daemon thread (task 4.4)
    threading.Thread(
        target=_run_modmail_stream,
        args=(reddit, settings, session_factory),
        daemon=True,
        name="modmail-stream",
    ).start()

    try:
        _run_stream(reddit, settings, session_factory, rate_limiter)
    finally:
        scheduler.shutdown(wait=False)
        log.info("Lorapok Red Bot stopped.")


# ── Comment stream ────────────────────────────────────────────────────────────


def _run_stream(
    reddit: praw.Reddit,
    settings: Settings,
    session_factory: Any,
    rate_limiter: RateLimiter,
) -> None:
    """Stream comments from all configured subreddits."""
    import prawcore

    sub_str = "+".join(settings.subreddit_names)
    subreddit = reddit.subreddit(sub_str)

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


# ── Modmail stream (task 4.4) ─────────────────────────────────────────────────


def _run_modmail_stream(
    reddit: praw.Reddit,
    settings: Settings,
    session_factory: Any,
) -> None:
    """Stream modmail conversations and triage them. Runs in a daemon thread."""
    try:
        from app.billing.features import has_feature
        from app.subreddit.modmail_triage import triage_conversation
    except ImportError:
        log.warning("Modmail triage unavailable — skipping modmail stream.")
        return

    log.info("Modmail stream started.")
    while True:
        try:
            sub_str = "+".join(settings.subreddit_names)
            stream = reddit.subreddit(sub_str).mod.stream.modmail_conversations(
                skip_existing=True
            )
            for conversation in stream:
                db = session_factory()
                try:
                    if has_feature(db, settings.tenant_id, "modmail_triage"):
                        triage_conversation(conversation, settings, db)
                        _dispatch(
                            "modmail.received",
                            {"id": str(conversation.id)},
                            db, settings,
                        )
                except Exception as exc:
                    log.error("Modmail triage error: %s", exc)
                finally:
                    db.close()
        except Exception as exc:
            log.error("Modmail stream error: %s", exc)
            time.sleep(30)


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
        _record_sentiment_async(text, comment, db, settings)
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
                ai_decision.action
                if ai_decision.action != "review"
                else rule_decision.action
            )
            case_id = queue_case(
                db, text, ai_decision.reason, "rules+ai", recommended,
                tenant_id=settings.tenant_id,
                subreddit_name=getattr(comment, "subreddit_name_prefixed", ""),
            )
            metrics_store.increment("queued_reviews")
            metrics_store.increment("comments_processed")
            _dispatch(
                "queue.case_added",
                {"case_id": case_id, "reason": ai_decision.reason},
                db, settings,
            )
            return

        _apply_decision(db, comment, ai_decision, settings)
        metrics_store.increment("comments_processed")
        _record_sentiment_async(text, comment, db, settings)
        return

    _apply_decision(db, comment, rule_decision, settings)
    metrics_store.increment("comments_processed")
    _record_sentiment_async(text, comment, db, settings)


# ── Submission processing ─────────────────────────────────────────────────────


def process_submission(db: Session, submission: Any, settings: Settings) -> None:
    """Route a single submission through the moderation pipeline."""
    title = getattr(submission, "title", "") or ""
    selftext = getattr(submission, "selftext", "") or ""
    text = f"{title}\n{selftext}".strip()
    if not text:
        return

    # Cross-subreddit spam detection (task 6.7)
    _check_spam(text, submission, db, settings)

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
                ai_decision.action
                if ai_decision.action != "review"
                else rule_decision.action
            )
            case_id = queue_case(
                db, text, ai_decision.reason, "rules+ai", recommended,
                tenant_id=settings.tenant_id,
                subreddit_name=getattr(submission, "subreddit_name_prefixed", ""),
            )
            metrics_store.increment("queued_reviews")
            metrics_store.increment("comments_processed")
            _dispatch(
                "queue.case_added",
                {"case_id": case_id, "reason": ai_decision.reason},
                db, settings,
            )
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
        db, getattr(comment, "body", ""), decision.action, decision.reason,
        "rules+ai", tenant_id=settings.tenant_id, subreddit_name=subreddit_name,
    )

    if decision.action == "remove":
        if settings.dry_run:
            log.info(
                "DRY_RUN remove comment %s: %s",
                getattr(comment, "id", "?"), decision.reason,
            )
        else:
            try:
                comment.mod.remove()
                comment.reply(REMOVAL_NOTICE)
            except Exception as exc:
                log.warning("Could not remove comment: %s", exc)
        metrics_store.increment("actions_taken")
        _dispatch(
            "comment.removed",
            {"id": getattr(comment, "id", ""), "reason": decision.reason},
            db, settings,
        )

    elif decision.action == "allow" and _should_offer_help(getattr(comment, "body", "")):
        if not settings.dry_run:
            try:
                comment.reply(HELP_PROMPT)
            except Exception as exc:
                log.warning("Could not reply to comment: %s", exc)


def _apply_submission_decision(
    db: Session, submission: Any, decision: ModerationDecision, settings: Settings
) -> None:
    text = (
        f"{getattr(submission, 'title', '')} "
        f"{getattr(submission, 'selftext', '')}".strip()
    )
    subreddit_name = getattr(submission, "subreddit_name_prefixed", "")
    remember_case(
        db, text, decision.action, decision.reason,
        "rules+ai", tenant_id=settings.tenant_id, subreddit_name=subreddit_name,
    )

    if decision.action == "remove":
        if settings.dry_run:
            log.info(
                "DRY_RUN remove submission %s: %s",
                getattr(submission, "id", "?"), decision.reason,
            )
        else:
            try:
                submission.mod.remove()
            except Exception as exc:
                log.warning("Could not remove submission: %s", exc)
        metrics_store.increment("actions_taken")
        _dispatch(
            "submission.removed",
            {"id": getattr(submission, "id", ""), "reason": decision.reason},
            db, settings,
        )


# ── AI intelligence helpers (tasks 6.7, 8.5) ─────────────────────────────────


def _record_sentiment_async(
    text: str, item: Any, db: Session, settings: Settings
) -> None:
    """Record sentiment in a fire-and-forget thread (non-blocking)."""
    try:
        from app.billing.features import has_feature

        if not has_feature(db, settings.tenant_id, "sentiment_analysis"):
            return
    except Exception:
        return

    def _run() -> None:
        try:
            from app.database import get_engine, get_session_factory
            from app.moderation.sentiment import analyze_sentiment, record_sentiment

            engine = get_engine(settings.database_url)
            sf = get_session_factory(engine)
            _db = sf()
            try:
                result = analyze_sentiment(text, model=settings.ai_model)
                subreddit_name = getattr(item, "subreddit_name_prefixed", "")
                record_sentiment(
                    _db, subreddit_name, result.score,
                    "comment", tenant_id=settings.tenant_id,
                )
            finally:
                _db.close()
        except Exception as exc:
            log.debug("Sentiment record failed: %s", exc)

    threading.Thread(target=_run, daemon=True).start()


def _check_spam(text: str, submission: Any, db: Session, settings: Settings) -> None:
    """Record submission for cross-subreddit spam detection (task 6.7)."""
    try:
        from app.billing.features import has_feature

        if not has_feature(db, settings.tenant_id, "cross_sub_spam"):
            return

        from app.moderation.spam_detector import detect_cross_sub_spam, record_submission
        from app.utils.text import normalize_text, stable_hash

        username = str(getattr(getattr(submission, "author", None), "name", ""))
        subreddit_name = getattr(submission, "subreddit_name_prefixed", "")
        content_hash = stable_hash(normalize_text(text))
        url = getattr(submission, "url", "")

        record_submission(
            db, username, subreddit_name, content_hash, url,
            tenant_id=settings.tenant_id,
        )
        signal = detect_cross_sub_spam(
            db, username, content_hash, tenant_id=settings.tenant_id,
        )
        if signal and signal.score >= 0.7:
            queue_case(
                db, text,
                f"Cross-sub spam detected in: {', '.join(signal.subreddits)}",
                "spam_detector", "remove",
                tenant_id=settings.tenant_id,
                subreddit_name=subreddit_name,
            )
            _dispatch(
                "spam_signal.detected",
                {"username": username, "score": signal.score,
                 "subreddits": signal.subreddits},
                db, settings,
            )
    except Exception as exc:
        log.debug("Spam check failed: %s", exc)


def _dispatch(
    event_type: str, payload: dict, db: Session, settings: Settings
) -> None:
    """Fire-and-forget outbound webhook dispatch (task 8.5)."""
    def _run() -> None:
        try:
            from app.billing.features import has_feature
            from app.database import get_engine, get_session_factory
            from app.integrations.webhooks import dispatch_event

            engine = get_engine(settings.database_url)
            sf = get_session_factory(engine)
            _db = sf()
            try:
                if has_feature(_db, settings.tenant_id, "custom_webhooks"):
                    dispatch_event(_db, settings.tenant_id, event_type, payload)
            finally:
                _db.close()
        except Exception as exc:
            log.debug("Webhook dispatch failed for %s: %s", event_type, exc)

    threading.Thread(target=_run, daemon=True).start()


# ── Helpers ───────────────────────────────────────────────────────────────────


def _should_offer_help(text: str) -> bool:
    signals = ["help", "error", "how do i", "how to", "not working", "broken", "issue"]
    lowered = text.lower()
    return any(s in lowered for s in signals)


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
