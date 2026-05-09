"""Unified notification helper — fans out alerts to all configured channels.

Channels: Discord, Slack, Telegram.  Any channel whose URL/token is not
configured is silently skipped.  Never raises to the caller.
"""

from __future__ import annotations

import logging
from typing import Any

log = logging.getLogger(__name__)


def send_alert_sync(message: str, settings: Any) -> None:
    """Send *message* to every configured notification channel (synchronous)."""
    _try_discord(message, settings)
    _try_slack(message, settings)
    _try_telegram(message, settings)


def _try_discord(message: str, settings: Any) -> None:
    url = getattr(settings, "discord_webhook_url", "") or ""
    if not url:
        return
    try:
        from app.integrations.discord_integration import send_discord_alert

        send_discord_alert(message)
    except Exception as exc:
        log.warning("Discord alert failed: %s", exc)


def _try_slack(message: str, settings: Any) -> None:
    url = getattr(settings, "slack_webhook_url", "") or ""
    if not url:
        return
    try:
        from app.integrations.slack_integration import send_slack_alert

        send_slack_alert(message)
    except Exception as exc:
        log.warning("Slack alert failed: %s", exc)


def _try_telegram(message: str, settings: Any) -> None:
    token = getattr(settings, "telegram_bot_token", "") or ""
    chat_id = getattr(settings, "telegram_chat_id", "") or ""
    if not token or not chat_id:
        return
    try:
        from app.integrations.telegram_integration import send_telegram_message

        send_telegram_message(chat_id, message)
    except Exception as exc:
        log.warning("Telegram alert failed: %s", exc)
