"""Outbound webhook dispatcher — HMAC-signed, retry-with-backoff delivery."""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
import time
from typing import Any

from sqlalchemy.orm import Session

from app.dashboard.models import WebhookConfig

log = logging.getLogger(__name__)

_VALID_EVENTS = {
    "comment.removed", "submission.removed", "user.banned",
    "modmail.received", "queue.case_added", "flair.assigned",
    "post.published", "health_score.alert", "sentiment.alert",
    "spam_signal.detected",
}
_MAX_RETRIES = 3
_BACKOFF_SECONDS = [2, 4, 8]
_MAX_FAILURES_BEFORE_DEACTIVATE = 10


def register_webhook(
    db: Session,
    tenant_id: str,
    url: str,
    events: list[str],
    secret: str,
) -> WebhookConfig:
    """Register a new outbound webhook endpoint."""
    secret_hash = hashlib.sha256(secret.encode()).hexdigest()
    record = WebhookConfig(
        tenant_id=tenant_id,
        url=url,
        events=[e for e in events if e in _VALID_EVENTS],
        secret_hash=secret_hash,
        is_active=True,
        failure_count=0,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


def list_webhooks(db: Session, tenant_id: str) -> list[dict[str, Any]]:
    records = (
        db.query(WebhookConfig)
        .filter(WebhookConfig.tenant_id == tenant_id)
        .all()
    )
    return [
        {
            "id": r.id,
            "url": r.url,
            "events": r.events,
            "is_active": r.is_active,
            "failure_count": r.failure_count,
            "last_triggered_at": r.last_triggered_at.isoformat() if r.last_triggered_at else None,
        }
        for r in records
    ]


def delete_webhook(db: Session, tenant_id: str, webhook_id: int) -> bool:
    record = (
        db.query(WebhookConfig)
        .filter(WebhookConfig.id == webhook_id, WebhookConfig.tenant_id == tenant_id)
        .first()
    )
    if not record:
        return False
    db.delete(record)
    db.commit()
    return True


def dispatch_event(
    db: Session,
    tenant_id: str,
    event_type: str,
    payload: dict[str, Any],
) -> None:
    """Dispatch *event_type* to all active matching webhooks.  Never raises."""
    try:
        _dispatch(db, tenant_id, event_type, payload)
    except Exception as exc:
        log.error("dispatch_event unexpected error: %s", exc)


def _dispatch(
    db: Session,
    tenant_id: str,
    event_type: str,
    payload: dict[str, Any],
) -> None:
    from datetime import datetime, timezone

    import httpx

    hooks = (
        db.query(WebhookConfig)
        .filter(
            WebhookConfig.tenant_id == tenant_id,
            WebhookConfig.is_active == True,  # noqa: E712
        )
        .all()
    )

    body = json.dumps({"event": event_type, "data": payload}, separators=(",", ":"), sort_keys=True)

    for hook in hooks:
        events: list[str] = hook.events or []
        if event_type not in events:
            continue

        signature = _sign(body, hook.secret_hash)
        headers = {
            "Content-Type": "application/json",
            "X-Lorapok-Signature": f"sha256={signature}",
            "X-Lorapok-Event": event_type,
        }

        delivered = False
        for attempt, backoff in enumerate(_BACKOFF_SECONDS):
            try:
                resp = httpx.post(hook.url, content=body, headers=headers, timeout=10)
                if resp.is_success:
                    delivered = True
                    break
                log.warning(
                    "Webhook %d attempt %d: HTTP %d",
                    hook.id, attempt + 1, resp.status_code,
                )
            except Exception as exc:
                log.warning("Webhook %d attempt %d failed: %s", hook.id, attempt + 1, exc)
            if attempt < len(_BACKOFF_SECONDS) - 1:
                time.sleep(backoff)

        hook.last_triggered_at = datetime.now(timezone.utc)
        if not delivered:
            hook.failure_count = (hook.failure_count or 0) + 1
            if hook.failure_count >= _MAX_FAILURES_BEFORE_DEACTIVATE:
                hook.is_active = False
                log.warning("Webhook %d deactivated after %d failures", hook.id, hook.failure_count)
        else:
            hook.failure_count = 0

        db.commit()


def _sign(body: str, secret_hash: str) -> str:
    """HMAC-SHA256 sign *body* using the stored secret hash as the key."""
    return hmac.new(secret_hash.encode(), body.encode(), hashlib.sha256).hexdigest()
