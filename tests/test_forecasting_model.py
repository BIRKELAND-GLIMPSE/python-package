import sys

import pytest

from glimpse_markets.forecasting.model import DEFAULT_CHECKPOINT, ForecastResult, TimesFMForecaster


def test_default_checkpoint_is_25_not_30() -> None:
    # TimesFM 3.0's pretrained weights are non-commercial/non-production only;
    # this package must default to the Apache-2.0 2.5 checkpoint.
    assert "2.5" in DEFAULT_CHECKPOINT
    assert "3.0" not in DEFAULT_CHECKPOINT


def test_forecast_result_deciles_at_strips_the_mean_column() -> None:
    # raw_quantiles[step] is 10-wide: index 0 is the mean, 1-9 are deciles.
    result = ForecastResult(
        point=[100.0],
        raw_quantiles=[[100.0, 80.0, 90.0, 95.0, 98.0, 100.0, 102.0, 105.0, 110.0, 120.0]],
    )
    assert result.deciles_at(0) == [80.0, 90.0, 95.0, 98.0, 100.0, 102.0, 105.0, 110.0, 120.0]


def test_timesfm_forecaster_raises_clean_error_without_timesfm_installed() -> None:
    if "timesfm" in sys.modules:
        pytest.skip("timesfm is installed in this environment; this test targets its absence")
    with pytest.raises(ImportError, match=r"pip install glimpse-markets\[forecasting\]"):
        TimesFMForecaster()
