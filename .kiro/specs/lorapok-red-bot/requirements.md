# Requirements Document: Lorapok Red Bot

## Introduction

Lorapok Red Bot is a full-spectrum Reddit automation platform and commercial SaaS product.
It automates every controllable surface of the Reddit API — moderation, user management, flair,
wiki, modmail, widgets, rules, analytics, and content scheduling — wrapped in a professional
dashboard built with the Lorapok Design Language (glassmorphism, animated biological UI, dark
theme with glowing accents).

The system is deployed for free on Railway/Render/Fly.io (bot worker + FastAPI dashboard) and
GitHub Pages (public marketing site). Commercially it operates as a tiered SaaS product with
Free, Starter ($19/mo), Pro ($49/mo), Agency ($149/mo), and Enterprise (custom) plans, each
gated by a feature-flag and tenant-isolation layer backed by Stripe subscriptions.

This document derives requirements from the approved design document at
`.kiro/specs/lorapok-red-bot/design.md` and the business model at
`.kiro/specs/lorapok-red-bot/business.md`.

---

## Glossary

- **Worker**: The background process (`app/main.py`) that streams Reddit events and orchestrates all domain calls.
- **Rule_Engine**: The deterministic, zero-latency first-pass filter (`app/moderation/rules.py`).
- **Classifier**: The AI-powered second-pass classifier via LiteLLM (`app/moderation/classifier.py`).
- **Queue**: The human-in-the-loop review queue (`app/moderation/queue.py`).
- **Memory**: The decision audit trail and similarity search store (`app/moderation/memory.py`).
- **Spam_Detector**: The cross-subreddit spam detection module (`app/moderation/spam_detector.py`).
- **Sentiment_Analyzer**: The sentiment analysis module (`app/moderation/sentiment.py`).
- **Flair_Engine**: The flair automation engine (`app/subreddit/flair_engine.py`).
- **Wiki_Manager**: The wiki page automation module (`app/subreddit/wiki_manager.py`).
- **Widget_Manager**: The sidebar widget management module (`app/subreddit/widget_manager.py`).
- **Rules_Engine_v2**: The subreddit rules and removal reasons manager (`app/subreddit/rules_engine.py`).
- **Modmail_Triage**: The modmail categorisation and auto-reply bot (`app/subreddit/modmail_triage.py`).
- **Settings_Manager**: The subreddit settings automation module (`app/subreddit/settings_manager.py`).
- **Reputation_System**: The user reputation scoring module (`app/users/reputation.py`).
- **Ban_Appeal_Workflow**: The ban appeal automation module (`app/users/ban_appeals.py`).
- **Onboarding_Flow**: The new subscriber welcome and flair assignment module (`app/users/onboarding.py`).
- **Contributor_Manager**: The contributor promotion/demotion module (`app/users/contributors.py`).
- **Mod_Notes**: The moderator notes system (`app/users/mod_notes.py`).
- **Engagement_Predictor**: The post engagement prediction module (`app/analytics/engagement.py`).
- **Content_Calendar**: The scheduled post management module (`app/posting/content_calendar.py`).
- **Cohort_Analyzer**: The user cohort analysis module (`app/analytics/cohort.py`).
- **Health_Score**: The subreddit health scoring module (`app/analytics/health_score.py`).
- **Multi_Sub_Dashboard**: The multi-subreddit aggregate analytics module (`app/analytics/multi_sub.py`).
- **Trending_Builder**: The trending post content builder (`app/posting/trending.py`).
- **Scheduler**: The APScheduler background job manager (`app/posting/scheduler.py`).
- **GitHub_Integration**: The GitHub API monitoring module (`app/integrations/github_integration.py`).
- **Discord_Integration**: The Discord webhook alert module (`app/integrations/discord_integration.py`).
- **Slack_Integration**: The Slack webhook and slash command module (`app/integrations/slack_integration.py`).
- **Telegram_Integration**: The Telegram bot command module (`app/integrations/telegram_integration.py`).
- **Webhook_Dispatcher**: The outbound webhook dispatch module (`app/integrations/webhooks.py`).
- **Billing_Engine**: The Stripe-backed multi-tenant billing system (`app/billing/`).
- **Feature_Flag_System**: The feature entitlement enforcement layer (`app/billing/features.py`).
- **Tenant**: A single paying or free customer account, identified by a UUID `tenant_id`.
- **Dashboard_API**: The FastAPI service exposing the moderator dashboard and JSON endpoints (`app/dashboard/api.py`).
- **ModerationDecision**: The dataclass `{action: str, reason: str, confidence: float}` produced by the Rule_Engine and Classifier.
- **ReviewCaseRecord**: A DB record representing a comment or submission queued for human review.
- **UserReputation**: A DB record tracking per-user karma, post history, ban history, and computed reputation score.
- **SpamSignal**: A dataclass representing a detected cross-subreddit spam pattern.
- **TenantConfig**: A DB record holding all per-tenant configuration including tier, subreddit list, and billing IDs.
- **ScheduledPost**: A DB record representing a post queued for future publication.
- **ModmailRecord**: A DB record representing a triaged modmail conversation.
- **WebhookConfig**: A DB record representing a customer-configured outbound webhook endpoint.
- **SLA**: Service Level Agreement — the maximum time allowed before a modmail conversation requires human attention.
- **HMAC**: Hash-based Message Authentication Code — used to sign outbound webhook payloads.
- **PRAW**: Python Reddit API Wrapper — the library used for all Reddit API interactions.
- **LiteLLM**: The multi-provider LLM router used for AI classification, summarisation, and sentiment analysis.
- **Dry_Run**: An operating mode where all Reddit write operations are replaced with log statements.
- **Lorapok_Design_Language**: The visual design system (glassmorphism, biological UI, dark theme, glowing accents) applied to the dashboard and marketing site.


---

## Requirements

### Requirement 1: Comment and Submission Stream Processing

**User Story:** As a subreddit moderator, I want the bot to continuously monitor new comments
and submissions in real time, so that moderation actions are applied automatically without
manual intervention.

#### Acceptance Criteria

1. WHEN a new comment event is received from the Reddit stream, THE Worker SHALL apply
   `apply_light_rules` before invoking the Classifier.
2. WHEN `apply_light_rules` returns `action="remove"` AND `confidence >= review_confidence_threshold`,
   THE Worker SHALL remove the comment and post a removal notice without calling the Classifier.
3. WHEN `apply_light_rules` returns `action="review"` OR `confidence < review_confidence_threshold`,
   THE Worker SHALL invoke the Classifier to obtain a second-pass decision.
4. WHEN the Classifier returns `action="review"` OR `confidence < review_confidence_threshold`,
   THE Worker SHALL call `queue_case` and SHALL NOT apply any Reddit action to the comment.
5. WHEN a non-queued moderation decision is applied, THE Worker SHALL call `remember_case` exactly once.
6. WHEN any comment is processed regardless of outcome, THE Worker SHALL increment the
   `comments_processed` metric exactly once.
7. WHEN any per-item exception occurs during stream processing, THE Worker SHALL log the error,
   send an alert to configured notification channels, and continue processing the next item.
8. WHEN `dry_run=True`, THE Worker SHALL replace all Reddit write operations with log statements
   and SHALL NOT modify any Reddit content.
9. WHILE the comment stream is active, THE Worker SHALL enforce a minimum 2-second interval
   between processing cycles to comply with Reddit API rate limits.
10. WHEN a new submission event is received, THE Worker SHALL apply the same moderation pipeline
    as for comments.


---

### Requirement 2: Moderation Rule Engine

**User Story:** As a subreddit moderator, I want fast, deterministic first-pass filtering of
comments, so that obvious spam and policy violations are caught instantly without AI latency.

#### Acceptance Criteria

1. THE Rule_Engine SHALL return a `ModerationDecision` with `action` in `{"allow", "review", "remove"}`
   for all string inputs including empty strings.
2. THE Rule_Engine SHALL return `confidence` in `[0.0, 1.0]` for all inputs.
3. THE Rule_Engine SHALL be deterministic: calling `apply_light_rules(t)` any number of times
   with the same input `t` SHALL return identical `action`, `reason`, and `confidence` values.
4. THE Rule_Engine SHALL perform no I/O, no database access, and no external calls.
5. WHEN a hard-spam term is matched, THE Rule_Engine SHALL return `action="remove"` with
   `confidence=0.95`.
6. WHEN an ambiguous term is matched but no hard-spam term is present, THE Rule_Engine SHALL
   return `action="review"` with `confidence=0.55`.
7. WHEN no term is matched, THE Rule_Engine SHALL return `action="allow"` with `confidence=0.70`.

---

### Requirement 3: AI Classifier

**User Story:** As a subreddit moderator, I want AI-assisted classification of ambiguous
content, so that nuanced policy violations are caught that simple keyword rules would miss.

#### Acceptance Criteria

1. THE Classifier SHALL never raise an exception for any input string, including empty strings
   and strings containing special characters.
2. THE Classifier SHALL return a dict with keys `action`, `reason`, and `confidence` for all inputs.
3. THE Classifier SHALL return `action` in `{"allow", "review", "remove"}`, coercing any
   unexpected LLM output to `"review"`.
4. THE Classifier SHALL return `confidence` clamped to `[0.0, 1.0]`.
5. IF the LLM API is unavailable or returns malformed JSON, THEN THE Classifier SHALL return
   `{"action": "review", "reason": "Classifier failure: <error>", "confidence": 0.0}`.
6. WHERE the `model` parameter is provided, THE Classifier SHALL route the request to that
   specific LiteLLM provider.
7. THE Classifier SHALL support at minimum OpenAI, Anthropic, Gemini, and Mistral as LLM providers.


---

### Requirement 4: Human-in-the-Loop Review Queue

**User Story:** As a subreddit moderator, I want uncertain moderation cases queued for my
review, so that I can make the final call on ambiguous content without the bot acting unilaterally.

#### Acceptance Criteria

1. WHEN `queue_case` is called, THE Queue SHALL contain exactly one more entry with
   `status="pending"` than before the call.
2. WHEN `list_queue` is called with `status="pending"`, THE Queue SHALL return all and only
   records with `status="pending"`.
3. WHEN `resolve_case` is called with a valid `case_id` and `status`, THE Queue SHALL update
   the record's status and record the `reviewer_note`.
4. WHEN `resolve_case` is called twice with the same `case_id` and `status`, THE Queue SHALL
   produce the same final DB state as calling it once (idempotent).
5. WHEN `resolve_case` is called with an unknown `case_id`, THE Queue SHALL return `False`
   without modifying any record.
6. THE Queue SHALL record `was_override=True` when a moderator's decision differs from the
   bot's `recommended_action`.
7. THE Queue SHALL support `status` values of `"pending"`, `"approved"`, `"rejected"`, and
   `"escalated"` only.

---

### Requirement 5: Decision Memory and Audit Trail

**User Story:** As a subreddit moderator, I want every bot decision recorded with its reason
and source, so that I can audit past actions and the bot can learn from moderator overrides.

#### Acceptance Criteria

1. WHEN `remember_case` is called, THE Memory SHALL include the case in the output of
   `recent_cases` on the next call.
2. THE Memory SHALL store `text`, `action`, `reason`, `source`, and `created_at` for every
   recorded case.
3. WHEN `find_similar_cases` is called with a query text, THE Memory SHALL return up to
   `limit` cases ordered by semantic similarity to the query.
4. THE Memory SHALL store a SHA-256 hash of the normalised text as `text_hash` for efficient
   deduplication and lookup.
5. THE Memory SHALL persist all records to PostgreSQL and survive process restarts.


---

### Requirement 6: Cross-Subreddit Spam Detection

**User Story:** As a moderator managing multiple subreddits, I want coordinated spam detected
automatically across all my communities, so that bad actors cannot evade bans by posting the
same content in different subreddits.

#### Acceptance Criteria

1. WHEN the same `(username, content_hash)` pair appears in fewer than 3 distinct subreddits
   within the detection window, THE Spam_Detector SHALL return `None`.
2. WHEN the same `(username, content_hash)` pair appears in 3 or more distinct subreddits
   within the detection window, THE Spam_Detector SHALL return a `SpamSignal` with
   `score in [0.0, 1.0]` and `occurrences >= 3`.
3. THE Spam_Detector score SHALL increase monotonically as the number of affected subreddits
   increases.
4. THE Spam_Detector SHALL use `stable_hash(normalize_text(content))` as the content hash to
   ensure equivalent content is matched regardless of minor formatting differences.
5. WHEN a `SpamSignal` with `score >= 0.7` is detected, THE Worker SHALL queue the submission
   for human review with the spam signal details as the reason.
6. THE Spam_Detector SHALL only compare submissions within subreddits managed by the same Tenant.

---

### Requirement 7: Sentiment Analysis

**User Story:** As a subreddit moderator, I want automated sentiment monitoring with alerts
when community tone deteriorates, so that I can intervene before toxic trends escalate.

#### Acceptance Criteria

1. WHEN `analyze_sentiment` is called with a text string, THE Sentiment_Analyzer SHALL return
   a `SentimentResult` with `score in [-1.0, 1.0]` and `label` in
   `{"positive", "neutral", "negative"}`.
2. WHEN `record_sentiment` is called, THE Sentiment_Analyzer SHALL persist the score and label
   to the `sentiment_data` table.
3. WHEN `get_sentiment_trend` is called, THE Sentiment_Analyzer SHALL return data points
   ordered chronologically for the requested number of days.
4. WHEN the 3-day rolling average sentiment score drops below the configured threshold
   (default `-0.3`), THE Sentiment_Analyzer SHALL trigger an alert to configured notification
   channels.
5. WHERE the Pro tier or higher is active, THE System SHALL run sentiment analysis on incoming
   comments and submissions.


---

### Requirement 8: Subreddit Settings Manager

**User Story:** As a subreddit moderator, I want to automate reading and writing all subreddit
settings, so that I can apply configuration changes programmatically and keep multiple
subreddits in sync.

#### Acceptance Criteria

1. WHEN `get_settings` is called, THE Settings_Manager SHALL return a `SubredditSettingsSnapshot`
   containing all current subreddit settings retrieved via `SubredditModeration.settings()`.
2. WHEN `update_settings` is called with `dry_run=False`, THE Settings_Manager SHALL apply the
   provided settings delta via `SubredditModeration.update()` and return `True` on success.
3. WHEN `update_settings` is called with `dry_run=True`, THE Settings_Manager SHALL log the
   intended changes without applying them and return `True`.
4. WHEN `schedule_setting_change` is called, THE Settings_Manager SHALL persist the settings
   delta and `apply_at` timestamp to the database and return a unique change ID.
5. WHEN `apply_scheduled_changes` is called by the Scheduler, THE Settings_Manager SHALL apply
   all pending changes whose `apply_at` timestamp is in the past.
6. WHEN `accept_mod_invite` is called, THE Settings_Manager SHALL accept the moderator
   invitation for the specified subreddit via PRAW.
7. WHEN `sync_policy` is called, THE Settings_Manager SHALL copy the specified policy types
   (rules, removal reasons, flair templates) from the source subreddit to each target subreddit.
8. WHEN `sync_policy` is called twice with the same arguments, THE Settings_Manager SHALL
   produce the same target subreddit state as calling it once (idempotent).
9. WHEN `sync_policy` partially fails for one target, THE Settings_Manager SHALL commit
   successful syncs and report the failure in `SyncResult.errors` without rolling back
   successful targets.
10. THE Settings_Manager SHALL support all PRAW `SubredditModeration.update()` settings keys
    including `subreddit_type`, `allow_images`, `allow_videos`, `allow_polls`, `wikimode`,
    and all other documented settings.


---

### Requirement 9: Flair Automation Engine

**User Story:** As a subreddit moderator, I want post flair assigned automatically based on
content and user flair updated based on karma tiers, so that my subreddit stays organised
without manual flair management.

#### Acceptance Criteria

1. WHEN a new submission is received and the Tenant has the `flair_automation` feature,
   THE Flair_Engine SHALL classify the submission content and assign the best-matching flair
   template via `submission.flair.select(template_id)`.
2. WHEN no matching flair template is found for a submission, THE Flair_Engine SHALL return
   `None` and leave the submission unflagged.
3. WHEN `run_user_flair_batch` is called, THE Flair_Engine SHALL update the flair of every
   active user whose computed flair tier has changed since the last batch run.
4. WHEN `create_flair_template` is called, THE Flair_Engine SHALL create the template via
   PRAW and persist the template metadata to the `flair_templates` table.
5. WHEN `delete_flair_template` is called, THE Flair_Engine SHALL remove the template from
   Reddit and delete the corresponding record from the database.
6. WHEN `list_flair_templates` is called, THE Flair_Engine SHALL return all templates for the
   specified subreddit and flair type from the database.
7. THE Flair_Engine SHALL support both `"link"` (post) and `"user"` flair types.
8. WHEN a flair assignment is made, THE Flair_Engine SHALL insert a `FlairAssignmentRecord`
   with `source` set to `"auto_content"`, `"auto_karma"`, or `"manual"` as appropriate.

---

### Requirement 10: Wiki Manager

**User Story:** As a subreddit moderator, I want wiki pages updated automatically from bot
data, so that the FAQ and changelog stay current without manual editing.

#### Acceptance Criteria

1. WHEN `get_wiki_page` is called, THE Wiki_Manager SHALL return the current content of the
   specified wiki page via PRAW.
2. WHEN `update_wiki_page` is called, THE Wiki_Manager SHALL write the new content to Reddit
   via `subreddit.wiki[page_name].edit(content, reason)` and return `True` on success.
3. WHEN `list_wiki_pages` is called, THE Wiki_Manager SHALL return the names of all wiki pages
   in the subreddit.
4. WHEN `get_wiki_revision_history` is called, THE Wiki_Manager SHALL return a list of
   `WikiRevision` objects ordered from most recent to oldest.
5. WHEN `auto_update_faq` is called, THE Wiki_Manager SHALL regenerate the FAQ page content
   from the database and post it to the subreddit wiki.
6. WHEN `auto_update_changelog` is called, THE Wiki_Manager SHALL append the latest GitHub
   release notes to the changelog wiki page.
7. WHERE the Pro tier or higher is active, THE Scheduler SHALL call `auto_update_faq` and
   `auto_update_changelog` on a configurable schedule.


---

### Requirement 11: Sidebar Widget Manager

**User Story:** As a subreddit moderator, I want sidebar widgets updated automatically with
live community stats, so that visitors always see current information without manual updates.

#### Acceptance Criteria

1. WHEN `list_widgets` is called, THE Widget_Manager SHALL return all current sidebar widgets
   for the subreddit via `SubredditWidgets`.
2. WHEN `update_text_widget` is called, THE Widget_Manager SHALL update the specified widget's
   text content and return `True` on success.
3. WHEN `update_community_stats_widget` is called, THE Widget_Manager SHALL fetch current
   subscriber and active user counts from the database and update the community stats widget.
4. WHEN `add_button_widget` is called, THE Widget_Manager SHALL create a new button widget
   with the specified text and URL and return the new widget ID.
5. WHEN `remove_widget` is called, THE Widget_Manager SHALL delete the specified widget and
   return `True` on success.
6. THE Widget_Manager SHALL support Button, Calendar, CommunityList, Custom, Image, Menu,
   PostFlair, Rules, and TextArea widget types.

---

### Requirement 12: Rules Engine v2

**User Story:** As a subreddit moderator, I want subreddit rules and removal reasons managed
programmatically with per-user violation tracking, so that rule enforcement is consistent and
repeat offenders are identified automatically.

#### Acceptance Criteria

1. WHEN `list_rules` is called, THE Rules_Engine_v2 SHALL return all current subreddit rules
   via `SubredditRules`.
2. WHEN `add_rule` is called, THE Rules_Engine_v2 SHALL create the rule on Reddit and return
   `True` on success.
3. WHEN `delete_rule` is called, THE Rules_Engine_v2 SHALL remove the rule from Reddit and
   return `True` on success.
4. WHEN `list_removal_reasons` is called, THE Rules_Engine_v2 SHALL return all removal reasons
   via `SubredditRemovalReasons`.
5. WHEN `add_removal_reason` is called, THE Rules_Engine_v2 SHALL create the removal reason
   on Reddit and return the new reason ID.
6. WHEN `delete_removal_reason` is called, THE Rules_Engine_v2 SHALL remove the removal reason
   from Reddit and return `True` on success.
7. WHEN `track_rule_violation` is called, THE Rules_Engine_v2 SHALL insert a
   `RuleViolationRecord` linking the username, subreddit, rule, and content ID.
8. WHEN `get_user_violation_history` is called, THE Rules_Engine_v2 SHALL return all
   `RuleViolationRecord` entries for the specified user and subreddit ordered by `created_at`
   descending.


---

### Requirement 13: Modmail Triage Bot

**User Story:** As a subreddit moderator, I want modmail conversations categorised and common
questions answered automatically, so that my modmail inbox stays manageable and response times
meet SLA targets.

#### Acceptance Criteria

1. WHEN a new modmail conversation is received, THE Modmail_Triage SHALL classify it into one
   of `{"ban_appeal", "spam_report", "question", "feedback", "unknown"}` using the Classifier.
2. WHEN the category is `"ban_appeal"`, THE Modmail_Triage SHALL send the ban appeal
   acknowledgement template and insert a `BanAppealRecord`.
3. WHEN the category is `"common_question"` AND `confidence >= 0.85`, THE Modmail_Triage SHALL
   reply with the matching FAQ template and archive the conversation.
4. WHEN the category is `"unknown"` OR `confidence < 0.60`, THE Modmail_Triage SHALL set the
   conversation status to `"needs_human"` and alert the moderator dashboard.
5. WHEN `triage_conversation` is called for the same `conversation_id` a second time, THE
   Modmail_Triage SHALL NOT insert a duplicate `ModmailRecord` (idempotent).
6. WHEN the Tenant tier is Free, THE Modmail_Triage SHALL set `sla_deadline=None` for all
   triaged conversations.
7. WHEN the Tenant tier is Starter, THE Modmail_Triage SHALL set `sla_deadline` to 48 hours
   from the conversation creation time.
8. WHEN the Tenant tier is Pro, THE Modmail_Triage SHALL set `sla_deadline` to 24 hours from
   the conversation creation time.
9. WHEN the Tenant tier is Agency or Enterprise, THE Modmail_Triage SHALL set `sla_deadline`
   to 4 hours from the conversation creation time.
10. WHEN `auto_replied=True` is set on a `ModmailTriageResult`, THE Modmail_Triage SHALL have
    actually sent a reply to Reddit (not merely logged the intent).
11. WHEN `create_modmail_template` is called, THE Modmail_Triage SHALL persist the template
    to the `modmail_templates` table and return the new template ID.
12. THE Modmail_Triage SHALL support template variable substitution for `{{username}}`,
    `{{subreddit}}`, and `{{ban_reason}}` placeholders.


---

### Requirement 14: User Reputation System

**User Story:** As a subreddit moderator, I want a composite reputation score for every user,
so that flair assignment, contributor promotion, and ban appeal decisions are based on
objective community contribution data.

#### Acceptance Criteria

1. THE Reputation_System SHALL compute `reputation_score` using the formula:
   `(approved_posts * 2 + approved_comments * 1 - removed_posts * 5 - bans * 20) / max(1, account_age_days)`.
2. THE Reputation_System SHALL clamp `reputation_score` to `[-100.0, 100.0]` for all valid inputs.
3. THE Reputation_System SHALL be deterministic: the same `UserReputation` input always
   produces the same score.
4. THE Reputation_System SHALL perform no I/O or side effects during score computation.
5. WHEN `get_or_create_reputation` is called, THE Reputation_System SHALL return the existing
   record if one exists for `(username, subreddit_name)`, or create a new one with zero counts.
6. WHEN `update_reputation` is called, THE Reputation_System SHALL apply the `ReputationDelta`
   and recompute `reputation_score` before saving.
7. WHEN `flag_suspicious_user` is called, THE Reputation_System SHALL set `is_suspicious=True`
   on the user's reputation record.
8. THE `user_reputations` table SHALL enforce a UNIQUE constraint on `(username, subreddit_name)`.

---

### Requirement 15: Ban Appeal Workflow

**User Story:** As a subreddit moderator, I want ban appeals reviewed automatically based on
reputation and ban history, so that clear-cut cases are resolved without moderator time and
borderline cases are escalated for human review.

#### Acceptance Criteria

1. WHEN `create_ban_appeal` is called, THE Ban_Appeal_Workflow SHALL insert a `BanAppeal`
   record with `status="pending"` and return the record.
2. WHEN `auto_review_appeal` is called and `reputation_score > 50` AND `ban_age > 90 days`
   AND the user has no prior bans, THE Ban_Appeal_Workflow SHALL set `auto_decision="approve"`.
3. WHEN `auto_review_appeal` is called and the user has 3 or more prior bans on record,
   THE Ban_Appeal_Workflow SHALL set `auto_decision="reject"`.
4. WHEN `auto_review_appeal` is called and neither auto-approve nor auto-reject criteria are
   met, THE Ban_Appeal_Workflow SHALL set `auto_decision="escalate"`.
5. WHEN `resolve_appeal` is called, THE Ban_Appeal_Workflow SHALL update the appeal's
   `final_decision`, `reviewer_note`, `status`, and `resolved_at` fields.
6. WHEN `get_pending_appeals` is called, THE Ban_Appeal_Workflow SHALL return all appeals with
   `status="pending"` for the specified subreddit.


---

### Requirement 16: User Onboarding Flow

**User Story:** As a subreddit moderator, I want new subscribers welcomed automatically with
a personalised DM and initial flair assignment, so that new members feel welcomed and
understand community norms from day one.

#### Acceptance Criteria

1. WHEN a new subscriber event is received, THE Onboarding_Flow SHALL check whether the user
   has already been welcomed via `is_welcomed`.
2. WHEN the user has not yet been welcomed, THE Onboarding_Flow SHALL send a welcome DM via
   `reddit.redditor(username).message(...)` using the configured welcome template.
3. WHEN the welcome DM is sent, THE Onboarding_Flow SHALL call `mark_welcomed` to record the
   event and prevent duplicate welcomes.
4. WHEN the user is eligible for auto-flair after onboarding, THE Onboarding_Flow SHALL call
   the Flair_Engine to assign the appropriate flair.
5. WHEN the user has already been welcomed, THE Onboarding_Flow SHALL take no action.
6. IF the welcome DM fails to send, THEN THE Onboarding_Flow SHALL log the error and SHALL
   NOT mark the user as welcomed, allowing a retry on the next event.

---

### Requirement 17: Contributor Management

**User Story:** As a subreddit moderator, I want trusted users promoted to approved contributor
status automatically and inactive contributors removed, so that the contributor list stays
current without manual maintenance.

#### Acceptance Criteria

1. WHEN `run_contributor_promotion_batch` is called, THE Contributor_Manager SHALL promote
   every user with `reputation_score > 30` AND `account_age_days > 30` AND no active bans
   via `subreddit.contributor.add(user)`.
2. WHEN `run_contributor_demotion_batch` is called, THE Contributor_Manager SHALL remove
   every contributor with no activity in the past 180 days via
   `subreddit.contributor.remove(user)`.
3. WHEN `add_contributor` is called, THE Contributor_Manager SHALL add the user as a
   contributor via PRAW and return `True` on success.
4. WHEN `remove_contributor` is called, THE Contributor_Manager SHALL remove the user from
   contributors via PRAW and return `True` on success.
5. WHEN a promotion or demotion is applied, THE Contributor_Manager SHALL update
   `UserReputation.is_contributor` accordingly.


---

### Requirement 18: Mod Notes System

**User Story:** As a subreddit moderator, I want bot actions automatically annotated with mod
notes on Reddit, so that the full moderation history is visible to all moderators in the
native Reddit interface.

#### Acceptance Criteria

1. WHEN `add_mod_note` is called, THE Mod_Notes SHALL create a note on Reddit via
   `subreddit.mod.notes` and return `True` on success.
2. WHEN `get_mod_notes` is called, THE Mod_Notes SHALL return all notes for the specified
   user and subreddit from Reddit via PRAW.
3. WHEN `auto_note_on_action` is called, THE Mod_Notes SHALL create a mod note with the
   appropriate label and persist a `ModNote` record to the database.
4. THE Mod_Notes SHALL support labels `"BOT_BAN"`, `"BOT_SPAM"`, `"BOT_REVIEW"`, and
   `"HUMAN_OVERRIDE"`.
5. WHEN `search_mod_notes` is called, THE Mod_Notes SHALL return all `ModNote` records
   matching the query string for the specified subreddit.
6. WHEN a moderator overrides a bot decision, THE Mod_Notes SHALL automatically create a
   `"HUMAN_OVERRIDE"` note recording the original bot action and the moderator's decision.

---

### Requirement 19: Engagement Predictor and Auto-Pin

**User Story:** As a subreddit moderator, I want high-potential posts identified and pinned
automatically, so that the best content gets maximum visibility without me monitoring the
feed manually.

#### Acceptance Criteria

1. WHEN `predict_engagement` is called, THE Engagement_Predictor SHALL return an
   `EngagementPrediction` with `score in [0.0, 1.0]`, `predicted_upvotes >= 0`, and
   `confidence in [0.0, 0.9]`.
2. WHEN `historical_data` is empty, THE Engagement_Predictor SHALL return `confidence=0.3`
   and base `predicted_upvotes` on upvote velocity alone.
3. WHEN `historical_data` contains entries, THE Engagement_Predictor SHALL increase
   `confidence` by `0.01` per entry up to a maximum of `0.9`.
4. WHEN `auto_pin_high_potential` is called, THE Engagement_Predictor SHALL pin submissions
   whose `score` exceeds the configured threshold via `submission.mod.sticky()`.
5. WHEN `get_rising_submissions` is called, THE Engagement_Predictor SHALL return up to
   `limit` submissions from `subreddit.rising()`.
6. WHERE the Pro tier or higher is active, THE Scheduler SHALL call `auto_pin_high_potential`
   on a configurable schedule.


---

### Requirement 20: Content Calendar and Scheduled Posts

**User Story:** As a subreddit moderator, I want posts scheduled for optimal times and
published automatically, so that community engagement is maximised without me being online
at specific hours.

#### Acceptance Criteria

1. WHEN `schedule_post` is called with a `post_at` timestamp in the future, THE
   Content_Calendar SHALL insert a `ScheduledPost` record with `status="scheduled"` and
   return the new post ID.
2. IF `schedule_post` is called with a `post_at` timestamp in the past, THEN THE
   Content_Calendar SHALL reject the request with a validation error.
3. WHEN `publish_due_posts` is called by the Scheduler, THE Content_Calendar SHALL submit
   all `ScheduledPost` records whose `post_at <= now()` AND `status="scheduled"` to Reddit.
4. WHEN a post is successfully published, THE Content_Calendar SHALL update its `status` to
   `"published"` and record the `reddit_post_id`.
5. WHEN `publish_due_posts` is called for a post with `status="published"`, THE
   Content_Calendar SHALL NOT re-publish the post (idempotent).
6. WHEN a post fails to publish, THE Content_Calendar SHALL set `status="failed"` and send
   an alert to configured notification channels.
7. WHEN `cancel_scheduled_post` is called, THE Content_Calendar SHALL set the post's
   `status` to `"cancelled"` and return `True`.
8. WHEN `get_optimal_post_times` is called, THE Content_Calendar SHALL analyse historical
   `DailyMetric` data and return the hours with the highest average engagement rates.
9. THE Scheduler SHALL call `publish_due_posts` every minute.
10. THE `ScheduledPost.status` field SHALL only transition through:
    `"scheduled" → "published" | "cancelled" | "failed"`.

---

### Requirement 21: Trending Post Builder

**User Story:** As a subreddit moderator, I want weekly trending discussion threads generated
and posted automatically from GitHub and developer news sources, so that the community always
has fresh, relevant content to engage with.

#### Acceptance Criteria

1. WHEN `build_trending_thread` is called with any list of trend dicts, THE Trending_Builder
   SHALL return a dict with non-empty `title` and `body` strings.
2. WHEN `fetch_trending_repos` is called, THE GitHub_Integration SHALL return repositories
   trending in the specified language over the specified number of days.
3. WHEN `fetch_latest_release` is called, THE GitHub_Integration SHALL return the most recent
   release metadata for the specified repository, or `None` if no release exists.
4. WHEN `fetch_recent_issues` is called, THE GitHub_Integration SHALL return issues created
   within the specified number of days.
5. WHEN `monitor_repositories` is called twice in succession, THE GitHub_Integration SHALL
   produce the same number of `PendingPost` and `GithubUpdateTracker` rows as calling it once
   (idempotent via `external_id` UNIQUE constraint).
6. THE Scheduler SHALL call the trending post pipeline on a weekly schedule.
7. WHEN the GitHub API rate limit is exceeded, THE GitHub_Integration SHALL log a warning and
   return `None` or `[]` without raising an exception.


---

### Requirement 22: Cohort Analysis and Churn Prediction

**User Story:** As a subreddit moderator, I want cohort retention tables and churn risk
identification, so that I can understand community health trends and re-engage at-risk members
before they leave.

#### Acceptance Criteria

1. WHEN `build_cohort_table` is called, THE Cohort_Analyzer SHALL return a `CohortTable`
   grouping users by their join month and tracking their activity in subsequent months.
2. WHEN `get_power_users` is called, THE Cohort_Analyzer SHALL return up to `limit` users
   ordered by `reputation_score` descending.
3. WHEN `get_churn_risk_users` is called, THE Cohort_Analyzer SHALL return users who were
   previously active but have had no activity in the past 30 days.
4. WHERE the Agency tier or higher is active, THE Dashboard_API SHALL expose cohort analysis
   endpoints.

---

### Requirement 23: Subreddit Health Score

**User Story:** As a subreddit moderator, I want a single composite health score for my
subreddit updated regularly, so that I can track overall community health at a glance and
identify which dimension needs attention.

#### Acceptance Criteria

1. WHEN `compute_health_score` is called, THE Health_Score SHALL return a
   `SubredditHealthScore` with `total in [0, 100]`.
2. THE Health_Score SHALL compute four components — growth, engagement, moderation quality,
   and spam rate — each contributing `[0, 25]` points to the total.
3. THE Health_Score `total` SHALL equal `growth + engagement + moderation + spam` for all
   valid inputs.
4. THE Health_Score growth component SHALL be based on subscriber growth rate over the past
   30 days.
5. THE Health_Score engagement component SHALL be based on the average comments-per-post
   ratio over the past 7 days relative to a baseline of 5.0.
6. THE Health_Score moderation component SHALL penalise high removal rates, high override
   rates, and large queue backlogs.
7. THE Health_Score spam component SHALL penalise high spam queue volume relative to total
   submissions.
8. WHERE the Agency tier or higher is active, THE Dashboard_API SHALL expose the health score
   endpoint and THE Scheduler SHALL recompute it on a daily schedule.


---

### Requirement 24: Multi-Subreddit Aggregate Dashboard

**User Story:** As a Reddit marketing agency managing many subreddits, I want a single
dashboard view aggregating metrics across all my managed communities, so that I can monitor
portfolio health without switching between individual subreddit views.

#### Acceptance Criteria

1. WHEN `get_aggregate_metrics` is called, THE Multi_Sub_Dashboard SHALL return combined
   metrics across all subreddits in the Tenant's `managed_subreddits` list.
2. WHEN `get_per_sub_breakdown` is called, THE Multi_Sub_Dashboard SHALL return a
   `SubredditSummary` for each managed subreddit with individual metrics.
3. WHERE the Agency tier or higher is active, THE Dashboard_API SHALL expose the
   `/analytics/multi-sub` endpoint.
4. THE Multi_Sub_Dashboard SHALL only include subreddits belonging to the requesting Tenant.

---

### Requirement 25: Discord, Slack, and Telegram Integrations

**User Story:** As a subreddit moderator, I want bot alerts and commands available in my
team's communication tools, so that I can monitor and control the bot without keeping the
dashboard open.

#### Acceptance Criteria

1. WHEN `send_discord_alert` is called with a non-empty message, THE Discord_Integration
   SHALL POST the message to the configured Discord webhook URL.
2. WHEN the `DISCORD_WEBHOOK_URL` environment variable is not set, THE Discord_Integration
   SHALL return immediately without making any HTTP call.
3. WHEN `send_slack_alert` is called, THE Slack_Integration SHALL POST the message to the
   configured Slack webhook URL and optional channel.
4. WHEN a Slack slash command `/redbot queue` is received, THE Slack_Integration SHALL return
   the current pending review queue count and top items.
5. WHEN a Slack slash command `/redbot approve <id>` or `/redbot reject <id>` is received,
   THE Slack_Integration SHALL call `resolve_case` with the specified ID and return the result.
6. WHEN a Slack slash command `/redbot stats` is received, THE Slack_Integration SHALL return
   current metrics from the Dashboard_API.
7. WHEN a Slack slash command `/redbot health` is received, THE Slack_Integration SHALL return
   the current subreddit health score.
8. WHEN `send_telegram_message` is called, THE Telegram_Integration SHALL POST the message to
   the specified Telegram chat via the Bot API.
9. WHEN a Telegram bot command is received, THE Telegram_Integration SHALL route it to the
   appropriate handler and return a response.
10. IF any notification channel webhook URL is not configured, THEN THE System SHALL skip that
    channel silently without raising an exception.
11. WHERE the Pro tier or higher is active, THE System SHALL enable Slack and Telegram
    integrations.


---

### Requirement 26: Outbound Webhook Dispatcher

**User Story:** As an Agency or Enterprise customer, I want bot events dispatched to my own
endpoints via signed webhooks, so that I can build custom automations and integrations on top
of the bot's event stream.

#### Acceptance Criteria

1. WHEN `register_webhook` is called, THE Webhook_Dispatcher SHALL persist a `WebhookConfig`
   record with the URL, event list, and HMAC signing secret, and return the config.
2. WHEN `dispatch_event` is called, THE Webhook_Dispatcher SHALL POST the event payload to
   every active `WebhookConfig` whose `events` list includes the `event_type`.
3. WHEN dispatching a webhook, THE Webhook_Dispatcher SHALL include an
   `X-Lorapok-Signature: sha256=<hex_digest>` header computed with HMAC-SHA256 over the
   JSON-serialised payload using the webhook's secret.
4. WHEN a webhook delivery fails with a non-2xx response or timeout, THE Webhook_Dispatcher
   SHALL retry up to 3 times with exponential backoff of 2s, 4s, and 8s.
5. WHEN all 3 retries are exhausted, THE Webhook_Dispatcher SHALL increment
   `WebhookConfig.failure_count` and log the failure.
6. WHEN `WebhookConfig.failure_count` reaches 10 consecutive failures, THE Webhook_Dispatcher
   SHALL set `is_active=False` and notify the Tenant.
7. THE Webhook_Dispatcher SHALL never raise an exception to the caller for any event type or
   payload, including unreachable endpoints.
8. THE Webhook_Dispatcher SHALL support event types: `comment.removed`, `submission.removed`,
   `user.banned`, `modmail.received`, `queue.case_added`, `flair.assigned`, `post.published`,
   `health_score.alert`, `sentiment.alert`, and `spam_signal.detected`.
9. WHEN `delete_webhook` is called, THE Webhook_Dispatcher SHALL set `is_active=False` on
   the specified `WebhookConfig` and return `True`.
10. WHERE the Agency tier or higher is active, THE Dashboard_API SHALL expose webhook
    management endpoints (`GET /webhooks`, `POST /webhooks`, `DELETE /webhooks/{id}`).


---

### Requirement 27: Billing Engine and Stripe Integration

**User Story:** As a SaaS operator, I want Stripe-backed subscription management with
automatic tier enforcement, so that customers are billed correctly and feature access is
always consistent with their subscription status.

#### Acceptance Criteria

1. WHEN `create_customer` is called, THE Billing_Engine SHALL create a Stripe Customer object
   and return the `customer_id`.
2. WHEN `create_subscription` is called, THE Billing_Engine SHALL create a Stripe Subscription
   and return the `subscription_id`.
3. WHEN `cancel_subscription` is called, THE Billing_Engine SHALL cancel the Stripe
   Subscription and return `True` on success.
4. WHEN `create_portal_session` is called, THE Billing_Engine SHALL create a Stripe Billing
   Portal session and return the session URL for redirect.
5. WHEN a `customer.subscription.updated` Stripe webhook event is received, THE Billing_Engine
   SHALL update `TenantConfig.tier` to match the new subscription's price ID.
6. WHEN a `customer.subscription.deleted` Stripe webhook event is received, THE Billing_Engine
   SHALL downgrade the Tenant to the `"free"` tier.
7. WHEN an `invoice.payment_failed` Stripe webhook event is received, THE Billing_Engine SHALL
   send a payment failure alert and begin a 7-day grace period before downgrading.
8. WHEN an `invoice.payment_succeeded` Stripe webhook event is received, THE Billing_Engine
   SHALL confirm the Tenant's tier and reset the AI call quota.
9. WHEN a Stripe webhook request arrives with an invalid or missing `Stripe-Signature` header,
   THE Billing_Engine SHALL return HTTP 400 without processing the event.
10. THE Billing_Engine SHALL support monthly and annual billing cycles for Starter, Pro, and
    Agency tiers.
11. THE Billing_Engine SHALL never store raw card data; all payment operations SHALL use the
    Stripe SDK exclusively.

---

### Requirement 28: Feature Flag and Tenant Isolation System

**User Story:** As a SaaS operator, I want feature access enforced at both the API and domain
layers for every tenant, so that customers can only use features included in their subscription
tier and tenant data is never accessible across accounts.

#### Acceptance Criteria

1. WHEN `has_feature` is called with an unknown `tenant_id`, THE Feature_Flag_System SHALL
   return `False`.
2. WHEN `has_feature` is called with `feature="ai_call"` and the Tenant's `ai_calls_today`
   equals or exceeds the tier's daily limit, THE Feature_Flag_System SHALL return `False`.
3. WHEN `has_feature` is called with `feature="ai_call"` and the Tenant is on Pro, Agency,
   or Enterprise tier, THE Feature_Flag_System SHALL return `True` regardless of call count.
4. WHEN `has_feature` is called with `feature="add_subreddit"` and the Tenant has reached
   the tier's `max_subreddits` limit, THE Feature_Flag_System SHALL return `False`.
5. WHEN `has_feature` is called with a feature included in the Tenant's tier feature set,
   THE Feature_Flag_System SHALL return `True`.
6. THE Feature_Flag_System SHALL enforce feature checks at the API middleware layer for all
   Dashboard_API endpoints that require a specific feature.
7. THE Feature_Flag_System SHALL enforce feature checks at the domain layer before any Reddit
   API call that requires a specific feature.
8. THE Feature_Flag_System SHALL cache `has_feature` results in Redis for 60 seconds to avoid
   per-comment database queries.
9. WHEN the AI call quota resets at midnight UTC, THE Scheduler SHALL reset
   `TenantConfig.ai_calls_today` to 0 for all tenants.
10. WHEN a Tenant's feature check fails at the API layer, THE Dashboard_API SHALL return
    HTTP 403 with an upgrade prompt message.
11. THE Worker SHALL refuse to process events for subreddits not in
    `TenantConfig.managed_subreddits` for the active Tenant.
12. EVERY database query that accesses tenant-specific data SHALL include a `tenant_id` filter.
13. THE Feature_Flag_System tier hierarchy SHALL be cumulative: each tier includes all features
    of lower tiers (enterprise ⊇ agency ⊇ pro ⊇ starter ⊇ free).


---

### Requirement 29: Dashboard API

**User Story:** As a subreddit moderator, I want a web dashboard exposing all bot metrics,
queued reviews, and management controls, so that I can monitor and operate the bot without
writing code or using the command line.

#### Acceptance Criteria

1. THE Dashboard_API SHALL expose `GET /health` returning `{"status": "ok"}` with HTTP 200.
2. THE Dashboard_API SHALL expose `GET /metrics` returning current counts for
   `comments_processed`, `actions_taken`, `queued_reviews`, and `posts_processed`.
3. THE Dashboard_API SHALL expose `GET /reviews` returning all pending review cases.
4. THE Dashboard_API SHALL expose `POST /reviews/{id}/resolve` accepting `status` and
   `reviewer_note` and delegating to `resolve_case`.
5. THE Dashboard_API SHALL expose `GET /analytics/growth` returning time-series subscriber
   and engagement data.
6. THE Dashboard_API SHALL expose `GET /analytics/sentiment` returning sentiment trend data
   for the past 7 days.
7. THE Dashboard_API SHALL expose `GET /users/{username}/reputation` returning the
   `UserReputation` record for the specified user.
8. THE Dashboard_API SHALL expose `GET /modmail` returning all open and needs-human modmail
   records.
9. THE Dashboard_API SHALL expose `POST /modmail/{id}/reply` to send a reply to a modmail
   conversation.
10. THE Dashboard_API SHALL expose `GET /flair/templates` and `POST /flair/auto-assign` for
    flair management.
11. THE Dashboard_API SHALL expose `GET /wiki/pages` and `POST /wiki/pages/{name}/update`
    for wiki management.
12. THE Dashboard_API SHALL expose `GET /billing/subscription` and `POST /billing/portal`
    for subscription management.
13. THE Dashboard_API SHALL expose `GET /scheduled-posts`, `POST /scheduled-posts`, and
    `DELETE /scheduled-posts/{id}` for content calendar management.
14. THE Dashboard_API SHALL expose `GET /subreddits` and `POST /subreddits/sync-policy` for
    subreddit management.
15. ALL Dashboard_API request bodies SHALL be validated by Pydantic models before processing.
16. THE Dashboard_API SHALL serve the moderator dashboard HTML using the Lorapok Design
    Language at `GET /`.
17. WHEN a feature-gated endpoint is accessed by a Tenant without the required feature,
    THE Dashboard_API SHALL return HTTP 403 with an upgrade prompt.


---

### Requirement 30: White-Label Dashboard

**User Story:** As a Reddit marketing agency, I want to present the bot dashboard under my
own brand to my clients, so that I can offer a professional managed service without exposing
the underlying platform.

#### Acceptance Criteria

1. WHERE the Agency or Enterprise tier is active, THE Dashboard_API SHALL read
   `TenantConfig.white_label_name` and substitute it for "Lorapok Red Bot" in the dashboard
   title at runtime.
2. WHERE the Agency or Enterprise tier is active and `TenantConfig.white_label_logo_url` is
   set, THE Dashboard_API SHALL substitute the Lorapok logo with the configured URL.
3. THE Dashboard_API SHALL serve white-label configuration via the `GET /config` endpoint so
   the dashboard HTML can apply branding at page load without a rebuild.
4. THE System SHALL support custom domain access via CNAME configuration pointing to the
   hosted dashboard.
5. WHEN white-label settings are updated in `TenantConfig`, THE Dashboard_API SHALL reflect
   the changes on the next page load without requiring a service restart.

---

### Requirement 31: Background Scheduler

**User Story:** As a system operator, I want all recurring jobs registered and managed by a
single scheduler, so that periodic tasks run reliably without manual intervention.

#### Acceptance Criteria

1. WHEN `create_scheduler` is called, THE Scheduler SHALL return a configured
   `BackgroundScheduler` instance ready to start.
2. WHEN `register_all_jobs` is called, THE Scheduler SHALL register all recurring jobs
   including: trending post pipeline (weekly), GitHub repository monitoring (hourly),
   metrics flush (every 5 minutes), scheduled post publisher (every minute), AI quota reset
   (daily at midnight UTC), and subreddit settings sync (configurable).
3. WHEN the Scheduler starts, THE Scheduler SHALL begin executing registered jobs at their
   configured intervals.
4. IF a scheduled job raises an exception, THEN THE Scheduler SHALL log the error and send
   an alert to configured notification channels without stopping other jobs.
5. THE Scheduler SHALL use APScheduler as the scheduling library.


---

### Requirement 32: Deployment and Infrastructure

**User Story:** As a self-hoster or SaaS operator, I want the system deployable for free on
Railway, Render, or Fly.io with a single configuration step, so that the bot is running 24/7
without infrastructure expertise or upfront cost.

#### Acceptance Criteria

1. THE System SHALL be fully configurable via environment variables with no hardcoded secrets
   or credentials.
2. THE System SHALL provide a `Dockerfile` that builds a runnable image containing both the
   Worker and Dashboard_API.
3. THE System SHALL provide a `docker-compose.yml` for local development including PostgreSQL
   and Redis services.
4. WHEN `DRY_RUN=true` is set (the default), THE System SHALL start and operate without
   performing any Reddit write operations.
5. THE System SHALL start successfully when only the required environment variables are
   configured (Reddit credentials, database URL, Redis URL).
6. THE System SHALL provide a `.env.example` file documenting all supported environment
   variables with placeholder values.
7. THE System SHALL be deployable to Railway, Render, or Fly.io free tiers using the provided
   Dockerfile.
8. THE GitHub Pages marketing site SHALL be deployed from the `gh-pages` branch at
   `lorapok.github.io/red-bot` using the Lorapok Design Language.
9. THE System SHALL support PostgreSQL as the primary database and Redis for caching and
   rate limiting.
10. ALL secrets SHALL be loaded exclusively from environment variables via `Settings.from_env()`
    and SHALL never be logged, committed to version control, or echoed in API responses.


---

## Non-Functional Requirements

### Requirement 33: Performance

**User Story:** As a moderator of a high-volume subreddit, I want the bot to keep up with
the comment stream without falling behind, so that moderation actions are applied promptly.

#### Acceptance Criteria

1. THE Worker SHALL process each comment within 3 seconds for rule-engine-only decisions
   (no AI call).
2. THE Worker SHALL process each comment within 5 seconds for AI-assisted decisions under
   normal LLM latency conditions.
3. THE Dashboard_API SHALL respond to `GET /metrics` and `GET /health` within 200ms under
   normal load.
4. THE Dashboard_API SHALL respond to `GET /analytics/cohort` and `GET /analytics/health-score`
   within 2 seconds, using Redis caching with a 10-minute TTL.
5. THE System SHALL handle at least 10,000 comments per day on a single worker process.
6. THE MetricsStore SHALL batch increments in memory and flush to the database every 5 minutes
   to avoid per-comment database writes.
7. THE Classifier SHALL cache results in Redis by `stable_hash(text)` with a 5-minute TTL to
   avoid redundant LLM calls for identical content.
8. WHEN a Tenant manages more than 20 GitHub repositories, THE GitHub_Integration SHALL
   parallelise fetch calls using a thread pool with a maximum of 5 workers.

---

### Requirement 34: Security

**User Story:** As a system operator, I want all credentials, API keys, and signing secrets
protected from exposure, so that the system cannot be compromised through credential leakage
or injection attacks.

#### Acceptance Criteria

1. THE System SHALL load all credentials exclusively from environment variables and SHALL
   never log, commit, or echo secret values.
2. THE System SHALL use minimum required Reddit OAuth scopes: `read`, `submit`, `modposts`,
   `modflair`, `modwiki`, `modcontributors`, `modmail`, `modnote`, `modconfig`.
3. ALL FastAPI request bodies SHALL be validated by Pydantic models with constrained field
   types before any processing occurs.
4. THE System SHALL treat all content received from Reddit as untrusted input and SHALL never
   execute it.
5. LLM prompts SHALL use `response_format={"type": "json_object"}` to mitigate prompt
   injection attacks.
6. THE Billing_Engine SHALL verify Stripe webhook signatures using `stripe.Webhook.construct_event`
   before processing any event.
7. Outbound webhook signing secrets SHALL be stored hashed (SHA-256) in the database and
   SHALL never be returned in API responses.
8. THE System SHALL pin all dependencies in `requirements.txt` and SHALL run `pip-audit` in CI.
9. THE System SHALL never store raw card data; all payment operations SHALL use the Stripe SDK.
10. WHEN `DRY_RUN=true`, THE System SHALL be safe to run with production Reddit credentials
    without risk of modifying any Reddit content.


---

### Requirement 35: Reliability and Error Handling

**User Story:** As a system operator, I want the bot to recover automatically from transient
failures, so that a single API error or network blip does not take the bot offline.

#### Acceptance Criteria

1. WHEN the Reddit API raises an exception during stream processing, THE Worker SHALL catch
   the exception, log it at ERROR level, send an alert to configured notification channels,
   sleep 5 seconds, and continue processing the next item.
2. WHEN the database connection is lost, THE Worker SHALL catch the `OperationalError`, log
   it, alert notification channels, sleep 5 seconds, close the session, and open a new
   session on the next item.
3. WHEN the LLM API is unavailable, THE Classifier SHALL return the fallback review decision
   and THE Worker SHALL queue the item for human review rather than dropping it.
4. WHEN the GitHub API returns HTTP 403 or 429, THE GitHub_Integration SHALL log a warning
   and return `None` or `[]` without raising.
5. WHEN a notification channel webhook URL is not configured, THE System SHALL skip that
   channel silently without raising an exception.
6. WHEN a scheduled post fails to publish, THE Content_Calendar SHALL set `status="failed"`,
   alert notification channels, and NOT retry automatically.
7. WHEN a Stripe webhook event cannot be processed, THE Billing_Engine SHALL return HTTP 400
   and allow Stripe to retry delivery for up to 72 hours.
8. THE Worker SHALL use a `try/except` around every per-item processing block so that one
   malformed item never terminates the stream.
9. WHEN `resolve_case` is called with an invalid `status` value, THE Dashboard_API SHALL
   return HTTP 400 before calling any domain function.

---

### Requirement 36: Scalability

**User Story:** As an Agency or Enterprise customer managing many subreddits, I want the
system to scale to handle high comment volumes without degrading moderation quality.

#### Acceptance Criteria

1. THE System architecture SHALL support migration to Celery + Redis for async AI
   classification without changes to the domain layer.
2. WHEN a Tenant manages more than 10 subreddits, THE System SHALL support partitioning the
   `moderation_decisions` table by `subreddit_name`.
3. THE System SHALL support horizontal scaling of the Dashboard_API by running multiple
   stateless FastAPI instances behind a load balancer.
4. THE Redis cache SHALL be shared across all Worker and Dashboard_API instances to ensure
   consistent feature flag enforcement and quota tracking.
5. THE System SHALL support configuring separate database connection pools for the Worker
   and Dashboard_API processes.

---

### Requirement 37: Observability and Audit

**User Story:** As a system operator and Enterprise customer, I want structured logs, metrics,
and a complete audit trail of all bot actions, so that I can diagnose issues and demonstrate
compliance.

#### Acceptance Criteria

1. THE System SHALL emit structured logs at DEBUG, INFO, WARNING, and ERROR levels for all
   significant events.
2. THE System SHALL record every moderation action in the `moderation_decisions` table with
   `text_hash`, `action`, `reason`, `source`, and `created_at`.
3. THE System SHALL record every human review decision in `review_cases` with `was_override`
   set correctly.
4. THE System SHALL record every policy sync operation in `policy_sync_records`.
5. THE System SHALL record every flair assignment in `FlairAssignmentRecord`.
6. THE System SHALL record every onboarding event in `onboarding_records`.
7. WHERE the Enterprise tier is active, THE System SHALL expose audit log export endpoints
   and compliance reports.
8. THE Dashboard_API SHALL expose `GET /memory` returning recent moderation decisions for
   moderator review.


---

### Requirement 38: Accessibility

**User Story:** As a moderator with accessibility needs, I want the dashboard to meet
baseline web accessibility standards, so that I can use the bot's management interface
regardless of my assistive technology setup.

#### Acceptance Criteria

1. THE Dashboard HTML SHALL use semantic HTML5 elements (`<nav>`, `<main>`, `<section>`,
   `<button>`, `<table>`) rather than generic `<div>` elements for all structural components.
2. ALL interactive elements in the dashboard SHALL have accessible labels via `aria-label`,
   `aria-labelledby`, or visible text content.
3. THE dashboard SHALL maintain a minimum colour contrast ratio of 4.5:1 between text and
   background for all body text, consistent with WCAG 2.1 AA.
4. ALL dashboard form inputs SHALL have associated `<label>` elements.
5. THE dashboard SHALL be navigable by keyboard alone, with visible focus indicators on all
   interactive elements.

---

## Business Requirements

### Requirement 39: SaaS Tier Definitions and Pricing

**User Story:** As a SaaS operator, I want clearly defined subscription tiers with enforced
feature boundaries, so that customers understand what they are paying for and the system
automatically enforces entitlements.

#### Acceptance Criteria

1. THE System SHALL support exactly five tiers: `"free"`, `"starter"`, `"pro"`, `"agency"`,
   and `"enterprise"`.
2. THE Free tier SHALL allow 1 managed subreddit, 100 AI calls per day, basic moderation,
   comment stream, dashboard, Discord integration, and GitHub integration.
3. THE Starter tier ($19/month) SHALL allow 3 managed subreddits, 1,000 AI calls per day,
   and add modmail triage, flair automation, and basic analytics.
4. THE Pro tier ($49/month) SHALL allow 10 managed subreddits, unlimited AI calls, and add
   advanced analytics, engagement predictor, sentiment analysis, content calendar, cross-sub
   spam detection, wiki manager, widget manager, Slack integration, Telegram integration,
   ban appeal workflow, and contributor management.
5. THE Agency tier ($149/month) SHALL allow unlimited subreddits, unlimited AI calls, and
   add white-label dashboard, API access, custom webhooks, policy sync, multi-sub dashboard,
   cohort analysis, health score, mod notes, and rules engine v2.
6. THE Enterprise tier (custom pricing) SHALL add on-premise deployment, custom AI models,
   SSO (SAML/OIDC), audit logs, compliance reports, and SLA guarantee.
7. THE System SHALL support annual billing at a 16.7% discount (2 months free) for Starter,
   Pro, and Agency tiers.
8. WHEN a Tenant's subscription is active, THE Feature_Flag_System SHALL enforce the exact
   feature set defined in `FEATURE_MATRIX` for their tier.


---

### Requirement 40: AI Call Quota Management

**User Story:** As a SaaS operator, I want AI call usage tracked and enforced per tenant per
day, so that Free and Starter customers cannot consume unlimited AI resources and Pro+ customers
are never blocked.

#### Acceptance Criteria

1. THE System SHALL track AI call counts per Tenant per day using a Redis counter keyed by
   `ai_calls:{tenant_id}:{date_utc}`.
2. WHEN a Tenant on the Free tier has made 100 or more AI calls today, THE Feature_Flag_System
   SHALL return `False` for `feature="ai_call"` and THE Worker SHALL fall back to rule-engine-
   only classification.
3. WHEN a Tenant on the Starter tier has made 1,000 or more AI calls today, THE
   Feature_Flag_System SHALL return `False` for `feature="ai_call"`.
4. WHEN a Tenant is on Pro, Agency, or Enterprise tier, THE Feature_Flag_System SHALL always
   return `True` for `feature="ai_call"` regardless of call count.
5. THE Scheduler SHALL reset all AI call counters at midnight UTC daily by deleting the
   previous day's Redis keys and setting `TenantConfig.ai_calls_today = 0`.
6. WHEN a Tenant's AI quota is exhausted, THE Dashboard_API SHALL display a quota warning
   banner on the dashboard.
7. THE System SHALL pass AI API costs through to Pro+ tenants at cost plus 20% markup,
   visible in the billing dashboard.

---

### Requirement 41: Open-Source and Self-Hosting

**User Story:** As a developer or self-hoster, I want to run the full bot from the public
GitHub repository without a paid subscription, so that I can use and contribute to the
platform without cost.

#### Acceptance Criteria

1. THE System core SHALL be published as open-source software on GitHub under a permissive
   licence.
2. THE System SHALL be fully functional for a single subreddit when self-hosted with only
   environment variables configured (no Stripe account required).
3. THE System SHALL provide a one-click Railway deploy button in the README.
4. THE System SHALL provide a complete `README.md` with setup instructions, architecture
   overview, and example use cases.
5. WHEN `STRIPE_PRICE_STARTER_MONTHLY` and related Stripe environment variables are not set,
   THE Billing_Engine SHALL operate in a no-billing mode granting all features to the single
   configured tenant.
6. THE System SHALL include a `docs/policy.md` documenting the bot's operating principles,
   allowed actions, and escalation rules for Reddit bot approval purposes.


---

## User Stories by Persona

### Persona 1: Solo Moderator (Free / Starter Tier)

**Background**: Volunteers 5–10 hours per week moderating a subreddit with 50,000 subscribers.
Wants to reduce time spent on repetitive modmail and spam removal.

**Stories**:

- As a solo moderator on the Free tier, I want spam comments removed automatically, so that
  I do not have to check the subreddit every hour.
- As a solo moderator on the Starter tier, I want common modmail questions answered
  automatically, so that I can focus on complex appeals and community building.
- As a solo moderator, I want a review queue in the dashboard for uncertain cases, so that
  I make the final call on ambiguous content rather than the bot acting unilaterally.
- As a solo moderator, I want new subscribers welcomed with a DM automatically, so that
  every new member feels acknowledged without me writing individual messages.
- As a solo moderator on the Starter tier, I want post flair assigned automatically based
  on content, so that my subreddit stays organised without manual flair work.

---

### Persona 2: Power Moderator / Mod Team (Pro Tier)

**Background**: Leads a mod team of 5 managing 3 subreddits with a combined 2 million
subscribers. Needs advanced analytics and multi-channel alerts.

**Stories**:

- As a power moderator on the Pro tier, I want sentiment alerts sent to our Discord server
  when community tone deteriorates, so that the whole mod team can respond quickly.
- As a power moderator, I want high-potential posts pinned automatically, so that the best
  content gets visibility without someone monitoring the feed around the clock.
- As a power moderator, I want a content calendar with optimal posting times, so that our
  weekly discussion threads are posted when engagement is highest.
- As a power moderator, I want cross-subreddit spam detected automatically across all three
  of our communities, so that ban evasion and coordinated spam are caught before they spread.
- As a power moderator, I want ban appeals reviewed automatically with escalation for
  borderline cases, so that clear-cut appeals are resolved without consuming mod team time.
- As a power moderator, I want Slack slash commands to approve or reject queued cases, so
  that I can moderate from our team Slack without opening the dashboard.


---

### Persona 3: Reddit Marketing Agency (Agency Tier)

**Background**: Manages 25 brand subreddits for clients. Needs white-label presentation,
API access for custom integrations, and policy consistency across communities.

**Stories**:

- As a Reddit marketing agency on the Agency tier, I want the dashboard presented under my
  agency's brand, so that my clients see a professional managed service rather than a
  third-party tool.
- As an agency, I want to sync moderation rules and removal reasons from a master subreddit
  to all client subreddits with one API call, so that policy changes propagate instantly
  across the portfolio.
- As an agency, I want outbound webhooks for every bot event sent to our internal systems,
  so that we can build custom reporting and client notification workflows.
- As an agency, I want a multi-subreddit aggregate dashboard, so that I can monitor all
  client communities in a single view and identify which ones need attention.
- As an agency, I want subreddit health scores updated daily, so that I can include them in
  client reports as an objective measure of community health.
- As an agency, I want API access to all bot data, so that I can build custom client-facing
  dashboards and integrate bot data into our existing reporting tools.

---

### Persona 4: Enterprise Community Operator (Enterprise Tier)

**Background**: Operates the official subreddit for a publicly traded company with 5 million
subscribers. Requires on-premise deployment, SSO, and compliance documentation.

**Stories**:

- As an enterprise community operator, I want the bot deployed on our own infrastructure,
  so that community data never leaves our security perimeter.
- As an enterprise operator, I want SSO via our corporate identity provider, so that
  moderators authenticate with their existing company credentials.
- As an enterprise operator, I want complete audit logs of every bot action exportable for
  compliance review, so that we can demonstrate responsible community management to legal
  and compliance teams.
- As an enterprise operator, I want a contractual SLA guarantee on support response times,
  so that critical moderation issues are addressed within agreed timeframes.
- As an enterprise operator, I want to use our own fine-tuned AI models for content
  classification, so that moderation decisions reflect our specific community standards.

---

### Persona 5: Bot Developer / Self-Hoster (Open-Source User)

**Background**: Python developer who wants to run a custom Reddit bot for their own
subreddit without paying for a SaaS subscription.

**Stories**:

- As a bot developer, I want to clone the repository and have a working bot running locally
  within 15 minutes, so that I can evaluate the platform before deciding whether to use the
  hosted service.
- As a self-hoster, I want all configuration via environment variables with a documented
  `.env.example`, so that I can deploy to any cloud provider without modifying code.
- As a bot developer, I want a comprehensive test suite I can run locally, so that I can
  verify my customisations do not break existing functionality.
- As a self-hoster, I want `DRY_RUN=true` as the default, so that I cannot accidentally
  take live moderation actions during development and testing.
- As a bot developer, I want the domain layer cleanly separated from infrastructure, so that
  I can swap out the Reddit client or database without rewriting business logic.


---

## Constraints

### Reddit API Constraints

1. **Rate limits**: Reddit enforces OAuth rate limits of 100 requests per minute per
   authenticated user. THE Worker SHALL enforce a minimum 2-second interval between
   processing cycles and SHALL use PRAW's built-in rate limit handling.
2. **Bot approval**: Reddit requires bot accounts to be approved before operating at scale.
   THE System SHALL include documentation (`docs/policy.md`) suitable for a Reddit bot
   approval submission, covering purpose, allowed actions, escalation rules, and human
   oversight mechanisms.
3. **OAuth scopes**: THE System SHALL request only the minimum required OAuth scopes and
   SHALL document the purpose of each scope in the README.
4. **Moderation permissions**: THE bot Reddit account SHALL be added as a moderator with
   limited permissions (not admin) on each managed subreddit.
5. **Stream reconnection**: PRAW's comment and submission streams may disconnect. THE Worker
   SHALL rely on PRAW's built-in stream reconnection and SHALL NOT implement custom
   reconnection logic that could cause duplicate processing.
6. **Subreddit restrictions**: THE System SHALL only act on subreddits where the bot account
   has been explicitly granted moderator permissions.
7. **Content policy**: THE System SHALL not automate actions that violate Reddit's Content
   Policy or Moderator Code of Conduct, including mass banning without human review.

### PRAW Capability Constraints

8. **No real-time push**: PRAW uses polling, not WebSockets. Stream latency is typically
   1–5 seconds. THE System SHALL not guarantee sub-second moderation response times.
9. **Modmail API**: The new modmail API (`subreddit.modmail`) is separate from the legacy
   modmail. THE Modmail_Triage SHALL use the new modmail API exclusively.
10. **Mod notes**: The mod notes API requires the bot account to be a moderator with the
    `posts` permission. THE Mod_Notes module SHALL document this prerequisite.
11. **Wiki permissions**: Wiki editing requires the `modwiki` OAuth scope and the bot to
    have wiki edit permissions on the subreddit.

### Free Hosting Constraints

12. **Railway/Render/Fly.io free tiers**: Free tier instances may sleep after inactivity.
    THE System SHALL document that always-on operation requires a paid hosting tier or a
    keep-alive mechanism.
13. **PostgreSQL free tier**: Railway and Render free PostgreSQL instances have storage
    limits (typically 500MB–1GB). THE System SHALL document recommended data retention
    policies to stay within free tier limits.
14. **Redis free tier**: Free Redis instances have memory limits (typically 25–30MB).
    THE System SHALL use Redis only for short-lived cache and counter data, not for
    persistent storage.
15. **GitHub Pages**: The marketing site is static HTML/CSS/JS only. THE GitHub Pages site
    SHALL NOT require a build step beyond committing files to the `gh-pages` branch.

### Technical Constraints

16. **Python version**: THE System SHALL support Python 3.11 or higher.
17. **Database**: THE System SHALL use PostgreSQL as the production database and SHALL
    support SQLite for local development and testing.
18. **Synchronous worker**: The current Worker is synchronous. AI classification adds
    500ms–2s latency per uncertain comment. For subreddits exceeding 10,000 comments per
    day, THE System documentation SHALL recommend migrating to Celery + Redis.
19. **LiteLLM dependency**: AI features depend on at least one valid LiteLLM provider API
    key. THE System SHALL fall back to rule-engine-only classification when no valid API
    key is configured.
20. **Stripe dependency**: Billing features require a Stripe account and configured price
    IDs. THE System SHALL operate in no-billing mode when Stripe environment variables are
    not set.


---

## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions
of a system — essentially, a formal statement about what the system should do. Properties
serve as the bridge between human-readable specifications and machine-verifiable correctness
guarantees.*

The following 24 properties are derived from the acceptance criteria above. Properties 1–18
are carried forward from the design document. Properties 19–24 are new properties derived
from requirements analysis.

---

### Property 1: Rule engine determinism

*For any* string `t`, calling `apply_light_rules(t)` any number of times returns identical
`action`, `reason`, and `confidence` values. No external state is read or written.

**Validates: Requirements 2.3, 2.4**

---

### Property 2: Rule engine output validity

*For any* string `t` (including empty string), `apply_light_rules(t)` returns a
`ModerationDecision` with `action in {"allow", "review", "remove"}` and
`confidence in [0.0, 1.0]`.

**Validates: Requirements 2.1, 2.2**

---

### Property 3: AI classifier never raises

*For any* string `t`, `classify_text(t)` returns a dict with keys `action`, `reason`, and
`confidence` — even when the LLM is unavailable or returns malformed JSON. `action` is always
in `{"allow", "review", "remove"}` and `confidence in [0.0, 1.0]`.

**Validates: Requirements 3.1, 3.2, 3.3, 3.4, 3.5**

---

### Property 4: Trending builder always returns content

*For any* list of trend dicts (including empty list), `build_trending_thread(trends)` returns
a dict with non-empty `title` and `body` strings.

**Validates: Requirement 21.1**

---

### Property 5: Queue case round-trip

*For any* valid `(text, reason, source)` triple, after calling `queue_case(db, text, reason, source)`,
`list_queue(db, status="pending")` contains exactly one more entry than before the call, with
`status="pending"`.

**Validates: Requirements 4.1, 4.2**

---

### Property 6: Resolve case idempotence

*For any* valid `case_id` and `status`, calling `resolve_case(db, case_id, status)` twice
produces the same final database state as calling it once.

**Validates: Requirement 4.4**

---

### Property 7: GitHub monitor idempotence

*For any* list of repository names, calling `monitor_repositories(db, repos)` twice in
succession produces the same number of `PendingPost` and `GithubUpdateTracker` rows as
calling it once.

**Validates: Requirement 21.5**

---

### Property 8: MetricsStore thread-safety

*For any* sequence of concurrent `increment` and `flush_to_db` calls, the total count
persisted equals the total number of `increment` calls made before the flush. No counts are
lost or double-counted.

**Validates: Requirement 33.6**

---

### Property 9: Stable hash consistency

*For any* two strings `a` and `b` where `normalize_text(a) == normalize_text(b)`,
`stable_hash(a) == stable_hash(b)`. For distinct normalised texts, SHA-256 collision
resistance ensures `stable_hash(a) != stable_hash(b)` with overwhelming probability.

**Validates: Requirements 5.4, 6.4**

---

### Property 10: `_to_decision` always produces a valid ModerationDecision

*For any* dict `payload` (including empty dict, missing keys, wrong types),
`_to_decision(payload)` returns a `ModerationDecision` with `action in {"allow", "review", "remove"}`
and `confidence in [0.0, 1.0]`.

**Validates: Requirement 1.3**

---

### Property 11: Reputation score is bounded

*For all* valid `UserReputation` inputs (all count fields non-negative integers,
`account_age_days >= 0`), `compute_reputation_score(r) in [-100.0, 100.0]`.

**Validates: Requirements 14.1, 14.2**

---

### Property 12: Feature flag returns False for unknown tenant

*For any* feature string `f`, `has_feature(db, "nonexistent-tenant-id", f) == False`.

**Validates: Requirement 28.1**

---

### Property 13: Spam detector threshold

*For any* `(username, content_hash)` pair appearing in fewer than 3 distinct subreddits
within the detection window, `detect_cross_sub_spam(db, username, content_hash)` returns
`None`.

**Validates: Requirements 6.1, 6.2**

---

### Property 14: Health score components sum to total

*For any* valid database state, `compute_health_score(db, subreddit_name, reddit)` returns a
`SubredditHealthScore` where `total == growth + engagement + moderation + spam`, each
component is in `[0, 25]`, and `total in [0, 100]`.

**Validates: Requirements 23.1, 23.2, 23.3**

---

### Property 15: Webhook dispatcher never raises

*For any* `event_type` string and JSON-serialisable `payload` dict,
`dispatch_event(db, tenant_id, event_type, payload)` completes without raising, even if all
configured webhook URLs are unreachable.

**Validates: Requirement 26.7**

---

### Property 16: Policy sync idempotence

*For any* valid `(source, targets, policy_types)` triple, calling
`sync_policy(reddit, db, source, targets, policy_types)` twice produces the same target
subreddit state as calling it once. The second call may insert additional `PolicySyncRecord`
rows but does not corrupt any target subreddit's policy.

**Validates: Requirement 8.8**

---

### Property 17: Modmail triage inserts exactly one record per conversation

*For any* `conversation.id`, calling `triage_conversation` twice with the same conversation
results in exactly one `ModmailRecord` in the database. The second call is a no-op or updates
the existing record.

**Validates: Requirement 13.5**

---

### Property 18: Scheduled post publish idempotence

*For any* `ScheduledPost` with `status="published"`, calling `publish_due_posts` again does
not re-publish it to Reddit. The `status` field acts as a guard preventing duplicate
publication.

**Validates: Requirement 20.5**

---

### Property 19: Worker pipeline sequencing

*For any* comment whose `apply_light_rules` result has `action="remove"` AND
`confidence >= review_confidence_threshold`, the Classifier is never invoked. The AI call
is only made when the rule engine result is uncertain.

**Validates: Requirements 1.1, 1.2**

---

### Property 20: Dry-run safety

*For any* system state with `dry_run=True`, no PRAW write methods (`mod.remove`,
`mod.approve`, `mod.lock`, `flair.select`, `subreddit.contributor.add`, etc.) are ever
called. All write operations are replaced with log statements.

**Validates: Requirements 1.8, 32.4**

---

### Property 21: Tenant subreddit authorization

*For any* Reddit event from a subreddit not in `TenantConfig.managed_subreddits` for the
active Tenant, THE Worker takes no action on that event. The managed subreddit list is the
sole authorization gate for all bot actions.

**Validates: Requirements 28.11, 28.12**

---

### Property 22: Webhook HMAC signature present

*For any* dispatched webhook event, the outbound HTTP request includes an
`X-Lorapok-Signature: sha256=<hex_digest>` header computed with HMAC-SHA256 over the
canonical JSON payload using the webhook's registered secret.

**Validates: Requirement 26.3**

---

### Property 23: Webhook retry count bounded

*For any* webhook delivery failure, `dispatch_event` retries at most 3 times. The total
number of HTTP attempts for a single event delivery never exceeds 4 (1 initial + 3 retries).

**Validates: Requirement 26.4**

---

### Property 24: Feature flag tier hierarchy

*For any* tier `T` and any feature `f` in `FEATURE_MATRIX[T]`, `has_feature(db, tenant_id, f)`
returns `True` for all tenants on tier `T` or any higher tier. The feature sets are
cumulative: enterprise ⊇ agency ⊇ pro ⊇ starter ⊇ free.

**Validates: Requirement 28.13**

