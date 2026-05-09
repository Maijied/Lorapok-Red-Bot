# Lorapok Red Bot Architecture
## System Overview
Lorapok Red Bot is built with a decoupled architecture, separating the autonomous worker from the management dashboard.

## Technical Components
- **Autonomous Worker (`app/main.py`):** The primary Reddit listener. It streams content, applies logic, and handles background tasks.
- **Multi-AI Engine (`app/moderation/classifier.py`):** Uses `litellm` to route requests to various LLM providers (OpenAI, Anthropic, Google) based on configuration.
- **Persistence Layer (`app/database.py`):** A PostgreSQL backend managed by SQLAlchemy, storing decisions, review cases, analytics, and GitHub event logs.
- **Management API (`app/dashboard/api.py`):** A FastAPI service providing endpoints for the dashboard UI and moderator controls.
- **Integration Layer (`app/integrations/`):** Modules for GitHub monitoring, Discord alerts, and other external services.

## Runtime Flow
1. **Ingestion:** Worker streams events from Reddit (PRAW).
2. **Analysis:** Logic is applied via rules (deterministic) and AI (probabilistic).
3. **Storage:** Outcomes are recorded in the persistent memory.
4. **Collaboration:** Uncertain cases or new GitHub content are queued for moderator review in the Labs Command Center.
5. **Action:** Approved posts or moderation decisions are executed back to Reddit.

## Infrastructure
- **Containerization:** Fully Dockerized with Compose orchestration.
- **Automation:** APScheduler handles periodic checks and metrics persistence.
- **CI/CD:** GitHub Actions for automated linting and unit tests.
