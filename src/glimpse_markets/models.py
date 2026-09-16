"""Response models, mirroring ``main_glimpse_service/docs/swagger.json``
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from glimpse_markets.enums import Prediction, TradeType
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


# trade requests
class TradeLeg(GlimpseModel):
    option_id: int
    contracts: float
    prediction: Prediction | None = None
    """Optional; omitting it makes the ledger infer from the outcome name."""


class ExitLegReq(GlimpseModel):
    option_id: int
    contracts: float


class EnterMultiTopicLegGroup(GlimpseModel):
    topic_id: int
    legs: list[TradeLeg] = Field(min_length=1)


class EnterMultiTopicMultiLegRequest(GlimpseModel):
    topics: list[EnterMultiTopicLegGroup] = Field(min_length=1)


class ExecuteTradeRequest(GlimpseModel):
    topic_id: int
    trade_type: TradeType
    legs: list[TradeLeg] = Field(min_length=1)


class ExitSingleRequest(GlimpseModel):
    topic_id: int
    option_id: int
    shares: float | None = None
    """0 or omitted = exit the full position."""


class ExitMultiTopicLegGroup(GlimpseModel):
    topic_id: int
    legs: list[ExitLegReq] = Field(min_length=1)


class ExitMultiTopicMultiLegRequest(GlimpseModel):
    topics: list[ExitMultiTopicLegGroup] = Field(min_length=1)


class ExitMultipleLegsRequest(GlimpseModel):
    topic_id: int
    legs: list[ExitLegReq] = Field(min_length=1)


class ExitBatchRequest(GlimpseModel):
    batch_id: str


# trade responses


class EstimateTradeLegsResponse(GlimpseModel):
    topic_id: int | None = None
    trade_type: str | None = None
    leg_count: int | None = None
    total_cost: float | None = None
    total_cost_millisats: Millisats | None = None
    commission_millisats: Millisats | None = None


class EnterMultiTopicTopicResult(GlimpseModel):
    topic_id: int | None = None
    trade_id: str | None = None
    total_cost_millisats: Millisats | None = None
    commission_millisats: Millisats | None = None
    error: str | None = None
    """Set on a per-topic failure even though the overall HTTP call was 200."""


class EnterMultiTopicMultiLegResponse(GlimpseModel):
    results: list[EnterMultiTopicTopicResult] | None = None
    topics_requested: int | None = None
    topics_entered: int | None = None
    topics_failed: int | None = None
    total_cost_millisats: Millisats | None = None
    total_commission_millisats: Millisats | None = None


class ExitBatchTopicResult(GlimpseModel):
    topic_id: int | None = None
    trade_id: str | None = None
    total_proceeds_millisats: Millisats | None = None
    commission_millisats: Millisats | None = None
    error: str | None = None
    """Set on a per-topic failure even though the overall HTTP call was 200."""


class ExitBatchResponse(GlimpseModel):
    batch_id: str | None = None
    results: list[ExitBatchTopicResult] | None = None
    topics_exited: int | None = None
    topics_failed: int | None = None
    total_proceeds_millisats: Millisats | None = None
    total_commission_millisats: Millisats | None = None


class ExitMultiTopicMultiLegResponse(GlimpseModel):
    results: list[ExitBatchTopicResult] | None = None
    topics_requested: int | None = None
    topics_exited: int | None = None
    topics_failed: int | None = None
    total_proceeds_millisats: Millisats | None = None
    total_commission_millisats: Millisats | None = None


# dry-run


class DryRunTradeResult(GlimpseModel):
    """Returned instead of a real trade response when ``Client(dry_run=True)``.
    """

    simulated: bool = True
    trade_type: TradeType
    estimates: list[EstimateTradeLegsResponse]


# streaming (/ws/nmarket-updates) 
class MarketUpdateQuote(GlimpseModel):
    option_id: int | None = None
    option_name: str | None = None
    yes_price: float | None = None
    no_price: float | None = None
    shares: float | None = None


class MarketUpdateBinaryQuote(GlimpseModel):
    option_id: int | None = None
    option_name: str | None = None
    price: float | None = None
    shares: float | None = None


class MarketUpdateData(GlimpseModel):
    topic_id: int | None = None
    topic_type: str | None = None
    batch_id: str | None = None
    alpha: float | None = None
    pot_size: float | None = None
    timestamp: int | None = None
    quotes: list[MarketUpdateQuote] | None = None
    binary_quotes: list[MarketUpdateBinaryQuote] | None = None



class MarketUpdate(GlimpseModel):
    """A single message from the ``/ws/nmarket-updates`` real-time feed.
    """

    type: str | None = None
    topic_id: int | None = None
    batch_id: str | None = None
    data: MarketUpdateData | None = None
