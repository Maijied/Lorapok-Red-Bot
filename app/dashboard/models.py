"""SQLAlchemy ORM models for Lorapok Red Bot.

All tenant-scoped tables include a ``tenant_id`` column so that every query
can be filtered to a single tenant without cross-tenant data leakage.
"""

from datetime import date, datetime, timezone
from typing import Any

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    Date,
    DateTime,
    Float,
    Integer,
    String,
    Text,
    UniqueConstraint,
)

from app.database import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


# ── Existing models (preserved) ───────────────────────────────────────────────


class DailyMetric(Base):
    __tablename__ = "daily_metrics"

    id = Column(Integer, primary_key=True, index=True)
    metric_date = Column(Date, default=date.today, index=True)
    metric_name = Column(String(50), index=True)
    count = Column(Integer, default=0)


class GithubUpdateTracker(Base):
    __tablename__ = "github_update_tracker"

    id = Column(Integer, primary_key=True, index=True)
    repo_name = Column(String(100), index=True)
    update_type = Column(String(20))  # "release" | "issue"
    external_id = Column(String(100), unique=True, index=True)
    processed_at = Column(DateTime, default=_utcnow)


class PendingPost(Base):
    __tablename__ = "pending_posts"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255))
    body = Column(Text)
    source_url = Column(String(255))
    status = Column(String(20), default="pending")  # pending | approved | rejected
    created_at = Column(DateTime, default=_utcnow)


class ReviewCaseRecord(Base):
    __tablename__ = "review_cases"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(String(64), index=True, default="default")
    subreddit_name = Column(String(100), index=True, default="")
    text = Column(Text)
    reason = Column(String(255))
    source = Column(String(50))  # "rules" | "ai" | "rules+ai"
    recommended_action = Column(String(20))  # "allow" | "review" | "remove"
    status = Column(String(20), default="pending")  # pending | approved | rejected | escalated
    reviewer_note = Column(Text, default="")
    was_override = Column(Boolean, default=False)
    created_at = Column(DateTime, default=_utcnow)


class ModerationDecisionRecord(Base):
    __tablename__ = "moderation_decisions"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(String(64), index=True, default="default")
    subreddit_name = Column(String(100), index=True, default="")
    text_hash = Column(String(64), index=True)  # SHA-256 of normalised text
    content = Column(Text)
    action = Column(String(20))  # "allow" | "review" | "remove"
    reason = Column(Text)
    source = Column(String(50))
    created_at = Column(DateTime, default=_utcnow)


# ── New models ────────────────────────────────────────────────────────────────


class ScheduledPost(Base):
    """Content calendar — posts queued for future publication."""

    __tablename__ = "scheduled_posts"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(String(64), index=True)
    subreddit_name = Column(String(100), index=True)
    title = Column(String(255))
    body = Column(Text)
    flair_id = Column(String(100), nullable=True)
    post_at = Column(DateTime, index=True)  # UTC — when to publish
    status = Column(String(20), default="scheduled")  # scheduled | published | cancelled | failed
    reddit_post_id = Column(String(20), nullable=True)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=_utcnow)


class UserReputation(Base):
    """Per-user reputation score within a subreddit."""

    __tablename__ = "user_reputations"
    __table_args__ = (UniqueConstraint("username", "subreddit_name", name="uq_user_sub"),)

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(String(64), index=True)
    username = Column(String(100), index=True)
    subreddit_name = Column(String(100), index=True)
    approved_posts = Column(Integer, default=0)
    approved_comments = Column(Integer, default=0)
    removed_posts = Column(Integer, default=0)
    removed_comments = Column(Integer, default=0)
    bans = Column(Integer, default=0)
    account_age_days = Column(Integer, default=0)
    reputation_score = Column(Float, default=0.0)  # clamped [-100, 100]
    flair_tier = Column(String(50), nullable=True)
    is_contributor = Column(Boolean, default=False)
    is_suspicious = Column(Boolean, default=False)
    last_active_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=_utcnow)
    updated_at = Column(DateTime, default=_utcnow, onupdate=_utcnow)


class ModNote(Base):
    """Moderator notes attached to users."""

    __tablename__ = "mod_notes"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(String(64), index=True)
    username = Column(String(100), index=True)
    subreddit_name = Column(String(100), index=True)
    note = Column(Text)
    label = Column(String(30))  # BOT_BAN | BOT_SPAM | BOT_REVIEW | HUMAN_OVERRIDE
    created_by = Column(String(100))  # bot username or moderator username
    reddit_note_id = Column(String(50), nullable=True)
    created_at = Column(DateTime, default=_utcnow)


class ModmailRecord(Base):
    """Tracked modmail conversations with triage metadata."""

    __tablename__ = "modmail_records"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(String(64), index=True)
    conversation_id = Column(String(50), unique=True, index=True)
    subreddit_name = Column(String(100), index=True)
    subject = Column(String(255))
    author = Column(String(100))
    category = Column(String(30))  # ban_appeal | spam_report | question | feedback | unknown
    confidence = Column(Float, default=0.0)
    status = Column(String(20), default="open")  # open | auto_replied | needs_human | resolved
    sla_deadline = Column(DateTime, nullable=True)
    auto_replied = Column(Boolean, default=False)
    created_at = Column(DateTime, default=_utcnow)
    resolved_at = Column(DateTime, nullable=True)


class ModmailTemplate(Base):
    """Reusable modmail reply templates per tenant."""

    __tablename__ = "modmail_templates"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(String(64), index=True)
    name = Column(String(100))
    category = Column(String(30))
    body = Column(Text)  # supports {{username}}, {{subreddit}}, {{ban_reason}}
    language = Column(String(10), default="en")
    created_at = Column(DateTime, default=_utcnow)


class FlairTemplate(Base):
    """Flair templates synced from Reddit with auto-assign keyword rules."""

    __tablename__ = "flair_templates"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(String(64), index=True)
    subreddit_name = Column(String(100), index=True)
    reddit_template_id = Column(String(50))
    text = Column(String(100))
    css_class = Column(String(100), default="")
    flair_type = Column(String(10), default="link")  # "link" | "user"
    auto_assign_keywords = Column(JSON, default=list)  # list[str]
    created_at = Column(DateTime, default=_utcnow)


class FlairAssignmentRecord(Base):
    """Audit log of every flair assignment made by the bot."""

    __tablename__ = "flair_assignments"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(String(64), index=True)
    subreddit_name = Column(String(100), index=True)
    target = Column(String(100))  # username or reddit post ID
    flair_text = Column(String(100))
    flair_type = Column(String(10))  # "link" | "user"
    source = Column(String(30))  # "auto_content" | "auto_karma" | "manual"
    created_at = Column(DateTime, default=_utcnow)


class WikiPage(Base):
    """Local cache of subreddit wiki pages with auto-update config."""

    __tablename__ = "wiki_pages"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(String(64), index=True)
    subreddit_name = Column(String(100), index=True)
    page_name = Column(String(100), index=True)
    content = Column(Text)
    last_synced_at = Column(DateTime, default=_utcnow)
    auto_update_enabled = Column(Boolean, default=False)
    auto_update_type = Column(String(20), nullable=True)  # "faq" | "changelog" | None


class WebhookConfig(Base):
    """Outbound webhook endpoints registered by tenants."""

    __tablename__ = "webhook_configs"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(String(64), index=True)
    url = Column(String(500))
    events = Column(JSON, default=list)  # list[str] of event type strings
    secret_hash = Column(String(64))  # SHA-256 of the signing secret
    is_active = Column(Boolean, default=True)
    failure_count = Column(Integer, default=0)
    last_triggered_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=_utcnow)


class TenantConfig(Base):
    """Multi-tenant SaaS configuration and Stripe subscription state."""

    __tablename__ = "tenant_configs"
    __table_args__ = (UniqueConstraint("reddit_username", name="uq_tenant_reddit_username"),)

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(String(64), unique=True, index=True)
    reddit_username = Column(String(100), unique=True, index=True)
    stripe_customer_id = Column(String(50), nullable=True)
    stripe_subscription_id = Column(String(50), nullable=True)
    tier = Column(String(20), default="free")  # free | starter | pro | agency | enterprise
    ai_calls_today = Column(Integer, default=0)
    ai_calls_reset_at = Column(DateTime, default=_utcnow)
    managed_subreddits = Column(JSON, default=list)  # list[str]
    white_label_name = Column(String(100), nullable=True)
    white_label_logo_url = Column(String(500), nullable=True)
    created_at = Column(DateTime, default=_utcnow)
    updated_at = Column(DateTime, default=_utcnow, onupdate=_utcnow)


class BanAppeal(Base):
    """Ban appeal submissions and their review state."""

    __tablename__ = "ban_appeals"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(String(64), index=True)
    username = Column(String(100), index=True)
    subreddit_name = Column(String(100), index=True)
    modmail_id = Column(String(50))
    appeal_text = Column(Text)
    auto_decision = Column(String(20), nullable=True)  # "approve" | "reject" | "escalate"
    auto_reason = Column(Text, nullable=True)
    final_decision = Column(String(20), nullable=True)
    reviewer_note = Column(Text, nullable=True)
    status = Column(String(20), default="pending")  # pending | approved | rejected | escalated
    created_at = Column(DateTime, default=_utcnow)
    resolved_at = Column(DateTime, nullable=True)


class SpamSignalRecord(Base):
    """Cross-subreddit spam signals detected by the spam detector."""

    __tablename__ = "spam_signals"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(String(64), index=True)
    username = Column(String(100), index=True)
    subreddit_name = Column(String(100), index=True)
    content_hash = Column(String(64), index=True)
    url = Column(String(500), default="")
    created_at = Column(DateTime, default=_utcnow)


class SentimentDataPoint(Base):
    """Time-series sentiment scores for subreddit health tracking."""

    __tablename__ = "sentiment_data"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(String(64), index=True)
    subreddit_name = Column(String(100), index=True)
    score = Column(Float)  # -1.0 to 1.0
    label = Column(String(20))  # "positive" | "neutral" | "negative"
    source = Column(String(20))  # "comment" | "submission"
    recorded_at = Column(DateTime, default=_utcnow, index=True)


class PolicySyncRecord(Base):
    """Audit log of policy sync operations between subreddits."""

    __tablename__ = "policy_sync_records"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(String(64), index=True)
    source_subreddit = Column(String(100))
    target_subreddit = Column(String(100))
    policy_types = Column(JSON, default=list)  # list[str]
    synced_at = Column(DateTime, default=_utcnow)
    success = Column(Boolean, default=True)
    error_message = Column(Text, nullable=True)


class OnboardingRecord(Base):
    """Tracks which new subscribers have been welcomed."""

    __tablename__ = "onboarding_records"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(String(64), index=True)
    username = Column(String(100), index=True)
    subreddit_name = Column(String(100), index=True)
    status = Column(String(20), default="welcomed")  # welcomed | flair_assigned | completed
    welcomed_at = Column(DateTime, default=_utcnow)
    flair_assigned_at = Column(DateTime, nullable=True)


class RuleViolationRecord(Base):
    """Per-user rule violation history within a subreddit."""

    __tablename__ = "rule_violations"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(String(64), index=True)
    username = Column(String(100), index=True)
    subreddit_name = Column(String(100), index=True)
    rule_id = Column(String(100))
    content_id = Column(String(20))  # Reddit comment/submission ID
    created_at = Column(DateTime, default=_utcnow)
