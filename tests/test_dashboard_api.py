"""Integration tests for the FastAPI dashboard API."""

import os
from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import app.dashboard.models  # noqa: F401 — register all models
from app.dashboard.api import app, _db_dep
from app.dashboard.models import DailyMetric
from app.database import Base
from app.moderation.queue import queue_case

TEST_DB = "test_lorapok.db"
SQLALCHEMY_DATABASE_URL = f"sqlite:///./{TEST_DB}"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[_db_dep] = override_db

client = TestClient(app)


def _reset_state() -> None:
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


def test_health_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_dashboard_homepage_renders():
    _reset_state()
    response = client.get("/")
    assert response.status_code == 200


def test_resolve_review_case_removes_pending_case():
    _reset_state()
    db = TestingSessionLocal()
    try:
        case_id = queue_case(db, "Suspicious link spam", "Possible spam", source="rules+ai")
    finally:
        db.close()

    before = client.get("/reviews")
    assert before.status_code == 200
    assert len(before.json()["pending"]) == 1

    response = client.post(
        f"/reviews/{case_id}/resolve",
        json={"status": "approved", "reviewer_note": "safe after manual review"},
    )
    assert response.status_code == 200
    assert response.json()["ok"] is True
    assert response.json()["pending"] == []


def test_resolve_review_case_unknown_returns_400():
    _reset_state()
    response = client.post(
        "/reviews/9999/resolve",
        json={"status": "rejected", "reviewer_note": "invalid"},
    )
    assert response.status_code == 400


def test_growth_analytics_returns_data():
    _reset_state()
    db = TestingSessionLocal()
    try:
        today = date.today()
        yesterday = today - timedelta(days=1)
        db.add(DailyMetric(metric_date=today, metric_name="comments_processed", count=10))
        db.add(DailyMetric(metric_date=yesterday, metric_name="comments_processed", count=5))
        db.commit()
    finally:
        db.close()

    response = client.get("/analytics/growth")
    assert response.status_code == 200
    data = response.json()
    assert "dates" in data
    assert "metrics" in data


def teardown_module(module):
    if os.path.exists(TEST_DB):
        os.remove(TEST_DB)
