import json
import logging
import os
from typing import Any

import litellm

logger = logging.getLogger(__name__)

# Configure LiteLLM to use environment variables for keys
# It will look for OPENAI_API_KEY, ANTHROPIC_API_KEY, etc. automatically.

def _normalize_confidence(value: Any) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return 0.0
    return max(0.0, min(1.0, parsed))


def classify_text(text: str, model: str | None = None) -> dict[str, Any]:
    ai_model = model or os.getenv("AI_MODEL", "openai/gpt-4o-mini")
    
    prompt = f"""
You are a Reddit moderation assistant for developer communities.
Return strict JSON with keys: action, reason, confidence.
Allowed actions: allow, review, remove.
Content: {text}
"""

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
        return {
            "action": action,
            "reason": str(parsed.get("reason", "No reason provided.")).strip(),
            "confidence": _normalize_confidence(parsed.get("confidence", 0.0)),
        }
    except Exception as exc:
        logger.error(f"Multi-AI Classifier error ({ai_model}): {exc}")
        return {
            "action": "review",
            "reason": f"Classifier failure: {exc}",
            "confidence": 0.0,
        }


def summarize_text(text: str, max_words: int = 100, model: str | None = None) -> str:
    """Generate a concise summary of the provided text using any AI provider."""
    ai_model = model or os.getenv("AI_MODEL", "openai/gpt-4o-mini")
    if not text.strip():
        return ""

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
        logger.error(f"Multi-AI Summary error ({ai_model}): {exc}")
        return text[:500] + "..."
