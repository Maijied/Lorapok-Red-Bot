import os
from dataclasses import dataclass, field
from typing import List, Optional

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


def _clamp(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, value))


@dataclass(frozen=True)
class Settings:
    # ── Reddit OAuth ──────────────────────────────────────────────────────────
    reddit_client_id: str
    reddit_client_secret: str
    reddit_username: str
    reddit_password: str
    reddit_user_agent: str

    # ── AI / LLM ──────────────────────────────────────────────────────────────
    ai_model: str
    openai_api_key: str
    anthropic_api_key: str
    gemini_api_key: str
    mistral_api_key: str

    # ── Infrastructure ────────────────────────────────────────────────────────
    database_url: str
    redis_url: str

    # ── Notification channels ─────────────────────────────────────────────────
    discord_webhook_url: str
    slack_webhook_url: str
    telegram_bot_token: str
    telegram_chat_id: str

    # ── GitHub ────────────────────────────────────────────────────────────────
    github_token: str
    monitored_repos: List[str]

    # ── Stripe billing ────────────────────────────────────────────────────────
    stripe_secret_key: str
    stripe_webhook_secret: str
    stripe_price_starter_monthly: str
    stripe_price_pro_monthly: str
    stripe_price_agency_monthly: str
    stripe_price_starter_annual: str
    stripe_price_pro_annual: str
    stripe_price_agency_annual: str

    # ── Bot behaviour ─────────────────────────────────────────────────────────
    # Legacy single-subreddit field kept for backward compatibility.
    # New code should use subreddit_names.
    subreddit_name: str
    # Multi-subreddit list (parsed from comma-separated SUBREDDIT_NAMES env var).
    subreddit_names: List[str]
    dry_run: bool
    log_level: str
    review_confidence_threshold: float  # clamped to [0.0, 1.0]

    # ── Multi-tenant SaaS ─────────────────────────────────────────────────────
    tenant_id: str

    # ── White-label (Agency / Enterprise) ────────────────────────────────────
    white_label_name: Optional[str]
    white_label_logo_url: Optional[str]

    @classmethod
    def from_env(cls) -> "Settings":
        subreddit_name = os.getenv("SUBREDDIT_NAME", "all")
        # SUBREDDIT_NAMES overrides SUBREDDIT_NAME when set.
        subreddit_names_raw = os.getenv("SUBREDDIT_NAMES", "")
        subreddit_names = (
            _as_list(subreddit_names_raw) if subreddit_names_raw else [subreddit_name]
        )

        return cls(
            # Reddit OAuth
            reddit_client_id=os.getenv("REDDIT_CLIENT_ID", ""),
            reddit_client_secret=os.getenv("REDDIT_CLIENT_SECRET", ""),
            reddit_username=os.getenv("REDDIT_USERNAME", ""),
            reddit_password=os.getenv("REDDIT_PASSWORD", ""),
            reddit_user_agent=os.getenv("REDDIT_USER_AGENT", "LorapokRedBot/1.0"),
            # AI
            ai_model=os.getenv("AI_MODEL", "openai/gpt-4o-mini"),
            openai_api_key=os.getenv("OPENAI_API_KEY", ""),
            anthropic_api_key=os.getenv("ANTHROPIC_API_KEY", ""),
            gemini_api_key=os.getenv("GEMINI_API_KEY", ""),
            mistral_api_key=os.getenv("MISTRAL_API_KEY", ""),
            # Infrastructure
            database_url=os.getenv(
                "DATABASE_URL",
                "postgresql://user:pass@localhost:5432/lorapok_red_bot",
            ),
            redis_url=os.getenv("REDIS_URL", "redis://localhost:6379/0"),
            # Notification channels
            discord_webhook_url=os.getenv("DISCORD_WEBHOOK_URL", ""),
            slack_webhook_url=os.getenv("SLACK_WEBHOOK_URL", ""),
            telegram_bot_token=os.getenv("TELEGRAM_BOT_TOKEN", ""),
            telegram_chat_id=os.getenv("TELEGRAM_CHAT_ID", ""),
            # GitHub
            github_token=os.getenv("GITHUB_TOKEN", ""),
            monitored_repos=_as_list(
                os.getenv("MONITORED_REPOS", "tiangolo/fastapi,python/cpython")
            ),
            # Stripe
            stripe_secret_key=os.getenv("STRIPE_SECRET_KEY", ""),
            stripe_webhook_secret=os.getenv("STRIPE_WEBHOOK_SECRET", ""),
            stripe_price_starter_monthly=os.getenv(
                "STRIPE_PRICE_STARTER_MONTHLY", ""
            ),
            stripe_price_pro_monthly=os.getenv("STRIPE_PRICE_PRO_MONTHLY", ""),
            stripe_price_agency_monthly=os.getenv(
                "STRIPE_PRICE_AGENCY_MONTHLY", ""
            ),
            stripe_price_starter_annual=os.getenv(
                "STRIPE_PRICE_STARTER_ANNUAL", ""
            ),
            stripe_price_pro_annual=os.getenv("STRIPE_PRICE_PRO_ANNUAL", ""),
            stripe_price_agency_annual=os.getenv("STRIPE_PRICE_AGENCY_ANNUAL", ""),
            # Bot behaviour
            subreddit_name=subreddit_name,
            subreddit_names=subreddit_names,
            dry_run=_as_bool(os.getenv("DRY_RUN"), default=True),
            log_level=os.getenv("LOG_LEVEL", "INFO"),
            review_confidence_threshold=_clamp(
                _as_float(os.getenv("REVIEW_CONFIDENCE_THRESHOLD"), default=0.75),
                0.0,
                1.0,
            ),
            # Multi-tenant
            tenant_id=os.getenv("TENANT_ID", "default"),
            # White-label
            white_label_name=os.getenv("WHITE_LABEL_NAME") or None,
            white_label_logo_url=os.getenv("WHITE_LABEL_LOGO_URL") or None,
        )
