"""Builds a local price history from ``MarketStream``, since Glimpse's API
has no historical/candle endpoint of its own — this is the SDK's own way
of accumulating the "context" a forecaster needs.

We will also be patching in real historical data soon. 
"""

from __future__ import annotations

import json
import time
from collections import deque
from pathlib import Path

from glimpse_markets.models import MarketUpdate

DEFAULT_MAX_POINTS = 4096


class MarketRecorder:

    def __init__(
        self,
        max_points_per_series: int = DEFAULT_MAX_POINTS,
        persist_path: str | Path | None = None,
    ) -> None:
        self._max_points = max_points_per_series
        self._series: dict[tuple[int, int], deque[tuple[int, float]]] = {}
        self._persist_path = Path(persist_path) if persist_path else None
        if self._persist_path is not None:
            self._persist_path.parent.mkdir(parents=True, exist_ok=True)

    def record(self, update: MarketUpdate) -> None:
        if update.topic_id is None or update.data is None:
            return
        now = int(time.time())
        for outcome in update.data.quotes or []:
            self._append(update.topic_id, outcome.option_id, outcome.yes_price, now)
        for binary_outcome in update.data.binary_quotes or []:
            self._append(update.topic_id, binary_outcome.option_id, binary_outcome.price, now)

    def _append(
        self, topic_id: int, option_id: int | None, price: float | None, ts: int
    ) -> None:
        if option_id is None or price is None:
            return
        key = (topic_id, option_id)
        series = self._series.setdefault(key, deque(maxlen=self._max_points))
        series.append((ts, price))
        if self._persist_path is not None:
            row = {"ts": ts, "topic_id": topic_id, "option_id": option_id, "price": price}
            with self._persist_path.open("a") as f:
                f.write(json.dumps(row) + "\n")

    def series_for(self, topic_id: int, option_id: int) -> list[tuple[int, float]]:
        """``(timestamp, price)`` pairs, oldest first, for one option."""
        return list(self._series.get((topic_id, option_id), ()))

    def prices_for(self, topic_id: int, option_id: int) -> list[float]:
        """Just the price values, oldest first — the raw, irregularly
        spaced series. Prefer ``resampled_prices_for`` for forecasting."""
        return [price for _, price in self.series_for(topic_id, option_id)]

    def resampled_prices_for(
        self, topic_id: int, option_id: int, interval_seconds: int = 60
    ) -> list[float]:
        points = self.series_for(topic_id, option_id)
        if not points:
            return []
        start, end = points[0][0], points[-1][0]
        buckets: dict[int, float] = {}
        for ts, price in points:
            buckets[(ts - start) // interval_seconds] = price
        num_buckets = (end - start) // interval_seconds + 1
        resampled = []
        last = points[0][1]
        for i in range(num_buckets):
            if i in buckets:
                last = buckets[i]
            resampled.append(last)
        return resampled

    def load(self, path: str | Path) -> None:
        """Rehydrate history from a previously persisted NDJSON file —
        appends into the in-memory buffers, doesn't clear existing data.
        Lets a long-running bot survive a restart with its history intact.
        """
        with Path(path).open() as f:
            for raw_line in f:
                stripped = raw_line.strip()
                if not stripped:
                    continue
                row = json.loads(stripped)
                key = (row["topic_id"], row["option_id"])
                series = self._series.setdefault(key, deque(maxlen=self._max_points))
                series.append((row["ts"], row["price"]))
