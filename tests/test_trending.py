from app.posting.trending import build_trending_thread


def test_trending_thread_payload() -> None:
    trends = [
        {
            "full_name": "tiangolo/fastapi",
            "stars": 60000,
            "description": "FastAPI framework",
            "url": "https://github.com/tiangolo/fastapi",
        },
        {
            "full_name": "redis/redis",
            "stars": 50000,
            "description": "Redis database",
            "url": "https://github.com/redis/redis",
        },
    ]
    payload = build_trending_thread(trends)
    assert "Weekly Developer Trends" in payload["title"]
    assert "tiangolo/fastapi" in payload["body"]
    assert "⭐ 60000 stars" in payload["body"]
    assert "Redis database" in payload["body"]


def test_trending_thread_empty() -> None:
    payload = build_trending_thread([])
    assert "No significant trends discovered" in payload["body"]
