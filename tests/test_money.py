from glimpse_markets.money import MILLISATS_PER_SAT, millisats_to_sats, sats_to_millisats


def test_millisats_to_sats() -> None:
    assert millisats_to_sats(1000) == 1.0
    assert millisats_to_sats(500) == 0.5
    assert millisats_to_sats(0) == 0.0


def test_sats_to_millisats() -> None:
    assert sats_to_millisats(1.0) == 1000
    assert sats_to_millisats(0.5) == 500
    assert sats_to_millisats(0) == 0


def test_round_trip() -> None:
    assert sats_to_millisats(millisats_to_sats(4200)) == 4200


def test_millisats_per_sat_constant() -> None:
    assert MILLISATS_PER_SAT == 1000
