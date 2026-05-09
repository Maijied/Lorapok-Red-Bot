"""Deterministic, zero-latency first-pass moderation rule engine.

Rules are loaded from ``app/moderation/rules.yaml`` at import time so they can
be updated without changing Python code.  The ``apply_light_rules`` function is
a pure function — same input always produces the same output, no I/O.
"""

from __future__ import annotations

import logging
import os
import re
from dataclasses import dataclass
from functools import lru_cache
from typing import Any

log = logging.getLogger(__name__)

_RULES_YAML_PATH = os.path.join(os.path.dirname(__file__), "rules.yaml")

# ── Rule config loading ───────────────────────────────────────────────────────


@lru_cache(maxsize=1)
def _load_rules() -> dict[str, Any]:
    """Load rules.yaml once and cache the result."""
    try:
        import yaml  # type: ignore[import]

        with open(_RULES_YAML_PATH, encoding="utf-8") as fh:
            return yaml.safe_load(fh) or {}
    except Exception as exc:
        log.warning("Could not load rules.yaml (%s); using built-in defaults.", exc)
        return {}


def _get_hard_spam_terms() -> list[str]:
    rules = _load_rules()
    return rules.get(
        "hard_spam_terms",
        ["free money", "buy now", "crypto pump", "visit my site"],
    )


def _get_ambiguous_terms() -> list[str]:
    rules = _load_rules()
    return rules.get("ambiguous_terms", [])


def _get_regex_rules() -> list[dict[str, Any]]:
    rules = _load_rules()
    return rules.get("regex_rules", [])


# ── Decision dataclass ────────────────────────────────────────────────────────


@dataclass
class ModerationDecision:
    action: str  # "allow" | "review" | "remove"
    reason: str
    confidence: float  # 0.0 – 1.0

    def __post_init__(self) -> None:
        if self.action not in {"allow", "review", "remove"}:
            self.action = "review"
        self.confidence = max(0.0, min(1.0, self.confidence))
        self.reason = (self.reason or "No reason provided.").strip()


# ── Core rule function ────────────────────────────────────────────────────────


def apply_light_rules(text: str) -> ModerationDecision:
    """Apply deterministic keyword and regex rules to *text*.

    Returns a :class:`ModerationDecision`.  This function is pure — it performs
    no I/O and has no side effects.

    Precedence:
    1. Hard-spam keyword match → ``remove`` (confidence 0.95)
    2. Regex rule match        → action from rule config
    3. Ambiguous keyword match → ``review`` (confidence 0.55)
    4. Default pass-through    → ``allow`` (confidence 0.70)
    """
    if not isinstance(text, str):
        text = str(text)

    lowered = text.lower()

    # 1. Hard-spam keywords
    for term in _get_hard_spam_terms():
        if term.lower() in lowered:
            return ModerationDecision(
                action="remove",
                reason="Possible spam or promotion pattern detected.",
                confidence=0.95,
            )

    # 2. Regex rules
    for rule in _get_regex_rules():
        pattern = rule.get("pattern", "")
        if not pattern:
            continue
        try:
            if re.search(pattern, text):
                return ModerationDecision(
                    action=rule.get("action", "review"),
                    reason=rule.get("reason", "Regex rule matched."),
                    confidence=float(rule.get("confidence", 0.70)),
                )
        except re.error:
            log.warning("Invalid regex pattern in rules.yaml: %r", pattern)

    # 3. Ambiguous keywords
    for term in _get_ambiguous_terms():
        if term.lower() in lowered:
            return ModerationDecision(
                action="review",
                reason="Potential policy violation — needs moderator review.",
                confidence=0.55,
            )

    # 4. Default
    return ModerationDecision(
        action="allow",
        reason="No obvious issue found.",
        confidence=0.70,
    )
