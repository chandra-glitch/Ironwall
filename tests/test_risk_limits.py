import json

import pytest

from ironwall.risk_limits import evaluate_risk_limits


def test_risk_limits_report_breaches_utilization_and_headroom():
    result = evaluate_risk_limits(
        {
            "annualized_volatility": 0.25,
            "value_at_risk": 0.03,
            "maximum_drawdown": 0.12,
        },
        {
            "annualized_volatility": 0.30,
            "value_at_risk": 0.025,
            "maximum_drawdown": 0.15,
        },
    )

    by_metric = {assessment.metric: assessment for assessment in result.assessments}
    assert result.assessed_metrics == 3
    assert result.breach_count == 1
    assert result.status == "breached"
    assert result.breached_metrics == ("value_at_risk",)
    assert by_metric["annualized_volatility"].utilization_ratio == pytest.approx(5 / 6)
    assert by_metric["annualized_volatility"].headroom == pytest.approx(0.05)
    assert by_metric["value_at_risk"].utilization_ratio == pytest.approx(1.2)
    assert by_metric["value_at_risk"].headroom == pytest.approx(-0.005)
    assert by_metric["value_at_risk"].breached is True


def test_value_equal_to_limit_is_fully_utilized_without_a_breach():
    result = evaluate_risk_limits(
        {"conditional_value_at_risk": 0.05}, {"conditional_value_at_risk": 0.05}
    )

    assessment = result.assessments[0]
    assert result.status == "within_limits"
    assert result.breach_count == 0
    assert assessment.utilization_ratio == 1.0
    assert assessment.headroom == 0.0
    assert assessment.breached is False


def test_limits_select_metrics_and_results_use_deterministic_order():
    result = evaluate_risk_limits(
        {"z_metric": 0.2, "a_metric": 0.1, "unused": float("nan")},
        {"z_metric": 0.4, "a_metric": 0.2},
    )

    assert [assessment.metric for assessment in result.assessments] == ["a_metric", "z_metric"]
    assert result.status == "within_limits"


def test_result_is_strict_json_ready():
    payload = evaluate_risk_limits(
        {"value_at_risk": 0.03, "maximum_drawdown": 0.12},
        {"value_at_risk": 0.025, "maximum_drawdown": 0.15},
    ).to_dict()

    encoded = json.dumps(payload, allow_nan=False, sort_keys=True)

    assert payload["breached_metrics"] == ["value_at_risk"]
    assert len(payload["assessments"]) == 2
    assert '"utilization_ratio"' in encoded


def test_utilization_overflow_has_an_explicit_json_safe_status():
    result = evaluate_risk_limits({"stress_loss": 1.0}, {"stress_loss": 5e-324})

    assessment = result.assessments[0]
    assert assessment.breached is True
    assert assessment.utilization_ratio is None
    assert assessment.utilization_status == "above_numeric_range"


@pytest.mark.parametrize("values", [None, [], 0.5])
def test_values_must_be_a_mapping(values):
    with pytest.raises(ValueError, match="values must be a mapping"):
        evaluate_risk_limits(values, {"value_at_risk": 0.05})


@pytest.mark.parametrize("limits", [None, [], {}, 0.5])
def test_limits_must_be_a_non_empty_mapping(limits):
    with pytest.raises(ValueError, match="limits must be a non-empty mapping"):
        evaluate_risk_limits({"value_at_risk": 0.03}, limits)


@pytest.mark.parametrize("metric", ["", " value_at_risk", "value_at_risk ", 42])
def test_invalid_limit_metric_names_are_rejected(metric):
    with pytest.raises(ValueError, match="metric names"):
        evaluate_risk_limits({metric: 0.03}, {metric: 0.05})


@pytest.mark.parametrize(
    "value",
    [-0.01, float("nan"), float("inf"), "invalid", True, 10**1000],
)
def test_invalid_risk_values_are_rejected(value):
    with pytest.raises(ValueError, match="value"):
        evaluate_risk_limits({"value_at_risk": value}, {"value_at_risk": 0.05})


@pytest.mark.parametrize(
    "limit",
    [0.0, -0.01, float("nan"), float("inf"), "invalid", True, 10**1000],
)
def test_invalid_risk_limits_are_rejected(limit):
    with pytest.raises(ValueError, match="limit"):
        evaluate_risk_limits({"value_at_risk": 0.03}, {"value_at_risk": limit})


def test_missing_limited_metric_is_rejected():
    with pytest.raises(ValueError, match="missing values.*maximum_drawdown"):
        evaluate_risk_limits(
            {"value_at_risk": 0.03},
            {"value_at_risk": 0.05, "maximum_drawdown": 0.20},
        )
