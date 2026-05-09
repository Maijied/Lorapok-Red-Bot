"""Tests for subreddit health score."""

from app.analytics.health_score import SubredditHealthScore, compute_health_score


def test_components_sum_to_total(db):
    score = compute_health_score(db, "python", tenant_id="default")
    assert abs(
        score.total - (score.growth + score.engagement + score.moderation + score.spam)
    ) < 0.001


def test_components_in_range(db):
    score = compute_health_score(db, "python", tenant_id="default")
    for component in [score.growth, score.engagement, score.moderation, score.spam]:
        assert 0.0 <= component <= 25.0


def test_total_in_range(db):
    score = compute_health_score(db, "python", tenant_id="default")
    assert 0.0 <= score.total <= 100.0


def test_dataclass_clamps():
    score = SubredditHealthScore(total=0, growth=30, engagement=30, moderation=30, spam=30)
    assert score.growth == 25.0
    assert score.engagement == 25.0
