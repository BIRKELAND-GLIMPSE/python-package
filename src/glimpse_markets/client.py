"""Synchronous client for the Glimpse Nmarket API.

Covers every ``GET`` endpoint in ``main_glimpse_service/docs/swagger.json``
"""

from __future__ import annotations

import os
from types import TracebackType
from typing import Any

import httpx

from glimpse_markets._base import DEFAULT_BASE_URL, DEFAULT_TIMEOUT, BaseClient
from glimpse_markets.models import (
    BatchMarketsPageResponse,
    BatchMarketsResponse,
    BatchStatsResponse,
    ConsolidatedPortfolioSummaryResponse,
    ListBatchesResponse,
    MarketStatsResponse,
    PaginatedPortfolioListResponse,
    PortfolioListResponse,
    QuotesResponse,
    VolumeByOptionResponse,
)
from glimpse_markets.ratelimit import RateLimiter


class Client(BaseClient):
    def __init__(
        self,
        api_key: str | None = None,
        base_url: str = DEFAULT_BASE_URL,
        timeout: float = DEFAULT_TIMEOUT,
        rate_limiter: RateLimiter | None = None,
    ) -> None:
        super().__init__(api_key=api_key, base_url=base_url)
        self._http = httpx.Client(timeout=timeout)
        self._rate_limiter = rate_limiter if rate_limiter is not None else RateLimiter()

    @classmethod
    def from_env(cls, **kwargs: Any) -> Client:
        """Build a client from the ``GLIMPSE_API_KEY`` / ``GLIMPSE_BASE_URL`` env vars."""
        api_key = os.environ.get("GLIMPSE_API_KEY")
        base_url = os.environ.get("GLIMPSE_BASE_URL", DEFAULT_BASE_URL)
        return cls(api_key=api_key, base_url=base_url, **kwargs)

    def close(self) -> None:
        self._http.close()

    def __enter__(self) -> Client:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        self.close()

    def _get(self, path: str, params: dict[str, Any] | None = None) -> Any:
        self._rate_limiter.acquire()
        response = self._http.get(
            self._url(path),
            params={k: v for k, v in (params or {}).items() if v is not None},
            headers=self._headers(),
        )
        self._raise_for_error(response)
        return response.json()

    # wallet

    def wallet_balance(self) -> dict[str, Any]:
        """``GET /api/v1/wallet-balance`` (requires API key).

        No response schema is published by the server (swagger marks it
        ``additionalProperties: true``), so this returns the raw parsed JSON.
        """
        return self._get("/api/v1/wallet-balance")  # type: ignore[no-any-return]

    # batches

    def batches(self) -> ListBatchesResponse:
        """``GET /api/v1/nmarket/batches`` (public)."""
        return ListBatchesResponse.model_validate(self._get("/api/v1/nmarket/batches"))

    def batch_active_markets(self, batch_id: str) -> BatchMarketsResponse:
        """``GET /api/v1/nmarket/batches/{batch_id}/active-markets`` (public)."""
        data = self._get(f"/api/v1/nmarket/batches/{batch_id}/active-markets")
        return BatchMarketsResponse.model_validate(data)

    def batch_markets(self, batch_id: str) -> BatchMarketsResponse:
        """``GET /api/v1/nmarket/batches/{batch_id}/markets`` (public).

        All markets in the batch, not just active ones.
        """
        data = self._get(f"/api/v1/nmarket/batches/{batch_id}/markets")
        return BatchMarketsResponse.model_validate(data)

    def batch_stats(self, batch_id: str) -> BatchStatsResponse:
        """``GET /api/v1/nmarket/batches/{batch_id}/stats`` (public)."""
        data = self._get(f"/api/v1/nmarket/batches/{batch_id}/stats")
        return BatchStatsResponse.model_validate(data)

    def batch_active_markets_page(
        self, batch_id: str, page: int | None = None, page_size: int | None = None
    ) -> BatchMarketsPageResponse:
        """``GET /api/v1/nmarket/v2/batches/{batch_id}/active-markets`` (public, paginated)."""
        data = self._get(
            f"/api/v1/nmarket/v2/batches/{batch_id}/active-markets",
            params={"page": page, "page_size": page_size},
        )
        return BatchMarketsPageResponse.model_validate(data)

    def batch_resolved_markets_page(
        self, batch_id: str, page: int | None = None, page_size: int | None = None
    ) -> BatchMarketsPageResponse:
        """``GET /api/v1/nmarket/v2/batches/{batch_id}/resolved-markets`` (public, paginated)."""
        data = self._get(
            f"/api/v1/nmarket/v2/batches/{batch_id}/resolved-markets",
            params={"page": page, "page_size": page_size},
        )
        return BatchMarketsPageResponse.model_validate(data)

    # markets

    def markets(self, batch_id: str | None = None) -> dict[str, Any]:
        """``GET /api/v1/nmarket/markets`` (public). No response schema published."""
        return self._get( 
            "/api/v1/nmarket/markets", params={"batch_id": batch_id}
        )

    def market_quotes(self, topic_id: int) -> QuotesResponse:
        """``GET /api/v1/nmarket/markets/{topic_id}/quotes`` (public). Live LMSR quote."""
        data = self._get(f"/api/v1/nmarket/markets/{topic_id}/quotes")
        return QuotesResponse.model_validate(data)

    def market_stats(self, topic_id: int) -> MarketStatsResponse:
        """``GET /api/v1/nmarket/markets/{topic_id}/stats`` (public)."""
        data = self._get(f"/api/v1/nmarket/markets/{topic_id}/stats")
        return MarketStatsResponse.model_validate(data)

    def market_volume(self, topic_id: int) -> VolumeByOptionResponse:
        """``GET /api/v1/nmarket/markets/{topic_id}/volume`` (public)."""
        data = self._get(f"/api/v1/nmarket/markets/{topic_id}/volume")
        return VolumeByOptionResponse.model_validate(data)

    #  ended / resolved market listings

    def ended_by_batch(
        self, batch_id: str, limit: int | None = None, offset: int | None = None
    ) -> dict[str, Any]:
        """``GET /api/v1/nmarket/ended-by-batch`` (public, paginated).

        No response schema is published for this endpoint.
        """
        return self._get(  # type: ignore[no-any-return]
            "/api/v1/nmarket/ended-by-batch",
            params={"batch_id": batch_id, "limit": limit, "offset": offset},
        )

    def ended_past_168h(self, batch_id: str) -> dict[str, Any]:
        """``GET /api/v1/nmarket/ended-past-168h`` (public). No response schema published."""
        return self._get(  # type: ignore[no-any-return]
            "/api/v1/nmarket/ended-past-168h", params={"batch_id": batch_id}
        )

    def resolved_past_168h(self, batch_id: str) -> dict[str, Any]:
        """``GET /api/v1/nmarket/resolved-past-168h`` (public). No response schema published."""
        return self._get(  # type: ignore[no-any-return]
            "/api/v1/nmarket/resolved-past-168h", params={"batch_id": batch_id}
        )

    def bet_slip(self, uuid: str) -> dict[str, Any]:
        """``GET /api/v1/nmarket/bet-slip-by-uuid`` (public). No response schema published."""
        return self._get(  # type: ignore[no-any-return]
            "/api/v1/nmarket/bet-slip-by-uuid", params={"uuid": uuid}
        )

    # portfolio (requires API key)

    def portfolio_active(self) -> PortfolioListResponse:
        """``GET /api/v1/nmarket/consolidated-active-portfolio-without-pagination``."""
        data = self._get("/api/v1/nmarket/consolidated-active-portfolio-without-pagination")
        return PortfolioListResponse.model_validate(data)

    def portfolio_ended(
        self, limit: int | None = None, offset: int | None = None
    ) -> PaginatedPortfolioListResponse:
        """``GET /api/v1/nmarket/consolidated-ended-unresolved-portfolio``.

        Positions in markets that have ended but not yet resolved.
        """
        data = self._get(
            "/api/v1/nmarket/consolidated-ended-unresolved-portfolio",
            params={"limit": limit, "offset": offset},
        )
        return PaginatedPortfolioListResponse.model_validate(data)

    def portfolio_resolved(
        self, limit: int | None = None, offset: int | None = None
    ) -> PaginatedPortfolioListResponse:
        """``GET /api/v1/nmarket/consolidated-ended-resolved-portfolio``."""
        data = self._get(
            "/api/v1/nmarket/consolidated-ended-resolved-portfolio",
            params={"limit": limit, "offset": offset},
        )
        return PaginatedPortfolioListResponse.model_validate(data)

    def portfolio_summary(self) -> ConsolidatedPortfolioSummaryResponse:
        """``GET /api/v1/nmarket/consolidated-portfolio-summary``."""
        data = self._get("/api/v1/nmarket/consolidated-portfolio-summary")
        return ConsolidatedPortfolioSummaryResponse.model_validate(data)
