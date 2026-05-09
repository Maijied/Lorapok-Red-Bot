from datetime import date, datetime, timezone

from sqlalchemy import Column, Date, DateTime, Integer, String, Text

from app.database import Base


class DailyMetric(Base):
    __tablename__ = "daily_metrics"
    id = Column(Integer, primary_key=True, index=True)
    metric_date = Column(Date, default=date.today, index=True)
    metric_name = Column(String(50), index=True)
    count = Column(Integer, default=0)


class GithubUpdateTracker(Base):
    __tablename__ = "github_update_tracker"
    id = Column(Integer, primary_key=True, index=True)
    repo_name = Column(String(100), index=True)
    update_type = Column(String(20))  # release, issue
    external_id = Column(String(100), unique=True, index=True)
    processed_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class PendingPost(Base):
    __tablename__ = "pending_posts"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255))
    body = Column(Text)
    source_url = Column(String(255))
    status = Column(String(20), default="pending")  # pending, approved, rejected
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
