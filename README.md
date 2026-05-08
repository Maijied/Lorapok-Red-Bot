# Lorapok Red Bot
Lorapok Red Bot is a Reddit moderation assistant for all developer communities. It combines rule-based checks, AI-assisted classification, a human review queue, trend post helpers, and integrations for moderator visibility.

## Safety and operating principles
- Assist moderators, do not replace moderators.
- Keep an audit trail of bot decisions.
- Prefer review queue escalation for uncertain cases.
- Use least-privilege credentials and environment-variable based secrets.
- Run in `DRY_RUN=true` by default for safer local testing.

## Current bootstrap scope
This repository currently includes:
- Reddit client setup and startup identity check.
- Comment stream processing loop with retry-safe handling.
- Rule engine + optional AI classifier fallback to review.
- In-memory moderation memory and review queue.
- Discord alert integration stub and GitHub release helper.
- FastAPI dashboard endpoints (`/health`, `/metrics`, `/reviews`).
- Docker and Docker Compose local deployment scaffold.

## Quick start
1. Create and activate a virtual environment.
2. Install dependencies.
3. Configure environment variables.
4. Run in dry-run mode and verify behavior.

```bash path=null start=null
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python3 -m app.main
```

Run dashboard API:

```bash path=null start=null
uvicorn app.dashboard.api:app --reload --host 0.0.0.0 --port 8000
```

## Testing and linting
```bash path=null start=null
python3 -m pytest
ruff check app tests
python3 -m compileall app tests
```

## Local container workflow
```bash path=null start=null
docker compose up --build
```

## Environment configuration
Use `.env.example` as the template for required variables:
- Reddit OAuth credentials
- OpenAI API key
- PostgreSQL + Redis connection URLs
- Discord webhook and GitHub token
- Subreddit name, log level, and dry-run mode

## Policy and architecture docs
- Bot policy: `docs/policy.md`
- Privacy and retention: `docs/privacy.md`
- Architecture overview: `docs/architecture.md`
