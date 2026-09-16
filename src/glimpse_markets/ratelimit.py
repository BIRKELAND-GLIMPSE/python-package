"""Client-side proactive throttle, sync and async variants.
"""

from __future__ import annotations

import asyncio
import threading
import time
from collections import deque

DEFAULT_MAX_REQUESTS = 60
DEFAULT_WINDOW_SECONDS = 60.0


def _evict_expired(timestamps: deque[float], window_seconds: float, now: float) -> None:
    while timestamps and now - timestamps[0] >= window_seconds:
        timestamps.popleft()


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
            _evict_expired(self._timestamps, self.window_seconds, time.monotonic())
            if len(self._timestamps) >= self.max_requests:
                sleep_for = self.window_seconds - (time.monotonic() - self._timestamps[0])
                if sleep_for > 0:
                    time.sleep(sleep_for)
                _evict_expired(self._timestamps, self.window_seconds, time.monotonic())
            self._timestamps.append(time.monotonic())


class AsyncRateLimiter:
    """Async counterpart to ``RateLimiter`` — identical sliding-window logic,
    but suspends with ``asyncio.sleep`` instead of blocking the thread
    """

    def __init__(
        self,
        max_requests: int = DEFAULT_MAX_REQUESTS,
        window_seconds: float = DEFAULT_WINDOW_SECONDS,
    ) -> None:
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._timestamps: deque[float] = deque()
        self._lock = asyncio.Lock()

    async def acquire(self) -> None:
        """Suspend, if necessary, until a request is safe to send."""
        async with self._lock:
            _evict_expired(self._timestamps, self.window_seconds, time.monotonic())
            if len(self._timestamps) >= self.max_requests:
                sleep_for = self.window_seconds - (time.monotonic() - self._timestamps[0])
                if sleep_for > 0:
                    await asyncio.sleep(sleep_for)
                _evict_expired(self._timestamps, self.window_seconds, time.monotonic())
            self._timestamps.append(time.monotonic())
