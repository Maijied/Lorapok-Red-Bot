import logging

from sqlalchemy.orm import Session

from app.dashboard.models import GithubUpdateTracker, PendingPost
from app.integrations.discord_integration import send_discord_alert
from app.integrations.github_integration import fetch_latest_release, fetch_recent_issues
from app.moderation.classifier import summarize_text

logger = logging.getLogger(__name__)


def monitor_repositories(db: Session, repos: list[str]) -> None:
    """Check for new releases and issues in monitored repos and create pending posts."""
    for repo in repos:
        # 1. Check for Releases
        release = fetch_latest_release(repo)
        if release:
            ext_id = f"release_{release['id']}"
            exists = db.query(GithubUpdateTracker).filter_by(external_id=ext_id).first()
            if not exists:
                logger.info(f"New release detected for {repo}: {release['name']}")

                # Task 9.1: AI Summary
                summary = summarize_text(release.get("body") or "")

                # Track it
                db.add(
                    GithubUpdateTracker(
                        repo_name=repo, update_type="release", external_id=ext_id
                    )
                )

                # Create Pending Post
                title = f"New Release: {repo} {release['name']}"
                body = (
                    f"A new version of **{repo}** has been released!\n\n"
                    f"**Summary:**\n{summary}\n\n"
                    f"[View on GitHub]({release['html_url']})"
                )
                db.add(PendingPost(title=title, body=body, source_url=release["html_url"]))
                db.commit()

                # Task 9.2: Discord Notification
                send_discord_alert(f"🚀 New Draft created for {repo} release: {release['name']}")

        # 2. Check for "Hot" Issues
        issues = fetch_recent_issues(repo, days_back=1)
        for issue in issues[:2]:
            ext_id = f"issue_{issue['id']}"
            exists = db.query(GithubUpdateTracker).filter_by(external_id=ext_id).first()
            if not exists:
                logger.info(f"New issue detected for {repo}: {issue['title']}")
                db.add(
                    GithubUpdateTracker(repo_name=repo, update_type="issue", external_id=ext_id)
                )

                title = f"Community Topic: {repo} - {issue['title']}"
                body = (
                    f"A new interesting discussion has started on **{repo}**:\n\n"
                    f"> {issue['title']}\n\n"
                    f"Opened by **{issue['user']}**.\n\n"
                    f"[Check it out here]({issue['html_url']})"
                )
                db.add(PendingPost(title=title, body=body, source_url=issue["html_url"]))
                db.commit()

                send_discord_alert(f"📝 New Draft created for {repo} issue: {issue['title']}")
