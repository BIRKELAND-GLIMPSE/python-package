"""Unit helpers for Glimpse's two distinct numeric scales.

The API mixes two unrelated scales that are easy to confuse:

- **millisats** (``*_millisats`` fields, wallet balance): real money.
  1 satoshi = 1000 millisatoshis (Bitcoin Lightning sub-unit).
- **price units** (``yes_price`` / ``no_price`` / ``odds`` from the quotes
  endpoint): a 0-100 LS-LMSR pricing scale. This is *not* millisats and is
  only converted to millisats (x1000) server-side at trade/settlement time.
"""

from __future__ import annotations

from typing import NewType

Millisats = NewType("Millisats", int)
"""An integer amount of millisatoshis — real money."""

PriceUnits = NewType("PriceUnits", float)
"""A 0-100 LS-LMSR quote price — not a currency amount."""

MILLISATS_PER_SAT = 1000


def millisats_to_sats(value: int) -> float:
    """Convert an integer millisats amount to fractional sats."""
    return value / MILLISATS_PER_SAT


def sats_to_millisats(value: float) -> int:
    """Convert a (possibly fractional) sats amount to integer millisats."""
    return round(value * MILLISATS_PER_SAT)
