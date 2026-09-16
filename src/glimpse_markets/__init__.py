"""Official Python client for the Glimpse Nmarket prediction-market API."""

from glimpse_markets.client import Client
from glimpse_markets.enums import QuoteMode
from glimpse_markets.exceptions import (
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
from glimpse_markets.money import Millisats, PriceUnits, millisats_to_sats, sats_to_millisats

__version__ = "0.1.0"

__all__ = [
    "Client",
    "QuoteMode",
    "GlimpseError",
    "GlimpseAPIError",
    "GlimpseAuthenticationError",
    "GlimpseForbiddenError",
    "GlimpseTradingNotEligibleError",
    "GlimpseNotFoundError",
    "GlimpseValidationError",
    "GlimpseRateLimitError",
    "GlimpseServerError",
    "Millisats",
    "PriceUnits",
    "millisats_to_sats",
    "sats_to_millisats",
    "__version__",
]
