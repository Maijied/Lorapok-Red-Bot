"""Engagement predictor — predict viral posts and auto-pin high-potential content."""

from __future__ import annotations

import logging
import statistics
from dataclasses import dataclass
from typing import Any

from sqlalchemy.orm import Session

log = logging.getLogger(__name__)


@dataclass
class EngagementPrediction:
    score: float           # 0.0 – 1.0
    predicted_upvotes: int
    confidence: float      # 0.0 – 0.9


def predict_engagement(
    submission: Any,
    historical_data: list[dict[str, Any]],
) -> EngagementPrediction:
    """Predict engagement for *submission* based on velocity and historical data.

    Pure function — no I/O, no side effects.
    """
    import time

    created_utc = getattr(submission, "created_utc", time.time())
    age_minutes = max(1, (time.time() - created_utc) / 60)
    score = max(0, getattr(submission, "score", 0))
    upvote_velocity = score / age_minutes

    if not historical_data:
        predicted_upvotes = max(0, round(upvote_velocity * 60 * 24))
        confidence = 0.3
        engagement_score = min(1.0, upvote_velocity / max(1.0, upvote_velocity + 1))
    else:
        avg_final = statistics.mean(
            h.get("final_upvotes", h.get("score", 0)) for h in historical_data
        )
        hist_velocities = [
            h.get("upvote_velocity", 0.01) for h in historical_data
        ]
        avg_velocity = statistics.mean(hist_velocities) if hist_velocities else 0.01
        velocity_ratio = upvote_velocity / max(0.001, avg_velocity)
        predicted_upvotes = max(0, round(avg_final * velocity_ratio))
        confidence = min(0.9, 0.3 + len(historical_data) * 0.01)
        engagement_score = min(1.0, predicted_upvotes / max(1, avg_final))

    return EngagementPrediction(
        score=max(0.0, min(1.0, engagement_score)),
        predicted_upvotes=predicted_upvotes,
        confidence=confidence,
    )


def get_rising_submissions(reddit: Any, subreddit_name: str, limit: int = 25) -> list[Any]:
    """Fetch rising submissions from a subreddit."""
    try:
        return list(reddit.subreddit(subreddit_name).rising(limit=limit))
    except Exception as exc:
        log.error("Could not fetch rising submissions for r/%s: %s", subreddit_name, exc)
        return []


def auto_pin_high_potential(
    reddit: Any,
    db: Session,
    subreddit_name: str,
    settings: Any,
    score_threshold: float = 0.8,
) -> int:
    """Pin submissions with predicted engagement score above *score_threshold*."""
    dry_run = getattr(settings, "dry_run", True)
    submissions = get_rising_submissions(reddit, subreddit_name)
    pinned = 0

    for submission in submissions:
        prediction = predict_engagement(submission, [])
        if prediction.score >= score_threshold:
            if dry_run:
                log.info(
                    "DRY_RUN auto-pin submission %s (score=%.2f)",
                    getattr(submission, "id", "?"),
                    prediction.score,
                )
            else:
                try:
                    submission.mod.sticky(state=True)
                    log.info("Auto-pinned submission %s", getattr(submission, "id", "?"))
                except Exception as exc:
                    log.warning("Could not pin submission: %s", exc)
                    continue
            pinned += 1

    return pinned
