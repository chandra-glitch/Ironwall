import json
import math

import pytest

from ironwall.serial_dependence import analyze_serial_dependence


def test_return_autocorrelation_uses_full_sample_mean_and_variance():
    result = analyze_serial_dependence([0.01, 0.02, 0.03, 0.04], max_lag=2)

    assert result.return_observations == 4
    assert result.max_lag == 2
    assert [lag.lag for lag in result.lags] == [1, 2]
    assert result.lags[0].return_autocorrelation == pytest.approx(0.25)
    assert result.lags[1].return_autocorrelation == pytest.approx(-0.30)


def test_squared_returns_expose_clustered_return_magnitudes():
    returns = [0.01, -0.01, 0.01, -0.01, 0.05, -0.05, 0.05, -0.05]

    result = analyze_serial_dependence(returns)

    assert result.squared_return_autocorrelation_available is True
    assert result.lags[0].squared_return_autocorrelation == pytest.approx(0.625)


def test_constant_magnitudes_have_no_squared_return_autocorrelation():
    result = analyze_serial_dependence([-0.02, 0.02, -0.02, 0.02, -0.02, 0.02])

    assert result.lags[0].return_autocorrelation == pytest.approx(-5 / 6)
    assert result.squared_return_autocorrelation_available is False
    assert result.lags[0].squared_return_autocorrelation is None


def test_result_is_strict_json_ready():
    payload = analyze_serial_dependence(
        [-0.03, -0.01, 0.02, 0.01, -0.02],
        max_lag=3,
    ).to_dict()

    encoded = json.dumps(payload, allow_nan=False, sort_keys=True)

    assert payload["max_lag"] == 3
    assert len(payload["lags"]) == 3
    assert '"return_autocorrelation"' in encoded


def test_extreme_finite_values_are_scaled_before_moment_calculation():
    result = analyze_serial_dependence([1e308, 5e307, 2e307, -0.5], max_lag=2)

    assert all(math.isfinite(lag.return_autocorrelation) for lag in result.lags)
    assert all(
        lag.squared_return_autocorrelation is not None
        and math.isfinite(lag.squared_return_autocorrelation)
        for lag in result.lags
    )


def test_subnormal_returns_do_not_underflow_before_analysis():
    result = analyze_serial_dependence([5e-324, 0.0, 5e-324])

    assert result.lags[0].return_autocorrelation == pytest.approx(-2 / 3)
    assert result.lags[0].squared_return_autocorrelation == pytest.approx(-2 / 3)


@pytest.mark.parametrize(
    "returns",
    [
        [],
        [0.01],
        [0.01, 0.02],
        [0.01, 0.02, "invalid"],
        [0.01, 0.02, float("nan")],
        [0.01, 0.02, float("inf")],
        [0.01, 0.02, -1.0],
        [0.01, 0.02, 10**1000],
    ],
)
def test_invalid_returns_are_rejected(returns):
    with pytest.raises(ValueError, match="returns|at least"):
        analyze_serial_dependence(returns)


def test_constant_returns_are_rejected():
    with pytest.raises(ValueError, match="non-constant"):
        analyze_serial_dependence([0.01, 0.01, 0.01])


@pytest.mark.parametrize("max_lag", [0, -1, 1.5, True, "1", 4])
def test_invalid_max_lag_is_rejected(max_lag):
    with pytest.raises(ValueError, match="max_lag"):
        analyze_serial_dependence([-0.02, 0.01, 0.03, -0.01], max_lag=max_lag)
