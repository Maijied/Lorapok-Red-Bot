"""Tests for user reputation scoring."""

from app.dashboard.models import UserReputation
from app.users.reputation import (
    ReputationDelta,
    compute_reputation_score,
    get_or_create_reputation,
    update_reputation,
)


def _make_rep(**kwargs):
    defaults = dict(
        approved_posts=0, approved_comments=0,
        removed_posts=0, removed_comments=0,
        bans=0, account_age_days=1,
    )
    defaults.update(kwargs)
    rep = UserReputation(**defaults)
    return rep


def test_score_positive():
    rep = _make_rep(approved_posts=10, account_age_days=30)
    score = compute_reputation_score(rep)
    assert score > 0


def test_score_negative():
    rep = _make_rep(bans=5, account_age_days=10)
    score = compute_reputation_score(rep)
    assert score < 0


def test_score_clamped_high():
    rep = _make_rep(approved_posts=10000, account_age_days=1)
    score = compute_reputation_score(rep)
    assert score <= 100.0


def test_score_clamped_low():
    rep = _make_rep(bans=1000, account_age_days=1)
    score = compute_reputation_score(rep)
    assert score >= -100.0


def test_score_zero_age():
    rep = _make_rep(approved_posts=5, account_age_days=0)
    score = compute_reputation_score(rep)
    assert -100.0 <= score <= 100.0


def test_get_or_create(db):
    rep = get_or_create_reputation(db, "testuser", "python")
    assert rep.username == "testuser"
    rep2 = get_or_create_reputation(db, "testuser", "python")
    assert rep.id == rep2.id  # same record


def test_update_reputation(db):
    rep = update_reputation(db, "testuser", "python", ReputationDelta(approved_posts=3))
    assert rep.approved_posts == 3
    assert rep.reputation_score != 0
