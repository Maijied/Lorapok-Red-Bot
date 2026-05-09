"""FastAPI feature gate middleware — enforces tier entitlements per endpoint."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import Request
from fastapi.responses import JSONResponse

log = logging.getLogger(__name__)

# Map URL path prefixes to required feature flags
_ENDPOINT_FEATURES: dict[str, str] = {
    "/analytics/cohort": "cohort_analysis",
    "/analytics/health-score": "health_score",
    "/analytics/multi-sub": "multi_sub_dashboard",
    "/analytics/sentiment": "sentiment_analysis",
    "/subreddits/sync-policy": "policy_sync",
    "/webhooks": "custom_webhooks",
    "/billing/portal": "basic_moderation",  # all tiers can access billing portal
    "/flair": "flair_automation",
    "/wiki": "wiki_manager",
    "/modmail": "modmail_triage",
    "/users": "basic_moderation",
    "/scheduled-posts": "content_calendar",
}


async def feature_gate_middleware(request: Request, call_next: Any) -> Any:
    """Check feature entitlement before forwarding the request."""
    path = request.url.path

    required_feature = _get_required_feature(path)
    if required_feature is None:
        return await call_next(request)

    tenant_id = _extract_tenant_id(request)
    if not tenant_id:
        return await call_next(request)

    try:
        import os

        from app.database import get_engine, get_session_factory

        engine = get_engine(os.getenv("DATABASE_URL", ""))
        session_factory = get_session_factory(engine)
        db = session_factory()
        try:
            from app.billing.features import has_feature

            if not has_feature(db, tenant_id, required_feature):
                return JSONResponse(
                    status_code=403,
                    content={
                        "error": "feature_not_available",
                        "message": (
                            f"Feature '{required_feature}' requires a higher "
                            "subscription tier. Visit /billing/portal to upgrade."
                        ),
                        "required_feature": required_feature,
                    },
                )
        finally:
            db.close()
    except Exception as exc:
        log.error("Feature gate middleware error: %s", exc)

    return await call_next(request)


def _get_required_feature(path: str) -> str | None:
    for prefix, feature in _ENDPOINT_FEATURES.items():
        if path.startswith(prefix):
            return feature
    return None


def _extract_tenant_id(request: Request) -> str | None:
    # Check X-Tenant-ID header first, then fall back to query param
    tenant_id = request.headers.get("X-Tenant-ID")
    if not tenant_id:
        tenant_id = request.query_params.get("tenant_id")
    return tenant_id or None
