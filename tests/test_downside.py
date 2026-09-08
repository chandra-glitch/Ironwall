import json
import math

import pytest

from ironwall.downside import analyze_downside_risk


def test_downside_risk_uses_only_target_shortfalls():
    result = analyze_downside_risk([0.02, -0.01, 0.03, -0.02])
    expected_deviation = math.sqrt((0.01**2 + 0.02**2) / 4)

    assert result.return_observations == 4
    assert result.downside_observations == 2
    assert result.target_return == pytest.approx(0.0)
    assert result.downside_deviation == pytest.approx(expected_deviation)
    assert result.annualized_downside_deviation == pytest.approx(
        expected_deviation * math.sqrt(252)
    )
    assert result.sortino_ratio == pytest.approx(0.005 / expected_deviation * math.sqrt(252))


def test_nonzero_target_changes_shortfall_and_sortino_ratio():
    result = analyze_downside_risk(
        [0.02, 0.01, -0.01],
        target_return=0.01,
        periods_per_year=12,
    )

    assert result.downside_observations == 1
    assert result.downside_deviation == pytest.approx(math.sqrt(0.02**2 / 3))
    assert result.sortino_ratio == pytest.approx(-1.0)


def test_sortino_is_undefined_without_target_shortfalls():
    result = analyze_downside_risk([0.01, 0.02, 0.03], target_return=0.005)

    assert result.downside_observations == 0
    assert result.downside_deviation == pytest.approx(0.0)
    assert result.annualized_downside_deviation == pytest.approx(0.0)
    assert result.sortino_ratio is None


def test_downside_metrics_are_json_ready():
    result = analyze_downside_risk([-0.01, 0.02], periods_per_year=12)

    payload = json.loads(json.dumps(result.to_dict()))
    assert payload["return_observations"] == 2
    assert payload["downside_observations"] == 1
    assert payload["sortino_ratio"] == pytest.approx(math.sqrt(6))


@pytest.mark.parametrize(
    "returns, target_return, periods_per_year, message",
    [
        ([0.01], 0.0, 252, "at least two return observations"),
        ([0.01, float("inf")], 0.0, 252, "finite values"),
        ([0.01, float("nan")], 0.0, 252, "finite values"),
        ([0.01, -1.0], 0.0, 252, "greater than -100%"),
        ([0.01, 0.02], float("inf"), 252, "target_return"),
        ([0.01, 0.02], float("nan"), 252, "target_return"),
        ([0.01, 0.02], -1.0, 252, "target_return"),
        ([0.01, 0.02], 0.0, 0, "positive integer"),
        ([0.01, 0.02], 0.0, True, "positive integer"),
        ([0.01, 0.02], 0.0, 252.5, "positive integer"),
    ],
)
def test_invalid_downside_inputs_are_rejected(
    returns,
    target_return,
    periods_per_year,
    message,
):
    with pytest.raises(ValueError, match=message):
        analyze_downside_risk(
            returns,
            target_return=target_return,
            periods_per_year=periods_per_year,
        )
