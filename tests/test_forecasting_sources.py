import sys

import pytest

from glimpse_markets.forecasting.sources import fetch_yfinance_history


def test_fetch_yfinance_history_raises_clean_error_without_yfinance_installed() -> None:
    if "yfinance" in sys.modules:
        pytest.skip("yfinance is installed in this environment; this test targets its absence")
    with pytest.raises(ImportError, match=r"pip install glimpse-markets\[yfinance\]"):
        fetch_yfinance_history("BTC-USD")
