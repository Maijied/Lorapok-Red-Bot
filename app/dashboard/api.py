"""Lorapok Red Bot — FastAPI dashboard API."""

from __future__ import annotations

import os
from typing import Any

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.billing.middleware import feature_gate_middleware
from app.config import Settings
from app.dashboard.metrics import metrics_store
from app.database import get_db

app = FastAPI(title="Lorapok Red Bot Dashboard", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)
app.middleware("http")(feature_gate_middleware)

_STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")
if os.path.isdir(_STATIC_DIR):
    app.mount("/static", StaticFiles(directory=_STATIC_DIR), name="static")


def _settings() -> Settings:
    return Settings.from_env()


def _db_dep():
    settings = _settings()
    yield from get_db(settings.database_url)


# ── Core ──────────────────────────────────────────────────────────────────────


@app.get("/", response_class=HTMLResponse)
def dashboard_root():
    index = os.path.join(_STATIC_DIR, "index.html")
    if os.path.isfile(index):
        return FileResponse(index)
    return HTMLResponse("<h1>Lorapok Red Bot Dashboard</h1><p>Static files not found.</p>")


@app.get("/health")
def health():
    return {"status": "ok", "version": "2.0.0"}


@app.get("/config")
def config(settings: Settings = Depends(_settings)):
    return {
        "ai_model": settings.ai_model,
        "dry_run": settings.dry_run,
        "subreddit_names": settings.subreddit_names,
        "white_label_name": settings.white_label_name,
        "white_label_logo_url": settings.white_label_logo_url,
    }


# ── Metrics & Analytics ───────────────────────────────────────────────────────


@app.get("/metrics")
def metrics(db: Session = Depends(_db_dep)):
    snap = metrics_store.snapshot()
    return {
        "comments_processed": snap.get("comments_processed", 0),
        "actions_taken": snap.get("actions_taken", 0),
        "queued_reviews": snap.get("queued_reviews", 0),
        "posts_processed": snap.get("posts_processed", 0),
    }


@app.get("/analytics/growth")
def analytics_growth(db: Session = Depends(_db_dep)):
    from app.dashboard.models import DailyMetric
    from datetime import date, timedelta

    dates = [(date.today() - timedelta(days=i)).isoformat() for i in range(29, -1, -1)]
    records = db.query(DailyMetric).filter(DailyMetric.metric_date >= date.today() - timedelta(days=29)).all()
    by_date: dict[str, dict[str, int]] = {d: {} for d in dates}
    for r in records:
        key = r.metric_date.isoformat() if r.metric_date else ""
        if key in by_date:
            by_date[key][r.metric_name] = r.count
    return {"dates": dates, "metrics": by_date}


@app.get("/analytics/sentiment")
def analytics_sentiment(db: Session = Depends(_db_dep), settings: Settings = Depends(_settings)):
    from app.moderation.sentiment import get_sentiment_trend

    data = []
    for sub in settings.subreddit_names:
        data.extend(get_sentiment_trend(db, sub, tenant_id=settings.tenant_id))
    return {"data": data}


@app.get("/analytics/cohort")
def analytics_cohort(db: Session = Depends(_db_dep), settings: Settings = Depends(_settings)):
    from app.analytics.cohort import build_cohort_table

    results = {}
    for sub in settings.subreddit_names:
        results[sub] = build_cohort_table(db, sub, tenant_id=settings.tenant_id)
    return results


@app.get("/analytics/health-score")
def analytics_health_score(db: Session = Depends(_db_dep), settings: Settings = Depends(_settings)):
    from app.analytics.health_score import compute_health_score
    from dataclasses import asdict

    results = {}
    for sub in settings.subreddit_names:
        score = compute_health_score(db, sub, tenant_id=settings.tenant_id)
        results[sub] = {"total": score.total, "growth": score.growth, "engagement": score.engagement, "moderation": score.moderation, "spam": score.spam}
    return results


@app.get("/analytics/multi-sub")
def analytics_multi_sub(db: Session = Depends(_db_dep), settings: Settings = Depends(_settings)):
    from app.analytics.multi_sub import get_aggregate_metrics, get_per_sub_breakdown

    return {
        "aggregate": get_aggregate_metrics(db, settings.tenant_id),
        "breakdown": get_per_sub_breakdown(db, settings.tenant_id),
    }


# ── Review queue ──────────────────────────────────────────────────────────────


@app.get("/reviews")
def list_reviews(db: Session = Depends(_db_dep), settings: Settings = Depends(_settings)):
    from app.moderation.queue import list_queue

    return {"pending": list_queue(db, status="pending", tenant_id=settings.tenant_id)}


class ResolveRequest(BaseModel):
    status: str = Field(pattern="^(approved|rejected|escalated)$")
    reviewer_note: str = ""


@app.post("/reviews/{case_id}/resolve")
def resolve_review(case_id: str, body: ResolveRequest, db: Session = Depends(_db_dep), settings: Settings = Depends(_settings)):
    from app.moderation.queue import list_queue, resolve_case

    ok = resolve_case(db, case_id, body.status, body.reviewer_note, tenant_id=settings.tenant_id)
    if not ok:
        raise HTTPException(400, "Unable to resolve review case.")
    return {"ok": True, "pending": list_queue(db, status="pending", tenant_id=settings.tenant_id)}


# ── Pending posts ─────────────────────────────────────────────────────────────


@app.get("/posts/pending")
def list_pending_posts(db: Session = Depends(_db_dep)):
    from app.dashboard.models import PendingPost

    posts = db.query(PendingPost).filter(PendingPost.status == "pending").order_by(PendingPost.created_at.desc()).all()
    return {"drafts": [{"id": p.id, "title": p.title, "body": p.body, "source_url": p.source_url, "created_at": p.created_at.isoformat() if p.created_at else None} for p in posts]}


class PostActionRequest(BaseModel):
    action: str = Field(pattern="^(approved|rejected)$")


@app.post("/posts/{post_id}/action")
def post_action(post_id: int, body: PostActionRequest, db: Session = Depends(_db_dep)):
    from app.dashboard.models import PendingPost

    post = db.query(PendingPost).filter(PendingPost.id == post_id).first()
    if not post:
        raise HTTPException(404, "Post not found.")
    post.status = body.action
    db.commit()
    return {"ok": True}


# ── Memory ────────────────────────────────────────────────────────────────────


@app.get("/memory")
def memory(db: Session = Depends(_db_dep), settings: Settings = Depends(_settings)):
    from app.moderation.memory import recent_cases

    return {"recent": recent_cases(db, limit=50, tenant_id=settings.tenant_id)}


# ── Users & Reputation ────────────────────────────────────────────────────────


@app.get("/users/{username}/reputation")
def user_reputation(username: str, db: Session = Depends(_db_dep), settings: Settings = Depends(_settings)):
    from app.dashboard.models import UserReputation

    records = db.query(UserReputation).filter(
        UserReputation.tenant_id == settings.tenant_id,
        UserReputation.username == username,
    ).all()
    if not records:
        raise HTTPException(404, f"No reputation data for u/{username}")
    return [{"subreddit": r.subreddit_name, "score": r.reputation_score, "flair_tier": r.flair_tier, "is_contributor": r.is_contributor} for r in records]


# ── Modmail ───────────────────────────────────────────────────────────────────


@app.get("/modmail")
def list_modmail(db: Session = Depends(_db_dep), settings: Settings = Depends(_settings)):
    from app.dashboard.models import ModmailRecord

    records = db.query(ModmailRecord).filter(
        ModmailRecord.tenant_id == settings.tenant_id,
        ModmailRecord.status.in_(["open", "needs_human"]),
    ).order_by(ModmailRecord.created_at.desc()).limit(50).all()
    return {"modmail": [{"id": r.id, "conversation_id": r.conversation_id, "subject": r.subject, "category": r.category, "status": r.status, "sla_deadline": r.sla_deadline.isoformat() if r.sla_deadline else None} for r in records]}


class ModmailReplyRequest(BaseModel):
    message: str


@app.post("/modmail/{record_id}/reply")
def reply_modmail(record_id: int, body: ModmailReplyRequest, db: Session = Depends(_db_dep)):
    from app.dashboard.models import ModmailRecord

    record = db.query(ModmailRecord).filter(ModmailRecord.id == record_id).first()
    if not record:
        raise HTTPException(404, "Modmail record not found.")
    record.status = "resolved"
    db.commit()
    return {"ok": True, "note": "Reply must be sent via Reddit modmail directly."}


# ── Flair ─────────────────────────────────────────────────────────────────────


@app.get("/flair/templates")
def flair_templates(db: Session = Depends(_db_dep), settings: Settings = Depends(_settings)):
    from app.subreddit.flair_engine import list_flair_templates

    results = {}
    for sub in settings.subreddit_names:
        results[sub] = list_flair_templates(db, sub, tenant_id=settings.tenant_id)
    return results


class FlairAutoAssignRequest(BaseModel):
    subreddit_name: str


@app.post("/flair/auto-assign")
def flair_auto_assign(body: FlairAutoAssignRequest, db: Session = Depends(_db_dep), settings: Settings = Depends(_settings)):
    return {"ok": True, "note": "Flair batch runs automatically via scheduler."}


# ── Wiki ──────────────────────────────────────────────────────────────────────


@app.get("/wiki/pages")
def wiki_pages(db: Session = Depends(_db_dep), settings: Settings = Depends(_settings)):
    from app.dashboard.models import WikiPage

    pages = db.query(WikiPage).filter(WikiPage.tenant_id == settings.tenant_id).all()
    return {"pages": [{"subreddit": p.subreddit_name, "name": p.page_name, "auto_update": p.auto_update_enabled} for p in pages]}


class WikiUpdateRequest(BaseModel):
    content: str
    reason: str = "Dashboard update"


@app.post("/wiki/pages/{page_name}/update")
def wiki_update(page_name: str, body: WikiUpdateRequest, db: Session = Depends(_db_dep), settings: Settings = Depends(_settings)):
    return {"ok": True, "note": "Wiki update queued. Apply via wiki_manager with Reddit credentials."}


# ── Webhooks ──────────────────────────────────────────────────────────────────


@app.get("/webhooks")
def list_webhooks_endpoint(db: Session = Depends(_db_dep), settings: Settings = Depends(_settings)):
    from app.integrations.webhooks import list_webhooks

    return {"webhooks": list_webhooks(db, settings.tenant_id)}


class WebhookCreateRequest(BaseModel):
    url: str
    events: list[str]
    secret: str


@app.post("/webhooks")
def create_webhook(body: WebhookCreateRequest, db: Session = Depends(_db_dep), settings: Settings = Depends(_settings)):
    from app.integrations.webhooks import register_webhook

    hook = register_webhook(db, settings.tenant_id, body.url, body.events, body.secret)
    return {"id": hook.id, "url": hook.url, "events": hook.events}


@app.delete("/webhooks/{webhook_id}")
def delete_webhook_endpoint(webhook_id: int, db: Session = Depends(_db_dep), settings: Settings = Depends(_settings)):
    from app.integrations.webhooks import delete_webhook

    ok = delete_webhook(db, settings.tenant_id, webhook_id)
    if not ok:
        raise HTTPException(404, "Webhook not found.")
    return {"ok": True}


# ── Scheduled posts ───────────────────────────────────────────────────────────


@app.get("/scheduled-posts")
def list_scheduled_posts(db: Session = Depends(_db_dep), settings: Settings = Depends(_settings)):
    from app.posting.content_calendar import get_scheduled_posts

    results = {}
    for sub in settings.subreddit_names:
        results[sub] = get_scheduled_posts(db, sub, tenant_id=settings.tenant_id)
    return results


class ScheduledPostRequest(BaseModel):
    subreddit_name: str
    title: str
    body: str
    post_at: str  # ISO 8601 UTC
    flair_id: str | None = None


@app.post("/scheduled-posts")
def create_scheduled_post(body: ScheduledPostRequest, db: Session = Depends(_db_dep), settings: Settings = Depends(_settings)):
    from datetime import datetime, timezone
    from app.posting.content_calendar import schedule_post

    try:
        post_at = datetime.fromisoformat(body.post_at.replace("Z", "+00:00"))
        post_id = schedule_post(db, body.subreddit_name, body.title, body.body, post_at, body.flair_id, settings.tenant_id)
        return {"id": post_id}
    except ValueError as exc:
        raise HTTPException(400, str(exc))


@app.delete("/scheduled-posts/{post_id}")
def cancel_scheduled_post_endpoint(post_id: str, db: Session = Depends(_db_dep), settings: Settings = Depends(_settings)):
    from app.posting.content_calendar import cancel_scheduled_post

    ok = cancel_scheduled_post(db, post_id, tenant_id=settings.tenant_id)
    if not ok:
        raise HTTPException(404, "Scheduled post not found or already published.")
    return {"ok": True}


# ── Subreddits ────────────────────────────────────────────────────────────────


@app.get("/subreddits")
def list_subreddits(settings: Settings = Depends(_settings)):
    return {"subreddits": settings.subreddit_names}


class PolicySyncRequest(BaseModel):
    source_subreddit: str
    target_subreddits: list[str]
    policy_types: list[str] = ["rules", "removal_reasons"]


@app.post("/subreddits/sync-policy")
def sync_policy_endpoint(body: PolicySyncRequest, db: Session = Depends(_db_dep)):
    return {"ok": True, "note": "Policy sync requires Reddit credentials — trigger via worker or CLI."}


# ── Billing ───────────────────────────────────────────────────────────────────


@app.get("/billing/subscription")
def billing_subscription(db: Session = Depends(_db_dep), settings: Settings = Depends(_settings)):
    from app.dashboard.models import TenantConfig

    tenant = db.query(TenantConfig).filter(TenantConfig.tenant_id == settings.tenant_id).first()
    if not tenant:
        return {"tier": "free", "tenant_id": settings.tenant_id}
    return {
        "tier": tenant.tier,
        "tenant_id": tenant.tenant_id,
        "managed_subreddits": tenant.managed_subreddits,
        "ai_calls_today": tenant.ai_calls_today,
    }


@app.post("/billing/portal")
def billing_portal(db: Session = Depends(_db_dep), settings: Settings = Depends(_settings)):
    from app.dashboard.models import TenantConfig
    from app.billing.stripe_client import create_portal_session

    tenant = db.query(TenantConfig).filter(TenantConfig.tenant_id == settings.tenant_id).first()
    if not tenant or not tenant.stripe_customer_id:
        raise HTTPException(400, "No Stripe customer found. Please subscribe first.")
    url = create_portal_session(tenant.stripe_customer_id, return_url="https://lorapok.github.io/red-bot")
    return {"url": url}


@app.post("/billing/stripe-webhook")
async def stripe_webhook(request: Request, db: Session = Depends(_db_dep)):
    from app.billing.webhook_handler import handle_stripe_webhook

    payload = await request.body()
    sig_header = request.headers.get("Stripe-Signature", "")
    try:
        return handle_stripe_webhook(payload, sig_header, db)
    except ValueError as exc:
        raise HTTPException(400, str(exc))
