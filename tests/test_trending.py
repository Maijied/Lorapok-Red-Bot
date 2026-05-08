from app.posting.trending import build_trending_thread


def test_trending_thread_payload() -> None:
    payload = build_trending_thread(["FastAPI release", "Redis performance tips"])
    assert "Weekly Developer Trends" in payload["title"]
    assert "- FastAPI release" in payload["body"]
    assert "- Redis performance tips" in payload["body"]
