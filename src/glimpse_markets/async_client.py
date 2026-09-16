"""Asynchronous client for the Glimpse Nmarket API.
"""

from __future__ import annotations

import os
from types import TracebackType
from typing import Any

import httpx

from glimpse_markets._base import DEFAULT_BASE_URL, DEFAULT_TIMEOUT, BaseClient
from glimpse_markets.enums import TradeType
from glimpse_markets.exceptions import GlimpseAmbiguousTradeStateError, GlimpseError
from glimpse_markets.models import (
    BatchMarketsPageResponse,
    BatchMarketsResponse,
    BatchStatsResponse,
    ConsolidatedPortfolioSummaryResponse,
    DryRunTradeResult,
    EnterMultiTopicLegGroup,
    EnterMultiTopicMultiLegRequest,
    EnterMultiTopicMultiLegResponse,
    EstimateTradeLegsResponse,
    ExecuteTradeRequest,
    ExitBatchRequest,
    ExitBatchResponse,
    ExitLegReq,
    ExitMultipleLegsRequest,
    ExitMultiTopicLegGroup,
    ExitMultiTopicMultiLegRequest,
    ExitMultiTopicMultiLegResponse,
    ExitSingleRequest,
    ListBatchesResponse,
    MarketStatsResponse,
    PaginatedPortfolioListResponse,
    PortfolioListResponse,
    QuotesResponse,
    TradeLeg,
    VolumeByOptionResponse,
)
from glimpse_markets.ratelimit import AsyncRateLimiter
from glimpse_markets.streaming import MarketStream


class AsyncClient(BaseClient):
    def __init__(
        self,
        api_key: str | None = None,
        base_url: str = DEFAULT_BASE_URL,
        timeout: float = DEFAULT_TIMEOUT,
        rate_limiter: AsyncRateLimiter | None = None,
        dry_run: bool = False,
    ) -> None:
        super().__init__(api_key=api_key, base_url=base_url)
        self._http = httpx.AsyncClient(timeout=timeout)
        self._rate_limiter = rate_limiter if rate_limiter is not None else AsyncRateLimiter()
        self.dry_run = dry_run

    @classmethod
    def from_env(cls, **kwargs: Any) -> AsyncClient:
        """Build a client from the ``GLIMPSE_API_KEY`` / ``GLIMPSE_BASE_URL`` env vars."""
        api_key = os.environ.get("GLIMPSE_API_KEY")
        base_url = os.environ.get("GLIMPSE_BASE_URL", DEFAULT_BASE_URL)
        return cls(api_key=api_key, base_url=base_url, **kwargs)

    async def close(self) -> None:
        await self._http.aclose()

    async def __aenter__(self) -> AsyncClient:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        await self.close()

    async def _get(self, path: str, params: dict[str, Any] | None = None) -> Any:
        await self._rate_limiter.acquire()
        response = await self._http.get(
            self._url(path),
            params={k: v for k, v in (params or {}).items() if v is not None},
            headers=self._headers(),
        )
        self._raise_for_error(response)
        return response.json()

    async def _post(self, path: str, json_body: dict[str, Any]) -> Any:
        """For side-effect-free POSTs (``/trades/estimate``). Not for trade
        execution — see ``_post_mutating``."""
        await self._rate_limiter.acquire()
        response = await self._http.post(self._url(path), json=json_body, headers=self._headers())
        self._raise_for_error(response)
        return response.json()

    async def _post_mutating(self, path: str, json_body: dict[str, Any]) -> Any:
        """For trade-execution POSTs. A network-level failure here can't be
        distinguished from "the order went through but the response was
        lost," so it's surfaced as GlimpseAmbiguousTradeStateError instead
        of a plain transport error
        """
        await self._rate_limiter.acquire()
        try:
            response = await self._http.post(
                self._url(path), json=json_body, headers=self._headers()
            )
        except httpx.TransportError as exc:
            raise GlimpseAmbiguousTradeStateError(path, exc) from exc
        self._raise_for_error(response)
        return response.json()

    # wallet

    async def wallet_balance(self) -> dict[str, Any]:
        """``GET /api/v1/wallet-balance`` (requires API key)."""
        return await self._get("/api/v1/wallet-balance")  # type: ignore[no-any-return]

    # batches

    async def batches(self) -> ListBatchesResponse:
        """``GET /api/v1/nmarket/batches`` (public)."""
        data = await self._get("/api/v1/nmarket/batches")
        return ListBatchesResponse.model_validate(data)

    async def batch_active_markets(self, batch_id: str) -> BatchMarketsResponse:
        """``GET /api/v1/nmarket/batches/{batch_id}/active-markets`` (public)."""
        data = await self._get(f"/api/v1/nmarket/batches/{batch_id}/active-markets")
        return BatchMarketsResponse.model_validate(data)

    async def batch_markets(self, batch_id: str) -> BatchMarketsResponse:
        """``GET /api/v1/nmarket/batches/{batch_id}/markets`` (public).

        All markets in the batch, not just active ones.
        """
        data = await self._get(f"/api/v1/nmarket/batches/{batch_id}/markets")
        return BatchMarketsResponse.model_validate(data)

    async def batch_stats(self, batch_id: str) -> BatchStatsResponse:
        """``GET /api/v1/nmarket/batches/{batch_id}/stats`` (public)."""
        data = await self._get(f"/api/v1/nmarket/batches/{batch_id}/stats")
        return BatchStatsResponse.model_validate(data)

    async def batch_active_markets_page(
        self, batch_id: str, page: int | None = None, page_size: int | None = None
    ) -> BatchMarketsPageResponse:
        """``GET /api/v1/nmarket/v2/batches/{batch_id}/active-markets`` (public, paginated)."""
        data = await self._get(
            f"/api/v1/nmarket/v2/batches/{batch_id}/active-markets",
            params={"page": page, "page_size": page_size},
        )
        return BatchMarketsPageResponse.model_validate(data)

    async def batch_resolved_markets_page(
        self, batch_id: str, page: int | None = None, page_size: int | None = None
    ) -> BatchMarketsPageResponse:
        """``GET /api/v1/nmarket/v2/batches/{batch_id}/resolved-markets`` (public, paginated)."""
        data = await self._get(
            f"/api/v1/nmarket/v2/batches/{batch_id}/resolved-markets",
            params={"page": page, "page_size": page_size},
        )
        return BatchMarketsPageResponse.model_validate(data)

    # markets

    async def markets(self, batch_id: str | None = None) -> dict[str, Any]:
        """``GET /api/v1/nmarket/markets`` (public). No response schema published."""
        return await self._get(  # type: ignore[no-any-return]
            "/api/v1/nmarket/markets", params={"batch_id": batch_id}
        )

    async def market_quotes(self, topic_id: int) -> QuotesResponse:
        """``GET /api/v1/nmarket/markets/{topic_id}/quotes`` (public). Live LMSR quote."""
        data = await self._get(f"/api/v1/nmarket/markets/{topic_id}/quotes")
        return QuotesResponse.model_validate(data)

    async def market_stats(self, topic_id: int) -> MarketStatsResponse:
        """``GET /api/v1/nmarket/markets/{topic_id}/stats`` (public)."""
        data = await self._get(f"/api/v1/nmarket/markets/{topic_id}/stats")
        return MarketStatsResponse.model_validate(data)

    async def market_volume(self, topic_id: int) -> VolumeByOptionResponse:
        """``GET /api/v1/nmarket/markets/{topic_id}/volume`` (public)."""
        data = await self._get(f"/api/v1/nmarket/markets/{topic_id}/volume")
        return VolumeByOptionResponse.model_validate(data)

    #  ended / resolved market listings

    async def ended_by_batch(
        self, batch_id: str, limit: int | None = None, offset: int | None = None
    ) -> dict[str, Any]:
        """``GET /api/v1/nmarket/ended-by-batch`` (public, paginated).

        No response schema is published for this endpoint.
        """
        return await self._get(  # type: ignore[no-any-return]
            "/api/v1/nmarket/ended-by-batch",
            params={"batch_id": batch_id, "limit": limit, "offset": offset},
        )

    async def ended_past_168h(self, batch_id: str) -> dict[str, Any]:
        """``GET /api/v1/nmarket/ended-past-168h`` (public). No response schema published."""
        return await self._get(  # type: ignore[no-any-return]
            "/api/v1/nmarket/ended-past-168h", params={"batch_id": batch_id}
        )

    async def resolved_past_168h(self, batch_id: str) -> dict[str, Any]:
        """``GET /api/v1/nmarket/resolved-past-168h`` (public). No response schema published."""
        return await self._get(  # type: ignore[no-any-return]
            "/api/v1/nmarket/resolved-past-168h", params={"batch_id": batch_id}
        )

    async def bet_slip(self, uuid: str) -> dict[str, Any]:
        """``GET /api/v1/nmarket/bet-slip-by-uuid`` (public). No response schema published."""
        return await self._get(  # type: ignore[no-any-return]
            "/api/v1/nmarket/bet-slip-by-uuid", params={"uuid": uuid}
        )

    # portfolio (requires API key)

    async def portfolio_active(self) -> PortfolioListResponse:
        """``GET /api/v1/nmarket/consolidated-active-portfolio-without-pagination``."""
        data = await self._get("/api/v1/nmarket/consolidated-active-portfolio-without-pagination")
        return PortfolioListResponse.model_validate(data)

    async def portfolio_ended(
        self, limit: int | None = None, offset: int | None = None
    ) -> PaginatedPortfolioListResponse:
        """``GET /api/v1/nmarket/consolidated-ended-unresolved-portfolio``.

        Positions in markets that have ended but not yet resolved.
        """
        data = await self._get(
            "/api/v1/nmarket/consolidated-ended-unresolved-portfolio",
            params={"limit": limit, "offset": offset},
        )
        return PaginatedPortfolioListResponse.model_validate(data)

    async def portfolio_resolved(
        self, limit: int | None = None, offset: int | None = None
    ) -> PaginatedPortfolioListResponse:
        """``GET /api/v1/nmarket/consolidated-ended-resolved-portfolio``."""
        data = await self._get(
            "/api/v1/nmarket/consolidated-ended-resolved-portfolio",
            params={"limit": limit, "offset": offset},
        )
        return PaginatedPortfolioListResponse.model_validate(data)

    async def portfolio_summary(self) -> ConsolidatedPortfolioSummaryResponse:
        """``GET /api/v1/nmarket/consolidated-portfolio-summary``."""
        data = await self._get("/api/v1/nmarket/consolidated-portfolio-summary")
        return ConsolidatedPortfolioSummaryResponse.model_validate(data)

    # streaming

    def stream_market_updates(
        self, topic_id: int | None = None, batch_id: str | None = None
    ) -> MarketStream:
        """A ``MarketStream`` over ``/ws/nmarket-updates``, using this client's ``base_url``.

        No API key is used — the feed is fully public. See ``streaming.py``
        for the wire protocol (subscribe filtering, message shape, and why
        there's no resolution event on this feed). Independent of this
        client's own HTTP connection; open as many as you like.
        """
        return MarketStream(base_url=self.base_url, topic_id=topic_id, batch_id=batch_id)

    # trades

    async def estimate_trade(
        self, topic_id: int, trade_type: TradeType | str, legs: list[TradeLeg]
    ) -> EstimateTradeLegsResponse:
        """``POST /api/v1/nmarket/trades/estimate`` (public).

        Side-effect-free — no funds move and no API key is required. Always
        call this before ``enter_multi_topic_multi_leg`` or an ``exit_*``
        call to check cost/price impact; it's also what ``dry_run`` mode
        uses under the hood.
        """
        request = ExecuteTradeRequest(
            topic_id=topic_id, trade_type=TradeType(trade_type), legs=legs
        )
        data = await self._post(
            "/api/v1/nmarket/trades/estimate", request.model_dump(mode="json", exclude_none=True)
        )
        return EstimateTradeLegsResponse.model_validate(data)

    async def enter_multi_topic_multi_leg(
        self, topics: list[EnterMultiTopicLegGroup], *, dry_run: bool | None = None
    ) -> EnterMultiTopicMultiLegResponse | DryRunTradeResult:
        """``POST /api/v1/nmarket/enter-multi-topic-multi-leg`` (requires API key). Buy-only.

        In dry-run mode (client default or this call's ``dry_run``
        override), no order is placed — each topic/leg group is priced via
        ``estimate_trade`` instead and a ``DryRunTradeResult`` comes back.
        """
        if self._effective_dry_run(dry_run):
            estimates = [
                await self.estimate_trade(group.topic_id, TradeType.BUY, group.legs)
                for group in topics
            ]
            return DryRunTradeResult(trade_type=TradeType.BUY, estimates=estimates)

        request = EnterMultiTopicMultiLegRequest(topics=topics)
        data = await self._post_mutating(
            "/api/v1/nmarket/enter-multi-topic-multi-leg",
            request.model_dump(mode="json", exclude_none=True),
        )
        return EnterMultiTopicMultiLegResponse.model_validate(data)

    async def exit_consolidated(
        self,
        topic_id: int,
        option_id: int,
        shares: float | None = None,
        *,
        dry_run: bool | None = None,
    ) -> dict[str, Any] | DryRunTradeResult:
        """``POST /api/v1/nmarket/exit-consolidated`` (requires API key).
        """
        if self._effective_dry_run(dry_run):
            contracts = shares if shares else await self._current_position_shares(
                topic_id, option_id
            )
            estimate = await self.estimate_trade(
                topic_id, TradeType.SELL, [TradeLeg(option_id=option_id, contracts=contracts)]
            )
            return DryRunTradeResult(trade_type=TradeType.SELL, estimates=[estimate])

        request = ExitSingleRequest(topic_id=topic_id, option_id=option_id, shares=shares)
        return await self._post_mutating(  # type: ignore[no-any-return]
            "/api/v1/nmarket/exit-consolidated", request.model_dump(mode="json", exclude_none=True)
        )

    async def exit_consolidated_multi(
        self, topic_id: int, legs: list[ExitLegReq], *, dry_run: bool | None = None
    ) -> dict[str, Any] | DryRunTradeResult:
        """``POST /api/v1/nmarket/exit-consolidated-multi`` (requires API key).
        """
        if self._effective_dry_run(dry_run):
            trade_legs = [
                TradeLeg(option_id=leg.option_id, contracts=leg.contracts) for leg in legs
            ]
            estimate = await self.estimate_trade(topic_id, TradeType.SELL, trade_legs)
            return DryRunTradeResult(trade_type=TradeType.SELL, estimates=[estimate])

        request = ExitMultipleLegsRequest(topic_id=topic_id, legs=legs)
        return await self._post_mutating(  # type: ignore[no-any-return]
            "/api/v1/nmarket/exit-consolidated-multi",
            request.model_dump(mode="json", exclude_none=True),
        )

    async def exit_multi_topic_multi_leg(
        self, topics: list[ExitMultiTopicLegGroup], *, dry_run: bool | None = None
    ) -> ExitMultiTopicMultiLegResponse | DryRunTradeResult:
        """``POST /api/v1/nmarket/exit-multi-topic-multi-leg`` (requires API key).
        """
        if self._effective_dry_run(dry_run):
            estimates = []
            for group in topics:
                trade_legs = [
                    TradeLeg(option_id=leg.option_id, contracts=leg.contracts)
                    for leg in group.legs
                ]
                estimates.append(
                    await self.estimate_trade(group.topic_id, TradeType.SELL, trade_legs)
                )
            return DryRunTradeResult(trade_type=TradeType.SELL, estimates=estimates)

        request = ExitMultiTopicMultiLegRequest(topics=topics)
        data = await self._post_mutating(
            "/api/v1/nmarket/exit-multi-topic-multi-leg",
            request.model_dump(mode="json", exclude_none=True),
        )
        return ExitMultiTopicMultiLegResponse.model_validate(data)

    async def exit_batch(
        self, batch_id: str, *, dry_run: bool | None = None
    ) -> ExitBatchResponse | DryRunTradeResult:
        """``POST /api/v1/nmarket/exit-batch`` (requires API key).
        """
        if self._effective_dry_run(dry_run):
            legs_by_topic: dict[int, list[TradeLeg]] = {}
            portfolio = await self.portfolio_active()
            for item in portfolio.message or []:
                if (
                    item.batch_id == batch_id
                    and item.topic_id is not None
                    and item.option_id is not None
                    and item.shares
                ):
                    legs_by_topic.setdefault(item.topic_id, []).append(
                        TradeLeg(option_id=item.option_id, contracts=item.shares)
                    )
            estimates = [
                await self.estimate_trade(topic_id, TradeType.SELL, legs)
                for topic_id, legs in legs_by_topic.items()
            ]
            return DryRunTradeResult(trade_type=TradeType.SELL, estimates=estimates)

        request = ExitBatchRequest(batch_id=batch_id)
        data = await self._post_mutating(
            "/api/v1/nmarket/exit-batch", request.model_dump(mode="json", exclude_none=True)
        )
        return ExitBatchResponse.model_validate(data)

    # dry-run helper

    def _effective_dry_run(self, override: bool | None) -> bool:
        return self.dry_run if override is None else override

    async def _current_position_shares(self, topic_id: int, option_id: int) -> float:
        """Look up the current share count for a position — used to price a
        dry-run "exit full position" call
        """
        portfolio = await self.portfolio_active()
        for item in portfolio.message or []:
            if item.topic_id == topic_id and item.option_id == option_id and item.shares:
                return item.shares
        raise GlimpseError(
            f"No active position found for topic_id={topic_id}, option_id={option_id} — "
            "cannot simulate a full-position exit without knowing the current share count."
        )
