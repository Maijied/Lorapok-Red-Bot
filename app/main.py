import logging
import time
from typing import Any

from sqlalchemy.orm import Session

from app.config import Settings
from app.dashboard.metrics import metrics_store
from app.dashboard.models import DailyMetric, GithubUpdateTracker, PendingPost  # noqa
from app.database import get_engine, get_session_factory, init_db
from app.integrations.discord_integration import send_discord_alert
from app.integrations.github_integration import fetch_trending_repos
from app.integrations.github_worker import monitor_repositories
from app.moderation.classifier import classify_text
from app.moderation.memory import remember_case
from app.moderation.queue import queue_case
from app.moderation.rules import ModerationDecision, apply_light_rules
from app.posting.scheduler import create_scheduler, schedule_weekly_trending_post
from app.reddit_client import get_reddit
from app.utils.logging import setup_logging
from app.utils.rate_limit import RateLimiter

logger = logging.getLogger(__name__)


def _should_offer_help(text: str) -> bool:
    lowered = text.lower()
    return "help" in lowered or "error" in lowered or "bug" in lowered


def _to_decision(payload: dict[str, Any]) -> ModerationDecision:
    action = str(payload.get("action", "review")).lower().strip()
    reason = str(payload.get("reason", "No reason provided.")).strip()
    try:
        confidence = float(payload.get("confidence", 0.0))
    except (TypeError, ValueError):
        confidence = 0.0
    confidence = max(0.0, min(1.0, confidence))
    if action not in {"allow", "review", "remove"}:
        action = "review"
    return ModerationDecision(action=action, reason=reason, confidence=confidence)


def _apply_decision(
    db: Session, comment: Any, decision: ModerationDecision, settings: Settings
) -> None:
    remember_case(db, comment.body, decision.action, decision.reason, "rules+ai")

    if decision.action == "remove":
        if settings.dry_run:
            logger.info(
                "DRY_RUN remove for comment %s reason=%s confidence=%.2f",
                comment.id,
                decision.reason,
                decision.confidence,
            )
        else:
            comment.mod.remove()
            comment.reply(
                "Your comment was removed by Lorapok Red Bot because it appears to violate "
                "community rules. If you think this was a mistake, please contact moderators."
            )
        metrics_store.increment("actions_taken")
    elif decision.action == "allow" and _should_offer_help(comment.body):
        message = (
            "Hi! Please include the code, error message, and what you expected. "
            "That helps the community provide faster and better answers."
        )
        if settings.dry_run:
            logger.info("DRY_RUN reply for comment %s", comment.id)
        else:
            comment.reply(message)

    metrics_store.increment("comments_processed")


def process_comment(db: Session, comment: Any, settings: Settings) -> None:
    rule_decision = apply_light_rules(comment.body)

    if (
        rule_decision.action == "review"
        or rule_decision.confidence < settings.review_confidence_threshold
    ):
        ai_decision = _to_decision(classify_text(comment.body))
        if (
            ai_decision.action == "review"
            or ai_decision.confidence < settings.review_confidence_threshold
        ):
            rec = ai_decision.action if ai_decision.action != "review" else rule_decision.action
            queue_case(
                db,
                comment.body,
                ai_decision.reason,
                source="rules+ai",
                recommended_action=rec,
            )
            metrics_store.increment("queued_reviews")
            logger.info("Queued comment %s for human review", comment.id)
            return
        _apply_decision(db, comment, ai_decision, settings)
        return

    _apply_decision(db, comment, rule_decision, settings)


def main() -> None:
    settings = Settings.from_env()
    setup_logging(settings.log_level)
    logger.info(
        "Starting Lorapok Red Bot subreddit=%s dry_run=%s",
        settings.subreddit_name,
        settings.dry_run,
    )

    # Initialize DB
    init_db(settings)
    engine = get_engine(settings)
    SessionLocal = get_session_factory(engine)

    reddit = get_reddit(settings)
    subreddit = reddit.subreddit(settings.subreddit_name)

    # Initialize and start the scheduler
    scheduler = create_scheduler()
    
    # Task 5.3: Weekly Trending Post
    schedule_weekly_trending_post(
        scheduler,
        topic_provider=lambda: fetch_trending_repos(language="python"),
        publish_callback=lambda p: logger.info(
            "Weekly post published: %s\nBody: %s", p["title"], p["body"]
        ),
    )
    
    # Task 7.1: Metric Flushing
    def _flush_metrics():
        db = SessionLocal()
        try:
            metrics_store.flush_to_db(db)
        finally:
            db.close()
    
    # Task 8.1: GitHub Repository Monitoring
    def _monitor_github():
        db = SessionLocal()
        try:
            monitor_repositories(db, settings.monitored_repos)
        finally:
            db.close()

    scheduler.add_job(_flush_metrics, "interval", minutes=5, id="flush_metrics")
    scheduler.add_job(_monitor_github, "interval", hours=1, id="monitor_github")
    
    scheduler.start()
    logger.info("Background scheduler started.")

    send_discord_alert(f"Lorapok Red Bot started in r/{settings.subreddit_name}.")

    limiter = RateLimiter(min_interval_seconds=2.0)
    try:
        for comment in subreddit.stream.comments(skip_existing=True):
            db = SessionLocal()
            try:
                process_comment(db, comment, settings)
                limiter.wait()
            except Exception as exc:
                logger.exception("Error while processing comment: %s", exc)
                send_discord_alert(f"Lorapok Red Bot error: {exc}")
                time.sleep(5)
            finally:
                db.close()
    except KeyboardInterrupt:
        logger.info("Bot shutting down...")
    finally:
        scheduler.shutdown()


if __name__ == "__main__":
    main()
