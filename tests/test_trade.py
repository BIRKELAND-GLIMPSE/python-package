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
from glimpse_markets.client import Client
from glimpse_markets.ratelimit import RateLimiter

BASE = "https://main.bpmapi.io"


def _client(dry_run: bool = False) -> Client:
    return Client(
        api_key="glp_live_test",
        rate_limiter=RateLimiter(max_requests=10_000),
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


# estimate_trade (always real, public)


@respx.mock
def test_estimate_trade_sends_correct_payload_and_no_api_key_required() -> None:
    route = respx.post(f"{BASE}/api/v1/nmarket/trades/estimate").mock(
        return_value=httpx.Response(200, json=_estimate_payload())
    )
    client = Client()  # no api_key — estimate is public
    try:
        result = client.estimate_trade(6674, "buy", [TradeLeg(option_id=500, contracts=10)])
    finally:
        client.close()

    assert result.total_cost_millisats == 5000
    sent_body = route.calls.last.request.content
    assert b'"trade_type":"buy"' in sent_body
    assert b'"option_id":500' in sent_body
    assert "X-API-Key" not in route.calls.last.request.headers


@respx.mock
def test_estimate_trade_accepts_tradetype_enum() -> None:
    respx.post(f"{BASE}/api/v1/nmarket/trades/estimate").mock(
        return_value=httpx.Response(200, json=_estimate_payload(trade_type="sell"))
    )
    with _client() as client:
        result = client.estimate_trade(6674, TradeType.SELL, [TradeLeg(option_id=500, contracts=5)])
    assert result.trade_type == "sell"


@respx.mock
def test_estimate_trade_network_failure_is_not_wrapped_as_ambiguous() -> None:
    respx.post(f"{BASE}/api/v1/nmarket/trades/estimate").mock(side_effect=httpx.ConnectError("boom"))
    with _client() as client, pytest.raises(httpx.ConnectError):
        client.estimate_trade(6674, "buy", [TradeLeg(option_id=500, contracts=1)])


# enter_multi_topic_multi_leg


@respx.mock
def test_enter_multi_topic_multi_leg_live() -> None:
    payload = {
        "results": [
            {
                "topic_id": 6674,
                "trade_id": "t1",
                "total_cost_millisats": 5000,
                "commission_millisats": 50,
            }
        ],
        "topics_requested": 1,
        "topics_entered": 1,
        "topics_failed": 0,
        "total_cost_millisats": 5000,
        "total_commission_millisats": 50,
    }
    route = respx.post(f"{BASE}/api/v1/nmarket/enter-multi-topic-multi-leg").mock(
        return_value=httpx.Response(200, json=payload)
    )
    topics = [EnterMultiTopicLegGroup(topic_id=6674, legs=[TradeLeg(option_id=500, contracts=10)])]
    with _client() as client:
        result = client.enter_multi_topic_multi_leg(topics)

    assert not isinstance(result, DryRunTradeResult)
    assert result.topics_entered == 1
    assert result.results is not None
    assert result.results[0].trade_id == "t1"
    assert route.calls.last.request.headers["X-API-Key"] == "glp_live_test"


@respx.mock
def test_enter_multi_topic_multi_leg_surfaces_per_topic_error_on_200() -> None:
    payload = {
        "results": [{"topic_id": 6674, "error": "insufficient balance"}],
        "topics_requested": 1,
        "topics_entered": 0,
        "topics_failed": 1,
    }
    respx.post(f"{BASE}/api/v1/nmarket/enter-multi-topic-multi-leg").mock(
        return_value=httpx.Response(200, json=payload)
    )
    topics = [EnterMultiTopicLegGroup(topic_id=6674, legs=[TradeLeg(option_id=500, contracts=10)])]
    with _client() as client:
        result = client.enter_multi_topic_multi_leg(topics)

    assert not isinstance(result, DryRunTradeResult)
    assert result.topics_failed == 1
    assert result.results is not None
    assert result.results[0].error == "insufficient balance"


@respx.mock
def test_enter_multi_topic_multi_leg_dry_run_never_calls_real_endpoint() -> None:
    real_route = respx.post(f"{BASE}/api/v1/nmarket/enter-multi-topic-multi-leg")
    estimate_route = respx.post(f"{BASE}/api/v1/nmarket/trades/estimate").mock(
        return_value=httpx.Response(200, json=_estimate_payload())
    )
    topics = [EnterMultiTopicLegGroup(topic_id=6674, legs=[TradeLeg(option_id=500, contracts=10)])]

    with _client(dry_run=True) as client:
        result = client.enter_multi_topic_multi_leg(topics)

    assert isinstance(result, DryRunTradeResult)
    assert result.simulated is True
    assert result.trade_type == TradeType.BUY
    assert len(result.estimates) == 1
    assert not real_route.called
    assert estimate_route.called


@respx.mock
def test_enter_multi_topic_multi_leg_per_call_dry_run_overrides_client_default() -> None:
    real_route = respx.post(f"{BASE}/api/v1/nmarket/enter-multi-topic-multi-leg").mock(
        return_value=httpx.Response(
            200,
            json={"results": [], "topics_requested": 1, "topics_entered": 1, "topics_failed": 0},
        )
    )
    estimate_route = respx.post(f"{BASE}/api/v1/nmarket/trades/estimate")
    topics = [EnterMultiTopicLegGroup(topic_id=6674, legs=[TradeLeg(option_id=500, contracts=10)])]

    # client defaults to dry_run=True, but this call explicitly opts into live execution
    with _client(dry_run=True) as client:
        result = client.enter_multi_topic_multi_leg(topics, dry_run=False)

    assert not isinstance(result, DryRunTradeResult)
    assert real_route.called
    assert not estimate_route.called


# exit_consolidated


@respx.mock
def test_exit_consolidated_live_with_explicit_shares() -> None:
    route = respx.post(f"{BASE}/api/v1/nmarket/exit-consolidated").mock(
        return_value=httpx.Response(200, json={"trade_id": "t2"})
    )
    with _client() as client:
        result = client.exit_consolidated(6674, 500, shares=5)
    assert result == {"trade_id": "t2"}
    sent_body = route.calls.last.request.content
    assert b'"shares":5' in sent_body


@respx.mock
def test_exit_consolidated_live_omits_shares_when_none() -> None:
    route = respx.post(f"{BASE}/api/v1/nmarket/exit-consolidated").mock(
        return_value=httpx.Response(200, json={"trade_id": "t2"})
    )
    with _client() as client:
        client.exit_consolidated(6674, 500)
    assert b"shares" not in route.calls.last.request.content


@respx.mock
def test_exit_consolidated_dry_run_with_explicit_shares_skips_portfolio_lookup() -> None:
    portfolio_route = respx.get(
        f"{BASE}/api/v1/nmarket/consolidated-active-portfolio-without-pagination"
    )
    estimate_route = respx.post(f"{BASE}/api/v1/nmarket/trades/estimate").mock(
        return_value=httpx.Response(200, json=_estimate_payload(trade_type="sell"))
    )
    with _client(dry_run=True) as client:
        result = client.exit_consolidated(6674, 500, shares=5)

    assert isinstance(result, DryRunTradeResult)
    assert not portfolio_route.called
    assert estimate_route.called


@respx.mock
def test_exit_consolidated_dry_run_full_position_looks_up_portfolio() -> None:
    portfolio_payload = {
        "success": True,
        "message": [
            {"topic_id": 6674, "option_id": 500, "shares": 12.5, "status": "active"},
            {"topic_id": 9999, "option_id": 1, "shares": 3.0, "status": "active"},
        ],
    }
    respx.get(f"{BASE}/api/v1/nmarket/consolidated-active-portfolio-without-pagination").mock(
        return_value=httpx.Response(200, json=portfolio_payload)
    )
    estimate_route = respx.post(f"{BASE}/api/v1/nmarket/trades/estimate").mock(
        return_value=httpx.Response(200, json=_estimate_payload(trade_type="sell"))
    )
    with _client(dry_run=True) as client:
        result = client.exit_consolidated(6674, 500)  # shares omitted -> full position

    assert isinstance(result, DryRunTradeResult)
    sent_body = estimate_route.calls.last.request.content
    assert b'"contracts":12.5' in sent_body


@respx.mock
def test_exit_consolidated_dry_run_zero_shares_means_full_position() -> None:
    portfolio_payload = {
        "success": True,
        "message": [{"topic_id": 6674, "option_id": 500, "shares": 7.0, "status": "active"}],
    }
    respx.get(f"{BASE}/api/v1/nmarket/consolidated-active-portfolio-without-pagination").mock(
        return_value=httpx.Response(200, json=portfolio_payload)
    )
    estimate_route = respx.post(f"{BASE}/api/v1/nmarket/trades/estimate").mock(
        return_value=httpx.Response(200, json=_estimate_payload(trade_type="sell"))
    )
    with _client(dry_run=True) as client:
        client.exit_consolidated(6674, 500, shares=0)

    assert b'"contracts":7.0' in estimate_route.calls.last.request.content


@respx.mock
def test_exit_consolidated_dry_run_no_position_raises_clear_error() -> None:
    respx.get(f"{BASE}/api/v1/nmarket/consolidated-active-portfolio-without-pagination").mock(
        return_value=httpx.Response(200, json={"success": True, "message": []})
    )
    with _client(dry_run=True) as client, pytest.raises(GlimpseError, match="No active position"):
        client.exit_consolidated(6674, 500)


# exit_consolidated_multi


@respx.mock
def test_exit_consolidated_multi_live() -> None:
    respx.post(f"{BASE}/api/v1/nmarket/exit-consolidated-multi").mock(
        return_value=httpx.Response(200, json={"proceeds": 100})
    )
    legs = [ExitLegReq(option_id=500, contracts=5), ExitLegReq(option_id=501, contracts=2)]
    with _client() as client:
        result = client.exit_consolidated_multi(6674, legs)
    assert result == {"proceeds": 100}


@respx.mock
def test_exit_consolidated_multi_dry_run_uses_given_contracts() -> None:
    real_route = respx.post(f"{BASE}/api/v1/nmarket/exit-consolidated-multi")
    estimate_route = respx.post(f"{BASE}/api/v1/nmarket/trades/estimate").mock(
        return_value=httpx.Response(200, json=_estimate_payload(trade_type="sell"))
    )
    legs = [ExitLegReq(option_id=500, contracts=5)]
    with _client(dry_run=True) as client:
        result = client.exit_consolidated_multi(6674, legs)

    assert isinstance(result, DryRunTradeResult)
    assert not real_route.called
    assert b'"contracts":5' in estimate_route.calls.last.request.content


#  exit_multi_topic_multi_leg 


@respx.mock
def test_exit_multi_topic_multi_leg_live() -> None:
    payload = {
        "results": [
            {"topic_id": 6674, "trade_id": "t3", "total_proceeds_millisats": 6000},
            {"topic_id": 7000, "error": "market already resolved"},
        ],
        "topics_requested": 2,
        "topics_exited": 1,
        "topics_failed": 1,
        "total_proceeds_millisats": 6000,
    }
    respx.post(f"{BASE}/api/v1/nmarket/exit-multi-topic-multi-leg").mock(
        return_value=httpx.Response(200, json=payload)
    )
    topics = [
        ExitMultiTopicLegGroup(topic_id=6674, legs=[ExitLegReq(option_id=500, contracts=5)]),
        ExitMultiTopicLegGroup(topic_id=7000, legs=[ExitLegReq(option_id=600, contracts=1)]),
    ]
    with _client() as client:
        result = client.exit_multi_topic_multi_leg(topics)

    assert not isinstance(result, DryRunTradeResult)
    assert result.topics_exited == 1
    assert result.topics_failed == 1
    assert result.results is not None
    assert result.results[1].error == "market already resolved"


@respx.mock
def test_exit_multi_topic_multi_leg_dry_run_estimates_each_topic() -> None:
    real_route = respx.post(f"{BASE}/api/v1/nmarket/exit-multi-topic-multi-leg")
    estimate_route = respx.post(f"{BASE}/api/v1/nmarket/trades/estimate").mock(
        return_value=httpx.Response(200, json=_estimate_payload(trade_type="sell"))
    )
    topics = [
        ExitMultiTopicLegGroup(topic_id=6674, legs=[ExitLegReq(option_id=500, contracts=5)]),
        ExitMultiTopicLegGroup(topic_id=7000, legs=[ExitLegReq(option_id=600, contracts=1)]),
    ]
    with _client(dry_run=True) as client:
        result = client.exit_multi_topic_multi_leg(topics)

    assert isinstance(result, DryRunTradeResult)
    assert len(result.estimates) == 2
    assert not real_route.called
    assert estimate_route.call_count == 2


# exit_batch


@respx.mock
def test_exit_batch_live() -> None:
    payload = {
        "batch_id": "b1",
        "results": [{"topic_id": 6674, "trade_id": "t4", "total_proceeds_millisats": 9000}],
        "topics_exited": 1,
        "topics_failed": 0,
        "total_proceeds_millisats": 9000,
        "total_commission_millisats": 90,
    }
    route = respx.post(f"{BASE}/api/v1/nmarket/exit-batch").mock(
        return_value=httpx.Response(200, json=payload)
    )
    with _client() as client:
        result = client.exit_batch("b1")
    assert not isinstance(result, DryRunTradeResult)
    assert result.topics_exited == 1
    sent_body = route.calls.last.request.content
    assert b'"batch_id":"b1"' in sent_body


@respx.mock
def test_exit_batch_dry_run_groups_positions_by_topic() -> None:
    portfolio_payload = {
        "success": True,
        "message": [
            {"topic_id": 6674, "option_id": 500, "batch_id": "b1", "shares": 10.0, "status": "a"},
            {"topic_id": 6674, "option_id": 501, "batch_id": "b1", "shares": 3.0, "status": "a"},
            {"topic_id": 7000, "option_id": 1, "batch_id": "b1", "shares": 2.0, "status": "a"},
            {"topic_id": 8000, "option_id": 1, "batch_id": "other", "shares": 99.0, "status": "a"},
        ],
    }
    respx.get(f"{BASE}/api/v1/nmarket/consolidated-active-portfolio-without-pagination").mock(
        return_value=httpx.Response(200, json=portfolio_payload)
    )
    real_route = respx.post(f"{BASE}/api/v1/nmarket/exit-batch")
    estimate_route = respx.post(f"{BASE}/api/v1/nmarket/trades/estimate").mock(
        return_value=httpx.Response(200, json=_estimate_payload(trade_type="sell"))
    )

    with _client(dry_run=True) as client:
        result = client.exit_batch("b1")

    assert isinstance(result, DryRunTradeResult)
    # two distinct topics belong to batch b1 (6674 with 2 legs, 7000 with 1) -> 2 estimate calls
    assert len(result.estimates) == 2
    assert not real_route.called
    assert estimate_route.call_count == 2


# GlimpseAmbiguousTradeStateError


@respx.mock
def test_network_failure_on_enter_raises_ambiguous_trade_state_error() -> None:
    respx.post(f"{BASE}/api/v1/nmarket/enter-multi-topic-multi-leg").mock(
        side_effect=httpx.ConnectError("connection reset")
    )
    topics = [EnterMultiTopicLegGroup(topic_id=6674, legs=[TradeLeg(option_id=500, contracts=10)])]
    with _client() as client, pytest.raises(GlimpseAmbiguousTradeStateError) as exc_info:
        client.enter_multi_topic_multi_leg(topics)

    assert "trade state is unknown" in str(exc_info.value)
    assert exc_info.value.path == "/api/v1/nmarket/enter-multi-topic-multi-leg"


@respx.mock
def test_network_failure_on_exit_batch_raises_ambiguous_trade_state_error() -> None:
    respx.post(f"{BASE}/api/v1/nmarket/exit-batch").mock(side_effect=httpx.ReadTimeout("timed out"))
    with _client() as client, pytest.raises(GlimpseAmbiguousTradeStateError):
        client.exit_batch("b1")


@respx.mock
def test_http_error_response_on_trade_post_is_not_ambiguous() -> None:
    respx.post(f"{BASE}/api/v1/nmarket/exit-batch").mock(
        return_value=httpx.Response(400, json={"error": "batch not found"})
    )
    with _client() as client, pytest.raises(GlimpseValidationError):
        client.exit_batch("b1")
