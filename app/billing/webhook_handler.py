"""Stripe webhook event handler — verifies signatures and updates tenant state."""

from __future__ import annotations

import logging
import os
from typing import Any

from sqlalchemy.orm import Session

log = logging.getLogger(__name__)


def handle_stripe_webhook(
    payload: bytes,
    sig_header: str,
    db: Session,
) -> dict[str, Any]:
    """Verify and process a Stripe webhook event.

    Returns ``{"ok": True}`` on success.
    Raises ``ValueError`` on signature verification failure (caller returns HTTP 400).
    """
    import stripe

    webhook_secret = os.getenv("STRIPE_WEBHOOK_SECRET", "")
    try:
        event = stripe.Webhook.construct_event(payload, sig_header, webhook_secret)
    except stripe.error.SignatureVerificationError as exc:
        raise ValueError(f"Invalid Stripe signature: {exc}") from exc

    event_type = event["type"]
    data = event["data"]["object"]

    if event_type == "customer.subscription.updated":
        _handle_subscription_updated(db, data)
    elif event_type == "customer.subscription.deleted":
        _handle_subscription_deleted(db, data)
    elif event_type == "invoice.payment_failed":
        _handle_payment_failed(db, data)
    elif event_type == "invoice.payment_succeeded":
        _handle_payment_succeeded(db, data)
    else:
        log.debug("Unhandled Stripe event type: %s", event_type)

    return {"ok": True}


# ── Event handlers ────────────────────────────────────────────────────────────


def _handle_subscription_updated(db: Session, data: dict) -> None:
    from app.billing.tenant import update_tenant_tier
    from app.dashboard.models import TenantConfig

    customer_id = data.get("customer")
    new_tier = _price_to_tier(data)
    tenant = (
        db.query(TenantConfig)
        .filter(TenantConfig.stripe_customer_id == customer_id)
        .first()
    )
    if tenant:
        update_tenant_tier(db, tenant.tenant_id, new_tier)
        tenant.stripe_subscription_id = data.get("id")
        db.commit()
        log.info("Subscription updated for customer %s → tier %s", customer_id, new_tier)


def _handle_subscription_deleted(db: Session, data: dict) -> None:
    from app.billing.tenant import update_tenant_tier
    from app.dashboard.models import TenantConfig

    customer_id = data.get("customer")
    tenant = (
        db.query(TenantConfig)
        .filter(TenantConfig.stripe_customer_id == customer_id)
        .first()
    )
    if tenant:
        update_tenant_tier(db, tenant.tenant_id, "free")
        log.info("Subscription cancelled for customer %s — downgraded to free", customer_id)


def _handle_payment_failed(db: Session, data: dict) -> None:
    from app.dashboard.models import TenantConfig

    customer_id = data.get("customer")
    tenant = (
        db.query(TenantConfig)
        .filter(TenantConfig.stripe_customer_id == customer_id)
        .first()
    )
    if tenant:
        log.warning("Payment failed for tenant %s (customer %s)", tenant.tenant_id, customer_id)
        # Grace period: keep current tier for 7 days — handled by Stripe dunning


def _handle_payment_succeeded(db: Session, data: dict) -> None:
    from app.dashboard.models import TenantConfig

    customer_id = data.get("customer")
    tenant = (
        db.query(TenantConfig)
        .filter(TenantConfig.stripe_customer_id == customer_id)
        .first()
    )
    if tenant:
        tenant.ai_calls_today = 0
        db.commit()
        log.info("Payment succeeded for tenant %s", tenant.tenant_id)


def _price_to_tier(subscription_data: dict) -> str:
    """Map a Stripe subscription's price ID to a tier name."""
    items = subscription_data.get("items", {}).get("data", [])
    if not items:
        return "free"
    price_id = items[0].get("price", {}).get("id", "")

    tier_map = {
        os.getenv("STRIPE_PRICE_STARTER_MONTHLY", ""): "starter",
        os.getenv("STRIPE_PRICE_PRO_MONTHLY", ""): "pro",
        os.getenv("STRIPE_PRICE_AGENCY_MONTHLY", ""): "agency",
        os.getenv("STRIPE_PRICE_STARTER_ANNUAL", ""): "starter",
        os.getenv("STRIPE_PRICE_PRO_ANNUAL", ""): "pro",
        os.getenv("STRIPE_PRICE_AGENCY_ANNUAL", ""): "agency",
    }
    return tier_map.get(price_id, "starter")
