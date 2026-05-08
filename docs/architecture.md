# Lorapok Red Bot architecture overview
## Runtime flow
1. Worker starts in `app/main.py`, loads settings, initializes logging, and authenticates Reddit.
2. Comment stream events are processed through `app/moderation/rules.py`.
3. Ambiguous items are passed to `app/moderation/classifier.py`.
4. Low-confidence outcomes are stored in `app/moderation/queue.py` for human review.
5. Finalized decisions are recorded in `app/moderation/memory.py`.
6. Metrics are tracked via `app/dashboard/metrics.py` and surfaced through `app/dashboard/api.py`.

## Major subsystem boundaries
- **Core moderation domain**: `app/moderation/*` for decisioning, queueing, and memory.
- **External IO/integrations**: `app/reddit_client.py`, `app/integrations/*`.
- **Operational infrastructure**: `app/utils/*` for logging, rate control, text utilities.
- **Posting/scheduling**: `app/posting/*` for trend thread construction and scheduled publishing hooks.
- **API surface**: `app/dashboard/api.py` exposes observability and review context.

## Entrypoints
- Worker bot: `python3 -m app.main`
- Dashboard API: `uvicorn app.dashboard.api:app --reload --host 0.0.0.0 --port 8000`
- Container orchestration: `docker compose up --build`
