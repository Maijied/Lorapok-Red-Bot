"""Tests for cross-subreddit spam detector."""

from app.moderation.spam_detector import detect_cross_sub_spam, record_submission


def test_no_signal_below_threshold(db):
    record_submission(db, "spammer", "python", "abc123", "http://x.com/1")
    record_submission(db, "spammer", "learnpython", "abc123", "http://x.com/2")
    signal = detect_cross_sub_spam(db, "spammer", "abc123")
    assert signal is None  # only 2 subreddits, need 3


def test_signal_at_threshold(db):
    record_submission(db, "spammer2", "python", "xyz789", "http://x.com/1")
    record_submission(db, "spammer2", "learnpython", "xyz789", "http://x.com/2")
    record_submission(db, "spammer2", "programming", "xyz789", "http://x.com/3")
    signal = detect_cross_sub_spam(db, "spammer2", "xyz789")
    assert signal is not None
    assert len(signal.subreddits) == 3
    assert signal.score > 0


def test_score_increases_with_subreddits(db):
    for i in range(8):
        record_submission(db, "bigspammer", f"sub{i}", "hash999", f"http://x.com/{i}")
    signal = detect_cross_sub_spam(db, "bigspammer", "hash999")
    assert signal is not None
    assert signal.score > 0.3


def test_score_capped_at_one(db):
    for i in range(20):
        record_submission(db, "megaspammer", f"sub{i}", "hashmax", f"http://x.com/{i}")
    signal = detect_cross_sub_spam(db, "megaspammer", "hashmax")
    assert signal is not None
    assert signal.score <= 1.0
