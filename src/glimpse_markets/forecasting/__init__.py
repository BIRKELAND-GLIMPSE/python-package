"""Forecasting tools for building signals on top of Glimpse's markets.

Glimpse's API has no historical/candle endpoint of its own as of now (we
will patch that in real soon), so any forecasting story here has to start
with data acquisition, not just a model wrapper:

- ``recorder.MarketRecorder`` builds a local price history from
  ``MarketStream`` — the SDK's own market prices, forecastable with zero
  external dependencies.
- ``model.TimesFMForecaster`` wraps Google's TimesFM 2.5 (Apache-2.0 —
  see its module docstring for why not 3.0) for point + quantile
  forecasting. Requires the optional ``forecasting`` extra:
  ``pip install glimpse-markets[forecasting]``.
- ``signal.py`` maps a decile forecast onto Glimpse's bucketed-option
  markets and compares it to the live LMSR price — model-agnostic and
  dependency-free, so it works with ``TimesFMForecaster``'s output or any
  other model's (e.g. your own forecast of the *underlying asset*, from
  whatever external price-data source you already use — this package
  doesn't pick a vendor for that)...
- ...except for ``sources.fetch_yfinance_history``, the one deliberate,
  clearly-labeled exception — an opt-in Yahoo Finance adapter for quickly
  getting real asset price history. **Read its module docstring before
  using it**: Yahoo's own terms restrict their finance data to personal
  use, which matters if you're building something commercial. Requires
  the separate ``yfinance`` extra: ``pip install glimpse-markets[yfinance]``.

Only ``model.py`` (``TimesFMForecaster``) and ``sources.py``
(``fetch_yfinance_history``) need their respective extras; ``recorder``
and ``signal`` are always available as part of the base package.
"""

from glimpse_markets.forecasting.model import DEFAULT_CHECKPOINT, ForecastResult, TimesFMForecaster
from glimpse_markets.forecasting.recorder import MarketRecorder
from glimpse_markets.forecasting.signal import (
    DEFAULT_DECILES,
    BucketSignal,
    bucket_probabilities,
    edge,
    parse_bucket_name,
    probability_between,
)
from glimpse_markets.forecasting.sources import fetch_yfinance_history

__all__ = [
    "MarketRecorder",
    "TimesFMForecaster",
    "ForecastResult",
    "DEFAULT_CHECKPOINT",
    "BucketSignal",
    "bucket_probabilities",
    "probability_between",
    "parse_bucket_name",
    "edge",
    "DEFAULT_DECILES",
    "fetch_yfinance_history",
]
