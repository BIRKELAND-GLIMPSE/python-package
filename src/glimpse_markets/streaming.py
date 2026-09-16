"""Real-time market data via ``/ws/nmarket-updates``.
"""

from __future__ import annotations

import json
from collections.abc import AsyncIterator
from types import TracebackType
from typing import Any

import websockets

from glimpse_markets._base import DEFAULT_BASE_URL
from glimpse_markets.models import MarketUpdate

WS_PATH = "/ws/nmarket-updates"


def _ws_url(base_url: str) -> str:
    if base_url.startswith("https://"):
        return "wss://" + base_url[len("https://") :] + WS_PATH
    if base_url.startswith("http://"):
        return "ws://" + base_url[len("http://") :] + WS_PATH
    raise ValueError(f"base_url must start with http:// or https://, got {base_url!r}")


class MarketStream:
    """An async iterator over live ``market_update`` events.
    """

    def __init__(
        self,
        base_url: str = DEFAULT_BASE_URL,
        topic_id: int | None = None,
        batch_id: str | None = None,
    ) -> None:
        self._url = _ws_url(base_url)
        self._initial_topic_id = topic_id
        self._initial_batch_id = batch_id
        self._conn: Any = None

    async def connect(self) -> None:
        self._conn = await websockets.connect(self._url)
        if self._initial_topic_id is not None or self._initial_batch_id is not None:
            await self.subscribe(self._initial_topic_id, self._initial_batch_id)

    async def subscribe(self, topic_id: int | None = None, batch_id: str | None = None) -> None:
        """Filter the stream to one topic and/or one batch. Replaces any previous filter."""
        if self._conn is None:
            raise RuntimeError("not connected — call connect() or use 'async with' first")
        payload = {"action": "subscribe", "topic_id": topic_id, "batch_id": batch_id}
        await self._conn.send(json.dumps(payload))

    async def close(self) -> None:
        if self._conn is not None:
            await self._conn.close()
            self._conn = None

    async def __aenter__(self) -> MarketStream:
        await self.connect()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        await self.close()

    def __aiter__(self) -> AsyncIterator[MarketUpdate]:
        return self._iter_messages()

    async def _iter_messages(self) -> AsyncIterator[MarketUpdate]:
        if self._conn is None:
            raise RuntimeError("not connected — call connect() or use 'async with' first")
        async for raw in self._conn:
            yield MarketUpdate.model_validate(json.loads(raw))
