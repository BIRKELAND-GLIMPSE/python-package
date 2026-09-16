"""Enums for values the server computes from a known, closed set.

Fields whose real-world value set is uncertain or API-version-dependent
(``topic_type``, ``category``, ``status``, ``trade_type`` on portfolio
items, ...) are deliberately typed as plain ``str`` on the response models
instead of an ``Enum``
"""

from __future__ import annotations

from enum import Enum


class QuoteMode(str, Enum):
    LIVE = "live"
    CLOSED = "closed"
    INACTIVE = "inactive"
    RESOLVED = "resolved"
