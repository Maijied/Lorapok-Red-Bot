"""APScheduler wrapper — registers all periodic background jobs.

All jobs are registered in ``register_all_jobs`` so ``app/main.py`` stays
clean.  Each job catches its own exceptions and sends an alert rather than
crashing the scheduler.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any

from apscheduler.schedulers.background import BackgroundScheduler

log = logging.getLogger(__name__)


def create_scheduler() -> BackgroundScheduler:
    """Return a UTC-timezone BackgroundScheduler."""
    return BackgroundScheduler(timezone="UTC")


def register_all_jobs(
    scheduler: BackgroundScheduler,
    settings: Any,  # app.config.Settings
    session_factory: Callable,
) -> None:
    """Register every periodic job on *scheduler*.

    Accepts *settings* and *session_factory* so jobs can open DB sessions
    without importing global state.
    """
    _register_weekly_trending(scheduler, settings, session_factory)
    _register_github_monitor(scheduler, settings, session_factory)
    _register_metrics_flush(scheduler, settings, session_factory)
    _register_scheduled_post_publisher(scheduler, settings, session_factory)
    _register_ai_quota_reset(scheduler, settings, session_factory)
    _register_contributor_batches(scheduler, settings, session_factory)
    _register_user_flair_batch(scheduler, settings, session_factory)
    _register_sentiment_alert(scheduler, settings, session_factory)
    log.info("All scheduler jobs registered.")


# ── Individual job registrations ──────────────────────────────────────────────


def _register_weekly_trending(scheduler, settings, session_factory) -> None:
    def _job() -> None:
        try:
            import praw

            from app.integrations.github_integration import fetch_trending_repos
            from app.posting.trending import build_trending_thread

            reddit = praw.Reddit(
                client_id=settings.reddit_client_id,
                client_secret=settings.reddit_client_secret,
                username=settings.reddit_username,
                password=settings.reddit_password,
                user_agent=settings.reddit_user_agent,
            )
            trends = fetch_trending_repos(language="python", days_back=7)
            payload = build_trending_thread(trends)
            if not settings.dry_run:
                for sub_name in settings.subreddit_names:
                    reddit.subreddit(sub_name).submit(
                        payload["title"], selftext=payload["body"]
                    )
                    log.info("Weekly trending post published to r/%s", sub_name)
            else:
                log.info("DRY_RUN: would publish trending post: %s", payload["title"])
        except Exception as exc:
            _alert(settings, f"weekly_trending_post job failed: {exc}")

    scheduler.add_job(
        _job,
        "cron",
        id="weekly_trending_post",
        day_of_week="mon",
        hour=14,
        minute=0,
        replace_existing=True,
    )


def _register_github_monitor(scheduler, settings, session_factory) -> None:
    def _job() -> None:
        try:
            from app.integrations.github_worker import monitor_repositories

            db = session_factory()
            try:
                monitor_repositories(db, settings.monitored_repos)
            finally:
                db.close()
        except Exception as exc:
            _alert(settings, f"github_monitor job failed: {exc}")

    scheduler.add_job(
        _job,
        "interval",
        id="github_monitor",
        hours=1,
        replace_existing=True,
    )


def _register_metrics_flush(scheduler, settings, session_factory) -> None:
    def _job() -> None:
        try:
            from app.dashboard.metrics import metrics_store

            db = session_factory()
            try:
                metrics_store.flush_to_db(db)
            finally:
                db.close()
        except Exception as exc:
            _alert(settings, f"metrics_flush job failed: {exc}")

    scheduler.add_job(
        _job,
        "interval",
        id="metrics_flush",
        minutes=5,
        replace_existing=True,
    )


def _register_scheduled_post_publisher(scheduler, settings, session_factory) -> None:
    def _job() -> None:
        try:
            import praw

            from app.posting.content_calendar import publish_due_posts

            reddit = praw.Reddit(
                client_id=settings.reddit_client_id,
                client_secret=settings.reddit_client_secret,
                username=settings.reddit_username,
                password=settings.reddit_password,
                user_agent=settings.reddit_user_agent,
            )
            db = session_factory()
            try:
                published = publish_due_posts(reddit, db, settings)
                if published:
                    log.info("Published %d scheduled post(s).", published)
            finally:
                db.close()
        except Exception as exc:
            _alert(settings, f"scheduled_post_publisher job failed: {exc}")

    scheduler.add_job(
        _job,
        "interval",
        id="scheduled_post_publisher",
        minutes=1,
        replace_existing=True,
    )


def _register_ai_quota_reset(scheduler, settings, session_factory) -> None:
    def _job() -> None:
        try:
            from app.billing.tenant import reset_all_ai_quotas

            db = session_factory()
            try:
                reset_all_ai_quotas(db)
                log.info("AI quota counters reset for all tenants.")
            finally:
                db.close()
        except Exception as exc:
            _alert(settings, f"ai_quota_reset job failed: {exc}")

    scheduler.add_job(
        _job,
        "cron",
        id="ai_quota_reset",
        hour=0,
        minute=0,
        replace_existing=True,
    )


def _register_contributor_batches(scheduler, settings, session_factory) -> None:
    def _job() -> None:
        try:
            import praw

            from app.billing.features import has_feature
            from app.users.contributors import (
                run_contributor_demotion_batch,
                run_contributor_promotion_batch,
            )

            reddit = praw.Reddit(
                client_id=settings.reddit_client_id,
                client_secret=settings.reddit_client_secret,
                username=settings.reddit_username,
                password=settings.reddit_password,
                user_agent=settings.reddit_user_agent,
            )
            db = session_factory()
            try:
                if has_feature(db, settings.tenant_id, "contributor_management"):
                    for sub_name in settings.subreddit_names:
                        run_contributor_promotion_batch(reddit, db, sub_name, settings)
                        run_contributor_demotion_batch(reddit, db, sub_name, settings)
            finally:
                db.close()
        except Exception as exc:
            _alert(settings, f"contributor_batches job failed: {exc}")

    scheduler.add_job(
        _job,
        "cron",
        id="contributor_batches",
        day_of_week="sun",
        hour=3,
        minute=0,
        replace_existing=True,
    )


def _register_user_flair_batch(scheduler, settings, session_factory) -> None:
    def _job() -> None:
        try:
            import praw

            from app.billing.features import has_feature
            from app.subreddit.flair_engine import run_user_flair_batch

            reddit = praw.Reddit(
                client_id=settings.reddit_client_id,
                client_secret=settings.reddit_client_secret,
                username=settings.reddit_username,
                password=settings.reddit_password,
                user_agent=settings.reddit_user_agent,
            )
            db = session_factory()
            try:
                if has_feature(db, settings.tenant_id, "flair_automation"):
                    for sub_name in settings.subreddit_names:
                        run_user_flair_batch(reddit, sub_name, db, settings)
            finally:
                db.close()
        except Exception as exc:
            _alert(settings, f"user_flair_batch job failed: {exc}")

    scheduler.add_job(
        _job,
        "cron",
        id="user_flair_batch",
        hour=2,
        minute=0,
        replace_existing=True,
    )


def _register_sentiment_alert(scheduler, settings, session_factory) -> None:
    def _job() -> None:
        try:
            from app.billing.features import has_feature
            from app.moderation.sentiment import check_sentiment_alert

            db = session_factory()
            try:
                if has_feature(db, settings.tenant_id, "sentiment_analysis"):
                    for sub_name in settings.subreddit_names:
                        if check_sentiment_alert(db, sub_name):
                            _alert(
                                settings,
                                f"⚠️ Negative sentiment alert for r/{sub_name}",
                            )
            finally:
                db.close()
        except Exception as exc:
            _alert(settings, f"sentiment_alert job failed: {exc}")

    scheduler.add_job(
        _job,
        "interval",
        id="sentiment_alert",
        hours=1,
        replace_existing=True,
    )


# ── Legacy helper kept for backward compatibility ─────────────────────────────


def schedule_weekly_trending_post(
    scheduler: BackgroundScheduler,
    topic_provider: Callable[[], list],
    publish_callback: Callable[[dict], None],
    day_of_week: str = "mon",
    hour_utc: int = 14,
) -> None:
    """Legacy single-job registration — prefer ``register_all_jobs``."""
    from app.posting.trending import build_trending_thread

    def _job() -> None:
        trends = topic_provider()
        payload = build_trending_thread(trends)
        publish_callback(payload)

    scheduler.add_job(
        _job,
        "cron",
        id="weekly_trending_post",
        day_of_week=day_of_week,
        hour=hour_utc,
        minute=0,
        replace_existing=True,
    )


# ── Internal alert helper ─────────────────────────────────────────────────────


def _alert(settings: Any, message: str) -> None:
    """Best-effort alert to all configured notification channels."""
    log.error("Scheduler job error: %s", message)
    try:
        from app.utils.notify import send_alert_sync

        send_alert_sync(message, settings)
    except Exception:
        pass
