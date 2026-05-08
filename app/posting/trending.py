from datetime import datetime, timezone


def build_trending_thread(trends: list[str]) -> dict[str, str]:
    date_text = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    title = f"Weekly Developer Trends — {date_text}"
    body = "\n".join([f"- {item}" for item in trends])
    return {"title": title, "body": body}
