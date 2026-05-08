from dataclasses import dataclass


@dataclass
class ModerationDecision:
    action: str
    reason: str
    confidence: float


def apply_light_rules(text: str) -> ModerationDecision:
    lowered = text.lower()

    hard_spam_terms = [
        "free money",
        "buy now",
        "crypto pump",
        "visit my site",
        "dm for signal",
    ]
    if any(term in lowered for term in hard_spam_terms):
        return ModerationDecision(
            action="remove",
            reason="Possible spam or promotion pattern detected.",
            confidence=0.95,
        )

    ambiguous_terms = ["telegram group", "guaranteed returns", "dm me for details"]
    if any(term in lowered for term in ambiguous_terms):
        return ModerationDecision(
            action="review",
            reason="Potential policy violation needs moderator review.",
            confidence=0.55,
        )

    return ModerationDecision(
        action="allow",
        reason="No obvious issue found.",
        confidence=0.70,
    )
