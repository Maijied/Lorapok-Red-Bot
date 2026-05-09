"""Integration tests for the full moderation pipeline."""

import pytest

from app.moderation.memory import recent_cases
from app.moderation.rules import apply_light_rules


def _make_settings(**kwargs):
    from app.config import Settings

    defaults = dict(
        reddit_client_id="", reddit_client_secret="", reddit_username="",
        reddit_password="", reddit_user_agent="test",
        ai_model="openai/gpt-4o-mini", openai_api_key="",
        anthropic_api_key="", gemini_api_key="", mistral_api_key="",
        database_url="sqlite:///:memory:", redis_url="",
        discord_webhook_url="", slack_webhook_url="",
        telegram_bot_token="", telegram_chat_id="",
        github_token="", monitored_repos=[],
        stripe_secret_key="", stripe_webhook_secret="",
        stripe_price_starter_monthly="", stripe_price_pro_monthly="",
        stripe_price_agency_monthly="", stripe_price_starter_annual="",
        stripe_price_pro_annual="", stripe_price_agency_annual="",
        subreddit_name="python", subreddit_names=["python"],
        dry_run=True, log_level="INFO",
        review_confidence_threshold=0.75,
        tenant_id="default", white_label_name=None, white_label_logo_url=None,
    )
    defaults.update(kwargs)
    return Settings(**defaults)


class FakeComment:
    def __init__(self, body, id="c1", subreddit_name_prefixed="r/python"):
        self.body = body
        self.id = id
        self.subreddit_name_prefixed = subreddit_name_prefixed

    def mod(self):
        pass

    def reply(self, text):
        pass


def test_spam_rule_flags_correctly():
    """Rule engine correctly flags spam — no litellm needed."""
    decision = apply_light_rules("Buy now and get free money — visit my site!")
    assert decision.action == "remove"


def test_help_comment_allowed():
    """Rule engine allows normal help questions."""
    decision = apply_light_rules("How do I fix this error in my Python code?")
    assert decision.action == "allow"


def test_process_comment_records_decision(db):
    pytest.importorskip("litellm")
    from app.main import process_comment

    settings = _make_settings()
    comment = FakeComment("Normal developer question about Python")
    process_comment(db, comment, settings)

    cases = recent_cases(db, limit=10, tenant_id="default")
    assert len(cases) >= 1


def test_dry_run_does_not_call_reddit_api(db):
    """In dry_run mode, no Reddit API calls should be made."""
    pytest.importorskip("litellm")
    from app.main import process_comment

    settings = _make_settings(dry_run=True)
    api_called = []

    class FakeCommentWithSpy:
        body = "free money buy now crypto pump"
        id = "spy1"
        subreddit_name_prefixed = "r/python"

        class mod:
            @staticmethod
            def remove():
                api_called.append("remove")

        def reply(self, text):
            api_called.append("reply")

    process_comment(db, FakeCommentWithSpy(), settings)
    assert "remove" not in api_called
    assert "reply" not in api_called
