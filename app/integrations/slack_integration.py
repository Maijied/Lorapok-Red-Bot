"""Slack integration — webhook alerts and slash command handler."""

from __future__ import annotations

import logging
import os
from typing import Any

log = logging.getLogger(__name__)


def send_slack_alert(message: str, channel: str | None = None) -> None:
    """POST *message* to the configured Slack webhook.  No-ops if URL not set."""
    url = os.getenv("SLACK_WEBHOOK_URL", "")
    if not url:
        return
    try:
        import httpx

        payload: dict[str, Any] = {"text": message}
        if channel:
            payload["channel"] = channel
        httpx.post(url, json=payload, timeout=10)
    except Exception as exc:
        log.warning("Slack alert failed: %s", exc)


def handle_slack_slash_command(
    payload: dict[str, Any],
    reddit: Any,
    db: Any,
    settings: Any,
) -> str:
    """Route a Slack slash command and return a response string."""
    text = str(payload.get("text", "")).strip()
    parts = text.split()
    command = parts[0].lower() if parts else ""
    args = parts[1:]

    if command == "queue":
        from app.moderation.queue import list_queue

        cases = list_queue(
            db, status="pending",
            tenant_id=getattr(settings, "tenant_id", "default"),
        )
        if not cases:
            return "✅ Review queue is empty."
        lines = [f"*{len(cases)} pending case(s):*"]
        for c in cases[:5]:
            lines.append(f"• `{c['case_id']}` — {c['reason'][:60]}")
        return "\n".join(lines)

    if command == "approve" and args:
        from app.moderation.queue import resolve_case

        ok = resolve_case(
            db, args[0], "approved",
            tenant_id=getattr(settings, "tenant_id", "default"),
        )
        return f"✅ Case {args[0]} approved." if ok else f"❌ Could not approve case {args[0]}."

    if command == "reject" and args:
        from app.moderation.queue import resolve_case

        ok = resolve_case(
            db, args[0], "rejected",
            tenant_id=getattr(settings, "tenant_id", "default"),
        )
        return f"✅ Case {args[0]} rejected." if ok else f"❌ Could not reject case {args[0]}."

    if command == "stats":
        from app.dashboard.metrics import metrics_store

        snap = metrics_store.snapshot()
        return (
            f"📊 *Bot Stats*\n"
            f"• Comments processed: {snap.get('comments_processed', 0)}\n"
            f"• Actions taken: {snap.get('actions_taken', 0)}\n"
            f"• Queued reviews: {snap.get('queued_reviews', 0)}\n"
            f"• Posts published: {snap.get('posts_processed', 0)}"
        )

    if command == "health":
        return "🟢 Lorapok Red Bot is running."

    return f"Unknown command: `{command}`. Try: queue, approve <id>, reject <id>, stats, health"
