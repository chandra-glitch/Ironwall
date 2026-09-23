import json

import pytest

from ironwall.position_exposure import analyze_position_exposure


def test_long_short_exposure_and_leverage_are_reported():
    result = analyze_position_exposure(
        {"LONG": 1_200_000, "SHORT": -400_000, "FLAT": 0},
        net_asset_value=1_000_000,
    )

    assert result.position_count == 3
    assert result.long_positions == 1
    assert result.short_positions == 1
    assert result.flat_positions == 1
    assert result.long_exposure == 1_200_000
    assert result.short_exposure == 400_000
    assert result.gross_exposure == 1_600_000
    assert result.net_exposure == 800_000
    assert result.long_leverage == pytest.approx(1.2)
    assert result.short_leverage == pytest.approx(0.4)
    assert result.gross_leverage == pytest.approx(1.6)
    assert result.net_leverage == pytest.approx(0.8)


def test_market_neutral_portfolio_retains_gross_exposure():
    result = analyze_position_exposure(
        {"LONG": 500_000, "SHORT": -500_000},
        net_asset_value=1_000_000,
    )

    assert result.net_exposure == 0
    assert result.net_leverage == 0
    assert result.gross_exposure == 1_000_000
    assert result.gross_leverage == 1


def test_positions_are_sorted_and_include_signed_nav_fractions():
    result = analyze_position_exposure(
        {"Z_SHORT": -25, "A_LONG": 100, "M_FLAT": -0.0},
        net_asset_value=50,
    )

    assert [position.asset for position in result.positions] == ["A_LONG", "M_FLAT", "Z_SHORT"]
    assert [position.side for position in result.positions] == ["long", "flat", "short"]
    assert result.positions[0].nav_fraction == 2
    assert result.positions[0].absolute_nav_fraction == 2
    assert result.positions[1].notional == 0
    assert result.positions[2].nav_fraction == -0.5
    assert result.positions[2].absolute_nav_fraction == 0.5


def test_result_is_strict_json_ready():
    payload = analyze_position_exposure(
        {"LONG": 120, "SHORT": -20},
        net_asset_value=100,
    ).to_dict()

    encoded = json.dumps(payload, allow_nan=False, sort_keys=True)

    assert payload["gross_leverage"] == pytest.approx(1.4)
    assert payload["net_leverage"] == pytest.approx(1.0)
    assert len(payload["positions"]) == 2
    assert '"absolute_nav_fraction"' in encoded


@pytest.mark.parametrize("positions", [None, [], {}, 1.0])
def test_positions_must_be_a_non_empty_mapping(positions):
    with pytest.raises(ValueError, match="positions must be a non-empty mapping"):
        analyze_position_exposure(positions, 100)


@pytest.mark.parametrize("asset", ["", " JPM", "JPM ", 42])
def test_invalid_asset_names_are_rejected(asset):
    with pytest.raises(ValueError, match="asset names"):
        analyze_position_exposure({asset: 10}, 100)


@pytest.mark.parametrize(
    "notional",
    [float("nan"), float("inf"), -float("inf"), "invalid", True, 10**1000],
)
def test_invalid_position_notionals_are_rejected(notional):
    with pytest.raises(ValueError, match="notional"):
        analyze_position_exposure({"JPM": notional}, 100)


@pytest.mark.parametrize(
    "net_asset_value",
    [0, -1, float("nan"), float("inf"), "invalid", True, 10**1000],
)
def test_invalid_net_asset_value_is_rejected(net_asset_value):
    with pytest.raises(ValueError, match="net_asset_value"):
        analyze_position_exposure({"JPM": 10}, net_asset_value)


def test_aggregate_exposure_overflow_is_rejected():
    with pytest.raises(ValueError, match="long exposure exceeds"):
        analyze_position_exposure({"A": 1e308, "B": 1e308}, 1e308)


def test_leverage_overflow_is_rejected():
    with pytest.raises(ValueError, match="NAV fraction.*numeric range"):
        analyze_position_exposure({"JPM": 1.0}, 5e-324)
