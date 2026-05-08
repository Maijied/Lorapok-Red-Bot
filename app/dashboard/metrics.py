from collections import Counter
from dataclasses import dataclass, field
from threading import Lock
from typing import Any


@dataclass
class MetricsStore:
    _counts: Counter[str] = field(default_factory=Counter)
    _lock: Lock = field(default_factory=Lock)

    def increment(self, metric_name: str, amount: int = 1) -> None:
        with self._lock:
            self._counts[metric_name] += amount

    def snapshot(self) -> dict[str, Any]:
        with self._lock:
            return dict(self._counts)


metrics_store = MetricsStore()
