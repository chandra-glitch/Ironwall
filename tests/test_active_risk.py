import json
import math

import pytest

from ironwall.active_risk import analyze_active_risk


def test_active_risk_calculates_tracking_error_and_information_ratio():
    result = analyze_active_risk(
        [0.02, 0.01, -0.01, 0.03],
        [0.01, 0.00, -0.02, 0.01],
    )

    assert result.return_observations == 4
    assert result.mean_active_return == pytest.approx(0.0125)
    assert result.annualized_mean_active_return == pytest.approx(0.0125 * 252)
    assert result.tracking_error == pytest.approx(0.005)
    assert result.annualized_tracking_error == pytest.approx(0.005 * math.sqrt(252))
    assert result.information_ratio == pytest.approx(2.5 * math.sqrt(252))


def test_custom_periods_per_year_control_annualization():
    result = analyze_active_risk(
        [0.02, 0.00, 0.01],
        [0.01, 0.01, 0.01],
        periods_per_year=12,
    )

    assert result.mean_active_return == pytest.approx(0.0)
    assert result.tracking_error == pytest.approx(0.01)
    assert result.annualized_tracking_error == pytest.approx(0.01 * math.sqrt(12))
    assert result.information_ratio == pytest.approx(0.0)


def test_underperformance_produces_negative_information_ratio():
    result = analyze_active_risk(
        [0.00, 0.00, 0.00],
        [0.01, 0.02, 0.00],
    )

    assert result.mean_active_return == pytest.approx(-0.01)
    assert result.tracking_error == pytest.approx(0.01)
    assert result.information_ratio == pytest.approx(-math.sqrt(252))


def test_information_ratio_is_undefined_for_zero_tracking_error():
    result = analyze_active_risk(
        [0.015625, 0.03125, 0.046875],
        [0.0, 0.015625, 0.03125],
    )

    assert result.mean_active_return == pytest.approx(0.015625)
    assert result.tracking_error == pytest.approx(0.0)
    assert result.annualized_tracking_error == pytest.approx(0.0)
    assert result.information_ratio is None


def test_active_risk_metrics_are_json_ready():
    result = analyze_active_risk([0.02, 0.00, 0.01], [0.01, 0.01, 0.01])

    payload = json.loads(json.dumps(result.to_dict()))
    assert payload["return_observations"] == 3
    assert payload["tracking_error"] == pytest.approx(0.01)
    assert payload["information_ratio"] == pytest.approx(0.0)


@pytest.mark.parametrize(
    "portfolio, benchmark, periods_per_year, message",
    [
        ([0.01], [0.01], 252, "at least two aligned observations"),
        ([0.01, 0.02], [0.01], 252, "same length"),
        ([0.01, float("inf")], [0.01, 0.02], 252, "finite values"),
        ([0.01, float("nan")], [0.01, 0.02], 252, "finite values"),
        ([0.01, 0.02], [0.01, float("inf")], 252, "finite values"),
        ([0.01, 0.02], [0.01, float("nan")], 252, "finite values"),
        ([0.01, -1.0], [0.01, 0.02], 252, "greater than -100%"),
        ([0.01, 0.02], [0.01, -1.0], 252, "greater than -100%"),
        ([0.01, 0.02], [0.01, 0.02], 0, "positive integer"),
        ([0.01, 0.02], [0.01, 0.02], True, "positive integer"),
        ([0.01, 0.02], [0.01, 0.02], 252.5, "positive integer"),
    ],
)
def test_invalid_active_risk_inputs_are_rejected(
    portfolio,
    benchmark,
    periods_per_year,
    message,
):
    with pytest.raises(ValueError, match=message):
        analyze_active_risk(
            portfolio,
            benchmark,
            periods_per_year=periods_per_year,
        )
