import json
from unittest.mock import patch

from glimpse_markets.forecasting.recorder import MarketRecorder
from glimpse_markets.models import MarketUpdate


def _quote_update(
    topic_id: int = 6674, option_id: int = 500, yes_price: float = 55.0
) -> MarketUpdate:
    return MarketUpdate.model_validate(
        {
            "type": "market_update",
            "topic_id": topic_id,
            "data": {
                "topic_id": topic_id,
                "quotes": [{"option_id": option_id, "name": "Yes", "yes_price": yes_price}],
            },
        }
    )


def _binary_update(topic_id: int = 6674, option_id: int = 500, price: float = 62.1) -> MarketUpdate:
    return MarketUpdate.model_validate(
        {
            "type": "market_update",
            "topic_id": topic_id,
            "data": {
                "topic_id": topic_id,
                "binary_quotes": [{"option_id": option_id, "name": "Yes", "price": price}],
            },
        }
    )


def test_record_quotes_populates_series() -> None:
    recorder = MarketRecorder()
    recorder.record(_quote_update(yes_price=55.0))

    assert recorder.prices_for(6674, 500) == [55.0]


def test_record_binary_quotes_populates_series() -> None:
    recorder = MarketRecorder()
    recorder.record(_binary_update(price=62.1))

    assert recorder.prices_for(6674, 500) == [62.1]


def test_record_appends_across_multiple_updates() -> None:
    recorder = MarketRecorder()
    recorder.record(_quote_update(yes_price=10.0))
    recorder.record(_quote_update(yes_price=20.0))
    recorder.record(_quote_update(yes_price=30.0))

    assert recorder.prices_for(6674, 500) == [10.0, 20.0, 30.0]


def test_record_separates_different_options() -> None:
    recorder = MarketRecorder()
    recorder.record(_quote_update(option_id=500, yes_price=10.0))
    recorder.record(_quote_update(option_id=501, yes_price=20.0))

    assert recorder.prices_for(6674, 500) == [10.0]
    assert recorder.prices_for(6674, 501) == [20.0]


def test_record_ignores_update_with_no_topic_id() -> None:
    recorder = MarketRecorder()
    update = MarketUpdate.model_validate({"type": "market_update", "data": {"quotes": []}})
    recorder.record(update)  # should not raise
    assert recorder.prices_for(1, 1) == []


def test_record_ignores_update_with_no_data() -> None:
    recorder = MarketRecorder()
    update = MarketUpdate.model_validate({"type": "market_update", "topic_id": 6674})
    recorder.record(update)  # should not raise


def test_record_ignores_outcome_with_no_price() -> None:
    recorder = MarketRecorder()
    update = MarketUpdate.model_validate(
        {
            "type": "market_update",
            "topic_id": 6674,
            "data": {"topic_id": 6674, "quotes": [{"option_id": 500, "name": "Yes"}]},
        }
    )
    recorder.record(update)
    assert recorder.prices_for(6674, 500) == []


def test_prices_for_unknown_option_is_empty() -> None:
    recorder = MarketRecorder()
    assert recorder.prices_for(1, 1) == []
    assert recorder.series_for(1, 1) == []


def test_ring_buffer_drops_oldest_points_beyond_max() -> None:
    recorder = MarketRecorder(max_points_per_series=3)
    for price in [1.0, 2.0, 3.0, 4.0, 5.0]:
        recorder.record(_quote_update(yes_price=price))

    assert recorder.prices_for(6674, 500) == [3.0, 4.0, 5.0]



def test_resampled_prices_for_empty_series() -> None:
    recorder = MarketRecorder()
    assert recorder.resampled_prices_for(1, 1) == []


def test_resampled_prices_for_forward_fills_gaps() -> None:
    recorder = MarketRecorder()
    fake_now = [0]
    with patch("glimpse_markets.forecasting.recorder.time.time", side_effect=lambda: fake_now[0]):
        fake_now[0] = 0
        recorder.record(_quote_update(yes_price=10.0))
        fake_now[0] = 30  # same 60s bucket as t=0
        recorder.record(_quote_update(yes_price=15.0))
        fake_now[0] = 125  # bucket index 2 (skips bucket 1 entirely)
        recorder.record(_quote_update(yes_price=20.0))

    resampled = recorder.resampled_prices_for(6674, 500, interval_seconds=60)
    # bucket 0: last price in [0,60) -> 15.0 (overwrites 10.0)
    # bucket 1: no trades -> forward-filled from bucket 0 -> 15.0
    # bucket 2: last price -> 20.0
    assert resampled == [15.0, 15.0, 20.0]


def test_resampled_prices_for_single_point() -> None:
    recorder = MarketRecorder()
    recorder.record(_quote_update(yes_price=42.0))
    assert recorder.resampled_prices_for(6674, 500, interval_seconds=60) == [42.0]


def test_record_with_persist_path_appends_ndjson(tmp_path) -> None:
    path = tmp_path / "history.ndjson"
    recorder = MarketRecorder(persist_path=path)
    recorder.record(_quote_update(yes_price=10.0))
    recorder.record(_quote_update(yes_price=20.0))

    lines = path.read_text().strip().splitlines()
    assert len(lines) == 2
    row = json.loads(lines[0])
    assert row["topic_id"] == 6674
    assert row["option_id"] == 500
    assert row["price"] == 10.0


def test_load_rehydrates_series_from_ndjson_file(tmp_path) -> None:
    path = tmp_path / "history.ndjson"
    path.write_text(
        "\n".join(
            [
                json.dumps({"ts": 1, "topic_id": 6674, "option_id": 500, "price": 10.0}),
                "",  # a genuine blank line mid-file should be skipped, not raise
                json.dumps({"ts": 2, "topic_id": 6674, "option_id": 500, "price": 20.0}),
            ]
        )
    )

    recorder = MarketRecorder()
    recorder.load(path)

    assert recorder.prices_for(6674, 500) == [10.0, 20.0]


def test_load_appends_to_existing_in_memory_history(tmp_path) -> None:
    path = tmp_path / "history.ndjson"
    path.write_text(json.dumps({"ts": 5, "topic_id": 6674, "option_id": 500, "price": 99.0}))

    recorder = MarketRecorder()
    recorder.record(_quote_update(yes_price=1.0))
    recorder.load(path)

    assert recorder.prices_for(6674, 500) == [1.0, 99.0]
