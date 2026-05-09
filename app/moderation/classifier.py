"""AI-powered second-pass moderation classifier via LiteLLM.

Supports any provider configured through environment variables
(OpenAI, Anthropic, Gemini, Mistral).  Results are cached in Redis by
content hash to avoid redundant LLM calls for identical text.

This module never raises to the caller — all exceptions are caught and
converted to a safe ``{"action": "review", "confidence": 0.0}`` fallback.
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass
from typing import Any

import litellm

from app.utils.text import stable_hash

log = logging.getLogger(__name__)

_CACHE_TTL = 300  # 5 minutes


# ── Result dataclass ──────────────────────────────────────────────────────────


@dataclass
class ClassifierResult:
    action: str      # "allow" | "review" | "remove"
    reason: str
    confidence: float  # 0.0 – 1.0

    def __post_init__(self) -> None:
        if self.action not in {"allow", "review", "remove"}:
            self.action = "review"
        self.confidence = max(0.0, min(1.0, self.confidence))
        self.reason = (self.reason or "No reason provided.").strip()

    def to_dict(self) -> dict[str, Any]:
        return {
            "action": self.action,
            "reason": self.reason,
            "confidence": self.confidence,
        }


# ── Redis cache helpers ───────────────────────────────────────────────────────


def _get_redis():
    """Return a Redis client or None if Redis is unavailable."""
    try:
        import redis as redis_lib

        url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        client = redis_lib.from_url(url, decode_responses=True, socket_connect_timeout=1)
        client.ping()
        return client
    except Exception:
        return None


def _cache_get(key: str) -> dict[str, Any] | None:
    r = _get_redis()
    if r is None:
        return None
    try:
        raw = r.get(key)
        if raw:
            return json.loads(raw)
    except Exception:
        pass
    return None


def _cache_set(key: str, value: dict[str, Any]) -> None:
    r = _get_redis()
    if r is None:
        return
    try:
        r.setex(key, _CACHE_TTL, json.dumps(value))
    except Exception:
        pass


# ── Internal helpers ──────────────────────────────────────────────────────────


def _normalize_confidence(value: Any) -> float:
    try:
        return max(0.0, min(1.0, float(value)))
    except (TypeError, ValueError):
        return 0.0


def _to_decision(payload: dict[str, Any]) -> "ModerationDecision":
    """Coerce any dict (including malformed LLM output) to a ModerationDecision.

    Imported here to avoid circular imports — rules.py is the canonical home.
    """
    from app.moderation.rules import ModerationDecision

    action = str(payload.get("action", "review")).lower().strip()
    if action not in {"allow", "review", "remove"}:
        action = "review"
    reason = str(payload.get("reason", "No reason provided.")).strip() or "No reason provided."
    confidence = _normalize_confidence(payload.get("confidence", 0.0))
    return ModerationDecision(action=action, reason=reason, confidence=confidence)


# ── Public API ────────────────────────────────────────────────────────────────


def classify_text(text: str, model: str | None = None) -> dict[str, Any]:
    """Classify *text* using an LLM and return a moderation decision dict.

    Returns ``{"action": str, "reason": str, "confidence": float}``.
    Never raises — falls back to ``action="review", confidence=0.0`` on error.
    """
    ai_model = model or os.getenv("AI_MODEL", "openai/gpt-4o-mini")
    cache_key = f"classify:{stable_hash(text)}:{ai_model}"

    cached = _cache_get(cache_key)
    if cached is not None:
        return cached

    prompt = (
        "You are a Reddit moderation assistant for developer communities.\n"
        "Return strict JSON with keys: action, reason, confidence.\n"
        "Allowed actions: allow, review, remove.\n"
        f"Content: {text}"
    )

    try:
        response = litellm.completion(
            model=ai_model,
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
        )
        raw = response.choices[0].message.content
        parsed = json.loads(raw)
        action = str(parsed.get("action", "review")).lower().strip()
        if action not in {"allow", "review", "remove"}:
            action = "review"
        result = {
            "action": action,
            "reason": str(parsed.get("reason", "No reason provided.")).strip(),
            "confidence": _normalize_confidence(parsed.get("confidence", 0.0)),
        }
        _cache_set(cache_key, result)
        return result
    except Exception as exc:
        log.error("Classifier error (%s): %s", ai_model, exc)
        return {
            "action": "review",
            "reason": f"Classifier failure: {exc}",
            "confidence": 0.0,
        }


def summarize_text(text: str, max_words: int = 100, model: str | None = None) -> str:
    """Summarise *text* in under *max_words* words for a developer audience.

    Returns an empty string when *text* is blank.  Never raises.
    """
    if not text or not text.strip():
        return ""

    ai_model = model or os.getenv("AI_MODEL", "openai/gpt-4o-mini")
    prompt = (
        f"Summarize the following technical content in under {max_words} words "
        f"for a developer audience. Focus on key changes or value:\n\n{text}"
    )

    try:
        response = litellm.completion(
            model=ai_model,
            messages=[{"role": "user", "content": prompt}],
        )
        return response.choices[0].message.content.strip()
    except Exception as exc:
        log.error("Summarize error (%s): %s", ai_model, exc)
        return text[:500]
