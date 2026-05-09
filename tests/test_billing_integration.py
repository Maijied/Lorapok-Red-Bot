"""Integration tests for billing feature flags and webhook dispatcher."""

from app.billing.features import has_feature
from app.billing.tenant import get_or_create_tenant, update_tenant_tier
from app.integrations.webhooks import dispatch_event, register_webhook


def test_feature_gate_free_to_pro_upgrade(db):
    tenant = get_or_create_tenant(db, "upgradeuser")
    assert has_feature(db, tenant.tenant_id, "advanced_analytics") is False

    update_tenant_tier(db, tenant.tenant_id, "pro")
    assert has_feature(db, tenant.tenant_id, "advanced_analytics") is True


def test_webhook_dispatch_no_raise_on_unreachable(db):
    """dispatch_event must never raise even when the URL is unreachable."""
    register_webhook(db, "default", "http://localhost:19999/unreachable", ["comment.removed"], "secret123")
    # Should complete without raising
    dispatch_event(db, "default", "comment.removed", {"id": "abc", "reason": "spam"})


def test_webhook_dispatch_only_matching_events(db):
    """Webhook registered for comment.removed should not fire on user.banned."""
    register_webhook(db, "default", "http://localhost:19999/hook2", ["comment.removed"], "secret456")
    # No exception, no delivery attempt for non-matching event
    dispatch_event(db, "default", "user.banned", {"username": "spammer"})


def test_webhook_hmac_signature_present(db, monkeypatch):
    """Verify HMAC signature header is included in outbound requests."""
    captured = {}

    def fake_post(url, content, headers, timeout):
        captured["headers"] = headers

        class FakeResp:
            status_code = 200
            def is_success(self): return True
            is_success = property(lambda self: True)

        return FakeResp()

    import httpx
    monkeypatch.setattr(httpx, "post", fake_post)

    register_webhook(db, "default", "http://example.com/hook", ["post.published"], "mysecret")
    dispatch_event(db, "default", "post.published", {"title": "Test"})

    assert "X-Lorapok-Signature" in captured.get("headers", {})
    assert captured["headers"]["X-Lorapok-Signature"].startswith("sha256=")
