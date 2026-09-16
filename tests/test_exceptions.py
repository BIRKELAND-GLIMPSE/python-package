import httpx
import pytest

from glimpse_markets._base import BaseClient
from glimpse_markets.exceptions import (
    GlimpseAPIError,
    GlimpseAuthenticationError,
    GlimpseForbiddenError,
    GlimpseNotFoundError,
    GlimpseRateLimitError,
    GlimpseServerError,
    GlimpseTradingNotEligibleError,
    GlimpseValidationError,
)

_REQUEST = httpx.Request("GET", "https://main.bpmapi.io/api/v1/wallet-balance")


def _response(
    status_code: int, json: dict | None = None, headers: dict | None = None
) -> httpx.Response:
    return httpx.Response(status_code, json=json or {}, headers=headers or {}, request=_REQUEST)


def test_success_does_not_raise() -> None:
    BaseClient._raise_for_error(_response(200, {"ok": True}))


def test_401_raises_authentication_error() -> None:
    with pytest.raises(GlimpseAuthenticationError) as exc_info:
        BaseClient._raise_for_error(_response(401, {"error": "invalid api key"}))
    err = exc_info.value
    assert err.status_code == 401
    assert err.error == "invalid api key"


def test_403_generic_raises_forbidden_error() -> None:
    with pytest.raises(GlimpseForbiddenError) as exc_info:
        BaseClient._raise_for_error(_response(403, {"error": "not allowed"}))
    assert not isinstance(exc_info.value, GlimpseTradingNotEligibleError)


def test_403_trading_not_allowed_raises_trading_not_eligible_error() -> None:
    body = {"error": "TRADING_NOT_ALLOWED", "canTrade": False, "reason": "SUITABILITY_NOT_MET"}
    with pytest.raises(GlimpseTradingNotEligibleError) as exc_info:
        BaseClient._raise_for_error(_response(403, body))
    err = exc_info.value
    assert err.reason == "SUITABILITY_NOT_MET"
    assert isinstance(err, GlimpseForbiddenError)


def test_404_raises_not_found_error() -> None:
    with pytest.raises(GlimpseNotFoundError):
        BaseClient._raise_for_error(_response(404, {"error": "not found"}))


def test_400_raises_validation_error() -> None:
    with pytest.raises(GlimpseValidationError):
        BaseClient._raise_for_error(_response(400, {"error": "bad request"}))


def test_429_raises_rate_limit_error_with_retry_after() -> None:
    body = {"error": "API key rate limit exceeded"}
    with pytest.raises(GlimpseRateLimitError) as exc_info:
        BaseClient._raise_for_error(_response(429, body, headers={"Retry-After": "12"}))
    assert exc_info.value.retry_after == 12.0


def test_429_without_retry_after_header() -> None:
    with pytest.raises(GlimpseRateLimitError) as exc_info:
        BaseClient._raise_for_error(_response(429, {"error": "rate limited"}))
    assert exc_info.value.retry_after is None


def test_500_raises_server_error() -> None:
    with pytest.raises(GlimpseServerError):
        BaseClient._raise_for_error(_response(500, {}))


def test_unmapped_status_raises_generic_api_error() -> None:
    with pytest.raises(GlimpseAPIError):
        BaseClient._raise_for_error(_response(418, {}))


def test_non_json_body_does_not_crash_parsing() -> None:
    response = httpx.Response(500, content=b"not json", request=_REQUEST)
    with pytest.raises(GlimpseServerError) as exc_info:
        BaseClient._raise_for_error(response)
    assert exc_info.value.error is None


def test_error_str_includes_status_and_reason() -> None:
    body = {"error": "TRADING_NOT_ALLOWED", "reason": "SUITABILITY_NOT_MET"}
    with pytest.raises(GlimpseTradingNotEligibleError) as exc_info:
        BaseClient._raise_for_error(_response(403, body))
    text = str(exc_info.value)
    assert "403" in text
    assert "TRADING_NOT_ALLOWED" in text
    assert "SUITABILITY_NOT_MET" in text
