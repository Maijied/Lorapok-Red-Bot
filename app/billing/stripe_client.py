"""Stripe API client — customer, subscription, and billing portal operations."""

from __future__ import annotations

import logging
import os
from typing import Any

log = logging.getLogger(__name__)


def _stripe():
    import stripe as _stripe_lib

    _stripe_lib.api_key = os.getenv("STRIPE_SECRET_KEY", "")
    return _stripe_lib


def create_customer(email: str, name: str) -> str:
    """Create a Stripe customer and return the customer ID."""
    stripe = _stripe()
    customer = stripe.Customer.create(email=email, name=name)
    return customer.id


def create_subscription(customer_id: str, price_id: str) -> str:
    """Create a subscription and return the subscription ID."""
    stripe = _stripe()
    sub = stripe.Subscription.create(
        customer=customer_id,
        items=[{"price": price_id}],
        payment_behavior="default_incomplete",
        expand=["latest_invoice.payment_intent"],
    )
    return sub.id


def cancel_subscription(subscription_id: str) -> bool:
    """Cancel a subscription immediately."""
    try:
        stripe = _stripe()
        stripe.Subscription.cancel(subscription_id)
        return True
    except Exception as exc:
        log.error("Failed to cancel subscription %s: %s", subscription_id, exc)
        return False


def create_portal_session(customer_id: str, return_url: str) -> str:
    """Create a Stripe billing portal session and return the URL."""
    stripe = _stripe()
    session = stripe.billing_portal.Session.create(
        customer=customer_id,
        return_url=return_url,
    )
    return session.url
