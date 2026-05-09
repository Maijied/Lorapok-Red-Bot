# Lorapok Red Bot — Architecture

## System Overview

Lorapok Red Bot is a full-spectrum Reddit automation platform built as a layered,
multi-tenant SaaS product. It covers every controllable Reddit API surface — moderation,
user management, flair, wiki, modmail, widgets, rules, analytics, and content scheduling —
wrapped in the Lorapok Design Language (biological UI, glassmorphism, animated dark theme).

---

## High-Level Architecture

```
Reddit API ──► Worker (app/main.py) ──► Rule Engine ──► AI Classifier (LiteLLM)
                      │                                         │
                      ▼                                         ▼
               PostgreSQL DB ◄──── Human Review Queue ◄──── Uncertain Cases
                      │
                      ▼
               FastAPI Dashboard ──► Stripe Billing ──► Feature Flags
                      │
              ┌───────┴────────┐
              ▼                ▼
         GitHub Pages     Outbound Webhooks
         (Marketing Site)  (Zapier / Make)
```

---

## Module Layers

### Entrypoints
| File | Purpose |
|---|---|
| `app/main.py` | Worker — streams Reddit events, orchestrates all domain calls |
| `app/dashboard/api.py` | FastAPI — 30+ endpoints for dashboard UI and moderator controls |
| `app/billing/webhook_handler.py` | Stripe webhook event processor |

### Domain (pure business logic, no I/O)
| Module | Purpose |
|---|---|
| `app/moderation/rules.py` | Deterministic keyword + regex rule engine (YAML-configurable) |
| `app/moderation/classifier.py` | LiteLLM AI classifier with Redis caching |
| `app/moderation/queue.py` | Human-in-the-loop review queue |
| `app/moderation/memory.py` | Append-only decision audit trail |
| `app/moderation/spam_detector.py` | Cross-subreddit spam detection |
| `app/moderation/sentiment.py` | Sentiment analysis + trend alerts |
| `app/subreddit/settings_manager.py` | Full SubredditModeration.update() automation |
| `app/subreddit/flair_engine.py` | Post flair by content, user flair by karma tier |
| `app/subreddit/wiki_manager.py` | Wiki CRUD + auto-update FAQ/changelog |
| `app/subreddit/widget_manager.py` | Sidebar widget management |
| `app/subreddit/rules_engine.py` | Rules/removal reasons CRUD + violation tracking |
| `app/subreddit/modmail_triage.py` | Modmail categorisation, auto-reply, SLA tracking |
| `app/users/reputation.py` | User reputation scoring system |
| `app/users/ban_appeals.py` | Ban appeal workflow |
| `app/users/onboarding.py` | Welcome DM + flair on new subscriber |
| `app/users/contributors.py` | Auto-promote/demote approved contributors |
| `app/users/mod_notes.py` | Mod notes CRUD via PRAW |
| `app/analytics/engagement.py` | Engagement prediction + auto-pin |
| `app/analytics/cohort.py` | Cohort analysis + churn prediction |
| `app/analytics/health_score.py` | Subreddit health score (0–100) |
| `app/analytics/multi_sub.py` | Multi-subreddit aggregate metrics |
| `app/posting/trending.py` | Trending thread builder |
| `app/posting/scheduler.py` | APScheduler — all periodic jobs |
| `app/posting/content_calendar.py` | Scheduled posts with optimal timing |

### Infrastructure (external side effects)
| Module | Purpose |
|---|---|
| `app/reddit_client.py` | Authenticated PRAW Reddit client |
| `app/integrations/github_integration.py` | GitHub REST API (releases, issues, trending) |
| `app/integrations/github_worker.py` | GitHub monitor orchestrator |
| `app/integrations/discord_integration.py` | Discord webhook alerts |
| `app/integrations/slack_integration.py` | Slack webhook + slash commands |
| `app/integrations/telegram_integration.py` | Telegram bot commands |
| `app/integrations/webhooks.py` | Outbound HMAC-signed webhook dispatcher |
| `app/billing/stripe_client.py` | Stripe customer/subscription/portal |
| `app/billing/features.py` | Feature flag matrix + enforcement |
| `app/billing/tenant.py` | Tenant lifecycle management |
| `app/billing/middleware.py` | FastAPI feature gate middleware |
| `app/database.py` | SQLAlchemy engine, session factory, Alembic runner |
| `app/config.py` | Settings dataclass loaded from environment |

### Utils
| Module | Purpose |
|---|---|
| `app/utils/logging.py` | Structured logging setup |
| `app/utils/rate_limit.py` | Reddit API rate limiter |
| `app/utils/text.py` | `normalize_text`, `stable_hash` (SHA-256) |
| `app/utils/notify.py` | Fan-out alerts to Discord + Slack + Telegram |

---

## Runtime Flow

1. **Startup**: `app/main.py` loads `Settings`, runs Alembic migrations, authenticates Reddit, starts APScheduler, sends startup alert.
2. **Stream**: Worker streams comments from all configured subreddits (`SUBREDDIT_NAMES`).
3. **Rule pass**: `apply_light_rules(text)` — deterministic, zero-latency, YAML-configurable.
4. **AI pass**: `classify_text(text)` via LiteLLM — cached in Redis by content hash.
5. **Decision routing**:
   - High-confidence remove → `comment.mod.remove()` (guarded by `dry_run`)
   - Uncertain → `queue_case()` → human review dashboard
   - Allow + help-seeking → `comment.reply(HELP_PROMPT)`
6. **Memory**: Every decision persisted to `moderation_decisions` table.
7. **Scheduler jobs** (APScheduler, UTC):
   - Every 1 min: publish due scheduled posts
   - Every 5 min: flush metrics to DB
   - Every hour: GitHub monitor, sentiment alert check
   - Daily 02:00: user flair batch
   - Daily 00:00: AI quota reset
   - Weekly Mon 14:00: trending post
   - Weekly Sun 03:00: contributor promotion/demotion batch

---

## Data Storage

| Table | Purpose |
|---|---|
| `moderation_decisions` | Append-only audit trail |
| `review_cases` | Human review queue |
| `daily_metrics` | Aggregated daily counters |
| `user_reputations` | Per-user reputation scores |
| `scheduled_posts` | Content calendar |
| `modmail_records` | Modmail triage state |
| `tenant_configs` | Multi-tenant SaaS config + Stripe state |
| `webhook_configs` | Outbound webhook endpoints |
| `spam_signals` | Cross-subreddit spam tracking |
| `sentiment_data` | Time-series sentiment scores |
| `ban_appeals` | Ban appeal workflow state |
| `flair_templates` | Flair template + keyword rules |
| `wiki_pages` | Local wiki cache |
| `onboarding_records` | New subscriber welcome tracking |
| `rule_violations` | Per-user rule violation history |
| `policy_sync_records` | Policy sync audit log |
| `github_update_tracker` | GitHub release/issue deduplication |
| `pending_posts` | GitHub-sourced post drafts |

---

## SaaS Tiers

| Tier | Price | Subreddits | AI/day |
|---|---|---|---|
| Free | $0 | 1 | 100 |
| Starter | $19/mo | 3 | 1,000 |
| Pro | $49/mo | 10 | Unlimited |
| Agency | $149/mo | Unlimited | Unlimited |
| Enterprise | Custom | Unlimited | Unlimited |

---

## Deployment

- **Bot worker + Dashboard**: Railway / Render / Fly.io (free tier)
- **Database**: Managed PostgreSQL (Railway / Render free tier)
- **Cache**: Redis (Railway / Render free tier)
- **Marketing site**: GitHub Pages (`gh-pages` branch, auto-deployed via GitHub Actions)

See `docker-compose.yml` for local development, `fly.toml` for Fly.io, `render.yaml` for Render.
