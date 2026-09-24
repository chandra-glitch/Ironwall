import json

import pytest

from ironwall.liquidity_ladder import analyze_liquidity_ladder


def test_liquidity_ladder_reconciles_cash_flows_and_buffer():
    result = analyze_liquidity_ladder(
        {10: -40, 1: -60, 5: 25},
        initial_liquidity=100,
    )

    assert result.bucket_count == 3
    assert result.total_inflows == 25
    assert result.total_outflows == 100
    assert result.net_cash_flow == -75
    assert result.ending_liquidity == 25
    assert result.minimum_liquidity == 25
    assert result.minimum_liquidity_day == 10
    assert result.maximum_shortfall == 0
    assert result.first_shortfall_day is None
    assert result.shortfall_bucket_count == 0
    assert result.survives_horizon is True
    assert [bucket.day for bucket in result.buckets] == [1, 5, 10]
    assert [bucket.projected_liquidity for bucket in result.buckets] == [40, 65, 25]


def test_shortfall_and_later_recovery_are_reported():
    result = analyze_liquidity_ladder(
        {1: -120, 2: 50, 3: -20},
        initial_liquidity=100,
    )

    assert result.first_shortfall_day == 1
    assert result.minimum_liquidity_day == 1
    assert result.minimum_liquidity == -20
    assert result.maximum_shortfall == 20
    assert result.shortfall_bucket_count == 1
    assert result.ending_liquidity == 10
    assert result.survives_horizon is False
    assert [bucket.is_shortfall for bucket in result.buckets] == [True, False, False]
    assert [bucket.liquidity_shortfall for bucket in result.buckets] == [20, 0, 0]


def test_zero_balance_is_not_a_shortfall():
    result = analyze_liquidity_ladder({1: -100, 2: 0}, initial_liquidity=100)

    assert result.minimum_liquidity == 0
    assert result.minimum_liquidity_day == 1
    assert result.maximum_shortfall == 0
    assert result.first_shortfall_day is None
    assert result.survives_horizon is True


def test_opening_balance_can_be_the_minimum():
    result = analyze_liquidity_ladder({1: 10, 2: 20}, initial_liquidity=5)

    assert result.minimum_liquidity == 5
    assert result.minimum_liquidity_day == 0
    assert result.ending_liquidity == 35


def test_result_is_strict_json_ready():
    payload = analyze_liquidity_ladder({2: 5, 1: -15}, 10).to_dict()

    encoded = json.dumps(payload, allow_nan=False, sort_keys=True)

    assert payload["first_shortfall_day"] == 1
    assert payload["buckets"][0]["cumulative_net_cash_flow"] == -15
    assert '"survives_horizon": false' in encoded


@pytest.mark.parametrize("net_cash_flows", [None, [], {}, 1.0])
def test_cash_flows_must_be_a_non_empty_mapping(net_cash_flows):
    with pytest.raises(ValueError, match="net_cash_flows must be a non-empty mapping"):
        analyze_liquidity_ladder(net_cash_flows, 100)


@pytest.mark.parametrize("day", [0, -1, 1.5, "1", True])
def test_bucket_days_must_be_positive_integers(day):
    with pytest.raises(ValueError, match="bucket days must be positive integers"):
        analyze_liquidity_ladder({day: 10}, 100)


@pytest.mark.parametrize(
    "cash_flow",
    [float("nan"), float("inf"), -float("inf"), "invalid", True, 10**1000],
)
def test_invalid_cash_flows_are_rejected(cash_flow):
    with pytest.raises(ValueError, match="cash flow for day 1"):
        analyze_liquidity_ladder({1: cash_flow}, 100)


@pytest.mark.parametrize(
    "initial_liquidity",
    [-1, float("nan"), float("inf"), "invalid", True, 10**1000],
)
def test_invalid_initial_liquidity_is_rejected(initial_liquidity):
    with pytest.raises(ValueError, match="initial_liquidity"):
        analyze_liquidity_ladder({1: 10}, initial_liquidity)


def test_total_cash_flow_overflow_is_rejected():
    with pytest.raises(ValueError, match="total inflows exceeds"):
        analyze_liquidity_ladder({1: 1e308, 2: 1e308}, 0)


def test_projected_liquidity_overflow_is_rejected():
    with pytest.raises(ValueError, match="projected liquidity on day 1 exceeds"):
        analyze_liquidity_ladder({1: 1e308}, 1e308)
