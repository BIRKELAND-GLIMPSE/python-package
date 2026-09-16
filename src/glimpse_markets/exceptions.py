"""Exception hierarchy for glimpse-markets.
"""

from __future__ import annotations

from typing import Any


class GlimpseError(Exception):
    """Base class for every error this package raises."""


class GlimpseAPIError(GlimpseError):
    """The API responded with a non-2xx status."""

    def __init__(
        self,
        status_code: int,
        error: str | None = None,
        reason: str | None = None,
        message: str | None = None,
        raw: dict[str, Any] | None = None,
    ) -> None:
        self.status_code = status_code
        self.error = error
        self.reason = reason
        self.message = message
        self.raw = raw or {}
        super().__init__(self._describe())

    def _describe(self) -> str:
        parts = [f"HTTP {self.status_code}"]
        if self.error:
            parts.append(self.error)
        if self.reason:
            parts.append(f"reason={self.reason}")
        if self.message:
            parts.append(self.message)
        return " - ".join(parts)


class GlimpseAuthenticationError(GlimpseAPIError):
    """401 — missing or invalid API key."""


class GlimpseForbiddenError(GlimpseAPIError):
    """403 — request understood but not permitted."""


class GlimpseTradingNotEligibleError(GlimpseForbiddenError):
    """403 specifically for trading-eligibility failures.

    ``.reason`` is one of the fixed set found in
    ``customer_eligibility_service.go``: ``SELF_EXCLUDED``,
    ``COOLDOWN_ACTIVE``, ``SUITABILITY_NOT_MET``, ``BASIC_QUIZ_NOT_PASSED``,
    ``RISK_DISCLOSURE_NOT_ACCEPTED``, ``RISK_DISCLOSURE_VERSION_OUTDATED``,
    ``BANKROLL_LIMIT_EXCEEDED``, ``ELIGIBILITY_LEVEL_NOT_TRADABLE``,
    ``TRADING_FROZEN_BY_ADMIN``, ``STATUS_NOT_FOUND``.
    """


class GlimpseNotFoundError(GlimpseAPIError):
    """404."""


class GlimpseValidationError(GlimpseAPIError):
    """400 — bad request parameters."""


class GlimpseRateLimitError(GlimpseAPIError):
    """429 — the 60-requests/60-seconds per-API-key limit was exceeded.

    ``.retry_after`` mirrors the server's ``Retry-After`` header (seconds),
    when present.
    """

    def __init__(self, *args: Any, retry_after: float | None = None, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.retry_after = retry_after


class GlimpseServerError(GlimpseAPIError):
    """5xx."""


class GlimpseAmbiguousTradeStateError(GlimpseError):
    """A network-level failure happened while submitting a trade-mutating
    request (``enter-multi-topic-multi-leg`` or any ``exit-*`` endpoint).
    """

    def __init__(self, path: str, original: Exception) -> None:
        self.path = path
        self.original = original
        super().__init__(
            f"Network failure while calling {path} — trade state is unknown. "
            f"Check your portfolio before retrying. Original error: {original!r}"
        )
