# Lorapok Red Bot — Full Development Plan

## 1) Project Goal
Build **Lorapok Red Bot**, a Reddit assistant for **all developers** that helps with moderation, community onboarding, trending discussion discovery, analytics, integrations, and long-running cloud deployment. The bot should be transparent, rate-limited, human-reviewed for risky actions, and easy to maintain.

## 2) Feature Scope

### Core features
- AI-assisted moderation with human-in-the-loop review.
- Helpful replies for developer questions.
- Auto-posting trending threads.
- Dashboard for subreddit growth.
- Memory system that learns from past mod decisions.
- GitHub + Discord integrations.
- Cloud deployment so it runs 24/7.

### Operating principles
- Assist moderators; do not replace them.
- Keep an audit trail for all bot actions.
- Use least-privilege API scopes.
- Make every automated action explainable.
- Prefer review queues over instant bans for ambiguous cases.

---

## 3) Task-Subtask Development Plan

## Phase 1 — Product Definition and Safety

### Task 1.1 — Define bot policy
Subtasks:
- Write bot purpose statement.
- Define allowed content types.
- Define disallowed content types.
- Define escalation rules for uncertain cases.
- Define mod override process.

### Task 1.2 — Define subreddits and permissions
Subtasks:
- List target subreddits.
- Decide whether one bot account or one per subreddit.
- Determine required OAuth scopes.
- Set moderation permissions for the bot account.

### Task 1.3 — Define data retention and privacy
Subtasks:
- Decide what data is stored.
- Decide retention period for logs.
- Decide whether to store deleted content snippets.
- Define how users can request review or correction.

---

## Phase 2 — Repo and Project Setup

### Task 2.1 — Create repository
Subtasks:
- Create public GitHub repo named `lorapok-red-bot`.
- Add README, license, and `.gitignore`.
- Add issue templates for bugs and feature requests.

### Task 2.2 — Set up Python project
Subtasks:
- Create virtual environment.
- Add dependencies.
- Define config and secrets management.
- Establish linting and formatting.

### Task 2.3 — Set up local development workflow
Subtasks:
- Create `.env.example`.
- Add a dry-run mode.
- Add logging configuration.
- Add a test subreddit for safe testing.

---

## Phase 3 — Reddit Core Bot

### Task 3.1 — Reddit client module
Subtasks:
- Build authenticated Reddit client.
- Verify identity on startup.
- Add helper methods for reading comments, posts, modlog, and modmail.

### Task 3.2 — Stream processor
Subtasks:
- Listen to new comments.
- Listen to new submissions.
- Prevent duplicate processing.
- Add retry logic for API failures.

### Task 3.3 — Rule engine
Subtasks:
- Create keyword and regex filters.
- Add content classification.
- Add a moderation decision object.
- Route low-risk actions automatically.
- Route medium/high-risk actions to human review.

### Task 3.4 — Response engine
Subtasks:
- Generate helpful replies.
- Detect when no reply is needed.
- Prevent spammy repeated replies.
- Add bot signature/footer.

---

## Phase 4 — AI Moderation and Assistant Features

### Task 4.1 — AI moderation classifier
Subtasks:
- Create prompt for content classification.
- Return structured JSON decisions.
- Include confidence score.
- Include reason and recommended action.

### Task 4.2 — AI reply generator
Subtasks:
- Create prompt for developer help.
- Make responses short and practical.
- Include request for code snippets when needed.
- Avoid hallucinated certainty.

### Task 4.3 — Human-in-the-loop review queue
Subtasks:
- Store uncertain cases in a queue.
- Expose queue in a dashboard.
- Allow approve/reject/escalate actions.
- Keep timestamps and mod notes.

---

## Phase 5 — Auto-Posting Trending Threads

### Task 5.1 — Trending source discovery
Subtasks:
- Pull trends from GitHub repositories.
- Pull trends from subreddit post activity.
- Pull trends from developer news sources.
- Pull trends from approved RSS feeds.

### Task 5.2 — Trend ranking engine
Subtasks:
- Score candidate topics by popularity.
- Filter low-quality or duplicate ideas.
- Avoid posting the same topic repeatedly.
- Respect subreddit rules and posting frequency.

### Task 5.3 — Scheduled post publisher
Subtasks:
- Create weekly discussion thread templates.
- Auto-post with title and body templates.
- Add flair automatically.
- Log every scheduled post.

---

## Phase 6 — Memory System

### Task 6.1 — Decision memory schema
Subtasks:
- Store message text hash.
- Store action taken.
- Store moderator decision.
- Store reason codes.
- Store outcome for future learning.

### Task 6.2 — Similarity search
Subtasks:
- Search prior cases by semantic similarity.
- Suggest previous mod decisions on similar content.
- Show confidence and supporting examples.

### Task 6.3 — Learning loop
Subtasks:
- Record when moderators override the bot.
- Convert overrides into training signals.
- Update rules or prompts from observed mistakes.
- Keep learning bounded and reviewable.

---

## Phase 7 — Dashboard and Analytics

### Task 7.1 — Backend analytics API
Subtasks:
- Expose metrics endpoints.
- Aggregate daily post volume.
- Aggregate comments, reports, removals, approvals.
- Track bot actions and confidence.

### Task 7.2 — Frontend dashboard
Subtasks:
- Build overview page.
- Show growth charts.
- Show moderation queue.
- Show trending topics.
- Show integration status.

### Task 7.3 — Moderator controls
Subtasks:
- Approve/reject queued cases.
- Re-run classification.
- Add notes to cases.
- Export logs.

---

## Phase 8 — GitHub Integration

### Task 8.1 — Repository monitoring
Subtasks:
- Watch approved repositories.
- Detect new releases.
- Detect new issues or pull requests.
- Convert selected updates into subreddit posts.

### Task 8.2 — Developer activity summaries
Subtasks:
- Summarize important repo changes.
- Create community-friendly post drafts.
- Let moderators approve before posting.

---

## Phase 9 — Discord Integration

### Task 9.1 — Discord bot connection
Subtasks:
- Connect a Discord bot account.
- Post subreddit announcements to Discord.
- Relay mod alerts to a private Discord channel.

### Task 9.2 — Cross-platform notification workflow
Subtasks:
- Notify mods when queue is high.
- Notify on failed scheduled posts.
- Notify on suspicious spam bursts.

---

## Phase 10 — Cloud Deployment and Operations

### Task 10.1 — Containerization
Subtasks:
- Write Dockerfile.
- Add environment variable support.
- Verify startup command.
- Separate app, worker, and dashboard services if needed.

### Task 10.2 — Hosting
Subtasks:
- Deploy to a cloud provider.
- Configure always-on process.
- Add restart policy.
- Protect secrets with managed environment variables.

### Task 10.3 — Observability
Subtasks:
- Add structured logs.
- Add error alerts.
- Add uptime checks.
- Add action audit records.

---

## Phase 11 — Testing and Approval Readiness

### Task 11.1 — Functional testing
Subtasks:
- Test comment replies.
- Test moderation classification.
- Test scheduled posts.
- Test GitHub and Discord notifications.

### Task 11.2 — Safety testing
Subtasks:
- Test against spam.
- Test against ambiguous content.
- Test manual override.
- Test duplicate suppression.

### Task 11.3 — Approval package
Subtasks:
- Publish repo.
- Write accurate README.
- Provide architecture diagram.
- Provide example use cases.
- Provide bot account info and subreddit scope.

---

## 4) Suggested Tech Stack
- **Python** for bot logic.
- **PRAW** for Reddit API access.
- **OpenAI API** for classification and replies.
- **FastAPI** for dashboard and webhook endpoints.
- **PostgreSQL** for persistent storage.
- **Redis** for queueing and rate control.
- **Celery or APScheduler** for scheduled jobs.
- **Docker** for deployment.
- **GitHub API** and **Discord webhooks/bot API** for integrations.

---

## 5) Recommended Repository Structure

```text
lorapok-red-bot/
├─ app/
│  ├─ main.py
│  ├─ reddit_client.py
│  ├─ moderation/
│  │  ├─ classifier.py
│  │  ├─ rules.py
│  │  ├─ queue.py
│  │  └─ memory.py
│  ├─ posting/
│  │  ├─ trending.py
│  │  └─ scheduler.py
│  ├─ integrations/
│  │  ├─ github_integration.py
│  │  └─ discord_integration.py
│  ├─ dashboard/
│  │  ├─ api.py
│  │  └─ metrics.py
│  └─ utils/
│     ├─ logging.py
│     ├─ rate_limit.py
│     └─ text.py
├─ tests/
├─ docs/
├─ Dockerfile
├─ docker-compose.yml
├─ requirements.txt
├─ .env.example
└─ README.md
```

---

## 6) Code Starter Pack

### 6.1 requirements.txt
```txt
praw
openai
python-dotenv
fastapi
uvicorn
sqlalchemy
psycopg2-binary
redis
httpx
apscheduler
pydantic
```

### 6.2 .env.example
```env
REDDIT_CLIENT_ID=
REDDIT_CLIENT_SECRET=
REDDIT_USERNAME=
REDDIT_PASSWORD=
REDDIT_USER_AGENT=LorapokRedBot/1.0
OPENAI_API_KEY=
DATABASE_URL=postgresql://user:pass@localhost:5432/lorapok_red_bot
REDIS_URL=redis://localhost:6379/0
DISCORD_WEBHOOK_URL=
GITHUB_TOKEN=
SUBREDDIT_NAME=all
```

### 6.3 app/reddit_client.py
```python
import os
import praw
from dotenv import load_dotenv

load_dotenv()


def get_reddit() -> praw.Reddit:
    reddit = praw.Reddit(
        client_id=os.getenv("REDDIT_CLIENT_ID"),
        client_secret=os.getenv("REDDIT_CLIENT_SECRET"),
        username=os.getenv("REDDIT_USERNAME"),
        password=os.getenv("REDDIT_PASSWORD"),
        user_agent=os.getenv("REDDIT_USER_AGENT", "LorapokRedBot/1.0"),
    )
    _ = reddit.user.me()
    return reddit
```

### 6.4 app/moderation/classifier.py
```python
import json
import os
from openai import OpenAI

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def classify_text(text: str) -> dict:
    prompt = f"""
You are a Reddit moderation assistant for developer communities.
Return JSON with keys: action, reason, confidence.
Allowed actions: allow, review, remove.
Content: {text}
"""
    response = client.responses.create(
        model="gpt-4.1-mini",
        input=prompt,
    )
    raw = response.output_text.strip()
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {
            "action": "review",
            "reason": "Model output was not valid JSON.",
            "confidence": 0.0,
        }
```

### 6.5 app/moderation/rules.py
```python
from dataclasses import dataclass

@dataclass
class ModerationDecision:
    action: str
    reason: str
    confidence: float


def apply_light_rules(text: str) -> ModerationDecision:
    lowered = text.lower()
    spam_terms = ["free money", "buy now", "crypto pump", "visit my site"]
    if any(term in lowered for term in spam_terms):
        return ModerationDecision("remove", "Possible spam or promotion.", 0.95)
    return ModerationDecision("allow", "No obvious issue found.", 0.60)
```

### 6.6 app/moderation/memory.py
```python
from datetime import datetime

MEMORY = []


def remember_case(text: str, action: str, reason: str, source: str) -> None:
    MEMORY.append({
        "text": text,
        "action": action,
        "reason": reason,
        "source": source,
        "created_at": datetime.utcnow().isoformat(),
    })


def recent_cases(limit: int = 20):
    return MEMORY[-limit:]
```

### 6.7 app/posting/trending.py
```python
from datetime import datetime


def build_trending_thread(trends: list[str]) -> dict:
    title = f"Weekly Developer Trends — {datetime.utcnow().strftime('%Y-%m-%d')}"
    body = "\n".join([f"- {item}" for item in trends])
    return {"title": title, "body": body}
```

### 6.8 app/integrations/discord_integration.py
```python
import os
import httpx


def send_discord_alert(message: str) -> None:
    url = os.getenv("DISCORD_WEBHOOK_URL")
    if not url:
        return
    httpx.post(url, json={"content": message}, timeout=10)
```

### 6.9 app/main.py
```python
import os
import time
from app.reddit_client import get_reddit
from app.moderation.rules import apply_light_rules
from app.moderation.memory import remember_case
from app.integrations.discord_integration import send_discord_alert

SUBREDDIT = os.getenv("SUBREDDIT_NAME", "all")


def main() -> None:
    reddit = get_reddit()
    subreddit = reddit.subreddit(SUBREDDIT)
    send_discord_alert(f"Lorapok Red Bot started in r/{SUBREDDIT}.")

    for comment in subreddit.stream.comments(skip_existing=True):
        try:
            decision = apply_light_rules(comment.body)
            remember_case(comment.body, decision.action, decision.reason, "rules")

            if decision.action == "remove":
                comment.mod.remove()
                comment.reply(
                    "Your comment was removed by Lorapok Red Bot because it appears to violate community rules. "
                    "If you think this was a mistake, please contact the moderators."
                )
            elif "help" in comment.body.lower():
                comment.reply(
                    "Hi! Please include the code, error message, and what you expected. That makes it easier for the community to help."
                )

            time.sleep(2)
        except Exception as exc:
            send_discord_alert(f"Lorapok Red Bot error: {exc}")
            time.sleep(5)


if __name__ == "__main__":
    main()
```

### 6.10 app/dashboard/api.py
```python
from fastapi import FastAPI

app = FastAPI(title="Lorapok Red Bot Dashboard")


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/metrics")
def metrics():
    return {
        "posts_processed": 0,
        "comments_processed": 0,
        "queued_reviews": 0,
        "actions_taken": 0,
    }
```

---

## 7) Deployment Plan

### Task 7.1 — Container setup
Subtasks:
- Add Dockerfile.
- Add Docker Compose for local dev.
- Separate dashboard from worker if needed.

### Task 7.2 — Cloud deployment
Subtasks:
- Choose a provider with always-on support.
- Store secrets in environment variables.
- Deploy worker and dashboard.
- Configure automatic restarts.

### Task 7.3 — Monitoring
Subtasks:
- Add uptime monitor.
- Add error alerts.
- Add daily health checks.
- Add scheduled backups.

---

## 8) Approval-Focused README Points
Include these statements in the public repo:
- This bot supports all developers, not just one niche community.
- The bot uses human review for uncertain moderation decisions.
- The bot is transparent about automated actions.
- The bot respects Reddit rate limits and API policies.
- The bot does not perform hidden or deceptive actions.

---

## 9) Milestone Checklist
- [ ] Repo created and public.
- [ ] README written.
- [ ] Reddit OAuth app configured.
- [ ] Core bot running locally.
- [ ] AI classifier working.
- [ ] Memory storage enabled.
- [ ] Trending thread scheduler working.
- [ ] Dashboard online.
- [ ] GitHub integration working.
- [ ] Discord alerts working.
- [ ] Cloud deployment active.
- [ ] Logs and backups verified.
- [ ] Approval submission ready.

---

## 10) Next Build Order
1. Build Reddit client and comment stream.
2. Add moderation rule engine.
3. Add AI classifier.
4. Add memory and review queue.
5. Add trending-post scheduler.
6. Add dashboard metrics.
7. Add GitHub and Discord integrations.
8. Deploy to cloud.
9. Prepare approval documentation.

---

## 11) Deliverable Summary
Lorapok Red Bot should end as:
- a Reddit moderation assistant,
- a developer community helper,
- a scheduled content publisher,
- a metrics dashboard provider,
- and a 24/7 cloud service with logs, memory, and integrations.

