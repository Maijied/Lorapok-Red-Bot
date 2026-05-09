"""Initial schema — all models

Revision ID: 0001
Revises:
Create Date: 2025-05-09
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "daily_metrics",
        sa.Column("id", sa.Integer, primary_key=True, index=True),
        sa.Column("metric_date", sa.Date, index=True),
        sa.Column("metric_name", sa.String(50), index=True),
        sa.Column("count", sa.Integer, default=0),
    )

    op.create_table(
        "github_update_tracker",
        sa.Column("id", sa.Integer, primary_key=True, index=True),
        sa.Column("repo_name", sa.String(100), index=True),
        sa.Column("update_type", sa.String(20)),
        sa.Column("external_id", sa.String(100), unique=True, index=True),
        sa.Column("processed_at", sa.DateTime),
    )

    op.create_table(
        "pending_posts",
        sa.Column("id", sa.Integer, primary_key=True, index=True),
        sa.Column("title", sa.String(255)),
        sa.Column("body", sa.Text),
        sa.Column("source_url", sa.String(255)),
        sa.Column("status", sa.String(20), default="pending"),
        sa.Column("created_at", sa.DateTime),
    )

    op.create_table(
        "review_cases",
        sa.Column("id", sa.Integer, primary_key=True, index=True),
        sa.Column("tenant_id", sa.String(64), index=True),
        sa.Column("subreddit_name", sa.String(100), index=True),
        sa.Column("text", sa.Text),
        sa.Column("reason", sa.String(255)),
        sa.Column("source", sa.String(50)),
        sa.Column("recommended_action", sa.String(20)),
        sa.Column("status", sa.String(20), default="pending"),
        sa.Column("reviewer_note", sa.Text, default=""),
        sa.Column("was_override", sa.Boolean, default=False),
        sa.Column("created_at", sa.DateTime),
    )

    op.create_table(
        "moderation_decisions",
        sa.Column("id", sa.Integer, primary_key=True, index=True),
        sa.Column("tenant_id", sa.String(64), index=True),
        sa.Column("subreddit_name", sa.String(100), index=True),
        sa.Column("text_hash", sa.String(64), index=True),
        sa.Column("content", sa.Text),
        sa.Column("action", sa.String(20)),
        sa.Column("reason", sa.Text),
        sa.Column("source", sa.String(50)),
        sa.Column("created_at", sa.DateTime),
    )

    op.create_table(
        "scheduled_posts",
        sa.Column("id", sa.Integer, primary_key=True, index=True),
        sa.Column("tenant_id", sa.String(64), index=True),
        sa.Column("subreddit_name", sa.String(100), index=True),
        sa.Column("title", sa.String(255)),
        sa.Column("body", sa.Text),
        sa.Column("flair_id", sa.String(100), nullable=True),
        sa.Column("post_at", sa.DateTime, index=True),
        sa.Column("status", sa.String(20), default="scheduled"),
        sa.Column("reddit_post_id", sa.String(20), nullable=True),
        sa.Column("error_message", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime),
    )

    op.create_table(
        "user_reputations",
        sa.Column("id", sa.Integer, primary_key=True, index=True),
        sa.Column("tenant_id", sa.String(64), index=True),
        sa.Column("username", sa.String(100), index=True),
        sa.Column("subreddit_name", sa.String(100), index=True),
        sa.Column("approved_posts", sa.Integer, default=0),
        sa.Column("approved_comments", sa.Integer, default=0),
        sa.Column("removed_posts", sa.Integer, default=0),
        sa.Column("removed_comments", sa.Integer, default=0),
        sa.Column("bans", sa.Integer, default=0),
        sa.Column("account_age_days", sa.Integer, default=0),
        sa.Column("reputation_score", sa.Float, default=0.0),
        sa.Column("flair_tier", sa.String(50), nullable=True),
        sa.Column("is_contributor", sa.Boolean, default=False),
        sa.Column("is_suspicious", sa.Boolean, default=False),
        sa.Column("last_active_at", sa.DateTime, nullable=True),
        sa.Column("created_at", sa.DateTime),
        sa.Column("updated_at", sa.DateTime),
        sa.UniqueConstraint("username", "subreddit_name", name="uq_user_sub"),
    )

    op.create_table(
        "mod_notes",
        sa.Column("id", sa.Integer, primary_key=True, index=True),
        sa.Column("tenant_id", sa.String(64), index=True),
        sa.Column("username", sa.String(100), index=True),
        sa.Column("subreddit_name", sa.String(100), index=True),
        sa.Column("note", sa.Text),
        sa.Column("label", sa.String(30)),
        sa.Column("created_by", sa.String(100)),
        sa.Column("reddit_note_id", sa.String(50), nullable=True),
        sa.Column("created_at", sa.DateTime),
    )

    op.create_table(
        "modmail_records",
        sa.Column("id", sa.Integer, primary_key=True, index=True),
        sa.Column("tenant_id", sa.String(64), index=True),
        sa.Column("conversation_id", sa.String(50), unique=True, index=True),
        sa.Column("subreddit_name", sa.String(100), index=True),
        sa.Column("subject", sa.String(255)),
        sa.Column("author", sa.String(100)),
        sa.Column("category", sa.String(30)),
        sa.Column("confidence", sa.Float, default=0.0),
        sa.Column("status", sa.String(20), default="open"),
        sa.Column("sla_deadline", sa.DateTime, nullable=True),
        sa.Column("auto_replied", sa.Boolean, default=False),
        sa.Column("created_at", sa.DateTime),
        sa.Column("resolved_at", sa.DateTime, nullable=True),
    )

    op.create_table(
        "modmail_templates",
        sa.Column("id", sa.Integer, primary_key=True, index=True),
        sa.Column("tenant_id", sa.String(64), index=True),
        sa.Column("name", sa.String(100)),
        sa.Column("category", sa.String(30)),
        sa.Column("body", sa.Text),
        sa.Column("language", sa.String(10), default="en"),
        sa.Column("created_at", sa.DateTime),
    )

    op.create_table(
        "flair_templates",
        sa.Column("id", sa.Integer, primary_key=True, index=True),
        sa.Column("tenant_id", sa.String(64), index=True),
        sa.Column("subreddit_name", sa.String(100), index=True),
        sa.Column("reddit_template_id", sa.String(50)),
        sa.Column("text", sa.String(100)),
        sa.Column("css_class", sa.String(100), default=""),
        sa.Column("flair_type", sa.String(10), default="link"),
        sa.Column("auto_assign_keywords", sa.JSON),
        sa.Column("created_at", sa.DateTime),
    )

    op.create_table(
        "flair_assignments",
        sa.Column("id", sa.Integer, primary_key=True, index=True),
        sa.Column("tenant_id", sa.String(64), index=True),
        sa.Column("subreddit_name", sa.String(100), index=True),
        sa.Column("target", sa.String(100)),
        sa.Column("flair_text", sa.String(100)),
        sa.Column("flair_type", sa.String(10)),
        sa.Column("source", sa.String(30)),
        sa.Column("created_at", sa.DateTime),
    )

    op.create_table(
        "wiki_pages",
        sa.Column("id", sa.Integer, primary_key=True, index=True),
        sa.Column("tenant_id", sa.String(64), index=True),
        sa.Column("subreddit_name", sa.String(100), index=True),
        sa.Column("page_name", sa.String(100), index=True),
        sa.Column("content", sa.Text),
        sa.Column("last_synced_at", sa.DateTime),
        sa.Column("auto_update_enabled", sa.Boolean, default=False),
        sa.Column("auto_update_type", sa.String(20), nullable=True),
    )

    op.create_table(
        "webhook_configs",
        sa.Column("id", sa.Integer, primary_key=True, index=True),
        sa.Column("tenant_id", sa.String(64), index=True),
        sa.Column("url", sa.String(500)),
        sa.Column("events", sa.JSON),
        sa.Column("secret_hash", sa.String(64)),
        sa.Column("is_active", sa.Boolean, default=True),
        sa.Column("failure_count", sa.Integer, default=0),
        sa.Column("last_triggered_at", sa.DateTime, nullable=True),
        sa.Column("created_at", sa.DateTime),
    )

    op.create_table(
        "tenant_configs",
        sa.Column("id", sa.Integer, primary_key=True, index=True),
        sa.Column("tenant_id", sa.String(64), unique=True, index=True),
        sa.Column("reddit_username", sa.String(100), unique=True, index=True),
        sa.Column("stripe_customer_id", sa.String(50), nullable=True),
        sa.Column("stripe_subscription_id", sa.String(50), nullable=True),
        sa.Column("tier", sa.String(20), default="free"),
        sa.Column("ai_calls_today", sa.Integer, default=0),
        sa.Column("ai_calls_reset_at", sa.DateTime),
        sa.Column("managed_subreddits", sa.JSON),
        sa.Column("white_label_name", sa.String(100), nullable=True),
        sa.Column("white_label_logo_url", sa.String(500), nullable=True),
        sa.Column("created_at", sa.DateTime),
        sa.Column("updated_at", sa.DateTime),
        sa.UniqueConstraint("reddit_username", name="uq_tenant_reddit_username"),
    )

    op.create_table(
        "ban_appeals",
        sa.Column("id", sa.Integer, primary_key=True, index=True),
        sa.Column("tenant_id", sa.String(64), index=True),
        sa.Column("username", sa.String(100), index=True),
        sa.Column("subreddit_name", sa.String(100), index=True),
        sa.Column("modmail_id", sa.String(50)),
        sa.Column("appeal_text", sa.Text),
        sa.Column("auto_decision", sa.String(20), nullable=True),
        sa.Column("auto_reason", sa.Text, nullable=True),
        sa.Column("final_decision", sa.String(20), nullable=True),
        sa.Column("reviewer_note", sa.Text, nullable=True),
        sa.Column("status", sa.String(20), default="pending"),
        sa.Column("created_at", sa.DateTime),
        sa.Column("resolved_at", sa.DateTime, nullable=True),
    )

    op.create_table(
        "spam_signals",
        sa.Column("id", sa.Integer, primary_key=True, index=True),
        sa.Column("tenant_id", sa.String(64), index=True),
        sa.Column("username", sa.String(100), index=True),
        sa.Column("subreddit_name", sa.String(100), index=True),
        sa.Column("content_hash", sa.String(64), index=True),
        sa.Column("url", sa.String(500), default=""),
        sa.Column("created_at", sa.DateTime),
    )

    op.create_table(
        "sentiment_data",
        sa.Column("id", sa.Integer, primary_key=True, index=True),
        sa.Column("tenant_id", sa.String(64), index=True),
        sa.Column("subreddit_name", sa.String(100), index=True),
        sa.Column("score", sa.Float),
        sa.Column("label", sa.String(20)),
        sa.Column("source", sa.String(20)),
        sa.Column("recorded_at", sa.DateTime, index=True),
    )

    op.create_table(
        "policy_sync_records",
        sa.Column("id", sa.Integer, primary_key=True, index=True),
        sa.Column("tenant_id", sa.String(64), index=True),
        sa.Column("source_subreddit", sa.String(100)),
        sa.Column("target_subreddit", sa.String(100)),
        sa.Column("policy_types", sa.JSON),
        sa.Column("synced_at", sa.DateTime),
        sa.Column("success", sa.Boolean, default=True),
        sa.Column("error_message", sa.Text, nullable=True),
    )

    op.create_table(
        "onboarding_records",
        sa.Column("id", sa.Integer, primary_key=True, index=True),
        sa.Column("tenant_id", sa.String(64), index=True),
        sa.Column("username", sa.String(100), index=True),
        sa.Column("subreddit_name", sa.String(100), index=True),
        sa.Column("status", sa.String(20), default="welcomed"),
        sa.Column("welcomed_at", sa.DateTime),
        sa.Column("flair_assigned_at", sa.DateTime, nullable=True),
    )

    op.create_table(
        "rule_violations",
        sa.Column("id", sa.Integer, primary_key=True, index=True),
        sa.Column("tenant_id", sa.String(64), index=True),
        sa.Column("username", sa.String(100), index=True),
        sa.Column("subreddit_name", sa.String(100), index=True),
        sa.Column("rule_id", sa.String(100)),
        sa.Column("content_id", sa.String(20)),
        sa.Column("created_at", sa.DateTime),
    )


def downgrade() -> None:
    for table in [
        "rule_violations", "onboarding_records", "policy_sync_records",
        "sentiment_data", "spam_signals", "ban_appeals", "tenant_configs",
        "webhook_configs", "wiki_pages", "flair_assignments", "flair_templates",
        "modmail_templates", "modmail_records", "mod_notes", "user_reputations",
        "scheduled_posts", "moderation_decisions", "review_cases",
        "pending_posts", "github_update_tracker", "daily_metrics",
    ]:
        op.drop_table(table)
