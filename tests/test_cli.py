import json

import httpx
import respx
from click.testing import CliRunner

from glimpse_markets.cli import main

BASE = "https://main.bpmapi.io"
KEY_ENV = {"GLIMPSE_API_KEY": "glp_live_test"}


def _runner() -> CliRunner:
    return CliRunner()


def test_help() -> None:
    result = _runner().invoke(main, ["--help"])
    assert result.exit_code == 0
    assert "balance" in result.output
    assert "portfolio" in result.output


def test_balance_missing_key_fails_cleanly(monkeypatch) -> None:
    monkeypatch.delenv("GLIMPSE_API_KEY", raising=False)
    result = _runner().invoke(main, ["balance"])
    assert result.exit_code == 1
    assert "GLIMPSE_API_KEY is required" in result.output


@respx.mock
def test_balance_success() -> None:
    respx.get(f"{BASE}/api/v1/wallet-balance").mock(
        return_value=httpx.Response(200, json={"balance_millisats": 1000})
    )
    result = _runner().invoke(main, ["balance"], env=KEY_ENV)
    assert result.exit_code == 0
    assert json.loads(result.output) == {"balance_millisats": 1000}


@respx.mock
def test_balance_api_error_surfaces_cleanly() -> None:
    respx.get(f"{BASE}/api/v1/wallet-balance").mock(
        return_value=httpx.Response(500, json={"error": "internal error"})
    )
    result = _runner().invoke(main, ["balance"], env=KEY_ENV)
    assert result.exit_code == 1
    assert "Error:" in result.output
    assert "internal error" in result.output


@respx.mock
def test_batches_without_batch_id_lists_batches() -> None:
    respx.get(f"{BASE}/api/v1/nmarket/batches").mock(
        return_value=httpx.Response(200, json={"batches": [], "count": 0})
    )
    result = _runner().invoke(main, ["batches"])
    assert result.exit_code == 0
    assert json.loads(result.output) == {"batches": [], "count": 0}


@respx.mock
def test_batches_with_batch_id_shows_active_markets() -> None:
    respx.get(f"{BASE}/api/v1/nmarket/batches/b1/active-markets").mock(
        return_value=httpx.Response(200, json={"batch_id": "b1", "markets": []})
    )
    result = _runner().invoke(main, ["batches", "--batch-id", "b1"])
    assert result.exit_code == 0
    assert json.loads(result.output)["batch_id"] == "b1"


@respx.mock
def test_quotes() -> None:
    respx.get(f"{BASE}/api/v1/nmarket/markets/6674/quotes").mock(
        return_value=httpx.Response(200, json={"topic_id": 6674, "quote_mode": "live"})
    )
    result = _runner().invoke(main, ["quotes", "--topic-id", "6674"])
    assert result.exit_code == 0
    assert json.loads(result.output)["topic_id"] == 6674


@respx.mock
def test_estimate_single_leg() -> None:
    route = respx.post(f"{BASE}/api/v1/nmarket/trades/estimate").mock(
        return_value=httpx.Response(200, json={"topic_id": 6674, "trade_type": "buy"})
    )
    result = _runner().invoke(
        main, ["estimate", "--topic-id", "6674", "--type", "buy", "--leg", "500:10"]
    )
    assert result.exit_code == 0
    assert json.loads(result.output)["trade_type"] == "buy"
    assert b'"option_id":500' in route.calls.last.request.content


@respx.mock
def test_estimate_multiple_legs() -> None:
    route = respx.post(f"{BASE}/api/v1/nmarket/trades/estimate").mock(
        return_value=httpx.Response(200, json={"leg_count": 2})
    )
    result = _runner().invoke(
        main,
        [
            "estimate",
            "--topic-id",
            "6674",
            "--type",
            "buy",
            "--leg",
            "500:10",
            "--leg",
            "501:5",
        ],
    )
    assert result.exit_code == 0
    body = json.loads(route.calls.last.request.content)
    assert len(body["legs"]) == 2


def test_estimate_bad_leg_format_is_a_usage_error() -> None:
    result = _runner().invoke(
        main, ["estimate", "--topic-id", "6674", "--type", "buy", "--leg", "not-a-leg"]
    )
    assert result.exit_code == 2
    assert "OPTION_ID:CONTRACTS" in result.output


@respx.mock
def test_execute_live_requires_api_key(monkeypatch) -> None:
    monkeypatch.delenv("GLIMPSE_API_KEY", raising=False)
    result = _runner().invoke(main, ["execute", "--topic-id", "6674", "--leg", "500:10"])
    assert result.exit_code == 1
    assert "GLIMPSE_API_KEY is required" in result.output


@respx.mock
def test_execute_dry_run_does_not_require_api_key() -> None:
    real_route = respx.post(f"{BASE}/api/v1/nmarket/enter-multi-topic-multi-leg")
    respx.post(f"{BASE}/api/v1/nmarket/trades/estimate").mock(
        return_value=httpx.Response(200, json={"topic_id": 6674, "trade_type": "buy"})
    )
    result = _runner().invoke(
        main, ["execute", "--topic-id", "6674", "--leg", "500:10", "--dry-run"]
    )
    assert result.exit_code == 0
    assert json.loads(result.output)["simulated"] is True
    assert not real_route.called


@respx.mock
def test_execute_live_success() -> None:
    respx.post(f"{BASE}/api/v1/nmarket/enter-multi-topic-multi-leg").mock(
        return_value=httpx.Response(200, json={"topics_entered": 1, "topics_failed": 0})
    )
    result = _runner().invoke(
        main, ["execute", "--topic-id", "6674", "--leg", "500:10"], env=KEY_ENV
    )
    assert result.exit_code == 0
    assert json.loads(result.output)["topics_entered"] == 1


@respx.mock
def test_exit_full_position_dry_run_requires_key() -> None:
    result = _runner().invoke(
        main, ["exit", "--topic-id", "6674", "--option-id", "500", "--dry-run"]
    )
    assert result.exit_code == 1
    assert "GLIMPSE_API_KEY is required" in result.output


@respx.mock
def test_exit_partial_dry_run_does_not_require_key() -> None:
    real_route = respx.post(f"{BASE}/api/v1/nmarket/exit-consolidated")
    respx.post(f"{BASE}/api/v1/nmarket/trades/estimate").mock(
        return_value=httpx.Response(200, json={"topic_id": 6674, "trade_type": "sell"})
    )
    result = _runner().invoke(
        main,
        ["exit", "--topic-id", "6674", "--option-id", "500", "--shares", "5", "--dry-run"],
    )
    assert result.exit_code == 0
    assert json.loads(result.output)["simulated"] is True
    assert not real_route.called


@respx.mock
def test_exit_live_success() -> None:
    respx.post(f"{BASE}/api/v1/nmarket/exit-consolidated").mock(
        return_value=httpx.Response(200, json={"trade_id": "t1"})
    )
    result = _runner().invoke(
        main, ["exit", "--topic-id", "6674", "--option-id", "500"], env=KEY_ENV
    )
    assert result.exit_code == 0
    assert json.loads(result.output) == {"trade_id": "t1"}


@respx.mock
def test_exit_batch_dry_run_still_requires_key() -> None:
    result = _runner().invoke(main, ["exit-batch", "--batch-id", "b1", "--dry-run"])
    assert result.exit_code == 1
    assert "GLIMPSE_API_KEY is required" in result.output


@respx.mock
def test_exit_batch_live_success() -> None:
    respx.post(f"{BASE}/api/v1/nmarket/exit-batch").mock(
        return_value=httpx.Response(200, json={"batch_id": "b1", "topics_exited": 2})
    )
    result = _runner().invoke(main, ["exit-batch", "--batch-id", "b1"], env=KEY_ENV)
    assert result.exit_code == 0
    assert json.loads(result.output)["topics_exited"] == 2


# --- portfolio subcommands ---------------------------------------------------


@respx.mock
def test_portfolio_active() -> None:
    respx.get(f"{BASE}/api/v1/nmarket/consolidated-active-portfolio-without-pagination").mock(
        return_value=httpx.Response(200, json={"success": True, "message": []})
    )
    result = _runner().invoke(main, ["portfolio", "active"], env=KEY_ENV)
    assert result.exit_code == 0
    assert json.loads(result.output)["success"] is True


@respx.mock
def test_portfolio_summary() -> None:
    respx.get(f"{BASE}/api/v1/nmarket/consolidated-portfolio-summary").mock(
        return_value=httpx.Response(200, json={"success": True, "message": None})
    )
    result = _runner().invoke(main, ["portfolio", "summary"], env=KEY_ENV)
    assert result.exit_code == 0


@respx.mock
def test_portfolio_ended_sends_pagination_params() -> None:
    route = respx.get(f"{BASE}/api/v1/nmarket/consolidated-ended-unresolved-portfolio").mock(
        return_value=httpx.Response(200, json={"success": True, "message": [], "total": 0})
    )
    result = _runner().invoke(
        main, ["portfolio", "ended", "--limit", "10", "--offset", "5"], env=KEY_ENV
    )
    assert result.exit_code == 0
    params = route.calls.last.request.url.params
    assert params["limit"] == "10"
    assert params["offset"] == "5"


@respx.mock
def test_portfolio_resolved() -> None:
    respx.get(f"{BASE}/api/v1/nmarket/consolidated-ended-resolved-portfolio").mock(
        return_value=httpx.Response(200, json={"success": True, "message": [], "total": 0})
    )
    result = _runner().invoke(main, ["portfolio", "resolved"], env=KEY_ENV)
    assert result.exit_code == 0


def test_portfolio_missing_key(monkeypatch) -> None:
    monkeypatch.delenv("GLIMPSE_API_KEY", raising=False)
    result = _runner().invoke(main, ["portfolio", "active"])
    assert result.exit_code == 1
    assert "GLIMPSE_API_KEY is required" in result.output


def test_help_mentions_optional_extras() -> None:
    result = _runner().invoke(main, ["--help"])
    assert result.exit_code == 0
    assert "glimpse-markets[forecasting]" in result.output
    assert "glimpse-markets[yfinance]" in result.output


def test_bare_invocation_also_shows_extras_notice() -> None:
    result = _runner().invoke(main, [])
    assert "glimpse-markets[forecasting]" in result.output
    assert "glimpse-markets[yfinance]" in result.output
