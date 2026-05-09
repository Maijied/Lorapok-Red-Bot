# How to Use Lorapok Red Bot

## Prerequisites

- Python 3.11+
- PostgreSQL 14+ (or use Docker Compose)
- Redis 7+ (or use Docker Compose)
- A Reddit account with a [script app](https://www.reddit.com/prefs/apps) created
- At least one LLM API key (OpenAI, Anthropic, Gemini, or Mistral)

---

## 1. Local Setup

```bash
git clone https://github.com/Lorapok/lorapok-red-bot
cd lorapok-red-bot
cp .env.example .env
```

Edit `.env` with your credentials:

```env
REDDIT_CLIENT_ID=your_client_id
REDDIT_CLIENT_SECRET=your_client_secret
REDDIT_USERNAME=your_bot_username
REDDIT_PASSWORD=your_bot_password
OPENAI_API_KEY=sk-...
DATABASE_URL=postgresql://user:pass@localhost:5432/lorapok_red_bot
REDIS_URL=redis://localhost:6379/0
SUBREDDIT_NAMES=your_subreddit
DRY_RUN=true   # set to false when ready for live actions
```

### Option A — Docker Compose (recommended)

```bash
docker compose up --build
```

This starts PostgreSQL, Redis, the bot worker, and the dashboard at http://localhost:8000.

### Option B — Manual

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Run migrations
alembic upgrade head

# Start dashboard
uvicorn app.dashboard.api:app --reload --port 8000

# Start worker (in a separate terminal)
python -m app.main
```

---

## 2. Reddit App Setup

1. Go to https://www.reddit.com/prefs/apps
2. Click "create another app"
3. Select **script**
4. Set redirect URI to `http://localhost:8080`
5. Copy the client ID (under the app name) and client secret
6. Add the bot account as a moderator of your subreddit with these permissions:
   - `posts` — approve/remove posts
   - `flair` — manage flair
   - `wiki` — edit wiki
   - `mail` — read/reply to modmail
   - `config` — update subreddit settings (optional)

---

## 3. Dashboard

Open http://localhost:8000 to access the moderator dashboard.

Key sections:
- **Metrics** — live comment/action counters
- **Queue** — pending human review cases (approve/reject)
- **Memory** — full decision audit trail
- **Modmail** — open modmail conversations with SLA tracking
- **Scheduled Posts** — content calendar
- **Billing** — subscription tier and Stripe portal

---

## 4. Configuration Reference

All settings are loaded from environment variables. See `.env.example` for the full list.

### Key settings

| Variable | Default | Description |
|---|---|---|
| `DRY_RUN` | `true` | Set to `false` to enable live Reddit actions |
| `SUBREDDIT_NAMES` | `all` | Comma-separated subreddits to manage |
| `AI_MODEL` | `openai/gpt-4o-mini` | LiteLLM model string |
| `REVIEW_CONFIDENCE_THRESHOLD` | `0.75` | Below this → human review queue |
| `TENANT_ID` | `default` | Unique ID for this deployment |

---

## 5. Enabling Features by Tier

Features are gated by subscription tier. To unlock Pro features locally, update the tenant record:

```python
from app.billing.tenant import get_or_create_tenant, update_tenant_tier
from app.database import get_engine, get_session_factory
from app.config import Settings

settings = Settings.from_env()
engine = get_engine(settings.database_url)
db = get_session_factory(engine)()
tenant = get_or_create_tenant(db, settings.reddit_username)
update_tenant_tier(db, tenant.tenant_id, "pro")
```

---

## 6. Running Tests

```bash
pytest --tb=short
ruff check app tests
```

---

## 7. Deploying to Production

See `docs/architecture.md` for deployment options (Railway, Render, Fly.io).

**Before going live:**
1. Set `DRY_RUN=false` in your deployment environment
2. Verify the bot account has the correct moderator permissions
3. Test with a low-traffic subreddit first
4. Monitor the dashboard queue for the first 24 hours
