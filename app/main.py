import logging
import time
from typing import Any

from app.config import Settings
from app.dashboard.metrics import metrics_store
from app.integrations.discord_integration import send_discord_alert
from app.moderation.classifier import classify_text
from app.moderation.memory import remember_case
from app.moderation.queue import queue_case
from app.moderation.rules import ModerationDecision, apply_light_rules
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


def _apply_decision(comment: Any, decision: ModerationDecision, settings: Settings) -> None:
    remember_case(comment.body, decision.action, decision.reason, "rules+ai")

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


def process_comment(comment: Any, settings: Settings) -> None:
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
            queue_case(comment.body, ai_decision.reason, source="rules+ai")
            metrics_store.increment("queued_reviews")
            logger.info("Queued comment %s for human review", comment.id)
            return
        _apply_decision(comment, ai_decision, settings)
        return

    _apply_decision(comment, rule_decision, settings)


def main() -> None:
    settings = Settings.from_env()
    setup_logging(settings.log_level)
    logger.info(
        "Starting Lorapok Red Bot subreddit=%s dry_run=%s",
        settings.subreddit_name,
        settings.dry_run,
    )

    reddit = get_reddit(settings)
    subreddit = reddit.subreddit(settings.subreddit_name)
    send_discord_alert(f"Lorapok Red Bot started in r/{settings.subreddit_name}.")

    limiter = RateLimiter(min_interval_seconds=2.0)
    for comment in subreddit.stream.comments(skip_existing=True):
        try:
            process_comment(comment, settings)
            limiter.wait()
        except KeyboardInterrupt:
            raise
        except Exception as exc:
            logger.exception("Error while processing comment: %s", exc)
            send_discord_alert(f"Lorapok Red Bot error: {exc}")
            time.sleep(5)


if __name__ == "__main__":
    main()
