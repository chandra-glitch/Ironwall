import json

import pytest

from ironwall.interest_rate_risk import analyze_fixed_income_sensitivity


def test_zero_coupon_bond_matches_closed_form_measures():
    result = analyze_fixed_income_sensitivity(
        {2: 100},
        annual_yield=0.05,
        rate_shock=0.01,
    )

    expected_value = 100 / 1.05**2
    expected_convexity = 2 * 3 / 1.05**2
    expected_shocked_value = 100 / 1.06**2
    expected_approximation_percentage = -(2 / 1.05) * 0.01 + (0.5 * expected_convexity * 0.01**2)

    assert result.present_value == pytest.approx(expected_value)
    assert result.macaulay_duration_years == pytest.approx(2)
    assert result.modified_duration_years == pytest.approx(2 / 1.05)
    assert result.convexity_years_squared == pytest.approx(expected_convexity)
    assert result.dv01 == pytest.approx(expected_value * (2 / 1.05) * 0.0001)
    assert result.shocked_present_value == pytest.approx(expected_shocked_value)
    assert result.exact_price_change == pytest.approx(expected_shocked_value - expected_value)
    assert result.duration_convexity_price_change_percentage == pytest.approx(
        expected_approximation_percentage
    )


def test_coupon_cash_flows_are_sorted_and_reconcile_to_value():
    result = analyze_fixed_income_sensitivity(
        {1.0: 102, 0.5: 2},
        annual_yield=0.04,
        compounds_per_year=2,
    )

    expected_values = [2 / 1.02, 102 / 1.02**2]

    assert [cash_flow.time_years for cash_flow in result.cash_flows] == [0.5, 1.0]
    assert [cash_flow.present_value for cash_flow in result.cash_flows] == pytest.approx(
        expected_values
    )
    assert result.present_value == pytest.approx(sum(expected_values))
    assert sum(cash_flow.price_weight for cash_flow in result.cash_flows) == pytest.approx(1)
    assert result.maturity_years == 1
    assert result.cash_flow_count == 2


def test_positive_and_negative_shocks_move_value_in_opposite_directions():
    cash_flows = {1: 5, 2: 5, 3: 105}

    higher_rates = analyze_fixed_income_sensitivity(cash_flows, 0.04, rate_shock=0.01)
    lower_rates = analyze_fixed_income_sensitivity(cash_flows, 0.04, rate_shock=-0.01)

    assert higher_rates.exact_price_change < 0
    assert higher_rates.exact_price_change_percentage < 0
    assert lower_rates.exact_price_change > 0
    assert lower_rates.exact_price_change_percentage > 0
    assert abs(higher_rates.duration_convexity_error) < 0.001
    assert abs(lower_rates.duration_convexity_error) < 0.001


def test_dv01_matches_a_central_one_basis_point_revaluation():
    cash_flows = {1: 4, 2: 4, 3: 4, 4: 104}
    result = analyze_fixed_income_sensitivity(cash_flows, 0.045)
    value_down_one_bp = analyze_fixed_income_sensitivity(
        cash_flows,
        0.045,
        rate_shock=-0.0001,
    ).shocked_present_value
    value_up_one_bp = analyze_fixed_income_sensitivity(
        cash_flows,
        0.045,
        rate_shock=0.0001,
    ).shocked_present_value

    central_dv01 = (value_down_one_bp - value_up_one_bp) / 2

    assert result.dv01 == pytest.approx(central_dv01, rel=1e-7)


def test_zero_shock_has_zero_change_and_error():
    result = analyze_fixed_income_sensitivity({1: 105}, 0.05, rate_shock=0)

    assert result.shocked_present_value == result.present_value
    assert result.exact_price_change == 0
    assert result.duration_convexity_price_change == 0
    assert result.duration_convexity_error == 0


def test_result_is_strict_json_ready():
    payload = analyze_fixed_income_sensitivity({1: 5, 2: 105}, 0.04).to_dict()

    encoded = json.dumps(payload, allow_nan=False, sort_keys=True)

    assert payload["cash_flow_count"] == 2
    assert len(payload["cash_flows"]) == 2
    assert '"modified_duration_years"' in encoded


@pytest.mark.parametrize("cash_flows", [None, [], {}, 1.0])
def test_cash_flows_must_be_a_non_empty_mapping(cash_flows):
    with pytest.raises(ValueError, match="cash_flows must be a non-empty mapping"):
        analyze_fixed_income_sensitivity(cash_flows, 0.05)


@pytest.mark.parametrize("time_years", [0, -1, float("nan"), float("inf"), "invalid", True])
def test_invalid_cash_flow_times_are_rejected(time_years):
    with pytest.raises(ValueError, match="cash-flow time"):
        analyze_fixed_income_sensitivity({time_years: 100}, 0.05)


def test_times_must_be_unique_after_numeric_conversion():
    with pytest.raises(ValueError, match="unique after numeric conversion"):
        analyze_fixed_income_sensitivity({"1": 5, 1: 105}, 0.05)


@pytest.mark.parametrize(
    "cash_flow",
    [0, -1, float("nan"), float("inf"), -float("inf"), "invalid", True, 10**1000],
)
def test_invalid_cash_flow_amounts_are_rejected(cash_flow):
    with pytest.raises(ValueError, match="cash flow|cash-flow amounts"):
        analyze_fixed_income_sensitivity({1: cash_flow}, 0.05)


@pytest.mark.parametrize(
    "annual_yield",
    [float("nan"), float("inf"), -float("inf"), "invalid", True, 10**1000],
)
def test_invalid_yields_are_rejected(annual_yield):
    with pytest.raises(ValueError, match="annual_yield"):
        analyze_fixed_income_sensitivity({1: 100}, annual_yield)


@pytest.mark.parametrize("compounds_per_year", [0, -1, 1.5, True, 10**1000])
def test_invalid_compounding_frequency_is_rejected(compounds_per_year):
    with pytest.raises(ValueError, match="compounds_per_year"):
        analyze_fixed_income_sensitivity(
            {1: 100},
            0.05,
            compounds_per_year=compounds_per_year,
        )


@pytest.mark.parametrize("rate_shock", [float("nan"), float("inf"), "invalid", True, 10**1000])
def test_invalid_rate_shocks_are_rejected(rate_shock):
    with pytest.raises(ValueError, match="rate_shock"):
        analyze_fixed_income_sensitivity({1: 100}, 0.05, rate_shock=rate_shock)


def test_current_and_shocked_yields_must_have_positive_discount_bases():
    with pytest.raises(ValueError, match="annual_yield must be greater"):
        analyze_fixed_income_sensitivity({1: 100}, -1.0)

    with pytest.raises(ValueError, match="shocked annual yield must be greater"):
        analyze_fixed_income_sensitivity({1: 100}, -0.9, rate_shock=-0.1)


def test_aggregate_value_overflow_is_rejected():
    with pytest.raises(ValueError, match="value at annual_yield exceeds"):
        analyze_fixed_income_sensitivity({1: 1e308, 2: 1e308}, 0)


def test_convexity_overflow_is_rejected():
    with pytest.raises(ValueError, match="convexity contribution.*numeric range"):
        analyze_fixed_income_sensitivity({1e308: 100}, 0, rate_shock=0)
