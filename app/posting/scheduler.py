from collections.abc import Callable

from apscheduler.schedulers.background import BackgroundScheduler

from app.posting.trending import build_trending_thread


def create_scheduler() -> BackgroundScheduler:
    return BackgroundScheduler(timezone="UTC")


def schedule_weekly_trending_post(
    scheduler: BackgroundScheduler,
    topic_provider: Callable[[], list[str]],
    publish_callback: Callable[[dict[str, str]], None],
    day_of_week: str = "mon",
    hour_utc: int = 14,
) -> None:
    def _job() -> None:
        trends = topic_provider()
        payload = build_trending_thread(trends)
        publish_callback(payload)

    scheduler.add_job(
        _job,
        "cron",
        id="weekly_trending_post",
        day_of_week=day_of_week,
        hour=hour_utc,
        minute=0,
        replace_existing=True,
    )
