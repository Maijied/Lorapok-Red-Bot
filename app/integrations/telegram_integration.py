"""Telegram integration — bot alerts and command handler."""

from __future__ import annotations

import logging
import os
from typing import Any

log = logging.getLogger(__name__)

_TELEGRAM_API = "https://api.telegram.org/bot{token}/sendMessage"


def send_telegram_message(chat_id: str, message: str) -> None:
    """Send *message* to *chat_id* via the Telegram Bot API.  No-ops if token not set."""
    token = os.getenv("TELEGRAM_BOT_TOKEN", "")
    if not token or not chat_id:
        return
    try:
        import httpx

        url = _TELEGRAM_API.format(token=token)
        httpx.post(
            url,
            json={"chat_id": chat_id, "text": message, "parse_mode": "Markdown"},
            timeout=10,
        )
    except Exception as exc:
        log.warning("Telegram message failed: %s", exc)


def handle_telegram_command(
    update: dict[str, Any],
    reddit: Any,
    db: Any,
    settings: Any,
) -> None:
    """Route a Telegram bot command update."""
    message = update.get("message", {})
    chat_id = str(message.get("chat", {}).get("id", ""))
    text = str(message.get("text", "")).strip()

    if not chat_id or not text.startswith("/"):
        return

    parts = text.lstrip("/").split()
    command = parts[0].lower() if parts else ""
    args = parts[1:]

    if command == "queue":
        from app.moderation.queue import list_queue

        cases = list_queue(
            db, status="pending",
            tenant_id=getattr(settings, "tenant_id", "default"),
        )
        reply = f"*{len(cases)} pending case(s)*" if cases else "✅ Queue is empty."
        send_telegram_message(chat_id, reply)

    elif command in ("approve", "reject") and args:
        from app.moderation.queue import resolve_case

        status = "approved" if command == "approve" else "rejected"
        ok = resolve_case(db, args[0], status, tenant_id=getattr(settings, "tenant_id", "default"))
        reply = f"✅ Case {args[0]} {status}." if ok else f"❌ Could not {command} case {args[0]}."
        send_telegram_message(chat_id, reply)

    elif command == "stats":
        from app.dashboard.metrics import metrics_store

        snap = metrics_store.snapshot()
        reply = (
            f"📊 *Bot Stats*\n"
            f"Comments: {snap.get('comments_processed', 0)}\n"
            f"Actions: {snap.get('actions_taken', 0)}\n"
            f"Queued: {snap.get('queued_reviews', 0)}"
        )
        send_telegram_message(chat_id, reply)

    elif command == "health":
        send_telegram_message(chat_id, "🟢 Lorapok Red Bot is running.")

    else:
        send_telegram_message(chat_id, "Commands: /queue /approve <id> /reject <id> /stats /health")
