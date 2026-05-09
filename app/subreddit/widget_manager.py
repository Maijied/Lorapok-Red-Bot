"""Sidebar widget manager — create, update, and remove subreddit widgets."""

from __future__ import annotations

import logging
from typing import Any

log = logging.getLogger(__name__)


def list_widgets(reddit: Any, subreddit_name: str) -> list[dict]:
    try:
        widgets = reddit.subreddit(subreddit_name).widgets
        result = []
        for w in widgets.sidebar:
            result.append({"id": w.id, "kind": w.kind, "shortName": getattr(w, "shortName", "")})
        return result
    except Exception as exc:
        log.error("Could not list widgets for r/%s: %s", subreddit_name, exc)
        return []


def update_text_widget(
    reddit: Any, subreddit_name: str, widget_id: str, text: str, dry_run: bool = True
) -> bool:
    if dry_run:
        log.info("DRY_RUN update_text_widget r/%s widget=%s", subreddit_name, widget_id)
        return True
    try:
        widgets = reddit.subreddit(subreddit_name).widgets
        for w in widgets.sidebar:
            if w.id == widget_id:
                w.mod.update(text=text)
                return True
        log.warning("Widget %s not found in r/%s", widget_id, subreddit_name)
        return False
    except Exception as exc:
        log.error("Failed to update widget %s: %s", widget_id, exc)
        return False


def update_community_stats_widget(
    reddit: Any, subreddit_name: str, db: Any, dry_run: bool = True
) -> bool:
    """Refresh the community stats text widget with current subscriber count."""
    try:
        sub = reddit.subreddit(subreddit_name)
        sub._fetch()
        count = sub.subscribers
        text = f"**{count:,}** members"
        widgets = sub.widgets
        for w in widgets.sidebar:
            if getattr(w, "kind", "") == "id-card":
                return True  # native id-card widget, no update needed
            if "stats" in getattr(w, "shortName", "").lower():
                return update_text_widget(reddit, subreddit_name, w.id, text, dry_run)
        return False
    except Exception as exc:
        log.error("Failed to update community stats widget: %s", exc)
        return False


def add_button_widget(
    reddit: Any, subreddit_name: str, text: str, url: str, dry_run: bool = True
) -> str:
    if dry_run:
        log.info("DRY_RUN add_button_widget r/%s: %s → %s", subreddit_name, text, url)
        return "dry_run_id"
    try:
        widgets = reddit.subreddit(subreddit_name).widgets
        new_widget = widgets.mod.add_button_widget(
            short_name=text[:30],
            description="",
            buttons=[{
                "kind": "text", "text": text, "url": url,
                "color": "#FF4500", "textColor": "#FFFFFF",
                "fillColor": "#FF4500",
            }],
        )
        return new_widget.id
    except Exception as exc:
        log.error("Failed to add button widget: %s", exc)
        return ""


def remove_widget(
    reddit: Any, subreddit_name: str, widget_id: str, dry_run: bool = True
) -> bool:
    if dry_run:
        log.info("DRY_RUN remove_widget r/%s widget=%s", subreddit_name, widget_id)
        return True
    try:
        widgets = reddit.subreddit(subreddit_name).widgets
        for w in widgets.sidebar:
            if w.id == widget_id:
                w.mod.delete()
                return True
        return False
    except Exception as exc:
        log.error("Failed to remove widget %s: %s", widget_id, exc)
        return False
