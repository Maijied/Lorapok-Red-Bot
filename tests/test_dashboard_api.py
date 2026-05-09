import os
from datetime import date, timedelta

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.dashboard.api import app
from app.dashboard.models import DailyMetric
from app.database import Base, get_db
from app.moderation.queue import queue_case

# Use a temporary file for testing instead of in-memory to avoid connection-scoped table loss
TEST_DB = "test_lorapok.db"
SQLALCHEMY_DATABASE_URL = f"sqlite:///./{TEST_DB}"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

client = TestClient(app)

def _reset_state() -> None:
    # Drop and recreate to ensure clean state
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

def test_dashboard_homepage_renders_lorapok_theme() -> None:
    _reset_state()
    response = client.get("/")
    assert response.status_code == 200
    assert "Lorapok Red Bot" in response.text

def test_resolve_review_case_removes_pending_case() -> None:
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

def test_resolve_review_case_unknown_case_returns_error() -> None:
    _reset_state()
    response = client.post(
        "/reviews/9999/resolve",
        json={"status": "rejected", "reviewer_note": "invalid"},
    )
    assert response.status_code == 400

def test_growth_analytics_returns_data() -> None:
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
    assert len(data["dates"]) == 2
    assert data["metrics"]["comments_processed"][today.isoformat()] == 10
    assert data["metrics"]["comments_processed"][yesterday.isoformat()] == 5

# Cleanup test DB after all tests
def teardown_module(module):
    if os.path.exists(TEST_DB):
        os.remove(TEST_DB)
