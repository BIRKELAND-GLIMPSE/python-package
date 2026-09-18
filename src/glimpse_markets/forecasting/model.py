"""A thin wrapper around TimesFM 2.5 for point + quantile forecasting.

Requires the optional ``forecasting`` extra: ``pip install
glimpse-markets[forecasting]``. This module itself imports fine without
it — only *instantiating* ``TimesFMForecaster`` requires ``timesfm``/
``torch`` to actually be installed, so the rest of
``glimpse_markets.forecasting`` (``recorder.py``, ``signal.py``) stays
usable without pulling in this.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

DEFAULT_CHECKPOINT = "google/timesfm-2.5-200m-pytorch"
"""Apache-2.0 licensed. Not to be swapped with a TimesFM 3.0 checkpoint here for
production/commercial use."""


@dataclass
class ForecastResult:
    """One series' forecast: a point estimate and a full decile band per
    horizon step."""

    point: list[float]
    """Point (mean) forecast, length == horizon."""
    raw_quantiles: list[list[float]]
    """Shape (horizon, 10) exactly as TimesFM returns it, index 0 per
    step is the mean (same as ``point``), indices 1-9 are deciles 0.1..0.9.
    """

    def deciles_at(self, step: int) -> list[float]:
        """The 9 decile values (0.1..0.9) at horizon step ``step``, ready
        to pass straight to ``signal.probability_between`` /
        ``signal.bucket_probabilities``."""
        return self.raw_quantiles[step][1:]


class TimesFMForecaster:
    """Wraps ``timesfm.TimesFM_2p5_200M_torch`` for point + quantile
    forecasting.
    """

    def __init__(
        self,
        checkpoint: str = DEFAULT_CHECKPOINT,
        max_context: int = 1024,
        max_horizon: int = 256,
        torch_compile: bool = True,
    ) -> None:
        try:
            import timesfm  # noqa: PLC0415 -- deliberately lazy, see module docstring
        except ImportError as exc:
            raise ImportError(
                "TimesFMForecaster needs the 'timesfm' package. Install it with: "
                "pip install glimpse-markets[forecasting]"
            ) from exc

        self._model = timesfm.TimesFM_2p5_200M_torch.from_pretrained(
            checkpoint, torch_compile=torch_compile
        )
        self._model.compile(
            timesfm.ForecastConfig(
                max_context=max_context,
                max_horizon=max_horizon,
                normalize_inputs=True,
                use_continuous_quantile_head=True,
                force_flip_invariance=True,
                infer_is_positive=True,
                fix_quantile_crossing=True,
            )
        )
        self.checkpoint = checkpoint
        self.max_context = max_context
        self.max_horizon = max_horizon

    def forecast(self, series: Sequence[float], horizon: int) -> ForecastResult:
        """Forecast one series ``horizon`` steps ahead."""
        return self.forecast_batch([series], horizon)[0]

    def forecast_batch(
        self, series_list: Sequence[Sequence[float]], horizon: int
    ) -> list[ForecastResult]:
        """Forecast many series in one batched call — much cheaper per
        series than calling ``forecast()`` in a loop."""
        import numpy as np  # noqa: PLC0415 -- deliberately lazy, see module docstring

        inputs = [np.asarray(series, dtype=np.float32) for series in series_list]
        points, quantiles = self._model.forecast(horizon=horizon, inputs=inputs)
        return [
            ForecastResult(point=points[i].tolist(), raw_quantiles=quantiles[i].tolist())
            for i in range(len(inputs))
        ]
