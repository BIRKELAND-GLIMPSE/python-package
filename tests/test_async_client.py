import httpx
import respx

from glimpse_markets import GlimpseAuthenticationError
from glimpse_markets.async_client import AsyncClient
from glimpse_markets.ratelimit import AsyncRateLimiter
from glimpse_markets.streaming import MarketStream

BASE = "https://main.bpmapi.io"


def _client() -> AsyncClient:
    return AsyncClient(api_key="glp_live_test", rate_limiter=AsyncRateLimiter(max_requests=10_000))


@respx.mock
async def test_wallet_balance_sends_api_key_header() -> None:
    route = respx.get(f"{BASE}/api/v1/wallet-balance").mock(
        return_value=httpx.Response(200, json={"balance_millisats": 500_000})
    )
    async with _client() as client:
        result = await client.wallet_balance()

    assert result == {"balance_millisats": 500_000}
    assert route.calls.last.request.headers["X-API-Key"] == "glp_live_test"


@respx.mock
async def test_batches() -> None:
    payload = {
        "batches": [{"batch_id": "b1", "main_topic_title": "Hourly BTC", "topic_count": 3}],
        "count": 1,
    }
    respx.get(f"{BASE}/api/v1/nmarket/batches").mock(return_value=httpx.Response(200, json=payload))

    async with _client() as client:
        result = await client.batches()

    assert result.count == 1
    assert result.batches is not None
    assert result.batches[0].batch_id == "b1"


@respx.mock
async def test_batch_active_markets() -> None:
    payload = {
        "batch_id": "b1",
        "markets": [
            {
                "topic_id": 6674,
                "quote_mode": "live",
                "outcomes": [{"option_id": 500, "name": "Yes", "yes_price": 62.1}],
            }
        ],
    }
    respx.get(f"{BASE}/api/v1/nmarket/batches/b1/active-markets").mock(
        return_value=httpx.Response(200, json=payload)
    )
    async with _client() as client:
        result = await client.batch_active_markets("b1")
    assert result.markets is not None
    assert result.markets[0].topic_id == 6674


@respx.mock
async def test_batch_markets() -> None:
    respx.get(f"{BASE}/api/v1/nmarket/batches/b1/markets").mock(
        return_value=httpx.Response(200, json={"batch_id": "b1", "markets": []})
    )
    async with _client() as client:
        result = await client.batch_markets("b1")
    assert result.batch_id == "b1"


@respx.mock
async def test_batch_stats() -> None:
    respx.get(f"{BASE}/api/v1/nmarket/batches/b1/stats").mock(
        return_value=httpx.Response(200, json={"batch_id": "b1", "active_market_count": 5})
    )
    async with _client() as client:
        result = await client.batch_stats("b1")
    assert result.active_market_count == 5


@respx.mock
async def test_batch_active_markets_page_sends_pagination_params() -> None:
    route = respx.get(f"{BASE}/api/v1/nmarket/v2/batches/b1/active-markets").mock(
        return_value=httpx.Response(200, json={"batch_id": "b1", "markets": [], "has_more": False})
    )
    async with _client() as client:
        result = await client.batch_active_markets_page("b1", page=2, page_size=20)
    assert result.has_more is False
    params = route.calls.last.request.url.params
    assert params["page"] == "2"
    assert params["page_size"] == "20"


@respx.mock
async def test_batch_resolved_markets_page_omits_none_params() -> None:
    route = respx.get(f"{BASE}/api/v1/nmarket/v2/batches/b1/resolved-markets").mock(
        return_value=httpx.Response(200, json={"batch_id": "b1", "markets": []})
    )
    async with _client() as client:
        await client.batch_resolved_markets_page("b1")
    assert "page" not in route.calls.last.request.url.params


@respx.mock
async def test_markets_returns_raw_dict() -> None:
    respx.get(f"{BASE}/api/v1/nmarket/markets").mock(
        return_value=httpx.Response(200, json={"anything": "goes"})
    )
    async with _client() as client:
        result = await client.markets(batch_id="b1")
    assert result == {"anything": "goes"}


@respx.mock
async def test_market_quotes() -> None:
    payload = {
        "topic_id": 6674,
        "quote_mode": "live",
        "outcomes": [{"option_id": 500, "name": "Yes", "yes_price": 55.0}],
    }
    respx.get(f"{BASE}/api/v1/nmarket/markets/6674/quotes").mock(
        return_value=httpx.Response(200, json=payload)
    )
    async with _client() as client:
        result = await client.market_quotes(6674)
    assert result.topic_id == 6674
    assert result.outcomes is not None
    assert result.outcomes[0].option_id == 500


@respx.mock
async def test_market_stats() -> None:
    respx.get(f"{BASE}/api/v1/nmarket/markets/6674/stats").mock(
        return_value=httpx.Response(200, json={"topic_id": 6674, "total_volume_millisats": 42})
    )
    async with _client() as client:
        result = await client.market_stats(6674)
    assert result.total_volume_millisats == 42


@respx.mock
async def test_market_volume() -> None:
    payload = {"topic_id": 6674, "volume_by_option": {"500": 1000}}
    respx.get(f"{BASE}/api/v1/nmarket/markets/6674/volume").mock(
        return_value=httpx.Response(200, json=payload)
    )
    async with _client() as client:
        result = await client.market_volume(6674)
    assert result.volume_by_option == {"500": 1000}


@respx.mock
async def test_ended_by_batch() -> None:
    route = respx.get(f"{BASE}/api/v1/nmarket/ended-by-batch").mock(
        return_value=httpx.Response(200, json={"items": []})
    )
    async with _client() as client:
        result = await client.ended_by_batch("b1", limit=10, offset=5)
    assert result == {"items": []}
    params = route.calls.last.request.url.params
    assert params["limit"] == "10"


@respx.mock
async def test_ended_past_168h() -> None:
    respx.get(f"{BASE}/api/v1/nmarket/ended-past-168h").mock(
        return_value=httpx.Response(200, json={"items": []})
    )
    async with _client() as client:
        result = await client.ended_past_168h("b1")
    assert result == {"items": []}


@respx.mock
async def test_resolved_past_168h() -> None:
    respx.get(f"{BASE}/api/v1/nmarket/resolved-past-168h").mock(
        return_value=httpx.Response(200, json={"items": []})
    )
    async with _client() as client:
        result = await client.resolved_past_168h("b1")
    assert result == {"items": []}


@respx.mock
async def test_bet_slip() -> None:
    respx.get(f"{BASE}/api/v1/nmarket/bet-slip-by-uuid").mock(
        return_value=httpx.Response(200, json={"uuid": "abc"})
    )
    async with _client() as client:
        result = await client.bet_slip("abc")
    assert result == {"uuid": "abc"}


@respx.mock
async def test_portfolio_active() -> None:
    payload = {"success": True, "message": [{"trade_id": "t1", "topic_id": 6674, "shares": 10.0}]}
    respx.get(f"{BASE}/api/v1/nmarket/consolidated-active-portfolio-without-pagination").mock(
        return_value=httpx.Response(200, json=payload)
    )
    async with _client() as client:
        result = await client.portfolio_active()
    assert result.message is not None
    assert result.message[0].trade_id == "t1"


@respx.mock
async def test_portfolio_ended_is_paginated() -> None:
    route = respx.get(f"{BASE}/api/v1/nmarket/consolidated-ended-unresolved-portfolio").mock(
        return_value=httpx.Response(200, json={"success": True, "message": [], "limit": 50})
    )
    async with _client() as client:
        result = await client.portfolio_ended(limit=50, offset=0)
    assert result.limit == 50
    assert route.calls.last.request.url.params["limit"] == "50"


@respx.mock
async def test_portfolio_resolved() -> None:
    respx.get(f"{BASE}/api/v1/nmarket/consolidated-ended-resolved-portfolio").mock(
        return_value=httpx.Response(200, json={"success": True, "message": []})
    )
    async with _client() as client:
        result = await client.portfolio_resolved()
    assert result.message == []


@respx.mock
async def test_portfolio_summary() -> None:
    payload = {"success": True, "message": {"active_market_count": 2, "total_pnl": 100}}
    respx.get(f"{BASE}/api/v1/nmarket/consolidated-portfolio-summary").mock(
        return_value=httpx.Response(200, json=payload)
    )
    async with _client() as client:
        result = await client.portfolio_summary()
    assert result.message is not None
    assert result.message.total_pnl == 100


@respx.mock
async def test_error_response_raises_typed_exception() -> None:
    respx.get(f"{BASE}/api/v1/wallet-balance").mock(
        return_value=httpx.Response(401, json={"error": "invalid api key"})
    )
    async with _client() as client:
        try:
            await client.wallet_balance()
        except GlimpseAuthenticationError as exc:
            assert exc.status_code == 401
        else:
            raise AssertionError("expected GlimpseAuthenticationError")


async def test_from_env(monkeypatch) -> None:
    monkeypatch.setenv("GLIMPSE_API_KEY", "glp_live_env_key")
    monkeypatch.setenv("GLIMPSE_BASE_URL", "https://staging.example.com")
    client = AsyncClient.from_env()
    try:
        assert client.api_key == "glp_live_env_key"
        assert client.base_url == "https://staging.example.com"
    finally:
        await client.close()


async def test_no_api_key_omits_header() -> None:
    client = AsyncClient()
    try:
        assert "X-API-Key" not in client._headers()
    finally:
        await client.close()


@respx.mock
async def test_rate_limiter_is_consulted_before_each_request() -> None:
    respx.get(f"{BASE}/api/v1/nmarket/batches").mock(
        return_value=httpx.Response(200, json={"batches": [], "count": 0})
    )
    calls = []
    limiter = AsyncRateLimiter(max_requests=10_000)

    async def fake_acquire() -> None:
        calls.append(1)

    limiter.acquire = fake_acquire  # type: ignore[method-assign]

    client = AsyncClient(rate_limiter=limiter)
    try:
        await client.batches()
        await client.batches()
    finally:
        await client.close()

    assert len(calls) == 2


def test_stream_market_updates_uses_client_base_url() -> None:
    client = AsyncClient(base_url="https://main.bpmapi.io")
    stream = client.stream_market_updates(topic_id=6674)
    assert isinstance(stream, MarketStream)
    assert stream._url == "wss://main.bpmapi.io/ws/nmarket-updates"
    assert stream._initial_topic_id == 6674
