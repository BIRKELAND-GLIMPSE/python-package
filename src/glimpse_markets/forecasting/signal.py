"""Model-agnostic probability/edge plumbing for Glimpse's bucketed markets.
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass

from glimpse_markets.models import QuoteOutcome

DEFAULT_DECILES: tuple[float, ...] = (0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9)

_BUCKET_NAME_RE = re.compile(r"^\s*(-?\d+(?:\.\d+)?)\s*-\s*(-?\d+(?:\.\d+)?)\s*$")


def parse_bucket_name(name: str | None) -> tuple[float | None, float | None]:
    if not name:
        return (None, None)
    match = _BUCKET_NAME_RE.match(name)
    if not match:
        return (None, None)
    lo, hi = float(match.group(1)), float(match.group(2))
    return (lo, hi) if lo <= hi else (hi, lo)


def _interp(x: float, xs: Sequence[float], ys: Sequence[float]) -> float:
    """Linear interpolation; clamps to the endpoint y-value outside
    ``[xs[0], xs[-1]]``. ``xs`` must be sorted ascending.

    A same-``x`` duplicate pair (``xs[i-1] == xs[i]``) can't actually reach
    the division below: the ``x <= xs[0]`` guard above, combined with the
    loop matching the *first* ``i`` with ``x <= xs[i]``
    """
    if x <= xs[0]:
        return ys[0]
    if x >= xs[-1]:
        return ys[-1]
    for i in range(1, len(xs)):
        if x <= xs[i]:
            x0, x1 = xs[i - 1], xs[i]
            y0, y1 = ys[i - 1], ys[i]
            return y0 + (y1 - y0) * (x - x0) / (x1 - x0)
    return ys[-1]  # unreachable given the bounds checks above


def probability_between(
    quantile_values: Sequence[float],
    lo: float | None,
    hi: float | None,
    deciles: Sequence[float] = DEFAULT_DECILES,
) -> float:
    """``P(lo <= X <= hi)`` implied by a decile forecast.
    """
    if len(quantile_values) != len(deciles):
        raise ValueError("quantile_values and deciles must be the same length")

    def cdf(x: float) -> float:
        if x <= quantile_values[0]:
            x0, x1 = quantile_values[0], quantile_values[1]
            y0, y1 = deciles[0], deciles[1]
            slope = (y1 - y0) / (x1 - x0) if x1 != x0 else 0.0
            return max(0.0, y0 + slope * (x - x0))
        if x >= quantile_values[-1]:
            x0, x1 = quantile_values[-2], quantile_values[-1]
            y0, y1 = deciles[-2], deciles[-1]
            slope = (y1 - y0) / (x1 - x0) if x1 != x0 else 0.0
            return min(1.0, y1 + slope * (x - x1))
        return _interp(x, quantile_values, deciles)

    upper = cdf(hi) if hi is not None else 1.0
    lower = cdf(lo) if lo is not None else 0.0
    return max(0.0, min(1.0, upper - lower))


def edge(model_probability: float, market_price: float) -> float:
    """``model_probability`` (0-1) minus the market-implied probability
    """
    return model_probability - (market_price / 100.0)


@dataclass
class BucketSignal:
    """One option's model-vs-market comparison from ``bucket_probabilities``."""

    option_id: int
    name: str | None
    lo: float | None
    hi: float | None
    market_price: float
    model_probability: float
    edge: float


def bucket_probabilities(
    outcomes: Sequence[QuoteOutcome],
    quantile_values: Sequence[float],
    deciles: Sequence[float] = DEFAULT_DECILES,
) -> list[BucketSignal]:
    """Model-vs-market comparison for every bucket-shaped option in
    ``outcomes`` — anything whose name doesn't parse as ``"LO-HI"`` is
    skipped rather than guessed at.
    """
    signals = []
    for outcome in outcomes:
        if outcome.option_id is None or outcome.yes_price is None:
            continue
        lo, hi = parse_bucket_name(outcome.name)
        if lo is None and hi is None:
            continue
        model_probability = probability_between(quantile_values, lo, hi, deciles)
        signals.append(
            BucketSignal(
                option_id=outcome.option_id,
                name=outcome.name,
                lo=lo,
                hi=hi,
                market_price=outcome.yes_price,
                model_probability=model_probability,
                edge=edge(model_probability, outcome.yes_price),
            )
        )
    return signals
