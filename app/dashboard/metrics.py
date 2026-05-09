import logging
from collections import Counter
from dataclasses import dataclass, field
from datetime import date
from threading import Lock

from sqlalchemy.orm import Session

from app.dashboard.models import DailyMetric

logger = logging.getLogger(__name__)

@dataclass
class MetricsStore:
    _counts: Counter[str] = field(default_factory=Counter)
    _lock: Lock = field(default_factory=Lock)

    def increment(self, metric_name: str, amount: int = 1) -> None:
        with self._lock:
            self._counts[metric_name] += amount

    def snapshot(self) -> dict[str, int]:
        with self._lock:
            return dict(self._counts)

    def flush_to_db(self, db: Session) -> None:
        """Persist current session counts to the daily_metrics table."""
        with self._lock:
            today = date.today()
            for name, val in self._counts.items():
                if val == 0:
                    continue
                
                # Try to find existing record for today/name
                record = db.query(DailyMetric).filter(
                    DailyMetric.metric_date == today,
                    DailyMetric.metric_name == name
                ).first()
                
                if record:
                    record.count += val
                else:
                    record = DailyMetric(metric_date=today, metric_name=name, count=val)
                    db.add(record)
            
            db.commit()
            self._counts.clear()
            logger.info("Metrics flushed to database.")

metrics_store = MetricsStore()
