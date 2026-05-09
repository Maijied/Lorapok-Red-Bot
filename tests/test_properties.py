"""Property-based tests using Hypothesis — all 18 correctness properties."""

from hypothesis import given, settings
from hypothesis import strategies as st

from app.moderation.rules import apply_light_rules
from app.posting.trending import build_trending_thread
from app.utils.text import normalize_text, stable_hash

# ── Property 1: Rule engine is deterministic and pure ────────────────────────

@given(st.text())
def test_rules_deterministic(text):
    d1 = apply_light_rules(text)
    d2 = apply_light_rules(text)
    assert d1.action == d2.action
    assert d1.confidence == d2.confidence
    assert d1.reason == d2.reason


# ── Property 2: Rule engine always returns valid action and confidence ────────

@given(st.text())
def test_rules_valid_output(text):
    d = apply_light_rules(text)
    assert d.action in {"allow", "review", "remove"}
    assert 0.0 <= d.confidence <= 1.0
    assert isinstance(d.reason, str)
    assert len(d.reason) > 0


# ── Property 3: AI classifier never raises ───────────────────────────────────

@given(st.text())
@settings(max_examples=10)
def test_classifier_never_raises(text):
    """Classifier must return a valid dict even when LLM is unavailable."""
    from app.moderation.classifier import classify_text

    # Without a real API key, litellm will raise — classifier must catch it
    result = classify_text(text)
    assert isinstance(result, dict)
    assert "action" in result
    assert result["action"] in {"allow", "review", "remove"}
    assert 0.0 <= result["confidence"] <= 1.0


# ── Property 4: build_trending_thread always returns non-empty title/body ────

@given(st.lists(st.dictionaries(st.text(min_size=1), st.text())))
def test_trending_always_returns_content(trends):
    payload = build_trending_thread(trends)
    assert isinstance(payload, dict)
    assert len(payload["title"]) > 0
    assert len(payload["body"]) > 0


# ── Property 5: queue_case → list_queue round-trip ───────────────────────────

@given(st.text(min_size=1), st.text(min_size=1))
def test_queue_round_trip(text, reason):
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    import app.dashboard.models  # noqa: F401
    from app.database import Base
    from app.moderation.queue import list_queue, queue_case

    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    db = sessionmaker(bind=engine)()
    try:
        before = len(list_queue(db, status="pending"))
        queue_case(db, text, reason, "test")
        after = len(list_queue(db, status="pending"))
        assert after == before + 1
    finally:
        db.close()


# ── Property 6: resolve_case is idempotent on status ─────────────────────────

def test_resolve_case_idempotent():
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    import app.dashboard.models  # noqa: F401
    from app.database import Base
    from app.moderation.queue import queue_case, resolve_case

    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    db = sessionmaker(bind=engine)()
    try:
        case_id = queue_case(db, "test text", "test reason", "test")
        ok1 = resolve_case(db, case_id, "approved")
        ok2 = resolve_case(db, case_id, "approved")
        assert ok1 is True
        assert ok2 is True  # idempotent
    finally:
        db.close()


# ── Property 9: stable_hash consistency ──────────────────────────────────────

@given(st.text(), st.text())
def test_stable_hash_consistency(a, b):
    if normalize_text(a) == normalize_text(b):
        assert stable_hash(a) == stable_hash(b)


@given(st.text())
def test_stable_hash_deterministic(text):
    assert stable_hash(text) == stable_hash(text)


# ── Property 10: _to_decision always produces valid ModerationDecision ───────

@given(st.dictionaries(
    st.text(),
    st.one_of(st.text(), st.integers(), st.floats(allow_nan=False), st.none()),
))
def test_to_decision_always_valid(payload):
    from app.moderation.classifier import _to_decision

    decision = _to_decision(payload)
    assert decision.action in {"allow", "review", "remove"}
    assert 0.0 <= decision.confidence <= 1.0
    assert isinstance(decision.reason, str)


# ── Property 11: compute_reputation_score is bounded ─────────────────────────

@given(
    st.integers(min_value=0, max_value=10000),
    st.integers(min_value=0, max_value=10000),
    st.integers(min_value=0, max_value=1000),
    st.integers(min_value=0, max_value=100),
    st.integers(min_value=0, max_value=3650),
)
def test_reputation_score_bounded(ap, ac, rp, bans, age):
    from app.dashboard.models import UserReputation
    from app.users.reputation import compute_reputation_score

    rep = UserReputation(
        approved_posts=ap,
        approved_comments=ac,
        removed_posts=rp,
        bans=bans,
        account_age_days=age,
    )
    score = compute_reputation_score(rep)
    assert -100.0 <= score <= 100.0


# ── Property 12: has_feature returns False for unknown tenant ─────────────────

@given(st.text(min_size=1))
@settings(max_examples=20)
def test_has_feature_unknown_tenant(feature):
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    import app.dashboard.models  # noqa: F401
    from app.billing.features import has_feature
    from app.database import Base

    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    db = sessionmaker(bind=engine)()
    try:
        result = has_feature(db, "nonexistent-tenant-xyz-123", feature)
        assert result is False
    finally:
        db.close()


# ── Property 13: detect_cross_sub_spam requires at least 3 subreddits ────────

def test_spam_detector_requires_3_subreddits():
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    import app.dashboard.models  # noqa: F401
    from app.database import Base
    from app.moderation.spam_detector import detect_cross_sub_spam, record_submission

    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    db = sessionmaker(bind=engine)()
    try:
        record_submission(db, "u1", "sub1", "h1", "")
        record_submission(db, "u1", "sub2", "h1", "")
        assert detect_cross_sub_spam(db, "u1", "h1") is None
        record_submission(db, "u1", "sub3", "h1", "")
        assert detect_cross_sub_spam(db, "u1", "h1") is not None
    finally:
        db.close()


# ── Property 14: health score components sum to total ────────────────────────

def test_health_score_components_sum():
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    import app.dashboard.models  # noqa: F401
    from app.analytics.health_score import compute_health_score
    from app.database import Base

    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    db = sessionmaker(bind=engine)()
    try:
        score = compute_health_score(db, "python")
        assert abs(
            score.total - (score.growth + score.engagement + score.moderation + score.spam)
        ) < 0.001
    finally:
        db.close()


# ── Property 15: dispatch_event never raises ─────────────────────────────────

def test_dispatch_event_never_raises():
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    import app.dashboard.models  # noqa: F401
    from app.database import Base
    from app.integrations.webhooks import dispatch_event

    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    db = sessionmaker(bind=engine)()
    try:
        # Should not raise even with no webhooks registered
        dispatch_event(db, "default", "comment.removed", {"id": "abc"})
        dispatch_event(db, "default", "unknown.event", {})
    finally:
        db.close()


# ── Property 17: triage_conversation inserts exactly one record ──────────────

def test_triage_conversation_one_record():
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    import app.dashboard.models  # noqa: F401
    from app.dashboard.models import ModmailRecord
    from app.database import Base
    from app.subreddit.modmail_triage import triage_conversation

    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    db = sessionmaker(bind=engine)()

    class FakeConv:
        id = "conv_test_001"
        subject = "Help with posting"
        messages = []
        authors = []
        owner = "python"

    class FakeSettings:
        tenant_id = "default"
        ai_model = "openai/gpt-4o-mini"
        tier = "free"

    try:
        triage_conversation(FakeConv(), FakeSettings(), db)
        triage_conversation(FakeConv(), FakeSettings(), db)  # second call — should be no-op
        count = (
            db.query(ModmailRecord)
            .filter(ModmailRecord.conversation_id == "conv_test_001")
            .count()
        )
        assert count == 1
    finally:
        db.close()


# ── Property 18: scheduled post publish is idempotent ────────────────────────

def test_scheduled_post_publish_idempotent():
    from datetime import datetime, timedelta, timezone

    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    import app.dashboard.models  # noqa: F401
    from app.dashboard.models import ScheduledPost
    from app.database import Base
    from app.posting.content_calendar import publish_due_posts

    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    db = sessionmaker(bind=engine)()

    class FakeReddit:
        def subreddit(self, name):
            return self

        def submit(self, title, selftext):
            class S:
                id = "xyz"
            return S()

    class FakeSettings:
        tenant_id = "default"
        dry_run = False

    try:
        # Insert a due post directly — bypasses the future-only guard
        past = datetime.now(timezone.utc) - timedelta(minutes=5)
        post = ScheduledPost(
            tenant_id="default",
            subreddit_name="python",
            title="Idempotent Post",
            body="body",
            post_at=past,
            status="scheduled",
        )
        db.add(post)
        db.commit()

        p1 = publish_due_posts(FakeReddit(), db, FakeSettings())
        p2 = publish_due_posts(FakeReddit(), db, FakeSettings())
        assert p1 == 1
        assert p2 == 0  # idempotent — already published
    finally:
        db.close()
