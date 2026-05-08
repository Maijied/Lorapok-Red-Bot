from fastapi.testclient import TestClient

from app.dashboard.api import app
from app.moderation.memory import MEMORY
from app.moderation.queue import REVIEW_QUEUE, queue_case

client = TestClient(app)


def _reset_state() -> None:
    REVIEW_QUEUE.clear()
    MEMORY.clear()


def test_dashboard_homepage_renders_lorapok_theme() -> None:
    _reset_state()
    response = client.get("/")
    assert response.status_code == 200
    assert "Lorapok Red Bot" in response.text
    assert "Moderator Dashboard" in response.text


def test_resolve_review_case_removes_pending_case() -> None:
    _reset_state()
    case_id = queue_case("Suspicious link spam", "Possible spam", source="rules+ai")

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
        "/reviews/not-a-real-case-id/resolve",
        json={"status": "rejected", "reviewer_note": "invalid"},
    )
    assert response.status_code == 400
