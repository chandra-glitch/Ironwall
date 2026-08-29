import math

import pytest

from ironwall.metrics import (
    analyze_prices,
    analyze_returns,
    backtest_var,
    build_wealth_index,
    calculate_cvar,
    calculate_max_drawdown,
    calculate_mean,
    calculate_returns,
    calculate_var,
    calculate_volatility,
)


def test_calculate_mean_and_returns():
    assert calculate_mean([1, 2, 3, 4, 5]) == 3
    assert calculate_returns([100, 110, 99]) == pytest.approx((0.10, -0.10))


def test_sample_volatility():
    result = calculate_volatility([0.01, 0.02, 0.03])
    assert result == pytest.approx(0.01)


def test_historical_var_and_cvar_are_positive_losses():
    returns = [-0.10, -0.05, -0.02, 0.01, 0.03]

    assert calculate_var(returns, confidence=0.80) == pytest.approx(0.06)
    assert calculate_cvar(returns, confidence=0.80) == pytest.approx(0.10)


def test_maximum_drawdown_is_positive_loss():
    assert calculate_max_drawdown([100, 120, 90, 130, 104]) == pytest.approx(0.25)


def test_build_wealth_index():
    assert build_wealth_index([0.10, -0.10]) == pytest.approx((100, 110, 99))


def test_var_backtest_uses_only_prior_returns_and_counts_exceptions():
    result = backtest_var(
        [-0.01, 0.02, -0.02, 0.01, -0.10, 0.00, 0.03, -0.05],
        confidence=0.75,
        window=4,
    )

    assert result.forecast_observations == 4
    assert result.exceptions == 2
    assert result.expected_exceptions == pytest.approx(1.0)
    assert result.exception_rate == pytest.approx(0.5)
    assert result.coverage_ratio == pytest.approx(2.0)
    assert 0 <= result.kupiec_p_value <= 1


@pytest.mark.parametrize("window", [True, 1, 8])
def test_var_backtest_rejects_invalid_windows(window):
    with pytest.raises(ValueError, match="window"):
        backtest_var([0.01, -0.01, 0.02, -0.02, 0.03, -0.03, 0.04, -0.04], window=window)


def test_analyze_prices_returns_complete_snapshot():
    metrics = analyze_prices([100, 110, 99, 120], confidence=0.95)

    assert metrics.return_observations == 3
    assert metrics.total_return == pytest.approx(0.20)
    assert metrics.maximum_drawdown == pytest.approx(0.10)
    assert metrics.annualized_volatility > 0
    assert math.isfinite(metrics.sharpe_ratio)


@pytest.mark.parametrize("confidence", [0, 1, -0.1, 1.1, float("nan")])
def test_invalid_confidence_is_rejected(confidence):
    with pytest.raises(ValueError, match="confidence"):
        calculate_var([-0.1, 0.1], confidence)


@pytest.mark.parametrize(
    "operation",
    [
        lambda: calculate_mean([]),
        lambda: calculate_var([], 0.95),
        lambda: calculate_cvar([], 0.95),
        lambda: calculate_returns([100, 0]),
        lambda: analyze_returns([0.01]),
        lambda: analyze_returns([-1.0, 0.1]),
    ],
)
def test_invalid_metric_inputs_raise_clear_errors(operation):
    with pytest.raises(ValueError):
        operation()
