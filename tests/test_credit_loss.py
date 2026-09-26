import json
import math
from decimal import Decimal

import pytest

from ironwall.credit_loss import analyze_credit_loss


def test_single_exposure_matches_closed_form_loss_measures():
    result = analyze_credit_loss(
        {"Borrower A": 1_000},
        {"Borrower A": 0.02},
        {"Borrower A": 0.45},
    )
    exposure = result.exposures[0]

    assert result.exposure_count == 1
    assert result.total_exposure_at_default == 1_000
    assert result.expected_loss == pytest.approx(9)
    assert result.expected_loss_rate == pytest.approx(0.009)
    assert result.exposure_weighted_probability_of_default == pytest.approx(0.02)
    assert result.exposure_weighted_loss_given_default == pytest.approx(0.45)
    assert result.independent_unexpected_loss == pytest.approx(63)
    assert exposure.loss_if_default == pytest.approx(450)
    assert exposure.loss_standard_deviation == pytest.approx(63)
    assert exposure.exposure_weight == 1
    assert exposure.expected_loss_contribution == 1
    assert exposure.loss_variance_contribution == 1


def test_portfolio_reconciles_expected_loss_and_independent_variance():
    result = analyze_credit_loss(
        {"Borrower B": 500, "Borrower A": 1_000},
        {"Borrower B": 0.05, "Borrower A": 0.02},
        {"Borrower B": 0.60, "Borrower A": 0.45},
    )

    assert [exposure.obligor for exposure in result.exposures] == ["Borrower A", "Borrower B"]
    assert result.total_exposure_at_default == 1_500
    assert result.expected_loss == pytest.approx(24)
    assert result.expected_loss_rate == pytest.approx(0.016)
    assert result.exposure_weighted_probability_of_default == pytest.approx(0.03)
    assert result.exposure_weighted_loss_given_default == pytest.approx(0.50)
    assert result.independent_unexpected_loss == pytest.approx(math.sqrt(3_969 + 4_275))
    assert sum(
        exposure.expected_loss_contribution for exposure in result.exposures
    ) == pytest.approx(1)
    assert sum(
        exposure.loss_variance_contribution for exposure in result.exposures
    ) == pytest.approx(1)
    assert sum(exposure.exposure_weight for exposure in result.exposures) == pytest.approx(1)


def test_certain_default_has_expected_loss_but_no_unexpected_loss():
    result = analyze_credit_loss(
        {"Defaulted": 100},
        {"Defaulted": 1},
        {"Defaulted": 0.4},
    )

    assert result.expected_loss == 40
    assert result.independent_unexpected_loss == 0
    assert result.exposures[0].expected_loss_contribution == 1
    assert result.exposures[0].loss_variance_contribution is None


def test_zero_risk_portfolio_uses_none_for_undefined_contributions():
    result = analyze_credit_loss(
        {"No default": 100, "No loss": 200},
        {"No default": 0, "No loss": 0.5},
        {"No default": 0.4, "No loss": 0},
    )

    assert result.expected_loss == 0
    assert result.expected_loss_rate == 0
    assert result.independent_unexpected_loss == 0
    assert all(exposure.expected_loss_contribution is None for exposure in result.exposures)
    assert all(exposure.loss_variance_contribution is None for exposure in result.exposures)


def test_result_is_strict_json_ready():
    payload = analyze_credit_loss(
        {"Borrower A": 1_000, "Borrower B": 500},
        {"Borrower A": 0.02, "Borrower B": 0.05},
        {"Borrower A": 0.45, "Borrower B": 0.60},
    ).to_dict()

    encoded = json.dumps(payload, allow_nan=False, sort_keys=True)

    assert payload["exposure_count"] == 2
    assert len(payload["exposures"]) == 2
    assert '"independent_unexpected_loss"' in encoded


def test_finite_decimal_inputs_are_supported_without_boundary_rounding():
    result = analyze_credit_loss(
        {"A": Decimal("1000")},
        {"A": Decimal("0.02")},
        {"A": Decimal("0.45")},
    )

    assert result.expected_loss == pytest.approx(9)


@pytest.mark.parametrize(
    "probability, message",
    [
        (Decimal("1.00000000000000000001"), "between 0 and 1"),
        (Decimal("-1e-10000"), "between 0 and 1"),
        (Decimal("1e-10000"), "loses material precision"),
        (Decimal("0.99999999999999999999"), "loses material precision"),
    ],
)
def test_decimal_values_cannot_round_onto_probability_boundaries(probability, message):
    with pytest.raises(ValueError, match=message):
        analyze_credit_loss({"A": 100}, {"A": probability}, {"A": 0.45})


@pytest.mark.parametrize("values", [None, [], {}, 1.0])
def test_inputs_must_be_non_empty_mappings(values):
    with pytest.raises(ValueError, match="non-empty mapping"):
        analyze_credit_loss(values, {"A": 0.01}, {"A": 0.45})


@pytest.mark.parametrize("obligor", ["", " A", "A ", 1, True])
def test_invalid_obligor_names_are_rejected(obligor):
    with pytest.raises(ValueError, match="obligor names"):
        analyze_credit_loss({obligor: 100}, {obligor: 0.01}, {obligor: 0.45})


@pytest.mark.parametrize(
    "probabilities, losses, message",
    [
        ({"A": 0.01}, {"A": 0.45, "B": 0.50}, "loss_given_default.*unknown B"),
        ({"B": 0.01}, {"A": 0.45}, "probability_of_default.*missing A; unknown B"),
    ],
)
def test_parameter_obligors_must_match_ead(probabilities, losses, message):
    with pytest.raises(ValueError, match=message):
        analyze_credit_loss({"A": 100}, probabilities, losses)


@pytest.mark.parametrize(
    "ead",
    [0, -1, float("nan"), float("inf"), -float("inf"), "invalid", True, 10**1000],
)
def test_invalid_exposure_at_default_is_rejected(ead):
    with pytest.raises(ValueError, match="exposure_at_default"):
        analyze_credit_loss({"A": ead}, {"A": 0.01}, {"A": 0.45})


@pytest.mark.parametrize(
    "probability",
    [-0.01, 1.01, float("nan"), float("inf"), "invalid", True, 10**1000],
)
def test_invalid_probability_of_default_is_rejected(probability):
    with pytest.raises(ValueError, match="probability_of_default"):
        analyze_credit_loss({"A": 100}, {"A": probability}, {"A": 0.45})


@pytest.mark.parametrize(
    "loss_given_default",
    [-0.01, 1.01, float("nan"), float("inf"), "invalid", True, 10**1000],
)
def test_invalid_loss_given_default_is_rejected(loss_given_default):
    with pytest.raises(ValueError, match="loss_given_default"):
        analyze_credit_loss({"A": 100}, {"A": 0.01}, {"A": loss_given_default})


def test_aggregate_ead_overflow_is_rejected():
    with pytest.raises(ValueError, match="total EAD exceeds"):
        analyze_credit_loss(
            {"A": 1e308, "B": 1e308},
            {"A": 0, "B": 0},
            {"A": 0, "B": 0},
        )


def test_expected_loss_underflow_is_rejected():
    with pytest.raises(ValueError, match="expected loss for A.*numeric range"):
        analyze_credit_loss({"A": 5e-324}, {"A": 0.5}, {"A": 1})


def test_exposure_weight_underflow_is_rejected():
    with pytest.raises(ValueError, match="exposure weight for A.*numeric range"):
        analyze_credit_loss(
            {"A": 5e-324, "B": 1e308},
            {"A": 0, "B": 0},
            {"A": 0, "B": 0},
        )
