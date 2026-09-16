import asyncio
from unittest.mock import patch

import pytest

from glimpse_markets import strategy as strategy_module
from glimpse_markets.models import MarketUpdate, PortfolioItem, PortfolioListResponse
from glimpse_markets.strategy import PositionTracker, Strategy, StrategyRunner


class FakeClient:
    def __init__(
        self,
        updates: list[MarketUpdate] | None = None,
        portfolio_items: list[PortfolioItem] | None = None,
    ) -> None:
        self._stream = FakeStream(updates or [])
        self._portfolio_items = portfolio_items or []
        self.closed = False
        self.portfolio_calls = 0
        self.requested_topic_id: int | None = None
        self.requested_batch_id: str | None = None

    def stream_market_updates(self, topic_id=None, batch_id=None):
        self.requested_topic_id = topic_id
        self.requested_batch_id = batch_id
        return self._stream

    async def portfolio_active(self) -> PortfolioListResponse:
        self.portfolio_calls += 1
        return PortfolioListResponse.model_validate(
            {"success": True, "message": [p.model_dump() for p in self._portfolio_items]}
        )

    async def close(self) -> None:
        self.closed = True


class FakeStream:
    def __init__(self, updates: list[MarketUpdate]) -> None:
        self._updates = list(updates)
        self.entered = False
        self.exited = False

    async def __aenter__(self) -> "FakeStream":
        self.entered = True
        return self

    async def __aexit__(self, *exc: object) -> None:
        self.exited = True

    def __aiter__(self):
        return self._iter()

    async def _iter(self):
        for u in self._updates:
            yield u


def _update(topic_id: int = 6674) -> MarketUpdate:
    return MarketUpdate.model_validate({"type": "market_update", "topic_id": topic_id})


def _position(topic_id: int, shares: float) -> PortfolioItem:
    return PortfolioItem.model_validate({"topic_id": topic_id, "option_id": 1, "shares": shares})


# PositionTracker


async def test_position_tracker_caches_within_refresh_window() -> None:
    client = FakeClient(portfolio_items=[_position(6674, 10.0)])
    tracker = PositionTracker(client, min_refresh_interval=60.0)

    fake_now = [1000.0]
    with patch("time.monotonic", side_effect=lambda: fake_now[0]):
        await tracker.get()
        await tracker.get()
        await tracker.get()

    assert client.portfolio_calls == 1


async def test_position_tracker_refreshes_after_window_elapses() -> None:
    client = FakeClient(portfolio_items=[_position(6674, 10.0)])
    tracker = PositionTracker(client, min_refresh_interval=5.0)

    fake_now = [1000.0]
    with patch("time.monotonic", side_effect=lambda: fake_now[0]):
        await tracker.get()
        fake_now[0] = 1006.0
        await tracker.get()

    assert client.portfolio_calls == 2


async def test_position_tracker_invalidate_forces_refresh() -> None:
    client = FakeClient(portfolio_items=[_position(6674, 10.0)])
    tracker = PositionTracker(client, min_refresh_interval=60.0)

    await tracker.get()
    tracker.invalidate()
    await tracker.get()

    assert client.portfolio_calls == 2


async def test_position_tracker_for_topic_filters() -> None:
    client = FakeClient(portfolio_items=[_position(6674, 10.0), _position(7000, 3.0)])
    tracker = PositionTracker(client, min_refresh_interval=60.0)

    positions = await tracker.for_topic(6674)

    assert len(positions) == 1
    assert positions[0].topic_id == 6674


# Strategy default hooks


async def test_default_hooks_are_noops() -> None:
    strategy = Strategy()
    await strategy.on_start()
    await strategy.on_quote(_update())
    await strategy.on_tick()
    await strategy.on_stop()


# StrategyRunner 


class RecordingStrategy(Strategy):
    def __init__(self) -> None:
        self.events: list[str] = []
        self.quotes: list[MarketUpdate] = []
        self.tick_count = 0

    async def on_start(self) -> None:
        self.events.append("start")

    async def on_quote(self, update: MarketUpdate) -> None:
        self.events.append("quote")
        self.quotes.append(update)

    async def on_tick(self) -> None:
        self.events.append("tick")
        self.tick_count += 1

    async def on_stop(self) -> None:
        self.events.append("stop")


async def test_runner_dispatches_quotes_and_lifecycle_hooks() -> None:
    client = FakeClient(updates=[_update(1), _update(2), _update(3)])
    strategy = RecordingStrategy()
    runner = StrategyRunner(strategy, client=client, tick_interval=1000.0)

    await runner.run()

    assert strategy.events[0] == "start"
    assert strategy.events[-1] == "stop"
    assert strategy.events.count("quote") == 3
    assert [u.topic_id for u in strategy.quotes] == [1, 2, 3]


async def test_runner_sets_client_and_positions_on_strategy() -> None:
    client = FakeClient(updates=[])
    strategy = RecordingStrategy()
    runner = StrategyRunner(strategy, client=client, tick_interval=1000.0)

    await runner.run()

    assert strategy.client is client
    assert isinstance(strategy.positions, PositionTracker)


async def test_runner_passes_topic_and_batch_filter_to_stream() -> None:
    client = FakeClient(updates=[])
    strategy = RecordingStrategy()
    runner = StrategyRunner(
        strategy, client=client, topic_id=6674, batch_id="b1", tick_interval=1000.0
    )

    await runner.run()

    assert client.requested_topic_id == 6674
    assert client.requested_batch_id == "b1"


async def test_runner_tick_fires_while_stream_stays_open() -> None:
    class SlowFakeStream(FakeStream):
        async def _iter(self):
            for u in self._updates:
                await asyncio.sleep(0.03)
                yield u

    client = FakeClient(updates=[_update(1), _update(2), _update(3)])
    client._stream = SlowFakeStream(client._stream._updates)
    strategy = RecordingStrategy()
    runner = StrategyRunner(strategy, client=client, tick_interval=0.02)

    await runner.run()

    assert strategy.tick_count >= 1
    assert strategy.events.count("quote") == 3


async def test_runner_does_not_close_a_client_it_was_given() -> None:
    client = FakeClient(updates=[])
    strategy = RecordingStrategy()
    runner = StrategyRunner(strategy, client=client, tick_interval=1000.0)
    assert runner._owns_client is False

    await runner.run()

    assert client.closed is False


async def test_runner_creates_and_closes_its_own_client_when_none_given(monkeypatch) -> None:
    owned_client = FakeClient(updates=[])
    monkeypatch.setattr(strategy_module.AsyncClient, "from_env", lambda **kw: owned_client)

    strategy = RecordingStrategy()
    runner = StrategyRunner(strategy, tick_interval=1000.0)
    assert runner._owns_client is True

    await runner.run()

    assert owned_client.closed is True


async def test_runner_propagates_on_quote_exception_and_cancels_tick() -> None:
    class BoomStrategy(RecordingStrategy):
        async def on_quote(self, update: MarketUpdate) -> None:
            await super().on_quote(update)
            raise ValueError("boom")

    client = FakeClient(updates=[_update(1)])
    strategy = BoomStrategy()
    runner = StrategyRunner(strategy, client=client, tick_interval=1000.0)

    with pytest.raises(ValueError, match="boom"):
        await runner.run()

    assert strategy.events[-1] == "stop"  # on_stop still runs via finally


async def test_runner_propagates_on_tick_exception() -> None:
    class SlowFakeStream(FakeStream):
        async def _iter(self):
            for u in self._updates:
                await asyncio.sleep(1.0)
                yield u

    class BoomTickStrategy(RecordingStrategy):
        async def on_tick(self) -> None:
            await super().on_tick()
            raise ValueError("tick boom")

    client = FakeClient(updates=[_update(1)])
    client._stream = SlowFakeStream(client._stream._updates)
    strategy = BoomTickStrategy()
    runner = StrategyRunner(strategy, client=client, tick_interval=0.01)

    with pytest.raises(ValueError, match="tick boom"):
        await runner.run()
