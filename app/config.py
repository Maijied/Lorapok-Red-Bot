import os
from dataclasses import dataclass
from typing import List

from dotenv import load_dotenv

load_dotenv()


def _as_bool(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _as_float(value: str | None, default: float) -> float:
    if value is None:
        return default
    try:
        return float(value)
    except ValueError:
        return default


def _as_list(value: str | None) -> List[str]:
    if not value:
        return []
    return [x.strip() for x in value.split(",") if x.strip()]


@dataclass(frozen=True)
class Settings:
    reddit_client_id: str
    reddit_client_secret: str
    reddit_username: str
    reddit_password: str
    reddit_user_agent: str
    
    # AI Config
    ai_model: str
    openai_api_key: str
    anthropic_api_key: str
    gemini_api_key: str
    mistral_api_key: str
    
    database_url: str
    redis_url: str
    discord_webhook_url: str
    github_token: str
    subreddit_name: str
    dry_run: bool
    log_level: str
    review_confidence_threshold: float
    monitored_repos: List[str]

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            reddit_client_id=os.getenv("REDDIT_CLIENT_ID", ""),
            reddit_client_secret=os.getenv("REDDIT_CLIENT_SECRET", ""),
            reddit_username=os.getenv("REDDIT_USERNAME", ""),
            reddit_password=os.getenv("REDDIT_PASSWORD", ""),
            reddit_user_agent=os.getenv("REDDIT_USER_AGENT", "LorapokRedBot/1.0"),
            
            ai_model=os.getenv("AI_MODEL", "openai/gpt-4o-mini"),
            openai_api_key=os.getenv("OPENAI_API_KEY", ""),
            anthropic_api_key=os.getenv("ANTHROPIC_API_KEY", ""),
            gemini_api_key=os.getenv("GEMINI_API_KEY", ""),
            mistral_api_key=os.getenv("MISTRAL_API_KEY", ""),
            
            database_url=os.getenv(
                "DATABASE_URL", "postgresql://user:pass@localhost:5432/lorapok_red_bot"
            ),
            redis_url=os.getenv("REDIS_URL", "redis://localhost:6379/0"),
            discord_webhook_url=os.getenv("DISCORD_WEBHOOK_URL", ""),
            github_token=os.getenv("GITHUB_TOKEN", ""),
            subreddit_name=os.getenv("SUBREDDIT_NAME", "all"),
            dry_run=_as_bool(os.getenv("DRY_RUN"), default=True),
            log_level=os.getenv("LOG_LEVEL", "INFO"),
            review_confidence_threshold=_as_float(
                os.getenv("REVIEW_CONFIDENCE_THRESHOLD"), default=0.75
            ),
            monitored_repos=_as_list(
                os.getenv("MONITORED_REPOS", "tiangolo/fastapi,python/cpython")
            ),
        )
