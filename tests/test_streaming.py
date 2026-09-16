import json

import pytest

from glimpse_markets import streaming
from glimpse_markets.streaming import MarketStream, _ws_url


def test_ws_url_https_to_wss() -> None:
    assert _ws_url("https://main.bpmapi.io") == "wss://main.bpmapi.io/ws/nmarket-updates"


def test_ws_url_http_to_ws() -> None:
    assert _ws_url("http://localhost:8080") == "ws://localhost:8080/ws/nmarket-updates"


def test_ws_url_invalid_scheme_raises() -> None:
    with pytest.raises(ValueError, match="http"):
        _ws_url("ftp://example.com")


class FakeConnection:
    """Mimics the object ``await websockets.connect(url)`` returns: an
    async-iterable of text frames, plus ``send``/``close``.
    """

    def __init__(self, messages: list[str] | None = None) -> None:
        self._messages = messages or []
        self.sent: list[str] = []
        self.closed = False

    def __aiter__(self):
        return self._iter()

    async def _iter(self):
        for m in self._messages:
            yield m

    async def send(self, data: str) -> None:
        self.sent.append(data)

    async def close(self) -> None:
        self.closed = True


def _market_update_json(topic_id: int = 3914) -> str:
    return json.dumps(
        {
            "type": "market_update",
            "topic_id": topic_id,
            "batch_id": "b1",
            "data": {
                "topic_id": topic_id,
                "topic_type": "btc",
                "batch_id": "b1",
                "alpha": 0.0006,
                "pot_size": 16237863,
                "timestamp": 1789548381,
                "quotes": [{"option_id": 1, "option_name": "A", "yes_price": 0, "shares": 4}],
                "binary_quotes": None,
            },
        }
    )


async def test_connect_with_no_filter_sends_no_subscribe(monkeypatch) -> None:
    fake = FakeConnection()

    async def fake_connect(url, **kwargs):
        assert url == "wss://main.bpmapi.io/ws/nmarket-updates"
        return fake

    monkeypatch.setattr(streaming.websockets, "connect", fake_connect)

    stream = MarketStream()
    await stream.connect()
    assert fake.sent == []
    await stream.close()
    assert fake.closed is True


async def test_connect_with_topic_id_sends_subscribe(monkeypatch) -> None:
    fake = FakeConnection()

    async def fake_connect(url, **kwargs):
        return fake

    monkeypatch.setattr(streaming.websockets, "connect", fake_connect)

    stream = MarketStream(topic_id=6674)
    await stream.connect()
    assert len(fake.sent) == 1
    assert json.loads(fake.sent[0]) == {"action": "subscribe", "topic_id": 6674, "batch_id": None}


async def test_connect_with_batch_id_sends_subscribe(monkeypatch) -> None:
    fake = FakeConnection()

    async def fake_connect(url, **kwargs):
        return fake

    monkeypatch.setattr(streaming.websockets, "connect", fake_connect)

    stream = MarketStream(batch_id="b1")
    await stream.connect()
    assert json.loads(fake.sent[0]) == {"action": "subscribe", "topic_id": None, "batch_id": "b1"}


async def test_subscribe_can_be_called_again_after_connect(monkeypatch) -> None:
    fake = FakeConnection()

    async def fake_connect(url, **kwargs):
        return fake

    monkeypatch.setattr(streaming.websockets, "connect", fake_connect)

    stream = MarketStream(topic_id=6674)
    await stream.connect()
    await stream.subscribe(topic_id=7000)
    assert len(fake.sent) == 2
    assert json.loads(fake.sent[1])["topic_id"] == 7000


async def test_iterating_parses_market_update_messages(monkeypatch) -> None:
    fake = FakeConnection(messages=[_market_update_json(3914), _market_update_json(3915)])

    async def fake_connect(url, **kwargs):
        return fake

    monkeypatch.setattr(streaming.websockets, "connect", fake_connect)

    updates = []
    async with MarketStream() as stream:
        async for update in stream:
            updates.append(update)

    assert len(updates) == 2
    assert updates[0].type == "market_update"
    assert updates[0].topic_id == 3914
    assert updates[0].data is not None
    assert updates[0].data.quotes is not None
    assert updates[0].data.quotes[0].option_id == 1
    assert updates[0].data.binary_quotes is None
    assert updates[1].topic_id == 3915


async def test_context_manager_closes_on_exit(monkeypatch) -> None:
    fake = FakeConnection(messages=[])

    async def fake_connect(url, **kwargs):
        return fake

    monkeypatch.setattr(streaming.websockets, "connect", fake_connect)

    async with MarketStream() as stream:
        async for _ in stream:
            pass

    assert fake.closed is True


async def test_iterating_before_connect_raises() -> None:
    stream = MarketStream()
    with pytest.raises(RuntimeError, match="not connected"):
        async for _ in stream:
            pass


async def test_subscribe_before_connect_raises() -> None:
    stream = MarketStream()
    with pytest.raises(RuntimeError, match="not connected"):
        await stream.subscribe(topic_id=1)


async def test_close_without_connect_is_a_no_op() -> None:
    stream = MarketStream()
    await stream.close()  # should not raise
