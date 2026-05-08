from app.moderation.rules import apply_light_rules


def test_spam_term_is_removed() -> None:
    decision = apply_light_rules("Buy now and get free money today.")
    assert decision.action == "remove"
    assert decision.confidence >= 0.9


def test_non_spam_is_allowed() -> None:
    decision = apply_light_rules("I need help debugging my Python API client.")
    assert decision.action == "allow"
