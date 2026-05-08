import os
from typing import Any

import httpx


def fetch_latest_release(repo_full_name: str) -> dict[str, Any] | None:
    token = os.getenv("GITHUB_TOKEN")
    headers = {"Accept": "application/vnd.github+json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    url = f"https://api.github.com/repos/{repo_full_name}/releases/latest"
    response = httpx.get(url, headers=headers, timeout=15)
    if response.status_code == 404:
        return None
    response.raise_for_status()
    data = response.json()
    return {
        "name": data.get("name"),
        "tag_name": data.get("tag_name"),
        "html_url": data.get("html_url"),
        "published_at": data.get("published_at"),
    }
