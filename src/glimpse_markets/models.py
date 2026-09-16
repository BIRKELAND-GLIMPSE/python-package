"""Response models, mirroring ``main_glimpse_service/docs/swagger.json``
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from glimpse_markets.money import Millisats


class GlimpseModel(BaseModel):
    model_config = ConfigDict(extra="ignore", populate_by_name=True)


# shared nested objects 


class QuoteOutcome(GlimpseModel):
    option_id: int | None = None
    name: str | None = None
    image_url: str | None = None
    yes_price: float | None = None
    """0-100 LS-LMSR price scale — not millisats. See money.PriceUnits."""
    no_price: float | None = None
    yes_price_millisats: Millisats | None = None
    no_price_millisats: Millisats | None = None
    odds: float | None = None
    shares: float | None = None
    subsidised_shares: float | None = None


class BatchOutcomeSlim(GlimpseModel):
    option_id: int | None = None
    name: str | None = None
    shares: float | None = None


# markets / batches


class BatchMarketItem(GlimpseModel):
    topic_id: int | None = None
    batch_id: str | None = None
    title: str | None = None
    description: str | None = None
    category: str | None = None
    topic_type: str | None = None
    topic_image_url: str | None = None
    quote_mode: str | None = None
    """Compare against enums.QuoteMode, e.g. ``market.quote_mode == QuoteMode.LIVE``."""
    is_active: bool | None = None
    is_resolved: bool | None = None
    resolved_option_id: int | None = None
    market_subsidised: bool | None = None
    subsidy_amount: int | None = None
    num_outcomes: int | None = None
    outcomes: list[QuoteOutcome] | None = None
    total_amount_in_market: float | None = None
    total_volume_millisats: Millisats | None = None
    volume_24h_millisats: Millisats | None = None
    date_created: int | None = None
    end_time_utc: int | None = None
    estimated_resolve_time: int | None = None


class BatchMarketItemV2(GlimpseModel):
    topic_id: int | None = None
    batch_id: str | None = None
    title: str | None = None
    description: str | None = None
    category: str | None = None
    topic_type: str | None = None
    topic_image_url: str | None = None
    quote_mode: str | None = None
    is_active: bool | None = None
    is_resolved: bool | None = None
    resolved_option_id: int | None = None
    market_subsidised: bool | None = None
    subsidy_amount: int | None = None
    num_outcomes: int | None = None
    outcomes: list[BatchOutcomeSlim] | None = None
    total_amount_in_market: float | None = None
    total_volume_millisats: Millisats | None = None
    volume_24h_millisats: Millisats | None = None
    date_created: int | None = None
    end_time_utc: int | None = None
    estimated_resolve_time: int | None = None


class BatchMarketsResponse(GlimpseModel):
    batch_id: str | None = None
    main_topic_title: str | None = None
    topic_count: int | None = None
    count: int | None = None
    start_time_utc: int | None = None
    end_time_utc: int | None = None
    cumulative_liquidity_millisats: Millisats | None = None
    cumulative_volume_millisats: Millisats | None = None
    markets: list[BatchMarketItem] | None = None


class BatchMarketsPageResponse(GlimpseModel):
    batch_id: str | None = None
    main_topic_title: str | None = None
    topic_count: int | None = None
    start_time_utc: int | None = None
    end_time_utc: int | None = None
    cumulative_liquidity_millisats: Millisats | None = None
    cumulative_volume_millisats: Millisats | None = None
    markets: list[BatchMarketItemV2] | None = None
    count: int | None = None
    """Rows in this page."""
    total: int | None = None
    """Total rows matching the filter, across all pages."""
    limit: int | None = None
    offset: int | None = None
    next_offset: int | None = None
    has_more: bool | None = None


class BatchStatsResponse(GlimpseModel):
    batch_id: str | None = None
    active_market_count: int | None = None
    liquidity_locked_millisats: Millisats | None = None
    total_volume_millisats: Millisats | None = None
    volume_24h_millisats: Millisats | None = None


class BatchSummaryItem(GlimpseModel):
    batch_id: str | None = None
    main_topic_title: str | None = None
    topic_count: int | None = None
    start_time_utc: int | None = None
    end_time_utc: int | None = None
    outcome_min_value: int | None = None
    outcome_max_value: int | None = None
    outcome_interval: int | None = None


class ListBatchesResponse(GlimpseModel):
    batches: list[BatchSummaryItem] | None = None
    count: int | None = None


class QuotesResponse(GlimpseModel):
    topic_id: int | None = None
    batch_id: str | None = None
    title: str | None = None
    description: str | None = None
    category: str | None = None
    topic_type: str | None = None
    topic_image_url: str | None = None
    quote_mode: str | None = None
    is_resolved: bool | None = None
    market_subsidised: bool | None = None
    liquidity_locked_millisats: Millisats | None = None
    total_amount_in_market: float | None = None
    total_volume_millisats: Millisats | None = None
    volume_24h_millisats: Millisats | None = None
    market_end_time_utc: int | None = None
    estimated_resolve_time: int | None = None
    outcomes: list[QuoteOutcome] | None = None


class MarketStatsResponse(GlimpseModel):
    topic_id: int | None = None
    liquidity_locked_millisats: Millisats | None = None
    total_volume_millisats: Millisats | None = None
    volume_24h_millisats: Millisats | None = None


class VolumeByOptionResponse(GlimpseModel):
    topic_id: int | None = None
    volume_by_option: dict[str, int] | None = None
    """Keyed by option_id as a string (JSON object keys are always strings)."""


# portfolio (requires API key)


class PortfolioItem(GlimpseModel):
    trade_id: str | None = None
    topic_id: int | None = None
    batch_id: str | None = None
    option_id: int | None = None
    option_name: str | None = None
    option_image_url: str | None = None
    topic_title: str | None = None
    topic_image_url: str | None = None
    topic_type: str | None = None
    trade_type: str | None = None
    prediction: str | None = None
    status: str | None = None
    shares: float | None = None
    current_price: int | None = None
    """Unit not confirmed by the spec — not wrapped in Millisats, verify before relying."""
    current_value: int | None = None
    """Unit not confirmed by the spec — not wrapped in Millisats, verify before relying."""
    purchase_value: int | None = None
    """Unit not confirmed by the spec — not wrapped in Millisats, verify before relying."""
    is_active: bool | None = None
    is_resolved: bool | None = None
    market_end_time: int | None = None
    last_trade_timestamp_int: int | None = None


class PortfolioListResponse(GlimpseModel):
    success: bool | None = None
    message: list[PortfolioItem] | None = None


class PaginatedPortfolioListResponse(GlimpseModel):
    success: bool | None = None
    message: list[PortfolioItem] | None = None
    total: int | None = None
    limit: int | None = None
    offset: int | None = None


class ConsolidatedPortfolioSummary(GlimpseModel):
    active_market_count: int | None = None
    ended_unresolved_market_count: int | None = None
    resolved_market_count: int | None = None
    total_current_value: int | None = None
    total_purchase_value: int | None = None
    total_pnl: int | None = None


class ConsolidatedPortfolioSummaryResponse(GlimpseModel):
    success: bool | None = None
    message: ConsolidatedPortfolioSummary | None = None
