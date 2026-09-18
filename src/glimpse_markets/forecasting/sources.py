"""Optional external asset-price data sources.

Glimpse has no historical data of its own (we will be patching it in real soon), and the
rest of this package deliberately doesn't bundle a specific data vendor —
so it never makes that call for you. This module is the one deliberate
exception: a thin, opt-in adapter for Yahoo Finance via ``yfinance``, for
quickly getting real asset price history (BTC, ETH, gold, ...) to forecast
against Glimpse's corresponding markets while you're between "no data
source yet" and having your own.

Requires the ``yfinance`` extra: ``pip install glimpse-markets[yfinance]``.
"""

from __future__ import annotations


def fetch_yfinance_history(
    ticker: str,
    period: str = "60d",
    interval: str = "1h",
) -> list[float]:
    """Closing prices for ``ticker`` from Yahoo Finance, oldest first, 
    ready to hand straight to ``TimesFMForecaster.forecast()`` or anywhere
    else in this package that expects a plain price series.

    - Bitcoin  -> ``"BTC-USD"``
    - Ethereum -> ``"ETH-USD"``
    - PAX Gold -> ``"PAXG-USD"``

    ``interval`` values below ``"1d"`` (e.g. ``"1h"``, ``"5m"``) are
    limited by Yahoo to roughly the last 60 days of history — use a
    coarser interval for anything longer-range.
    """
    try:
        import yfinance as yf  # noqa: PLC0415 -- deliberately lazy, see module docstring
    except ImportError as exc:
        raise ImportError(
            "fetch_yfinance_history needs the 'yfinance' package. Install it with: "
            "pip install glimpse-markets[yfinance]"
        ) from exc

    data = yf.Ticker(ticker).history(period=period, interval=interval)
    return data["Close"].tolist()  # type: ignore[no-any-return]
