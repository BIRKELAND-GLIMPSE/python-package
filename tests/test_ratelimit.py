from unittest.mock import patch

from glimpse_markets.ratelimit import RateLimiter


def test_acquire_does_not_block_under_budget() -> None:
    limiter = RateLimiter(max_requests=3, window_seconds=60.0)
    with patch("time.sleep") as sleep_mock:
        for _ in range(3):
            limiter.acquire()
    sleep_mock.assert_not_called()
    assert len(limiter._timestamps) == 3


def test_acquire_blocks_once_budget_exhausted() -> None:
    limiter = RateLimiter(max_requests=2, window_seconds=10.0)
    fake_now = [1000.0]

    def fake_monotonic() -> float:
        return fake_now[0]

    def fake_sleep(seconds: float) -> None:
        fake_now[0] += seconds

    with (
        patch("time.monotonic", side_effect=fake_monotonic),
        patch("time.sleep", side_effect=fake_sleep) as sleep_mock,
    ):
        limiter.acquire()  # t=1000
        limiter.acquire()  # t=1000, budget now full
        limiter.acquire()  # must wait until t=1010 before the 3rd request

    sleep_mock.assert_called_once()
    (slept_for,) = sleep_mock.call_args.args
    assert slept_for == 10.0


def test_expired_timestamps_are_evicted() -> None:
    limiter = RateLimiter(max_requests=1, window_seconds=5.0)
    fake_now = [0.0]

    with patch("time.monotonic", side_effect=lambda: fake_now[0]):
        limiter.acquire()  # t=0, fills the single slot
        fake_now[0] = 10.0  # well past the 5s window
        with patch("time.sleep") as sleep_mock:
            limiter.acquire()  # should not block — old timestamp already expired
        sleep_mock.assert_not_called()
