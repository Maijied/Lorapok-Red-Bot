# How to Use Lorapok Red Bot
## 1. Quick Start
Lorapok Red Bot is designed for automated community management and content discovery.

- **Multi-AI Moderation:** Real-time comment filtering using rules and LLMs.
- **Labs Command Center:** A high-end, professional moderator dashboard with real-time stats and growth tracking.
- **Content Discovery:** Automatic monitoring of GitHub trends with one-click publishing.

## 2. Local Setup
1. **Configure Environment:** Copy `.env.example` to `.env` and fill in your Reddit API credentials, AI provider keys (e.g., OpenAI, Anthropic), and Discord webhook URL.
2. **Launch with Docker:**
   ```bash
   docker-compose up --build
   ```
3. **Database Migrations:** The system automatically initializes the schema on first run.

## 3. Configuration
- `SUBREDDIT_NAME`: Target subreddit.
- `AI_MODEL`: Multi-AI engine selection (e.g., `openai/gpt-4o-mini`, `anthropic/claude-3-haiku`).
- `DRY_RUN`: Set to `True` for testing without taking actual actions on Reddit.

## 4. Components
- `bot`: The main Reddit worker.
- `dashboard`: Labs Command Center UI (Port 8000).
- `postgres`: Analytics and queue storage.
- `redis`: Rate limiting and temporary state.

## 5. Using the Command Center
The **Labs Command Center** is accessible at:
`http://localhost:8000`

- **Overview:** Monitor processed comments and automated actions.
- **Review Queue:** Manually approve or reject comments that the AI flagged as uncertain.
- **Content Drafts:** Review fetched GitHub repositories and publish them to your subreddit.

## 6. Development
- **Testing:**
  ```bash
  pytest tests/
  ```
- **Linting:**
  ```bash
  ruff check .
  ```

---
*Built for developers, by Lorapok Labs.*
