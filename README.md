# Lorapok Red Bot

**Full-spectrum Reddit automation platform.** AI moderation, community analytics, scheduled content, GitHub & Discord integrations — wrapped in the [Lorapok Design Language](https://lorapok.github.io/).

[![CI](https://github.com/Lorapok/lorapok-red-bot/actions/workflows/ci.yml/badge.svg)](https://github.com/Lorapok/lorapok-red-bot/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://python.org)

---

## What it does

Lorapok Red Bot automates every controllable surface of the Reddit API:

- **AI moderation** — LiteLLM classifier (OpenAI, Anthropic, Gemini, Mistral) with human-in-the-loop review queue
- **Subreddit automation** — settings, flair, wiki, widgets, rules, removal reasons, policy sync
- **Modmail triage** — auto-categorise, auto-reply, SLA tracking, ban appeal workflow
- **User management** — reputation scoring, contributor promotion, onboarding DMs, mod notes
- **Content calendar** — schedule posts, auto-post weekly trending threads from GitHub
- **Analytics** — health score, cohort analysis, sentiment trends, engagement prediction
- **Integrations** — GitHub, Discord, Slack, Telegram, outbound webhooks (Zapier/Make)
- **SaaS billing** — Stripe-backed Free / Starter / Pro / Agency / Enterprise tiers

---

## Quick start (Docker Compose)

```bash
git clone https://github.com/Lorapok/lorapok-red-bot
cd lorapok-red-bot
cp .env.example .env
# Fill in REDDIT_CLIENT_ID, REDDIT_CLIENT_SECRET, REDDIT_USERNAME, REDDIT_PASSWORD
docker compose up --build
```

Dashboard: http://localhost:8000

---

## Deploy free

| Platform | Command |
|---|---|
| Railway | [![Deploy on Railway](https://railway.app/button.svg)](https://railway.app/new/template) |
| Fly.io | `fly deploy` |
| Render | Push to main — `render.yaml` handles the rest |

---

## Configuration

Copy `.env.example` to `.env` and fill in the required values:

```env
# Required
REDDIT_CLIENT_ID=
REDDIT_CLIENT_SECRET=
REDDIT_USERNAME=
REDDIT_PASSWORD=
DATABASE_URL=postgresql://...
REDIS_URL=redis://...

# Set to false in production
DRY_RUN=true
```

See `.env.example` for the full list including Stripe, Slack, Telegram, and white-label settings.

---

## Development

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Run tests
pytest --tb=short

# Lint
ruff check app tests

# Start dashboard
uvicorn app.dashboard.api:app --reload --port 8000

# Start worker (dry_run=true by default)
python -m app.main
```

---

## Architecture

```
Reddit API ──► Worker (main.py) ──► Rule Engine ──► AI Classifier
                    │                                    │
                    ▼                                    ▼
             PostgreSQL DB ◄──── Review Queue ◄──── Human Mods
                    │
                    ▼
             FastAPI Dashboard ──► Stripe Billing ──► Feature Flags
```

Full design: [`.kiro/specs/lorapok-red-bot/design.md`](.kiro/specs/lorapok-red-bot/design.md)

---

## Bot approval statement

- This bot uses human review for all uncertain moderation decisions.
- All automated actions are logged and explainable.
- `DRY_RUN=true` is the default — no live Reddit actions without explicit opt-in.
- The bot uses least-privilege OAuth scopes: `read`, `submit`, `modposts`, `modflair`, `modwiki`, `modmail`.
- The bot does not perform hidden or deceptive actions.

---

## License

MIT — see [LICENSE](LICENSE).

Built by [Lorapok Labs](https://lorapok.github.io/).
