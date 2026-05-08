import time


class RateLimiter:
    def __init__(self, min_interval_seconds: float = 1.0) -> None:
        self.min_interval_seconds = min_interval_seconds
        self._last_time = 0.0

    def wait(self) -> None:
        now = time.time()
        elapsed = now - self._last_time
        if elapsed < self.min_interval_seconds:
            time.sleep(self.min_interval_seconds - elapsed)
        self._last_time = time.time()
