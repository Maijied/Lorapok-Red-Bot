"""Sentiment analysis — track community mood and alert on negative trends."""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.dashboard.models import SentimentDataPoint

log = logging.getLogger(__name__)


@dataclass
class SentimentResult:
    score: float   # -1.0 (negative) to 1.0 (positive)
    label: str     # "positive" | "neutral" | "negative"

    def __post_init__(self) -> None:
        self.score = max(-1.0, min(1.0, self.score))
        if self.label not in {"positive", "neutral", "negative"}:
            self.label = "neutral"


def analyze_sentiment(text: str, model: str | None = None) -> SentimentResult:
    """Analyse sentiment of *text* via LiteLLM.  Never raises."""
    if not text or not text.strip():
        return SentimentResult(score=0.0, label="neutral")

    ai_model = model or os.getenv("AI_MODEL", "openai/gpt-4o-mini")
    prompt = (
        "Analyse the sentiment of the following Reddit comment.\n"
        "Return strict JSON with keys: score (float -1.0 to 1.0), "
        "label (positive/neutral/negative).\n"
        f"Comment: {text[:500]}"
    )

    try:
        import litellm

        response = litellm.completion(
            model=ai_model,
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
        )
        raw = response.choices[0].message.content
        parsed = json.loads(raw)
        score = max(-1.0, min(1.0, float(parsed.get("score", 0.0))))
        label = str(parsed.get("label", "neutral")).lower()
        if label not in {"positive", "neutral", "negative"}:
            label = "neutral"
        return SentimentResult(score=score, label=label)
    except Exception as exc:
        log.debug("Sentiment analysis failed: %s", exc)
        return SentimentResult(score=0.0, label="neutral")


def record_sentiment(
    db: Session,
    subreddit_name: str,
    score: float,
    source: str,
    tenant_id: str = "default",
) -> None:
    label = "positive" if score > 0.1 else ("negative" if score < -0.1 else "neutral")
    record = SentimentDataPoint(
        tenant_id=tenant_id,
        subreddit_name=subreddit_name,
        score=score,
        label=label,
        source=source,
        recorded_at=datetime.now(timezone.utc),
    )
    db.add(record)
    db.commit()


def get_sentiment_trend(
    db: Session,
    subreddit_name: str,
    tenant_id: str = "default",
    days: int = 7,
) -> list[dict[str, Any]]:
    since = datetime.now(timezone.utc) - timedelta(days=days)
    records = (
        db.query(SentimentDataPoint)
        .filter(
            SentimentDataPoint.tenant_id == tenant_id,
            SentimentDataPoint.subreddit_name == subreddit_name,
            SentimentDataPoint.recorded_at >= since,
        )
        .order_by(SentimentDataPoint.recorded_at.asc())
        .all()
    )
    return [
        {
            "score": r.score,
            "label": r.label,
            "source": r.source,
            "recorded_at": r.recorded_at.isoformat() if r.recorded_at else None,
        }
        for r in records
    ]


def check_sentiment_alert(
    db: Session,
    subreddit_name: str,
    tenant_id: str = "default",
    threshold: float = -0.3,
) -> bool:
    """Return True if the 3-day rolling average sentiment is below *threshold*."""
    since = datetime.now(timezone.utc) - timedelta(days=3)
    records = (
        db.query(SentimentDataPoint)
        .filter(
            SentimentDataPoint.tenant_id == tenant_id,
            SentimentDataPoint.subreddit_name == subreddit_name,
            SentimentDataPoint.recorded_at >= since,
        )
        .all()
    )
    if not records:
        return False
    avg = sum(r.score for r in records) / len(records)
    return avg < threshold
