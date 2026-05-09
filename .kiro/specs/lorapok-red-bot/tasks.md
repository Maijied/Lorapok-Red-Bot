# Implementation Plan: Lorapok Red Bot

## Overview

Full-spectrum Reddit automation platform built in Python. The existing bootstrap under `app/`
is functionally correct but architecturally flat. This plan extends it into a layered,
multi-tenant SaaS product covering subreddit automation, AI intelligence, analytics, billing,
integrations, and a GitHub Pages marketing site.

All tasks are Python unless otherwise noted. Property-based tests use `hypothesis`.

---

## Tasks

- [x] 1. Phase 1 — Architecture Redesign & Foundation
  - [x] 1.1 Update `requirements.txt` with all new dependencies
    - Add `stripe`, `hypothesis`, `celery`, `alembic`, `pip-audit` with pinned versions
    - Verify existing pins for `praw`, `litellm`, `redis`, `fastapi`, `sqlalchemy`
    - _Requirements: 32.1, 34.8_

  - [x] 1.2 Expand `app/config.py` with all new settings fields
    - Add `stripe_secret_key`, `stripe_webhook_secret`, `stripe_price_*` fields
    - Add `slack_webhook_url`, `telegram_bot_token`, `telegram_chat_id` fields
    - Add `subreddit_names: list[str]` (multi-subreddit), `tenant_id: str`
    - Add `white_label_name`, `white_label_logo_url` optional fields
    - Keep `Settings.from_env()` as the single construction path; no hardcoded defaults for secrets
    - _Requirements: 32.1, 32.6_

  - [x] 1.3 Add all 22 SQLAlchemy models to `app/dashboard/models.py`
    - Add `ScheduledPost`, `UserReputation`, `ModNote`, `ModmailRecord`, `ModmailTemplate`
    - Add `FlairTemplate`, `WikiPage`, `WebhookConfig`, `TenantConfig`
    - Add `BanAppeal`, `SpamSignalRecord`, `SentimentDataPoint`, `PolicySyncRecord`
    - Add `OnboardingRecord`, `RuleViolationRecord`, `FlairAssignmentRecord`
    - Enforce UNIQUE constraint on `(username, subreddit_name)` for `UserReputation`
    - Enforce UNIQUE on `tenant_id` for `TenantConfig`; UNIQUE on `external_id` for `GithubUpdateTracker`
    - Add `tenant_id` column to every tenant-scoped table
    - _Requirements: 28.12, 37.2–37.6_

  - [x] 1.4 Set up Alembic for database migrations
    - Run `alembic init alembic` and configure `alembic.ini` to read `DATABASE_URL` from env
    - Generate initial migration from current `Base.metadata`
    - Add `alembic upgrade head` to startup sequence in `app/database.py`
    - _Requirements: 32.3_

  - [ ]* 1.5 Write property test for `stable_hash` consistency
    - **Property 9: `stable_hash` is collision-resistant for distinct normalised texts**
    - **Validates: Requirements 5.4, 6.4**
    - _Requirements: 5.4, 6.4_


- [-] 2. Phase 2 — Core Reddit Bot Improvements
  - [x] 2.1 Redesign `app/main.py` worker entrypoint
    - Add `process_submission` function mirroring `process_comment` pipeline
    - Add multi-subreddit support: iterate `settings.subreddit_names` and merge streams
    - Replace inline scheduler setup with `register_all_jobs(scheduler, settings, session_factory)`
    - Add `process_submission` call in the stream loop alongside `process_comment`
    - Wrap every per-item block in `try/except`; catch `OperationalError` separately to reopen session
    - _Requirements: 1.7, 1.8, 1.10, 31.2, 35.1, 35.2, 35.8_

  - [x] 2.2 Improve `app/moderation/rules.py` rule engine
    - Load keyword lists from a YAML config file (`app/moderation/rules.yaml`) instead of hardcoded lists
    - Add regex pattern support alongside plain keyword matching
    - Keep `apply_light_rules` signature unchanged; no I/O inside the function
    - _Requirements: 2.1–2.7_

  - [ ]* 2.3 Write property tests for rule engine
    - **Property 1: Rule engine is deterministic and pure**
    - **Validates: Requirements 2.3, 2.4**
    - **Property 2: Rule engine always returns a valid action and confidence**
    - **Validates: Requirements 2.1, 2.2**
    - _Requirements: 2.1–2.4_

  - [x] 2.4 Improve `app/moderation/classifier.py`
    - Add `ClassifierResult` dataclass with `action`, `reason`, `confidence` fields
    - Add Redis caching: cache `classify_text` result by `stable_hash(text)` with 5-minute TTL
    - Add `_to_decision` helper that coerces any dict to a valid `ModerationDecision`
    - _Requirements: 3.1–3.7, 33.7_

  - [ ]* 2.5 Write property test for AI classifier
    - **Property 3: AI classifier never raises**
    - **Validates: Requirements 3.1, 3.2, 3.3, 3.4, 3.5**
    - _Requirements: 3.1–3.5_

  - [ ]* 2.6 Write property test for `_to_decision`
    - **Property 10: `_to_decision` always produces a valid `ModerationDecision`**
    - **Validates: Requirement 1.3**
    - _Requirements: 1.3_

  - [x] 2.7 Improve `app/moderation/queue.py` review queue
    - Add `tenant_id` filter to `list_queue` and `resolve_case`
    - Verify `was_override` logic covers all action/recommendation combinations
    - _Requirements: 4.1–4.7_

  - [ ]* 2.8 Write property test for queue round-trip
    - **Property 5: `queue_case` → `list_queue` round-trip**
    - **Validates: Requirements 4.1, 4.2**
    - **Property 6: `resolve_case` is idempotent on status**
    - **Validates: Requirement 4.4**
    - _Requirements: 4.1, 4.2, 4.4_

  - [x] 2.9 Improve `app/moderation/memory.py` decision audit trail
    - Add `tenant_id` and `subreddit_name` columns to `ModerationDecisionRecord`
    - Verify `stable_hash` is used for `text_hash` field
    - _Requirements: 5.1–5.5_

  - [x] 2.10 Update `app/posting/scheduler.py` with `register_all_jobs`
    - Implement `register_all_jobs(scheduler, settings, session_factory)` replacing inline setup
    - Register: trending post (weekly), GitHub monitor (hourly), metrics flush (5 min), scheduled post publisher (1 min), AI quota reset (daily midnight UTC), settings sync (configurable)
    - Add error handler on each job: log + alert notification channels on exception
    - _Requirements: 31.1–31.5_

  - [x] 2.11 Checkpoint — ensure all existing tests pass with the refactored code
    - Run `pytest tests/` and fix any regressions from Phase 1–2 changes
    - _Requirements: 1.1–1.10, 2.1–2.7_


- [-] 3. Phase 3 — Full Subreddit Automation
  - [x] 3.1 Create `app/subreddit/__init__.py` package file
    - Empty init; establishes the `app/subreddit/` package
    - _Requirements: 8.1_

  - [x] 3.2 Implement `app/subreddit/settings_manager.py`
    - Implement `SubredditSettingsSnapshot` dataclass and `get_settings(reddit, subreddit_name)`
    - Implement `update_settings(reddit, subreddit_name, dry_run, **kwargs)` calling `SubredditModeration.update()`
    - Implement `schedule_setting_change(db, subreddit_name, settings_delta, apply_at)` persisting to DB
    - Implement `apply_scheduled_changes(db, reddit)` applying all past-due scheduled changes
    - Implement `accept_mod_invite(reddit, subreddit_name)` via PRAW
    - Implement `sync_policy(reddit, db, source, targets, policy_types)` returning `SyncResult`
    - `sync_policy` must be idempotent and commit successful targets independently of failures
    - Insert `PolicySyncRecord` per `(source, target)` pair
    - _Requirements: 8.1–8.10, 37.4_

  - [ ]* 3.3 Write property test for `sync_policy` idempotency
    - **Property 16: `sync_policy` is idempotent**
    - **Validates: Requirements 8.7, 8.8**
    - _Requirements: 8.7, 8.8_

  - [x] 3.4 Implement `app/subreddit/flair_engine.py`
    - Implement `FlairAssignment` dataclass with `template_id`, `text`, `css_class`, `source`
    - Implement `auto_assign_post_flair(submission, subreddit, settings)` using keyword matching against `FlairTemplate.auto_assign_keywords`
    - Implement `auto_assign_user_flair(reddit, subreddit_name, username, reputation)` calling `subreddit.flair.set()`
    - Implement `run_user_flair_batch(reddit, subreddit_name, db, settings)` iterating active users
    - Implement `create_flair_template`, `delete_flair_template`, `list_flair_templates` with PRAW + DB sync
    - Insert `FlairAssignmentRecord` with correct `source` on every assignment
    - _Requirements: 9.1–9.8, 37.5_

  - [x] 3.5 Implement `app/subreddit/wiki_manager.py`
    - Implement `get_wiki_page`, `update_wiki_page`, `list_wiki_pages`, `get_wiki_revision_history`
    - Implement `auto_update_faq(reddit, subreddit_name, db, settings)` regenerating FAQ from DB
    - Implement `auto_update_changelog(reddit, subreddit_name, db, settings)` appending latest GitHub release notes
    - _Requirements: 10.1–10.7_

  - [x] 3.6 Implement `app/subreddit/widget_manager.py`
    - Implement `list_widgets`, `update_text_widget`, `update_community_stats_widget`
    - Implement `add_button_widget`, `remove_widget`
    - Support all nine widget types via `SubredditWidgets` and `SubredditWidgetsModeration`
    - _Requirements: 11.1–11.6_

  - [x] 3.7 Implement `app/subreddit/rules_engine.py`
    - Implement `list_rules`, `add_rule`, `delete_rule` via `SubredditRules` / `SubredditRulesModeration`
    - Implement `list_removal_reasons`, `add_removal_reason`, `delete_removal_reason` via `SubredditRemovalReasons`
    - Implement `track_rule_violation(db, username, subreddit_name, rule_id, content_id)` inserting `RuleViolationRecord`
    - Implement `get_user_violation_history(db, username, subreddit_name)` ordered by `created_at` desc
    - _Requirements: 12.1–12.8_


- [ ] 4. Phase 4 — Modmail Automation
  - [x] 4.1 Implement `app/subreddit/modmail_triage.py`
    - Implement `ModmailTriageResult` dataclass with `conversation_id`, `category`, `confidence`, `auto_replied`, `sla_deadline`
    - Implement `triage_conversation(conversation, settings, db)` following Algorithm 5 from design
    - Classify into `{"ban_appeal", "spam_report", "question", "feedback", "unknown"}` via `classify_text`
    - Set `sla_deadline` based on tenant tier: Free=None, Starter=48h, Pro=24h, Agency/Enterprise=4h
    - Guard against duplicate `ModmailRecord` inserts using `conversation_id` uniqueness check
    - Implement `reply_to_conversation`, `archive_conversation`
    - Implement `get_modmail_analytics(db, subreddit_name, days)` returning response time and category breakdown
    - _Requirements: 13.1–13.12_

  - [ ]* 4.2 Write property test for modmail triage idempotency
    - **Property 17: `triage_conversation` inserts exactly one record per conversation**
    - **Validates: Requirements 13.5**
    - _Requirements: 13.5_

  - [x] 4.3 Implement modmail template CRUD
    - Implement `list_modmail_templates(db, tenant_id)` and `create_modmail_template(db, tenant_id, name, category, body)`
    - Implement template variable substitution for `{{username}}`, `{{subreddit}}`, `{{ban_reason}}`
    - _Requirements: 13.11, 13.12_

  - [x] 4.4 Wire modmail stream into `app/main.py`
    - Add `subreddit.mod.stream.modmail_conversations()` loop alongside comment/submission streams
    - Call `triage_conversation` for each new conversation; guard with `has_feature(db, tenant_id, "modmail_triage")`
    - _Requirements: 13.1, 28.7_


- [ ] 5. Phase 5 — User Management
  - [x] 5.1 Create `app/users/__init__.py` package file
    - Empty init; establishes the `app/users/` package
    - _Requirements: 14.1_

  - [x] 5.2 Implement `app/users/reputation.py`
    - Implement `compute_reputation_score(reputation)` using the formula from Algorithm 2; clamp to `[-100, 100]`; no I/O
    - Implement `get_or_create_reputation(db, username, subreddit_name)` with upsert on UNIQUE constraint
    - Implement `update_reputation(db, username, subreddit_name, delta)` recomputing score before save
    - Implement `get_top_contributors(db, subreddit_name, limit)` ordered by `reputation_score` desc
    - Implement `flag_suspicious_user(db, username, subreddit_name, reason)` setting `is_suspicious=True`
    - _Requirements: 14.1–14.8_

  - [ ]* 5.3 Write property test for reputation score bounds
    - **Property 11: `compute_reputation_score` is bounded**
    - **Validates: Requirements 14.1, 14.2**
    - _Requirements: 14.1, 14.2_

  - [x] 5.4 Implement `app/users/ban_appeals.py`
    - Implement `create_ban_appeal(db, username, subreddit_name, modmail_id, appeal_text)` inserting `BanAppeal` with `status="pending"`
    - Implement `auto_review_appeal(db, appeal, reputation, settings)` applying auto-approve/reject/escalate logic from design
    - Implement `escalate_appeal(db, appeal_id, reason)`, `resolve_appeal(db, appeal_id, decision, reviewer_note)`
    - Implement `get_pending_appeals(db, subreddit_name)` filtering by `status="pending"`
    - _Requirements: 15.1–15.6_

  - [x] 5.5 Implement `app/users/onboarding.py`
    - Implement `is_welcomed(db, username, subreddit_name)` querying `OnboardingRecord`
    - Implement `send_welcome_dm(reddit, username, template, subreddit_name)` via `reddit.redditor(username).message()`
    - Implement `mark_welcomed(db, username, subreddit_name)` inserting `OnboardingRecord`
    - Implement `handle_new_subscriber(reddit, db, username, subreddit_name, settings)` orchestrating the full flow
    - Only call `mark_welcomed` after DM succeeds; log and skip on failure without marking welcomed
    - _Requirements: 16.1–16.6_

  - [x] 5.6 Implement `app/users/contributors.py`
    - Implement `add_contributor(reddit, subreddit_name, username)` via `subreddit.contributor.add()`
    - Implement `remove_contributor(reddit, subreddit_name, username)` via `subreddit.contributor.remove()`
    - Implement `run_contributor_promotion_batch(reddit, db, subreddit_name, settings)` applying promotion thresholds
    - Implement `run_contributor_demotion_batch(reddit, db, subreddit_name, settings)` applying 180-day inactivity rule
    - Update `UserReputation.is_contributor` on every promotion/demotion
    - _Requirements: 17.1–17.5_

  - [x] 5.7 Implement `app/users/mod_notes.py`
    - Implement `add_mod_note(reddit, subreddit_name, username, note, label)` via `subreddit.mod.notes`
    - Implement `get_mod_notes(reddit, subreddit_name, username)` fetching from Reddit via PRAW
    - Implement `auto_note_on_action(reddit, db, username, subreddit_name, action, reason)` creating note + `ModNote` DB record
    - Implement `search_mod_notes(db, subreddit_name, query)` querying `ModNote` table
    - Support labels: `"BOT_BAN"`, `"BOT_SPAM"`, `"BOT_REVIEW"`, `"HUMAN_OVERRIDE"`
    - Auto-create `"HUMAN_OVERRIDE"` note when `was_override=True` is set on a `ReviewCaseRecord`
    - _Requirements: 18.1–18.6_

  - [x] 5.8 Wire user management jobs into scheduler
    - Register `run_contributor_promotion_batch` and `run_contributor_demotion_batch` as weekly APScheduler jobs
    - Register `run_user_flair_batch` as a daily APScheduler job
    - Guard all batch jobs with `has_feature` checks before executing
    - _Requirements: 17.1, 17.2, 31.2_


- [ ] 6. Phase 6 — AI Intelligence Layer
  - [x] 6.1 Implement `app/moderation/spam_detector.py`
    - Implement `SpamSignal` dataclass with `username`, `content_hash`, `subreddits`, `occurrences`, `score`
    - Implement `record_submission(db, username, subreddit_name, content_hash, url)` inserting `SpamSignalRecord`
    - Implement `detect_cross_sub_spam(db, username, content_hash, window_hours=24)` following Algorithm 4
    - Return `None` when fewer than 3 distinct subreddits; return `SpamSignal` with `score = min(1.0, len(subreddits) / 10.0)` otherwise
    - Implement `get_spam_signals(db, subreddit_name, min_score=0.7)`
    - Only compare submissions within subreddits belonging to the same tenant
    - _Requirements: 6.1–6.6_

  - [ ]* 6.2 Write property test for spam detector threshold
    - **Property 13: `detect_cross_sub_spam` requires at least 3 subreddits**
    - **Validates: Requirements 6.1, 6.2**
    - _Requirements: 6.1, 6.2_

  - [x] 6.3 Implement `app/moderation/sentiment.py`
    - Implement `SentimentResult` dataclass with `score: float` in `[-1.0, 1.0]` and `label` in `{"positive", "neutral", "negative"}`
    - Implement `analyze_sentiment(text, model=None)` via LiteLLM returning `SentimentResult`
    - Implement `record_sentiment(db, subreddit_name, score, source)` inserting `SentimentDataPoint`
    - Implement `get_sentiment_trend(db, subreddit_name, days=7)` returning chronologically ordered data points
    - Implement `check_sentiment_alert(db, subreddit_name, threshold=-0.3)` computing 3-day rolling average and returning bool
    - _Requirements: 7.1–7.5_

  - [x] 6.4 Implement `app/analytics/engagement.py`
    - Create `app/analytics/__init__.py` package file
    - Implement `EngagementPrediction` dataclass with `score`, `predicted_upvotes`, `confidence`
    - Implement `predict_engagement(submission, historical_data)` following Algorithm 3; `confidence=0.3` when `historical_data` is empty, capped at `0.9`
    - Implement `get_rising_submissions(reddit, subreddit_name, limit=25)` via `subreddit.rising()`
    - Implement `auto_pin_high_potential(reddit, db, subreddit_name, settings)` calling `submission.mod.sticky()` for high-score posts
    - _Requirements: 19.1–19.6_

  - [x] 6.5 Implement `app/posting/content_calendar.py`
    - Implement `schedule_post(db, subreddit_name, title, body, flair_id, post_at)` — reject `post_at` in the past with `ValueError`
    - Implement `get_scheduled_posts(db, subreddit_name)` and `cancel_scheduled_post(db, post_id)`
    - Implement `publish_due_posts(reddit, db, settings)` submitting all due `ScheduledPost` records; set `status="published"` on success, `status="failed"` on error
    - Implement `get_optimal_post_times(db, subreddit_name)` analysing `DailyMetric` engagement data
    - Enforce status transition guard: never re-publish a post with `status != "scheduled"`
    - _Requirements: 20.1–20.10_

  - [ ]* 6.6 Write property test for scheduled post publish idempotency
    - **Property 18: Scheduled post publish is idempotent**
    - **Validates: Requirement 20.5**
    - _Requirements: 20.5_

  - [x] 6.7 Wire AI intelligence jobs into scheduler and stream
    - Call `record_submission` + `detect_cross_sub_spam` in `process_submission`; queue if `signal.score >= 0.7`
    - Call `analyze_sentiment` + `record_sentiment` in `process_comment` (async background task, non-blocking)
    - Call `check_sentiment_alert` in a scheduled job (hourly); dispatch alert to notification channels if triggered
    - Register `auto_pin_high_potential` as a scheduled job (configurable interval)
    - Guard all AI calls with `has_feature(db, tenant_id, "ai_call")` and fall back to rules-only on quota exhaustion
    - _Requirements: 6.5, 7.4, 7.5, 19.6, 28.2, 28.3_

  - [x] 6.8 Checkpoint — ensure all tests pass through Phase 6
    - Run `pytest tests/` and fix any regressions
    - _Requirements: 1.1–20.10_


- [ ] 7. Phase 7 — Analytics & Dashboard
  - [x] 7.1 Implement `app/analytics/cohort.py`
    - Implement `build_cohort_table(db, subreddit_name, months=6)` grouping users by join month and tracking subsequent activity
    - Implement `get_power_users(db, subreddit_name, limit=50)` ordered by `reputation_score` desc
    - Implement `get_churn_risk_users(db, subreddit_name)` returning users with no activity in past 30 days
    - _Requirements: 22.1–22.4_

  - [x] 7.2 Implement `app/analytics/health_score.py`
    - Implement `SubredditHealthScore` dataclass with `total`, `growth`, `engagement`, `moderation`, `spam` fields
    - Implement `compute_health_score(db, subreddit_name, reddit)` following Algorithm 6
    - Each component clamped to `[0, 25]`; `total = growth + engagement + moderation + spam`
    - _Requirements: 23.1–23.8_

  - [ ]* 7.3 Write property test for health score component sum
    - **Property 14: `compute_health_score` components sum to total**
    - **Validates: Requirements 23.3**
    - _Requirements: 23.3_

  - [x] 7.4 Implement `app/analytics/multi_sub.py`
    - Implement `get_aggregate_metrics(db, tenant_id)` combining metrics across all `TenantConfig.managed_subreddits`
    - Implement `get_per_sub_breakdown(db, tenant_id)` returning a `SubredditSummary` per managed subreddit
    - Filter strictly by `tenant_id` — never return data from other tenants
    - _Requirements: 24.1–24.4_

  - [x] 7.5 Expand `app/dashboard/api.py` with all new endpoints
    - Add `GET /analytics/cohort` (Agency+), `GET /analytics/health-score` (Agency+), `GET /analytics/multi-sub` (Agency+)
    - Add `GET /analytics/sentiment` returning 7-day trend data
    - Add `GET /users/{username}/reputation`, `GET /modmail`, `POST /modmail/{id}/reply`
    - Add `GET /flair/templates`, `POST /flair/auto-assign`
    - Add `GET /wiki/pages`, `POST /wiki/pages/{name}/update`
    - Add `GET /webhooks`, `POST /webhooks`, `DELETE /webhooks/{id}` (Agency+)
    - Add `GET /billing/subscription`, `POST /billing/portal`
    - Add `GET /scheduled-posts`, `POST /scheduled-posts`, `DELETE /scheduled-posts/{id}`
    - Add `GET /subreddits`, `POST /subreddits/sync-policy` (Agency+)
    - Validate all request bodies with Pydantic models before processing
    - Cache `/analytics/cohort` and `/analytics/health-score` responses in Redis with 10-minute TTL
    - _Requirements: 29.1–29.17_

  - [x] 7.6 Extract dashboard HTML to `app/dashboard/static/index.html`
    - Move the `_DASHBOARD_HTML` string from `api.py` to `app/dashboard/static/index.html`
    - Mount `app/dashboard/static/` via `StaticFiles` and serve `index.html` at `GET /`
    - Update the HTML to read white-label config from `GET /config` at page load
    - Add all new nav sections: Modmail, Flair, Wiki, Billing, Scheduled Posts, Subreddits, Analytics sub-pages
    - Apply Lorapok Design Language tokens consistently; use semantic HTML5 elements (`<nav>`, `<main>`, `<section>`, `<button>`, `<table>`)
    - Ensure all interactive elements have `aria-label` or visible text; all form inputs have `<label>` elements
    - _Requirements: 29.16, 30.1–30.5, 38.1–38.5_


- [ ] 8. Phase 8 — Integrations Expansion
  - [x] 8.1 Implement `app/integrations/slack_integration.py`
    - Implement `send_slack_alert(message, channel=None)` POSTing to `SLACK_WEBHOOK_URL`; return immediately if URL not set
    - Implement `handle_slack_slash_command(payload, reddit, db, settings)` routing `/redbot queue`, `/redbot approve <id>`, `/redbot reject <id>`, `/redbot stats`, `/redbot health`
    - Return immediately without raising if `SLACK_WEBHOOK_URL` is not configured
    - _Requirements: 25.3–25.7, 25.10_

  - [x] 8.2 Implement `app/integrations/telegram_integration.py`
    - Implement `send_telegram_message(chat_id, message)` via Telegram Bot API using `httpx`
    - Implement `handle_telegram_command(update, reddit, db, settings)` routing bot commands
    - Return immediately without raising if `TELEGRAM_BOT_TOKEN` is not configured
    - _Requirements: 25.8, 25.9, 25.10_

  - [x] 8.3 Implement `app/integrations/webhooks.py` outbound webhook dispatcher
    - Implement `WebhookConfig` DB model interactions: `register_webhook`, `list_webhooks`, `delete_webhook`
    - Implement `dispatch_event(db, tenant_id, event_type, payload)` — POST to all active matching webhooks
    - Sign every payload with `X-Lorapok-Signature: sha256=<hmac_hex>` using the webhook's secret
    - Retry up to 3 times with exponential backoff (2s, 4s, 8s) on non-2xx or timeout
    - Increment `failure_count` after 3 exhausted retries; set `is_active=False` at 10 consecutive failures
    - Never raise to caller for any event type or unreachable endpoint
    - Store webhook secrets hashed (SHA-256) in DB; never return raw secret in API responses
    - Support all 10 event types from design: `comment.removed`, `submission.removed`, `user.banned`, `modmail.received`, `queue.case_added`, `flair.assigned`, `post.published`, `health_score.alert`, `sentiment.alert`, `spam_signal.detected`
    - _Requirements: 26.1–26.10_

  - [ ]* 8.4 Write property test for webhook dispatcher never raises
    - **Property 15: `dispatch_event` never raises to caller**
    - **Validates: Requirement 26.7**
    - _Requirements: 26.7_

  - [x] 8.5 Wire `dispatch_event` calls into domain modules
    - Call `dispatch_event` after: comment/submission removed, user banned, modmail received, queue case added, flair assigned, post published, health score alert, sentiment alert, spam signal detected
    - All dispatch calls must be non-blocking (background task or fire-and-forget)
    - _Requirements: 26.2, 26.8_

  - [x] 8.6 Update notification helper to fan out to all configured channels
    - Create `app/utils/notify.py` with `send_alert(message, db, tenant_id)` fanning out to Discord, Slack, Telegram
    - Replace direct `send_discord_alert` calls in `app/main.py` with `send_alert`
    - Skip any channel whose URL/token is not configured without raising
    - _Requirements: 25.1, 25.2, 25.10, 35.5_


- [ ] 9. Phase 9 — SaaS Billing Engine
  - [x] 9.1 Create `app/billing/__init__.py` package file
    - Empty init; establishes the `app/billing/` package
    - _Requirements: 27.1_

  - [x] 9.2 Implement `app/billing/stripe_client.py`
    - Implement `create_customer(email, name)` via `stripe.Customer.create()` returning `customer_id`
    - Implement `create_subscription(customer_id, price_id)` returning `subscription_id`
    - Implement `cancel_subscription(subscription_id)` returning `True` on success
    - Implement `create_portal_session(customer_id, return_url)` returning the session URL
    - Never store raw card data; use Stripe SDK exclusively for all payment operations
    - _Requirements: 27.1–27.4, 27.11, 34.9_

  - [x] 9.3 Implement `app/billing/features.py`
    - Define `FEATURE_MATRIX` dict mapping tier names to cumulative feature sets (enterprise ⊇ agency ⊇ pro ⊇ starter ⊇ free)
    - Define `TIERS` dict with `SubscriptionTier` dataclasses including `max_subreddits` and `ai_calls_per_day`
    - Implement `get_tenant_features(db, tenant_id)` and `has_feature(db, tenant_id, feature)` following Algorithm 7
    - Handle `"ai_call"` quota check against `TenantConfig.ai_calls_today` and tier limit
    - Handle `"add_subreddit"` check against `len(managed_subreddits)` and tier limit
    - Return `False` for unknown `tenant_id` without raising
    - Cache `has_feature` results in Redis for 60 seconds
    - _Requirements: 28.1–28.13_

  - [ ]* 9.4 Write property test for `has_feature` unknown tenant
    - **Property 12: `has_feature` returns False for unknown tenant**
    - **Validates: Requirement 28.1**
    - _Requirements: 28.1_

  - [x] 9.5 Implement `app/billing/tenant.py`
    - Implement `get_or_create_tenant(db, reddit_username)` with upsert on `reddit_username` UNIQUE constraint
    - Implement `update_tenant_tier(db, tenant_id, tier)` updating `TenantConfig.tier`
    - Implement `add_managed_subreddit(db, tenant_id, subreddit_name)` and `remove_managed_subreddit`
    - _Requirements: 27.5, 27.6, 28.4, 28.11_

  - [x] 9.6 Implement `app/billing/webhook_handler.py` Stripe webhook handler
    - Implement `handle_stripe_webhook(payload, sig_header)` verifying signature via `stripe.Webhook.construct_event()`
    - Return HTTP 400 on `SignatureVerificationError` without processing the event
    - Handle `customer.subscription.updated` → `update_tenant_tier`
    - Handle `customer.subscription.deleted` → downgrade to `"free"`
    - Handle `invoice.payment_failed` → send alert + begin 7-day grace period
    - Handle `invoice.payment_succeeded` → confirm tier + reset `ai_calls_today`
    - _Requirements: 27.5–27.10, 34.6_

  - [x] 9.7 Implement `app/billing/middleware.py` FastAPI feature gate middleware
    - Implement `feature_gate_middleware` extracting `tenant_id` from API key header
    - Check `has_feature(db, tenant_id, required_feature)` for each gated endpoint
    - Return HTTP 403 with upgrade prompt message when feature check fails
    - _Requirements: 28.6, 28.10, 29.17_

  - [x] 9.8 Register Stripe webhook route and billing endpoints in `app/dashboard/api.py`
    - Add `POST /billing/stripe-webhook` route calling `handle_stripe_webhook`
    - Add `POST /billing/create-customer` and `POST /billing/subscribe` routes
    - Mount `feature_gate_middleware` on the FastAPI app
    - _Requirements: 27.9, 29.12_

  - [x] 9.9 Implement AI quota tracking and reset job
    - Increment `TenantConfig.ai_calls_today` in Redis on every AI call (hot path — avoid DB write per comment)
    - Register APScheduler job at midnight UTC to reset `ai_calls_today` to 0 for all tenants
    - Sync Redis counter back to `TenantConfig.ai_calls_today` in DB during the reset job
    - _Requirements: 28.2, 28.9_

  - [x] 9.10 Checkpoint — ensure all tests pass through Phase 9
    - Run `pytest tests/` and fix any regressions
    - _Requirements: 27.1–28.13_


- [x] 10. Phase 10 — GitHub Pages Website
  - [x] 10.1 Create `website/index.html` marketing site
    - Full single-page site using Lorapok Design Language (glassmorphism, dark theme, glowing accents)
    - Sections: hero with tagline, feature grid (all tier features), pricing table (Free/Starter/Pro/Agency/Enterprise), architecture overview, live status badge, CTA buttons
    - Use semantic HTML5 (`<header>`, `<nav>`, `<main>`, `<section>`, `<footer>`)
    - All interactive elements must have `aria-label` or visible text; minimum 4.5:1 colour contrast
    - Include one-click Railway deploy button linking to Railway template
    - _Requirements: 32.8, 38.1–38.5_

  - [x] 10.2 Create `website/css/style.css`
    - Define all Lorapok Design Language CSS custom properties: `--bg-deep`, `--bg-panel`, `--accent-neon`, `--accent-cyber`, `--accent-pulse`, `--accent-reddit`, `--border-glass`, glow shadows
    - Implement glassmorphism panels with `backdrop-filter: blur(12px)` and semi-transparent backgrounds
    - Implement animated pulse dots, hover float effects (`transform: translateY(-4px)`), and grid background with radial gradient mask
    - Responsive layout: mobile-first, breakpoints at 768px and 1200px
    - _Requirements: 32.8_

  - [x] 10.3 Create `website/js/main.js`
    - Implement scroll-triggered fade-in animations using `IntersectionObserver`
    - Implement live status badge fetching `GET /health` from the deployed dashboard API URL (configurable via `data-api-url` attribute)
    - Implement Mermaid.js architecture diagram initialisation (load Mermaid from CDN)
    - Implement smooth scroll for nav anchor links
    - _Requirements: 32.8_

  - [x] 10.4 Create `.github/workflows/deploy-website.yml`
    - Trigger on push to `main` branch when files under `website/` change
    - Use `actions/checkout`, copy `website/` contents to a temp dir, push to `gh-pages` branch via `peaceiris/actions-gh-pages`
    - _Requirements: 32.8_


- [x] 11. Phase 11 — CI/CD & Deployment
  - [x] 11.1 Create `.github/workflows/ci.yml` GitHub Actions CI pipeline
    - Trigger on push and pull_request to `main`
    - Steps: checkout, set up Python 3.11, `pip install -r requirements.txt`, `ruff check app tests`, `pytest --tb=short`, `pip-audit`
    - Upload coverage report as artifact
    - _Requirements: 34.8_

  - [x] 11.2 Update `Dockerfile` for multi-service support
    - Use `python:3.11-slim` base; install dependencies from `requirements.txt`
    - Add `CMD` defaulting to worker (`python -m app.main`); allow override via `COMMAND` env var for dashboard service
    - Ensure `DRY_RUN=true` is the default so the image is safe to run without explicit override
    - _Requirements: 32.2, 32.4_

  - [x] 11.3 Update `docker-compose.yml` for full local stack
    - Services: `bot` (worker), `dashboard` (uvicorn), `postgres` (postgres:16), `redis` (redis:7)
    - Both `bot` and `dashboard` depend on `postgres` and `redis` with health checks
    - Mount `.env` file; expose dashboard on port 8000
    - Add `alembic upgrade head` as an init container or entrypoint step before worker starts
    - _Requirements: 32.3_

  - [x] 11.4 Create `fly.toml` Fly.io deployment config
    - Configure app name, region, `[build]` section pointing to Dockerfile
    - Define two processes: `worker` (`python -m app.main`) and `web` (`uvicorn app.dashboard.api:app --host 0.0.0.0 --port 8080`)
    - Set `[[services]]` for the web process on port 8080 with health check at `/health`
    - _Requirements: 32.7_

  - [x] 11.5 Create Railway/Render deployment config files
    - Create `railway.json` with `build.builder = "DOCKERFILE"` and two services: worker and dashboard
    - Create `render.yaml` with two services: `lorapok-worker` (worker command) and `lorapok-dashboard` (uvicorn command), both referencing the same Dockerfile
    - _Requirements: 32.7_

  - [x] 11.6 Generate and verify Alembic migrations
    - Run `alembic revision --autogenerate -m "add_all_new_models"` to generate migration from all Phase 1–9 model additions
    - Review generated migration for correctness; add UNIQUE constraints and indexes manually if autogenerate misses them
    - Verify `alembic upgrade head` runs cleanly against a fresh PostgreSQL instance
    - _Requirements: 32.3_

  - [x] 11.7 Update `.env.example` with all new environment variables
    - Document all new vars: `STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET`, `STRIPE_PRICE_*`, `SLACK_WEBHOOK_URL`, `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`, `SUBREDDIT_NAMES`, `TENANT_ID`, `WHITE_LABEL_NAME`, `WHITE_LABEL_LOGO_URL`
    - Add comments explaining each variable's purpose and which tier requires it
    - _Requirements: 32.6, 34.1_


- [x] 12. Phase 12 — Testing & Launch Readiness
  - [x] 12.1 Write unit tests for all new domain modules
    - `tests/test_memory.py`: `remember_case` → `recent_cases` round-trip; `find_similar_cases` with matching and non-matching queries
    - `tests/test_queue.py`: `queue_case` → `list_queue` → `resolve_case` state machine; `was_override` detection for all action combinations
    - `tests/test_classifier.py`: `_normalize_confidence` clamping at 0.0 and 1.0; `_to_decision` with missing keys, wrong types, empty dict
    - `tests/test_metrics.py`: `MetricsStore.increment` with multiple calls; `flush_to_db` upsert logic with SQLite
    - `tests/test_github_worker.py`: `monitor_repositories` idempotency with mocked `httpx` responses
    - `tests/test_reputation.py`: `compute_reputation_score` formula correctness; score clamping at boundaries
    - `tests/test_spam_detector.py`: signal fires at exactly 3 subreddits; returns `None` at 2; score monotonicity across 3–10 subreddits
    - `tests/test_health_score.py`: each component in `[0, 25]`; `total == sum(components)` for multiple DB states
    - `tests/test_features.py`: feature matrix coverage for all 5 tiers; AI quota enforcement; unknown tenant returns `False`; tier hierarchy is cumulative
    - `tests/test_flair_engine.py`: post flair assignment with matching and non-matching keywords; user flair batch with tier change detection
    - `tests/test_modmail_triage.py`: category routing for all 5 categories; SLA deadline by tier; duplicate conversation guard
    - `tests/test_content_calendar.py`: `publish_due_posts` idempotency; `schedule_post` rejects past `post_at`; status transitions
    - _Requirements: 2.1–20.10_

  - [x]* 12.2 Write all 18 property-based tests in `tests/test_properties.py`
    - **Property 1: Rule engine is deterministic and pure** — `@given(st.text())`
    - **Property 2: Rule engine always returns valid action and confidence** — `@given(st.text())`
    - **Property 3: AI classifier never raises** — `@given(st.text())`
    - **Property 4: `build_trending_thread` always returns non-empty title and body** — `@given(st.lists(st.dictionaries(st.text(), st.text())))`
    - **Property 5: `queue_case` → `list_queue` round-trip** — with SQLite in-memory DB
    - **Property 6: `resolve_case` is idempotent on status** — with SQLite in-memory DB
    - **Property 7: `monitor_repositories` is idempotent** — with mocked httpx
    - **Property 8: `MetricsStore` thread-safety** — concurrent increment + flush
    - **Property 9: `stable_hash` collision-resistance** — `@given(st.text(), st.text())`
    - **Property 10: `_to_decision` always produces valid `ModerationDecision`** — `@given(st.dictionaries(st.text(), st.one_of(st.text(), st.integers(), st.floats(allow_nan=False))))`
    - **Property 11: `compute_reputation_score` is bounded** — `@given(st.integers(min_value=0), ...)`
    - **Property 12: `has_feature` returns False for unknown tenant** — `@given(st.text())`
    - **Property 13: `detect_cross_sub_spam` requires at least 3 subreddits** — with SQLite in-memory DB
    - **Property 14: `compute_health_score` components sum to total** — with mocked DB state
    - **Property 15: `dispatch_event` never raises to caller** — with mocked unreachable URLs
    - **Property 16: `sync_policy` is idempotent** — with mocked PRAW
    - **Property 17: `triage_conversation` inserts exactly one record per conversation** — with SQLite in-memory DB
    - **Property 18: Scheduled post publish is idempotent** — with SQLite in-memory DB
    - _Requirements: 2.3, 2.4, 3.1–3.5, 4.1, 4.2, 4.4, 5.4, 6.1, 6.2, 8.7, 13.5, 14.1, 14.2, 20.5, 21.1, 21.5, 23.3, 26.7, 28.1_

  - [x] 12.3 Write integration tests for billing and webhooks
    - Test full Stripe webhook flow with mocked `stripe.Webhook.construct_event`: valid event updates tier; invalid signature returns 400
    - Test `dispatch_event` with mocked `httpx`: assert HMAC-SHA256 `X-Lorapok-Signature` header present and correct; assert retry on 500 response
    - Test feature gate middleware: assert 403 on quota-exceeded AI call; assert 200 when feature is available
    - _Requirements: 27.5–27.10, 26.3, 26.4, 28.6, 28.10_

  - [x] 12.4 Write integration tests for moderation pipeline and policy sync
    - Test full comment pipeline with mocked PRAW comment: `process_comment` → assert `ModerationDecisionRecord` inserted and `metrics_store` incremented
    - Test `sync_policy` with mocked PRAW: assert `PolicySyncRecord` inserted per target; assert idempotency on second call
    - Test `monitor_repositories` with mocked `httpx`: assert `PendingPost` and `GithubUpdateTracker` rows; assert idempotency
    - _Requirements: 1.1–1.10, 8.7, 8.8, 21.5_

  - [x] 12.5 Safety and dry-run testing
    - Verify `DRY_RUN=true` prevents all Reddit write operations: `comment.mod.remove()`, `comment.reply()`, `submission.flair.select()`, `subreddit.flair.set()`, `submission.mod.sticky()`
    - Verify bot starts and processes events with only required env vars set (Reddit credentials + DB URL + Redis URL)
    - Test ambiguous content routing: assert ambiguous comments are queued, not removed
    - _Requirements: 1.8, 32.4, 32.5_

  - [x] 12.6 Rewrite `README.md` for launch
    - Add project description, feature list by tier, architecture diagram (Mermaid), and screenshots of the dashboard
    - Add one-click Railway deploy button and Fly.io deploy instructions
    - Add local development quickstart: clone → `cp .env.example .env` → `docker compose up`
    - Add Reddit bot approval statement: human review for uncertain cases, dry-run default, least-privilege scopes, transparent actions
    - Add link to GitHub Pages marketing site and docs
    - _Requirements: 32.7_

  - [x] 12.7 Final checkpoint — full test suite passes
    - Run `pytest tests/ --tb=short` and confirm all tests pass
    - Run `ruff check app tests` and confirm zero lint errors
    - Run `pip-audit` and confirm no known vulnerabilities
    - _Requirements: 34.8_

---

## Notes

- Tasks marked with `*` are optional and can be skipped for a faster MVP
- Each task references specific requirements from `requirements.md` for traceability
- Property tests use `hypothesis` — add `hypothesis` to `requirements.txt` in task 1.1
- All Reddit write operations must be guarded by `settings.dry_run` check
- All tenant-scoped DB queries must include a `tenant_id` filter (Requirement 28.12)
- Feature flag checks are required at both API middleware layer and domain layer before any Reddit API call
- The `stable_hash` / `normalize_text` utilities in `app/utils/text.py` are used throughout — do not duplicate
- Checkpoints at tasks 2.11, 6.8, 9.10, and 12.7 ensure incremental validation
