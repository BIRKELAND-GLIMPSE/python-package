"""Minimal scaffolding for running a trading bot off live quotes.
"""

from __future__ import annotations

import asyncio
import contextlib
import time

from glimpse_markets.async_client import AsyncClient
from glimpse_markets.models import MarketUpdate, PortfolioItem
from glimpse_markets.streaming import MarketStream

DEFAULT_TICK_INTERVAL = 5.0
DEFAULT_MIN_REFRESH_INTERVAL = 5.0


class PositionTracker:
    """Caches ``portfolio_active()`` so a strategy can check its positions
    on every quote update without a REST call per check.
    """

    def __init__(
        self, client: AsyncClient, min_refresh_interval: float = DEFAULT_MIN_REFRESH_INTERVAL
    ) -> None:
        self._client = client
        self._min_refresh_interval = min_refresh_interval
        self._cached: list[PortfolioItem] = []
        self._last_refresh: float | None = None
        self._lock = asyncio.Lock()

    def invalidate(self) -> None:
        """Force the next access to refetch rather than return the cache."""
        self._last_refresh = None

    async def get(self) -> list[PortfolioItem]:
        """All open positions, refreshed at most every ``min_refresh_interval`` seconds."""
        async with self._lock:
            now = time.monotonic()
            age = None if self._last_refresh is None else now - self._last_refresh
            if age is None or age >= self._min_refresh_interval:
                response = await self._client.portfolio_active()
                self._cached = response.message or []
                self._last_refresh = now
        return self._cached

    async def for_topic(self, topic_id: int) -> list[PortfolioItem]:
        """Open positions in one topic — a convenience filter over ``get()``."""
        return [item for item in await self.get() if item.topic_id == topic_id]


class Strategy:
    """Base class for a bot driven by live market data.
    """

    client: AsyncClient
    positions: PositionTracker

    async def on_start(self) -> None:
        """Called once, before the stream starts. Override for setup."""

    async def on_quote(self, update: MarketUpdate) -> None:
        """Called for every ``market_update`` received from the stream."""

    async def on_tick(self) -> None:
        """Called on a fixed interval (``StrategyRunner``'s ``tick_interval``),
        """

    async def on_stop(self) -> None:
        """Called once after the runner stops, success or failure. Override for cleanup."""


class StrategyRunner:
    """Drives a ``Strategy``: opens a ``MarketStream``, dispatches
    ``on_quote`` for every message, and runs ``on_tick`` concurrently on a
    fixed interval — until the stream ends or either hook raises.
    """

    def __init__(
        self,
        strategy: Strategy,
        client: AsyncClient | None = None,
        topic_id: int | None = None,
        batch_id: str | None = None,
        tick_interval: float = DEFAULT_TICK_INTERVAL,
    ) -> None:
        self._strategy = strategy
        self._client = client
        self._owns_client = client is None
        self._topic_id = topic_id
        self._batch_id = batch_id
        self._tick_interval = tick_interval

    async def run(self) -> None:
        client = self._client if self._client is not None else AsyncClient.from_env()
        strategy = self._strategy
        strategy.client = client
        strategy.positions = PositionTracker(client)

        try:
            await strategy.on_start()
            async with client.stream_market_updates(self._topic_id, self._batch_id) as stream:
                quote_task = asyncio.ensure_future(self._quote_loop(stream))
                tick_task = asyncio.ensure_future(self._tick_loop())
                done, pending = await asyncio.wait(
                    {quote_task, tick_task}, return_when=asyncio.FIRST_COMPLETED
                )
                for task in pending:
                    task.cancel()
                for task in pending:
                    with contextlib.suppress(asyncio.CancelledError):
                        await task
                for task in done:
                    task.result()  # re-raises if that task failed
        finally:
            await strategy.on_stop()
            if self._owns_client:
                await client.close()

    async def _quote_loop(self, stream: MarketStream) -> None:
        async for update in stream:
            await self._strategy.on_quote(update)

    async def _tick_loop(self) -> None:
        while True:
            await asyncio.sleep(self._tick_interval)
            await self._strategy.on_tick()
