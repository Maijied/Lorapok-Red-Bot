"""Tenant lifecycle management — create, update, and manage subreddit lists."""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

from app.dashboard.models import TenantConfig

log = logging.getLogger(__name__)


def get_or_create_tenant(db: Session, reddit_username: str) -> TenantConfig:
    """Fetch or create a TenantConfig for *reddit_username*."""
    tenant = (
        db.query(TenantConfig)
        .filter(TenantConfig.reddit_username == reddit_username)
        .first()
    )
    if tenant:
        return tenant

    tenant = TenantConfig(
        tenant_id=str(uuid.uuid4()),
        reddit_username=reddit_username,
        tier="free",
        ai_calls_today=0,
        managed_subreddits=[],
    )
    db.add(tenant)
    db.commit()
    db.refresh(tenant)
    log.info("Created tenant for u/%s (id=%s)", reddit_username, tenant.tenant_id)
    return tenant


def update_tenant_tier(db: Session, tenant_id: str, tier: str) -> bool:
    """Update the subscription tier for *tenant_id*."""
    from app.billing.features import TIERS

    if tier not in TIERS:
        log.error("Unknown tier: %s", tier)
        return False
    tenant = db.query(TenantConfig).filter(TenantConfig.tenant_id == tenant_id).first()
    if not tenant:
        return False
    tenant.tier = tier
    tenant.updated_at = datetime.now(timezone.utc)
    db.commit()
    log.info("Tenant %s upgraded to tier: %s", tenant_id, tier)
    return True


def add_managed_subreddit(db: Session, tenant_id: str, subreddit_name: str) -> bool:
    """Add *subreddit_name* to the tenant's managed list."""
    from app.billing.features import has_feature

    if not has_feature(db, tenant_id, "add_subreddit"):
        log.warning("Tenant %s has reached subreddit limit", tenant_id)
        return False

    tenant = db.query(TenantConfig).filter(TenantConfig.tenant_id == tenant_id).first()
    if not tenant:
        return False

    subs: list[str] = list(tenant.managed_subreddits or [])
    if subreddit_name not in subs:
        subs.append(subreddit_name)
        tenant.managed_subreddits = subs
        db.commit()
    return True


def remove_managed_subreddit(db: Session, tenant_id: str, subreddit_name: str) -> bool:
    tenant = db.query(TenantConfig).filter(TenantConfig.tenant_id == tenant_id).first()
    if not tenant:
        return False
    subs: list[str] = list(tenant.managed_subreddits or [])
    if subreddit_name in subs:
        subs.remove(subreddit_name)
        tenant.managed_subreddits = subs
        db.commit()
    return True


def reset_all_ai_quotas(db: Session) -> None:
    """Reset ai_calls_today to 0 for all tenants (called at midnight UTC)."""
    db.query(TenantConfig).update(
        {"ai_calls_today": 0, "ai_calls_reset_at": datetime.now(timezone.utc)}
    )
    db.commit()
    log.info("AI quota counters reset for all tenants.")


def increment_ai_calls(db: Session, tenant_id: str) -> None:
    """Increment the AI call counter for *tenant_id*."""
    tenant = db.query(TenantConfig).filter(TenantConfig.tenant_id == tenant_id).first()
    if tenant:
        tenant.ai_calls_today = (tenant.ai_calls_today or 0) + 1
        db.commit()
