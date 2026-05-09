import os
from datetime import datetime, timedelta, timezone
from typing import Any, List, Optional

import httpx


def _get_headers() -> dict:
    token = os.getenv("GITHUB_TOKEN")
    headers = {"Accept": "application/vnd.github+json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def fetch_latest_release(repo_full_name: str) -> Optional[dict[str, Any]]:
    url = f"https://api.github.com/repos/{repo_full_name}/releases/latest"
    try:
        response = httpx.get(url, headers=_get_headers(), timeout=15)
        if response.status_code == 404:
            return None
        response.raise_for_status()
        data = response.json()
        return {
            "id": str(data.get("id")),
            "name": data.get("name") or data.get("tag_name"),
            "tag_name": data.get("tag_name"),
            "html_url": data.get("html_url"),
            "body": data.get("body"),
            "published_at": data.get("published_at"),
        }
    except Exception:
        return None


def fetch_recent_issues(repo_full_name: str, days_back: int = 1) -> List[dict[str, Any]]:
    since = (datetime.now(timezone.utc) - timedelta(days=days_back)).isoformat()
    url = f"https://api.github.com/repos/{repo_full_name}/issues?since={since}&state=open&sort=created"
    try:
        response = httpx.get(url, headers=_get_headers(), timeout=15)
        response.raise_for_status()
        issues = response.json()
        return [
            {
                "id": str(issue["id"]),
                "title": issue["title"],
                "html_url": issue["html_url"],
                "user": issue["user"]["login"],
                "created_at": issue["created_at"],
            }
            for issue in issues if "pull_request" not in issue # Filter out PRs
        ]
    except Exception:
        return []


def fetch_trending_repos(language: str = "python", days_back: int = 7) -> List[dict[str, Any]]:
    """Fetch repositories created in the last N days sorted by stars."""
    since_date = (datetime.now(timezone.utc) - timedelta(days=days_back)).strftime("%Y-%m-%d")
    query = f"language:{language} created:>{since_date}"
    url = f"https://api.github.com/search/repositories?q={query}&sort=stars&order=desc&per_page=10"

    try:
        response = httpx.get(url, headers=_get_headers(), timeout=15)
        response.raise_for_status()
        items = response.json().get("items", [])
        return [
            {
                "full_name": item["full_name"],
                "description": item["description"],
                "stars": item["stargazers_count"],
                "url": item["html_url"],
            }
            for item in items
        ]
    except Exception:
        return []
