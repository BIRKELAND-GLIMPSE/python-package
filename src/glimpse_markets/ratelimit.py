"""Client-side proactive throttle.
"""

from __future__ import annotations

import threading
import time
from collections import deque

DEFAULT_MAX_REQUESTS = 60
DEFAULT_WINDOW_SECONDS = 60.0


class RateLimiter:
    """A blocking sliding-window limiter, safe to share across threads."""

    def __init__(
        self,
        max_requests: int = DEFAULT_MAX_REQUESTS,
        window_seconds: float = DEFAULT_WINDOW_SECONDS,
    ) -> None:
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._timestamps: deque[float] = deque()
        self._lock = threading.Lock()

    def acquire(self) -> None:
        """Block, if necessary, until a request is safe to send."""
        with self._lock:
            self._evict_expired(time.monotonic())
            if len(self._timestamps) >= self.max_requests:
                sleep_for = self.window_seconds - (time.monotonic() - self._timestamps[0])
                if sleep_for > 0:
                    time.sleep(sleep_for)
                self._evict_expired(time.monotonic())
            self._timestamps.append(time.monotonic())

    def _evict_expired(self, now: float) -> None:
        while self._timestamps and now - self._timestamps[0] >= self.window_seconds:
            self._timestamps.popleft()
