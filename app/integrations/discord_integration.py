import logging
import os

import httpx

logger = logging.getLogger(__name__)


def send_discord_alert(message: str) -> None:
    url = os.getenv("DISCORD_WEBHOOK_URL")
    if not url:
        return
    try:
        response = httpx.post(url, json={"content": message}, timeout=10)
        response.raise_for_status()
    except Exception as exc:
        logger.warning("Failed to send Discord alert: %s", exc)
