# AGENTS.md
This file provides guidance to WARP (warp.dev) when working with code in this repository.

## Repository Status
This worktree now contains a Python bootstrap implementation for Lorapok Red Bot with:
- core application modules under `app/`
- tests under `tests/`
- deployment scaffold (`Dockerfile`, `docker-compose.yml`)
- project config files (`requirements.txt`, `pyproject.toml`, `.env.example`)
- policy and architecture docs under `docs/`

## Build, Lint, and Test Commands
Use these commands based on checked-in files:

Setup:
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Run tests:
```bash
python3 -m pytest
```

Lint:
```bash
ruff check app tests
```

Syntax sanity check:
```bash
python3 -m compileall app tests
```

Run services:
```bash
python3 -m app.main
uvicorn app.dashboard.api:app --reload --host 0.0.0.0 --port 8000
docker compose up --build
```

## Architecture Overview
High-level runtime flow:
1. `app/main.py` is the worker entrypoint that loads settings, initializes logging, authenticates Reddit, streams comments, and routes moderation actions.
2. `app/moderation/rules.py` performs lightweight deterministic moderation checks.
3. `app/moderation/classifier.py` performs AI classification for uncertain cases.
4. `app/moderation/queue.py` stores human-review cases and `app/moderation/memory.py` stores action history.
5. `app/dashboard/api.py` exposes health, metrics, review queue, and memory endpoints for moderator visibility.

Boundaries:
- Core decisioning logic is in `app/moderation/*`.
- External side effects are in integration modules (`app/reddit_client.py`, `app/integrations/*`).
- Operational concerns (logging, throttling, text normalization) are in `app/utils/*`.
- Posting helpers and scheduling live in `app/posting/*`.
