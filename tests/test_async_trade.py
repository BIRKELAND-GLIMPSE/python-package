import httpx
import pytest
import respx

from glimpse_markets import (
    DryRunTradeResult,
    EnterMultiTopicLegGroup,
    ExitLegReq,
    ExitMultiTopicLegGroup,
    GlimpseAmbiguousTradeStateError,
    GlimpseError,
    GlimpseValidationError,
    TradeLeg,
    TradeType,
)
from glimpse_markets.async_client import AsyncClient
from glimpse_markets.ratelimit import AsyncRateLimiter

BASE = "https://main.bpmapi.io"


def _client(dry_run: bool = False) -> AsyncClient:
    return AsyncClient(
        api_key="glp_live_test",
        rate_limiter=AsyncRateLimiter(max_requests=10_000),
        dry_run=dry_run,
    )


def _estimate_payload(topic_id: int = 6674, trade_type: str = "buy") -> dict:
    return {
        "topic_id": topic_id,
        "trade_type": trade_type,
        "leg_count": 1,
        "total_cost": 5.0,
        "total_cost_millisats": 5000,
        "commission_millisats": 50,
    }


@respx.mock
async def test_estimate_trade_no_api_key_required() -> None:
    respx.post(f"{BASE}/api/v1/nmarket/trades/estimate").mock(
        return_value=httpx.Response(200, json=_estimate_payload())
    )
    client = AsyncClient()
    try:
        result = await client.estimate_trade(6674, "buy", [TradeLeg(option_id=500, contracts=10)])
    finally:
        await client.close()
    assert result.total_cost_millisats == 5000


@respx.mock
async def test_enter_multi_topic_multi_leg_live() -> None:
    payload = {
        "results": [{"topic_id": 6674, "trade_id": "t1"}],
        "topics_entered": 1,
        "topics_failed": 0,
    }
    respx.post(f"{BASE}/api/v1/nmarket/enter-multi-topic-multi-leg").mock(
        return_value=httpx.Response(200, json=payload)
    )
    topics = [EnterMultiTopicLegGroup(topic_id=6674, legs=[TradeLeg(option_id=500, contracts=10)])]
    async with _client() as client:
        result = await client.enter_multi_topic_multi_leg(topics)
    assert not isinstance(result, DryRunTradeResult)
    assert result.topics_entered == 1


@respx.mock
async def test_enter_multi_topic_multi_leg_dry_run_never_calls_real_endpoint() -> None:
    real_route = respx.post(f"{BASE}/api/v1/nmarket/enter-multi-topic-multi-leg")
    estimate_route = respx.post(f"{BASE}/api/v1/nmarket/trades/estimate").mock(
        return_value=httpx.Response(200, json=_estimate_payload())
    )
    topics = [EnterMultiTopicLegGroup(topic_id=6674, legs=[TradeLeg(option_id=500, contracts=10)])]

    async with _client(dry_run=True) as client:
        result = await client.enter_multi_topic_multi_leg(topics)

    assert isinstance(result, DryRunTradeResult)
    assert result.trade_type == TradeType.BUY
    assert not real_route.called
    assert estimate_route.called


@respx.mock
async def test_enter_multi_topic_multi_leg_per_call_override() -> None:
    real_route = respx.post(f"{BASE}/api/v1/nmarket/enter-multi-topic-multi-leg").mock(
        return_value=httpx.Response(200, json={"topics_entered": 1, "topics_failed": 0})
    )
    estimate_route = respx.post(f"{BASE}/api/v1/nmarket/trades/estimate")
    topics = [EnterMultiTopicLegGroup(topic_id=6674, legs=[TradeLeg(option_id=500, contracts=10)])]

    async with _client(dry_run=True) as client:
        result = await client.enter_multi_topic_multi_leg(topics, dry_run=False)

    assert not isinstance(result, DryRunTradeResult)
    assert real_route.called
    assert not estimate_route.called


@respx.mock
async def test_exit_consolidated_live_with_explicit_shares() -> None:
    route = respx.post(f"{BASE}/api/v1/nmarket/exit-consolidated").mock(
        return_value=httpx.Response(200, json={"trade_id": "t2"})
    )
    async with _client() as client:
        result = await client.exit_consolidated(6674, 500, shares=5)
    assert result == {"trade_id": "t2"}
    assert b'"shares":5' in route.calls.last.request.content


@respx.mock
async def test_exit_consolidated_dry_run_full_position_looks_up_portfolio() -> None:
    portfolio_payload = {
        "success": True,
        "message": [{"topic_id": 6674, "option_id": 500, "shares": 12.5}],
    }
    respx.get(f"{BASE}/api/v1/nmarket/consolidated-active-portfolio-without-pagination").mock(
        return_value=httpx.Response(200, json=portfolio_payload)
    )
    estimate_route = respx.post(f"{BASE}/api/v1/nmarket/trades/estimate").mock(
        return_value=httpx.Response(200, json=_estimate_payload(trade_type="sell"))
    )
    async with _client(dry_run=True) as client:
        result = await client.exit_consolidated(6674, 500)

    assert isinstance(result, DryRunTradeResult)
    assert b'"contracts":12.5' in estimate_route.calls.last.request.content


@respx.mock
async def test_exit_consolidated_dry_run_no_position_raises_clear_error() -> None:
    respx.get(f"{BASE}/api/v1/nmarket/consolidated-active-portfolio-without-pagination").mock(
        return_value=httpx.Response(200, json={"success": True, "message": []})
    )
    async with _client(dry_run=True) as client:
        with pytest.raises(GlimpseError, match="No active position"):
            await client.exit_consolidated(6674, 500)


@respx.mock
async def test_exit_consolidated_multi_live() -> None:
    respx.post(f"{BASE}/api/v1/nmarket/exit-consolidated-multi").mock(
        return_value=httpx.Response(200, json={"proceeds": 100})
    )
    legs = [ExitLegReq(option_id=500, contracts=5), ExitLegReq(option_id=501, contracts=2)]
    async with _client() as client:
        result = await client.exit_consolidated_multi(6674, legs)
    assert result == {"proceeds": 100}


@respx.mock
async def test_exit_consolidated_multi_dry_run_uses_given_contracts() -> None:
    real_route = respx.post(f"{BASE}/api/v1/nmarket/exit-consolidated-multi")
    estimate_route = respx.post(f"{BASE}/api/v1/nmarket/trades/estimate").mock(
        return_value=httpx.Response(200, json=_estimate_payload(trade_type="sell"))
    )
    legs = [ExitLegReq(option_id=500, contracts=5)]
    async with _client(dry_run=True) as client:
        result = await client.exit_consolidated_multi(6674, legs)

    assert isinstance(result, DryRunTradeResult)
    assert not real_route.called
    assert b'"contracts":5' in estimate_route.calls.last.request.content


@respx.mock
async def test_exit_multi_topic_multi_leg_live() -> None:
    payload = {
        "results": [
            {"topic_id": 6674, "trade_id": "t3"},
            {"topic_id": 7000, "error": "market already resolved"},
        ],
        "topics_exited": 1,
        "topics_failed": 1,
    }
    respx.post(f"{BASE}/api/v1/nmarket/exit-multi-topic-multi-leg").mock(
        return_value=httpx.Response(200, json=payload)
    )
    topics = [
        ExitMultiTopicLegGroup(topic_id=6674, legs=[ExitLegReq(option_id=500, contracts=5)]),
        ExitMultiTopicLegGroup(topic_id=7000, legs=[ExitLegReq(option_id=600, contracts=1)]),
    ]
    async with _client() as client:
        result = await client.exit_multi_topic_multi_leg(topics)

    assert not isinstance(result, DryRunTradeResult)
    assert result.topics_failed == 1
    assert result.results is not None
    assert result.results[1].error == "market already resolved"


@respx.mock
async def test_exit_multi_topic_multi_leg_dry_run_estimates_each_topic() -> None:
    real_route = respx.post(f"{BASE}/api/v1/nmarket/exit-multi-topic-multi-leg")
    estimate_route = respx.post(f"{BASE}/api/v1/nmarket/trades/estimate").mock(
        return_value=httpx.Response(200, json=_estimate_payload(trade_type="sell"))
    )
    topics = [
        ExitMultiTopicLegGroup(topic_id=6674, legs=[ExitLegReq(option_id=500, contracts=5)]),
        ExitMultiTopicLegGroup(topic_id=7000, legs=[ExitLegReq(option_id=600, contracts=1)]),
    ]
    async with _client(dry_run=True) as client:
        result = await client.exit_multi_topic_multi_leg(topics)

    assert isinstance(result, DryRunTradeResult)
    assert len(result.estimates) == 2
    assert not real_route.called
    assert estimate_route.call_count == 2


@respx.mock
async def test_exit_batch_live() -> None:
    payload = {"batch_id": "b1", "results": [], "topics_exited": 1, "topics_failed": 0}
    route = respx.post(f"{BASE}/api/v1/nmarket/exit-batch").mock(
        return_value=httpx.Response(200, json=payload)
    )
    async with _client() as client:
        result = await client.exit_batch("b1")
    assert not isinstance(result, DryRunTradeResult)
    assert result.topics_exited == 1
    assert b'"batch_id":"b1"' in route.calls.last.request.content


@respx.mock
async def test_exit_batch_dry_run_groups_positions_by_topic() -> None:
    portfolio_payload = {
        "success": True,
        "message": [
            {"topic_id": 6674, "option_id": 500, "batch_id": "b1", "shares": 10.0},
            {"topic_id": 6674, "option_id": 501, "batch_id": "b1", "shares": 3.0},
            {"topic_id": 7000, "option_id": 1, "batch_id": "b1", "shares": 2.0},
            {"topic_id": 8000, "option_id": 1, "batch_id": "other", "shares": 99.0},
        ],
    }
    respx.get(f"{BASE}/api/v1/nmarket/consolidated-active-portfolio-without-pagination").mock(
        return_value=httpx.Response(200, json=portfolio_payload)
    )
    real_route = respx.post(f"{BASE}/api/v1/nmarket/exit-batch")
    estimate_route = respx.post(f"{BASE}/api/v1/nmarket/trades/estimate").mock(
        return_value=httpx.Response(200, json=_estimate_payload(trade_type="sell"))
    )

    async with _client(dry_run=True) as client:
        result = await client.exit_batch("b1")

    assert isinstance(result, DryRunTradeResult)
    assert len(result.estimates) == 2  # two distinct topics in batch b1
    assert not real_route.called
    assert estimate_route.call_count == 2


@respx.mock
async def test_network_failure_on_enter_raises_ambiguous_trade_state_error() -> None:
    respx.post(f"{BASE}/api/v1/nmarket/enter-multi-topic-multi-leg").mock(
        side_effect=httpx.ConnectError("connection reset")
    )
    topics = [EnterMultiTopicLegGroup(topic_id=6674, legs=[TradeLeg(option_id=500, contracts=10)])]
    async with _client() as client:
        with pytest.raises(GlimpseAmbiguousTradeStateError) as exc_info:
            await client.enter_multi_topic_multi_leg(topics)

    assert "trade state is unknown" in str(exc_info.value)
    assert exc_info.value.path == "/api/v1/nmarket/enter-multi-topic-multi-leg"


@respx.mock
async def test_http_error_response_on_trade_post_is_not_ambiguous() -> None:
    respx.post(f"{BASE}/api/v1/nmarket/exit-batch").mock(
        return_value=httpx.Response(400, json={"error": "batch not found"})
    )
    async with _client() as client:
        with pytest.raises(GlimpseValidationError):
            await client.exit_batch("b1")
