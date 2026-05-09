"""Feature flag matrix and enforcement for multi-tenant SaaS billing."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

from sqlalchemy.orm import Session

log = logging.getLogger(__name__)

# ── Feature matrix — cumulative (each tier includes all lower tiers) ──────────

_FREE_FEATURES: set[str] = {
    "basic_moderation",
    "comment_stream",
    "dashboard",
    "discord_integration",
    "github_integration",
}

_STARTER_FEATURES: set[str] = _FREE_FEATURES | {
    "modmail_triage",
    "flair_automation",
    "basic_analytics",
    "ban_appeal_workflow",
}

_PRO_FEATURES: set[str] = _STARTER_FEATURES | {
    "advanced_analytics",
    "engagement_predictor",
    "content_calendar",
    "cross_sub_spam",
    "sentiment_analysis",
    "wiki_manager",
    "widget_manager",
    "slack_integration",
    "telegram_integration",
    "contributor_management",
    "submission_stream",
}

_AGENCY_FEATURES: set[str] = _PRO_FEATURES | {
    "white_label",
    "api_access",
    "custom_webhooks",
    "policy_sync",
    "multi_sub_dashboard",
    "mod_notes",
    "rules_engine_v2",
    "health_score",
    "cohort_analysis",
}

_ENTERPRISE_FEATURES: set[str] = _AGENCY_FEATURES | {
    "on_premise",
    "custom_ai_models",
    "sso",
    "audit_logs",
    "compliance_reports",
    "sla_guarantee",
}

FEATURE_MATRIX: dict[str, set[str]] = {
    "free": _FREE_FEATURES,
    "starter": _STARTER_FEATURES,
    "pro": _PRO_FEATURES,
    "agency": _AGENCY_FEATURES,
    "enterprise": _ENTERPRISE_FEATURES,
}


@dataclass(frozen=True)
class SubscriptionTier:
    name: str
    monthly_price_usd: float
    stripe_price_env: str
    max_subreddits: int   # -1 = unlimited
    ai_calls_per_day: int  # -1 = unlimited
    features: set[str] = field(default_factory=set)


TIERS: dict[str, SubscriptionTier] = {
    "free": SubscriptionTier("free", 0.0, "", 1, 100, _FREE_FEATURES),
    "starter": SubscriptionTier("starter", 19.0, "STRIPE_PRICE_STARTER_MONTHLY", 3, 1000, _STARTER_FEATURES),
    "pro": SubscriptionTier("pro", 49.0, "STRIPE_PRICE_PRO_MONTHLY", 10, -1, _PRO_FEATURES),
    "agency": SubscriptionTier("agency", 149.0, "STRIPE_PRICE_AGENCY_MONTHLY", -1, -1, _AGENCY_FEATURES),
    "enterprise": SubscriptionTier("enterprise", 0.0, "", -1, -1, _ENTERPRISE_FEATURES),
}


def get_tenant_features(db: Session, tenant_id: str) -> set[str]:
    """Return the full feature set for *tenant_id*."""
    from app.dashboard.models import TenantConfig

    tenant = db.query(TenantConfig).filter(TenantConfig.tenant_id == tenant_id).first()
    if not tenant:
        return set()
    return FEATURE_MATRIX.get(tenant.tier, _FREE_FEATURES)


def has_feature(db: Session, tenant_id: str, feature: str) -> bool:
    """Return True if *tenant_id* is entitled to *feature*.  Never raises."""
    try:
        return _has_feature(db, tenant_id, feature)
    except Exception as exc:
        log.error("has_feature error for tenant %s feature %s: %s", tenant_id, feature, exc)
        return False


def _has_feature(db: Session, tenant_id: str, feature: str) -> bool:
    from app.dashboard.models import TenantConfig

    tenant = db.query(TenantConfig).filter(TenantConfig.tenant_id == tenant_id).first()
    if not tenant:
        return False

    tier = TIERS.get(tenant.tier, TIERS["free"])

    # AI call quota check
    if feature == "ai_call":
        if tier.ai_calls_per_day == -1:
            return True
        return (tenant.ai_calls_today or 0) < tier.ai_calls_per_day

    # Subreddit count check
    if feature == "add_subreddit":
        if tier.max_subreddits == -1:
            return True
        current = len(tenant.managed_subreddits or [])
        return current < tier.max_subreddits

    return feature in tier.features
