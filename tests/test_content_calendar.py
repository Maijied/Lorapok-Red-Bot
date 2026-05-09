"""Tests for content calendar scheduling."""

from datetime import datetime, timedelta, timezone

import pytest

from app.posting.content_calendar import (
    cancel_scheduled_post,
    get_scheduled_posts,
    publish_due_posts,
    schedule_post,
)


def _future(minutes=60):
    return datetime.now(timezone.utc) + timedelta(minutes=minutes)


def _past(minutes=5):
    return datetime.now(timezone.utc) - timedelta(minutes=minutes)


def test_schedule_post_creates_record(db):
    schedule_post(db, "python", "Test Title", "Test body", _future())
    posts = get_scheduled_posts(db, "python")
    assert len(posts) == 1
    assert posts[0]["title"] == "Test Title"
    assert posts[0]["status"] == "scheduled"


def test_schedule_post_rejects_past(db):
    with pytest.raises(ValueError):
        schedule_post(db, "python", "Past Post", "body", _past())


def test_cancel_scheduled_post(db):
    post_id = schedule_post(db, "python", "Cancel Me", "body", _future())
    ok = cancel_scheduled_post(db, post_id)
    assert ok is True
    posts = get_scheduled_posts(db, "python")
    assert posts[0]["status"] == "cancelled"


def test_cancel_nonexistent_post(db):
    ok = cancel_scheduled_post(db, "99999")
    assert ok is False


def test_publish_due_posts_idempotent(db):
    """Publishing a due post twice should not re-publish it."""
    from datetime import datetime, timezone

    from app.dashboard.models import ScheduledPost

    # Insert a due post directly (bypassing the future-only guard)
    post = ScheduledPost(
        tenant_id="default",
        subreddit_name="python",
        title="Due Post",
        body="body",
        post_at=datetime.now(timezone.utc) - timedelta(minutes=5),
        status="scheduled",
    )
    db.add(post)
    db.commit()

    class FakeReddit:
        def subreddit(self, name):
            return self

        def submit(self, title, selftext):
            class FakeSub:
                id = "abc123"
            return FakeSub()

    class FakeSettings:
        tenant_id = "default"
        dry_run = False

    published1 = publish_due_posts(FakeReddit(), db, FakeSettings())
    published2 = publish_due_posts(FakeReddit(), db, FakeSettings())
    assert published1 == 1
    assert published2 == 0  # already published — idempotent
