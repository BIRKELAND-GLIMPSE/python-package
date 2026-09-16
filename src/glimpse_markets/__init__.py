"""Official Python client for the Glimpse Nmarket prediction-market API."""

from glimpse_markets.async_client import AsyncClient
from glimpse_markets.client import Client
from glimpse_markets.enums import Prediction, QuoteMode, TradeType
from glimpse_markets.exceptions import (
    GlimpseAmbiguousTradeStateError,
    GlimpseAPIError,
    GlimpseAuthenticationError,
    GlimpseError,
    GlimpseForbiddenError,
    GlimpseNotFoundError,
    GlimpseRateLimitError,
    GlimpseServerError,
    GlimpseTradingNotEligibleError,
    GlimpseValidationError,
)
from glimpse_markets.models import (
    DryRunTradeResult,
    EnterMultiTopicLegGroup,
    ExitLegReq,
    ExitMultiTopicLegGroup,
    MarketUpdate,
    TradeLeg,
)
from glimpse_markets.money import Millisats, PriceUnits, millisats_to_sats, sats_to_millisats
from glimpse_markets.strategy import PositionTracker, Strategy, StrategyRunner
from glimpse_markets.streaming import MarketStream

__version__ = "0.1.0"

__all__ = [
    "Client",
    "AsyncClient",
    "MarketStream",
    "MarketUpdate",
    "Strategy",
    "StrategyRunner",
    "PositionTracker",
    "QuoteMode",
    "TradeType",
    "Prediction",
    "TradeLeg",
    "ExitLegReq",
    "EnterMultiTopicLegGroup",
    "ExitMultiTopicLegGroup",
    "DryRunTradeResult",
    "GlimpseError",
    "GlimpseAPIError",
    "GlimpseAuthenticationError",
    "GlimpseForbiddenError",
    "GlimpseTradingNotEligibleError",
    "GlimpseNotFoundError",
    "GlimpseValidationError",
    "GlimpseRateLimitError",
    "GlimpseServerError",
    "GlimpseAmbiguousTradeStateError",
    "Millisats",
    "PriceUnits",
    "millisats_to_sats",
    "sats_to_millisats",
    "__version__",
]
