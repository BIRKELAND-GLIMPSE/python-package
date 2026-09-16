import httpx
import respx

from glimpse_markets import GlimpseAuthenticationError
from glimpse_markets.client import Client
from glimpse_markets.ratelimit import RateLimiter

BASE = "https://main.bpmapi.io"


def _client() -> Client:
    # A rate limiter with a huge budget so tests never actually block.
    return Client(api_key="glp_live_test", rate_limiter=RateLimiter(max_requests=10_000))


@respx.mock
def test_wallet_balance_sends_api_key_header() -> None:
    route = respx.get(f"{BASE}/api/v1/wallet-balance").mock(
        return_value=httpx.Response(200, json={"balance_millisats": 500_000})
    )
    with _client() as client:
        result = client.wallet_balance()

    assert result == {"balance_millisats": 500_000}
    assert route.calls.last.request.headers["X-API-Key"] == "glp_live_test"


@respx.mock
def test_batches() -> None:
    payload = {
        "batches": [
            {
                "batch_id": "b1",
                "main_topic_title": "Hourly BTC",
                "topic_count": 3,
                "start_time_utc": 1000,
                "end_time_utc": 2000,
                "outcome_min_value": 0,
                "outcome_max_value": 100,
                "outcome_interval": 10,
            }
        ],
        "count": 1,
    }
    respx.get(f"{BASE}/api/v1/nmarket/batches").mock(return_value=httpx.Response(200, json=payload))

    with _client() as client:
        result = client.batches()

    assert result.count == 1
    assert result.batches is not None
    assert result.batches[0].batch_id == "b1"
    assert result.batches[0].main_topic_title == "Hourly BTC"


@respx.mock
def test_batch_active_markets() -> None:
    payload = {
        "batch_id": "b1",
        "main_topic_title": "Hourly BTC",
        "topic_count": 1,
        "count": 1,
        "start_time_utc": 1000,
        "end_time_utc": 2000,
        "cumulative_liquidity_millisats": 100_000,
        "cumulative_volume_millisats": 200_000,
        "markets": [
            {
                "topic_id": 6674,
                "batch_id": "b1",
                "title": "BTC > 100k?",
                "quote_mode": "live",
                "outcomes": [
                    {"option_id": 500, "name": "Yes", "yes_price": 62.1, "no_price": 37.9},
                ],
            }
        ],
    }
    respx.get(f"{BASE}/api/v1/nmarket/batches/b1/active-markets").mock(
        return_value=httpx.Response(200, json=payload)
    )

    with _client() as client:
        result = client.batch_active_markets("b1")

    assert result.markets is not None
    market = result.markets[0]
    assert market.topic_id == 6674
    assert market.quote_mode == "live"
    assert market.outcomes is not None
    assert market.outcomes[0].yes_price == 62.1


@respx.mock
def test_batch_markets() -> None:
    respx.get(f"{BASE}/api/v1/nmarket/batches/b1/markets").mock(
        return_value=httpx.Response(200, json={"batch_id": "b1", "markets": []})
    )
    with _client() as client:
        result = client.batch_markets("b1")
    assert result.batch_id == "b1"
    assert result.markets == []


@respx.mock
def test_batch_stats() -> None:
    payload = {
        "batch_id": "b1",
        "active_market_count": 5,
        "liquidity_locked_millisats": 1000,
        "total_volume_millisats": 2000,
        "volume_24h_millisats": 300,
    }
    respx.get(f"{BASE}/api/v1/nmarket/batches/b1/stats").mock(
        return_value=httpx.Response(200, json=payload)
    )
    with _client() as client:
        result = client.batch_stats("b1")
    assert result.active_market_count == 5


@respx.mock
def test_batch_active_markets_page_sends_pagination_params() -> None:
    route = respx.get(f"{BASE}/api/v1/nmarket/v2/batches/b1/active-markets").mock(
        return_value=httpx.Response(
            200,
            json={
                "batch_id": "b1",
                "markets": [],
                "count": 0,
                "total": 0,
                "limit": 20,
                "offset": 0,
                "has_more": False,
            },
        )
    )
    with _client() as client:
        result = client.batch_active_markets_page("b1", page=2, page_size=20)

    assert result.has_more is False
    sent_params = route.calls.last.request.url.params
    assert sent_params["page"] == "2"
    assert sent_params["page_size"] == "20"


@respx.mock
def test_batch_resolved_markets_page_omits_none_params() -> None:
    route = respx.get(f"{BASE}/api/v1/nmarket/v2/batches/b1/resolved-markets").mock(
        return_value=httpx.Response(200, json={"batch_id": "b1", "markets": []})
    )
    with _client() as client:
        client.batch_resolved_markets_page("b1")

    assert "page" not in route.calls.last.request.url.params
    assert "page_size" not in route.calls.last.request.url.params


@respx.mock
def test_markets_returns_raw_dict() -> None:
    respx.get(f"{BASE}/api/v1/nmarket/markets").mock(
        return_value=httpx.Response(200, json={"anything": "goes"})
    )
    with _client() as client:
        result = client.markets(batch_id="b1")
    assert result == {"anything": "goes"}


@respx.mock
def test_market_quotes() -> None:
    payload = {
        "topic_id": 6674,
        "quote_mode": "live",
        "outcomes": [{"option_id": 500, "name": "Yes", "yes_price": 55.0}],
    }
    respx.get(f"{BASE}/api/v1/nmarket/markets/6674/quotes").mock(
        return_value=httpx.Response(200, json=payload)
    )
    with _client() as client:
        result = client.market_quotes(6674)
    assert result.topic_id == 6674
    assert result.outcomes is not None
    assert result.outcomes[0].option_id == 500


@respx.mock
def test_market_stats() -> None:
    respx.get(f"{BASE}/api/v1/nmarket/markets/6674/stats").mock(
        return_value=httpx.Response(200, json={"topic_id": 6674, "total_volume_millisats": 42})
    )
    with _client() as client:
        result = client.market_stats(6674)
    assert result.total_volume_millisats == 42


@respx.mock
def test_market_volume() -> None:
    payload = {"topic_id": 6674, "volume_by_option": {"500": 1000, "501": 2000}}
    respx.get(f"{BASE}/api/v1/nmarket/markets/6674/volume").mock(
        return_value=httpx.Response(200, json=payload)
    )
    with _client() as client:
        result = client.market_volume(6674)
    assert result.volume_by_option == {"500": 1000, "501": 2000}


@respx.mock
def test_ended_by_batch() -> None:
    route = respx.get(f"{BASE}/api/v1/nmarket/ended-by-batch").mock(
        return_value=httpx.Response(200, json={"items": []})
    )
    with _client() as client:
        result = client.ended_by_batch("b1", limit=10, offset=5)
    assert result == {"items": []}
    params = route.calls.last.request.url.params
    assert params["batch_id"] == "b1"
    assert params["limit"] == "10"
    assert params["offset"] == "5"


@respx.mock
def test_ended_past_168h() -> None:
    respx.get(f"{BASE}/api/v1/nmarket/ended-past-168h").mock(
        return_value=httpx.Response(200, json={"items": []})
    )
    with _client() as client:
        result = client.ended_past_168h("b1")
    assert result == {"items": []}


@respx.mock
def test_resolved_past_168h() -> None:
    respx.get(f"{BASE}/api/v1/nmarket/resolved-past-168h").mock(
        return_value=httpx.Response(200, json={"items": []})
    )
    with _client() as client:
        result = client.resolved_past_168h("b1")
    assert result == {"items": []}


@respx.mock
def test_bet_slip() -> None:
    respx.get(f"{BASE}/api/v1/nmarket/bet-slip-by-uuid").mock(
        return_value=httpx.Response(200, json={"uuid": "abc"})
    )
    with _client() as client:
        result = client.bet_slip("abc")
    assert result == {"uuid": "abc"}


@respx.mock
def test_portfolio_active() -> None:
    payload = {
        "success": True,
        "message": [{"trade_id": "t1", "topic_id": 6674, "shares": 10.0, "status": "active"}],
    }
    respx.get(f"{BASE}/api/v1/nmarket/consolidated-active-portfolio-without-pagination").mock(
        return_value=httpx.Response(200, json=payload)
    )
    with _client() as client:
        result = client.portfolio_active()
    assert result.message is not None
    assert result.message[0].trade_id == "t1"


@respx.mock
def test_portfolio_ended_is_paginated() -> None:
    route = respx.get(f"{BASE}/api/v1/nmarket/consolidated-ended-unresolved-portfolio").mock(
        return_value=httpx.Response(
            200, json={"success": True, "message": [], "total": 0, "limit": 50, "offset": 0}
        )
    )
    with _client() as client:
        result = client.portfolio_ended(limit=50, offset=0)
    assert result.limit == 50
    params = route.calls.last.request.url.params
    assert params["limit"] == "50"
    assert params["offset"] == "0"


@respx.mock
def test_portfolio_resolved() -> None:
    respx.get(f"{BASE}/api/v1/nmarket/consolidated-ended-resolved-portfolio").mock(
        return_value=httpx.Response(200, json={"success": True, "message": [], "total": 0})
    )
    with _client() as client:
        result = client.portfolio_resolved()
    assert result.message == []


@respx.mock
def test_portfolio_summary() -> None:
    payload = {
        "success": True,
        "message": {
            "active_market_count": 2,
            "ended_unresolved_market_count": 0,
            "resolved_market_count": 1,
            "total_current_value": 1000,
            "total_purchase_value": 900,
            "total_pnl": 100,
        },
    }
    respx.get(f"{BASE}/api/v1/nmarket/consolidated-portfolio-summary").mock(
        return_value=httpx.Response(200, json=payload)
    )
    with _client() as client:
        result = client.portfolio_summary()
    assert result.message is not None
    assert result.message.total_pnl == 100


@respx.mock
def test_error_response_raises_typed_exception() -> None:
    respx.get(f"{BASE}/api/v1/wallet-balance").mock(
        return_value=httpx.Response(401, json={"error": "invalid api key"})
    )
    with _client() as client:
        try:
            client.wallet_balance()
        except GlimpseAuthenticationError as exc:
            assert exc.status_code == 401
        else:
            raise AssertionError("expected GlimpseAuthenticationError")


def test_from_env(monkeypatch) -> None:
    monkeypatch.setenv("GLIMPSE_API_KEY", "glp_live_env_key")
    monkeypatch.setenv("GLIMPSE_BASE_URL", "https://staging.example.com")
    client = Client.from_env()
    try:
        assert client.api_key == "glp_live_env_key"
        assert client.base_url == "https://staging.example.com"
    finally:
        client.close()


def test_from_env_defaults_base_url(monkeypatch) -> None:
    monkeypatch.delenv("GLIMPSE_API_KEY", raising=False)
    monkeypatch.delenv("GLIMPSE_BASE_URL", raising=False)
    client = Client.from_env()
    try:
        assert client.api_key is None
        assert client.base_url == BASE
    finally:
        client.close()


def test_no_api_key_omits_header() -> None:
    client = Client()
    try:
        headers = client._headers()
        assert "X-API-Key" not in headers
    finally:
        client.close()


@respx.mock
def test_rate_limiter_is_consulted_before_each_request() -> None:
    respx.get(f"{BASE}/api/v1/nmarket/batches").mock(
        return_value=httpx.Response(200, json={"batches": [], "count": 0})
    )
    calls = []
    limiter = RateLimiter(max_requests=10_000)
    limiter.acquire = lambda: calls.append(1) 

    client = Client(rate_limiter=limiter)
    try:
        client.batches()
        client.batches()
    finally:
        client.close()

    assert len(calls) == 2
