import pytest

from glimpse_markets.forecasting.signal import (
    _interp,
    bucket_probabilities,
    edge,
    parse_bucket_name,
    probability_between,
)
from glimpse_markets.models import QuoteOutcome

DECILE_VALUES = [10.0, 20.0, 30.0, 40.0, 50.0, 60.0, 70.0, 80.0, 90.0]


def test_parse_bucket_name_basic() -> None:
    assert parse_bucket_name("64000-65000") == (64000.0, 65000.0)
    assert parse_bucket_name("0-1000") == (0.0, 1000.0)


def test_parse_bucket_name_whitespace() -> None:
    assert parse_bucket_name("  100 - 200  ") == (100.0, 200.0)


def test_parse_bucket_name_swaps_reversed_range() -> None:
    assert parse_bucket_name("100-50") == (50.0, 100.0)


def test_parse_bucket_name_negative_numbers() -> None:
    assert parse_bucket_name("-50--10") == (-50.0, -10.0)


def test_parse_bucket_name_none_input() -> None:
    assert parse_bucket_name(None) == (None, None)


def test_parse_bucket_name_empty_string() -> None:
    assert parse_bucket_name("") == (None, None)


def test_parse_bucket_name_non_numeric_format() -> None:
    assert parse_bucket_name("Yes") == (None, None)
    assert parse_bucket_name("above 100000") == (None, None)


def test_interp_clamps_below_range() -> None:
    assert _interp(-5.0, [0.0, 10.0], [1.0, 2.0]) == 1.0


def test_interp_clamps_above_range() -> None:
    assert _interp(15.0, [0.0, 10.0], [1.0, 2.0]) == 2.0


def test_interp_midpoint() -> None:
    assert _interp(5.0, [0.0, 10.0], [0.0, 100.0]) == pytest.approx(50.0)


def test_interp_multi_segment_picks_the_right_one() -> None:
    assert _interp(7.0, [0.0, 5.0, 10.0], [0.0, 50.0, 100.0]) == pytest.approx(70.0)



def test_probability_between_exact_decile_bounds() -> None:
    # 40 and 60 are exactly the 0.4 and 0.6 decile values.
    assert probability_between(DECILE_VALUES, 40.0, 60.0) == pytest.approx(0.2)


def test_probability_between_open_ended_covers_everything() -> None:
    assert probability_between(DECILE_VALUES, None, None) == pytest.approx(1.0)


def test_probability_between_open_lower_bound() -> None:
    # Only an upper bound -- P(X <= 60) should be the 0.6 decile exactly.
    assert probability_between(DECILE_VALUES, None, 60.0) == pytest.approx(0.6)


def test_probability_between_open_upper_bound() -> None:
    assert probability_between(DECILE_VALUES, 40.0, None) == pytest.approx(0.6)


def test_probability_between_extrapolates_below_range() -> None:
    # Slope from (10, 0.1) to (20, 0.2) is 0.01/unit; at x=5:
    # 0.1 + 0.01 * (5 - 10) = 0.05
    assert probability_between(DECILE_VALUES, None, 5.0) == pytest.approx(0.05)


def test_probability_between_extrapolates_above_range() -> None:
    # Slope from (80, 0.8) to (90, 0.9) is 0.01/unit; at x=95:
    # 0.9 + 0.01 * (95 - 90) = 0.95 -- so P(X > 95) = 1 - 0.95 = 0.05
    assert probability_between(DECILE_VALUES, 95.0, None) == pytest.approx(0.05)


def test_probability_between_far_below_range_clamps_toward_zero() -> None:
    # P(X <= -1000): a value far below anything observed -- should be ~0.
    assert probability_between(DECILE_VALUES, None, -1000.0) == pytest.approx(0.0)


def test_probability_between_far_above_range_clamps_toward_one() -> None:
    # P(X <= 1000): a value far above anything observed -- should be ~1.
    assert probability_between(DECILE_VALUES, None, 1000.0) == pytest.approx(1.0)


def test_probability_between_tail_beyond_range_clamps_toward_zero() -> None:
    # P(X >= 1000): asking for mass far beyond the observed range -- ~0.
    assert probability_between(DECILE_VALUES, 1000.0, None) == pytest.approx(0.0)


def test_probability_between_mismatched_lengths_raises() -> None:
    with pytest.raises(ValueError, match="same length"):
        probability_between([1.0, 2.0], 0.0, 1.0, deciles=[0.1, 0.2, 0.3])


def test_edge_positive_when_model_more_bullish_than_market() -> None:
    assert edge(0.6, 50.0) == pytest.approx(0.1)


def test_edge_zero_when_model_matches_market() -> None:
    assert edge(0.3, 30.0) == pytest.approx(0.0)


def test_edge_negative_when_model_less_bullish_than_market() -> None:
    assert edge(0.1, 90.0) == pytest.approx(-0.8)

def test_bucket_probabilities_computes_signal_per_bucket_option() -> None:
    outcomes = [
        QuoteOutcome(option_id=1, name="0-40", yes_price=30.0),
        QuoteOutcome(option_id=2, name="40-60", yes_price=25.0),
    ]

    signals = bucket_probabilities(outcomes, DECILE_VALUES)

    assert len(signals) == 2
    first = next(s for s in signals if s.option_id == 1)
    assert first.lo == 0.0
    assert first.hi == 40.0
    assert first.market_price == 30.0
    assert first.model_probability == pytest.approx(0.4)  # P(0<=X<=40)
    assert first.edge == pytest.approx(0.4 - 0.3)


def test_bucket_probabilities_skips_non_bucket_names() -> None:
    outcomes = [
        QuoteOutcome(option_id=1, name="Yes", yes_price=50.0),
        QuoteOutcome(option_id=2, name="40-60", yes_price=25.0),
    ]

    signals = bucket_probabilities(outcomes, DECILE_VALUES)

    assert len(signals) == 1
    assert signals[0].option_id == 2


def test_bucket_probabilities_skips_missing_price_or_id() -> None:
    outcomes = [
        QuoteOutcome(option_id=None, name="0-40", yes_price=30.0),
        QuoteOutcome(option_id=2, name="40-60", yes_price=None),
    ]

    signals = bucket_probabilities(outcomes, DECILE_VALUES)

    assert signals == []
