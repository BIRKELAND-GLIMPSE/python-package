"""Transport-agnostic request building and error parsing.
"""

from __future__ import annotations

import contextlib
import math
import time
from datetime import timezone
from email.utils import parsedate_to_datetime
from typing import Any

import httpx

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

DEFAULT_BASE_URL = "https://main.bpmapi.io"
DEFAULT_TIMEOUT = 30.0


def _parse_retry_after(value: str | None) -> float | None:
    """Return a finite delay for a seconds value or an HTTP-date.

    A malformed advisory header must not mask the underlying HTTP 429.
    """
    if not value:
        return None
    try:
        seconds = float(value)
    except ValueError:
        try:
            retry_at = parsedate_to_datetime(value)
            # The obsolete asctime HTTP-date format has no explicit zone.
            if retry_at.tzinfo is None:
                retry_at = retry_at.replace(tzinfo=timezone.utc)
            return max(0.0, retry_at.timestamp() - time.time())
        except (ValueError, TypeError, OverflowError):
            return None
    return seconds if math.isfinite(seconds) and seconds >= 0 else None


class BaseClient:
    """Holds credentials/base URL and knows how to build headers and raise errors."""

    def __init__(self, api_key: str | None, base_url: str) -> None:
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")

    def _headers(self) -> dict[str, str]:
        headers = {"Accept": "application/json"}
        if self.api_key:
            headers["X-API-Key"] = self.api_key
        return headers

    def _url(self, path: str) -> str:
        return f"{self.base_url}{path}"

    @staticmethod
    def _raise_for_error(response: httpx.Response) -> None:
        if response.is_success:
            return

        body: Any = {}
        with contextlib.suppress(ValueError):
            body = response.json()

        error = body.get("error") if isinstance(body, dict) else None
        reason = body.get("reason") if isinstance(body, dict) else None
        message = body.get("message") if isinstance(body, dict) else None
        status = response.status_code

        if status == 401:
            raise GlimpseAuthenticationError(status, error, reason, message, body)
        if status == 403:
            if error == "TRADING_NOT_ALLOWED" or reason is not None:
                raise GlimpseTradingNotEligibleError(status, error, reason, message, body)
            raise GlimpseForbiddenError(status, error, reason, message, body)
        if status == 404:
            raise GlimpseNotFoundError(status, error, reason, message, body)
        if status == 429:
            retry_after_header = response.headers.get("Retry-After")
            retry_after = _parse_retry_after(retry_after_header)
            raise GlimpseRateLimitError(
                status, error, reason, message, body, retry_after=retry_after
            )
        if status == 400:
            raise GlimpseValidationError(status, error, reason, message, body)
        if status >= 500:
            raise GlimpseServerError(status, error, reason, message, body)
        raise GlimpseAPIError(status, error, reason, message, body)
