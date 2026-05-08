import json
import os
from typing import Any

from openai import OpenAI


def _normalize_confidence(value: Any) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return 0.0
    return max(0.0, min(1.0, parsed))


def classify_text(text: str, model: str = "gpt-4.1-mini") -> dict[str, Any]:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return {
            "action": "review",
            "reason": "OPENAI_API_KEY is not configured.",
            "confidence": 0.0,
        }

    prompt = f"""
You are a Reddit moderation assistant for developer communities.
Return strict JSON with keys: action, reason, confidence.
Allowed actions: allow, review, remove.
Content: {text}
"""

    client = OpenAI(api_key=api_key)
    try:
        response = client.responses.create(model=model, input=prompt)
        raw = response.output_text.strip()
        parsed = json.loads(raw)
        action = str(parsed.get("action", "review")).lower().strip()
        if action not in {"allow", "review", "remove"}:
            action = "review"
        return {
            "action": action,
            "reason": str(parsed.get("reason", "No reason provided.")).strip(),
            "confidence": _normalize_confidence(parsed.get("confidence", 0.0)),
        }
    except json.JSONDecodeError:
        return {
            "action": "review",
            "reason": "Model output was not valid JSON.",
            "confidence": 0.0,
        }
    except Exception as exc:
        return {
            "action": "review",
            "reason": f"Classifier failure: {exc}",
            "confidence": 0.0,
        }
