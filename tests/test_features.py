"""Tests for billing feature flags."""

from app.billing.features import FEATURE_MATRIX, TIERS, has_feature
from app.billing.tenant import get_or_create_tenant


def test_unknown_tenant_returns_false(db):
    assert has_feature(db, "nonexistent-tenant-id", "basic_moderation") is False


def test_free_tier_has_basic_moderation(db):
    tenant = get_or_create_tenant(db, "freetestuser")
    assert has_feature(db, tenant.tenant_id, "basic_moderation") is True


def test_free_tier_lacks_advanced_analytics(db):
    tenant = get_or_create_tenant(db, "freetestuser2")
    assert has_feature(db, tenant.tenant_id, "advanced_analytics") is False


def test_tier_hierarchy_is_cumulative():
    # Every feature in free must be in starter, pro, agency, enterprise
    for tier_name in ["starter", "pro", "agency", "enterprise"]:
        for feature in FEATURE_MATRIX["free"]:
            assert feature in FEATURE_MATRIX[tier_name], f"{feature} missing from {tier_name}"


def test_ai_quota_free_tier(db):
    tenant = get_or_create_tenant(db, "quotatestuser")
    # Fresh tenant has 0 calls today — should be allowed
    assert has_feature(db, tenant.tenant_id, "ai_call") is True


def test_ai_quota_exhausted(db):
    from app.dashboard.models import TenantConfig

    tenant = get_or_create_tenant(db, "exhausteduser")
    # Manually set ai_calls_today to the free tier limit
    free_limit = TIERS["free"].ai_calls_per_day
    db.query(TenantConfig).filter(TenantConfig.tenant_id == tenant.tenant_id).update(
        {"ai_calls_today": free_limit}
    )
    db.commit()
    assert has_feature(db, tenant.tenant_id, "ai_call") is False
