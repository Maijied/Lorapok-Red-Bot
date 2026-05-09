# Lorapok Red Bot

**Lorapok Red Bot** is a high-performance Reddit assistant designed for developer communities. It combines rule-based moderation with OpenAI-powered intelligence to maintain community standards while providing automated trending content discovery and release monitoring.

## 🚀 Key Features

- **🧠 AI-Powered Moderation:** Uses GPT-4o-mini to classify content, with a human-in-the-loop review queue.
- **📚 Persistent Memory:** Tracks all moderation decisions and overrides in a PostgreSQL backend.
- **🔭 GitHub Monitoring:** Automatically watches repositories for new releases and issues, generating AI-summarized draft posts.
- **📊 Interactive Dashboard:** A modern, themed web interface for moderators to review cases, manage growth analytics, and approve automated posts.
- **⏰ Scheduled Trends:** Automatically discovers and posts weekly trending developer repositories.
- **🔔 Discord Alerts:** Instant notifications for moderation failures or new content drafts.

## 🛠 Tech Stack

- **Core:** Python 3.12, PRAW (Reddit API)
- **AI:** OpenAI GPT-4o-mini
- **Backend:** FastAPI, SQLAlchemy, PostgreSQL, Redis
- **Automation:** APScheduler
- **Deployment:** Docker, Docker Compose, GitHub Actions

## 📦 Setup & Installation

1.  **Clone the Repository:**
    ```bash
    git clone https://github.com/your-repo/lorapok-red-bot.git
    cd lorapok-red-bot
    ```

2.  **Environment Configuration:**
    ```bash
    cp .env.example .env
    # Fill in your REDDIT, OPENAI, and GITHUB credentials in .env
    ```

3.  **Run with Docker (Recommended):**
    ```bash
    docker-compose up --build -d
    ```

4.  **Local Development:**
    ```bash
    python -m venv .venv
    source .venv/bin/activate
    pip install -r requirements.txt
    python -m app.main
    ```

## 🖥 Dashboard

Access the moderator dashboard at `http://localhost:8000`.

- **Pending Review:** Human-in-the-loop queue for suspicious content.
- **Draft Updates:** Review and approve AI-generated GitHub release posts.
- **Growth:** Time-series analytics for subreddit activity.
- **Action Log:** Historical record of all bot and moderator actions.

## 🤝 Documentation

- [Full Usage Guide](docs/how_to_use.md)
- [Architecture Overview](docs/architecture.md)
- [Bot Policy](docs/policy.md)
- [Privacy & Data Retention](docs/privacy.md)

---
*Built for developers, by Lorapok.*
