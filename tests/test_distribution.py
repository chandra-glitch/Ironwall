import json
import math

import pytest

from ironwall.distribution import analyze_return_distribution

SYMMETRIC_RETURNS = [-0.02, -0.01, 0.01, 0.02]


def test_symmetric_distribution_has_zero_skewness():
    result = analyze_return_distribution(SYMMETRIC_RETURNS)

    assert result.return_observations == 4
    assert result.mean_return == pytest.approx(0.0, abs=1e-15)
    assert result.sample_volatility == pytest.approx(math.sqrt(0.001 / 3))
    assert result.skewness == pytest.approx(0.0, abs=1e-15)
    assert result.excess_kurtosis == pytest.approx(-1.64)
    assert result.jarque_bera_statistic == pytest.approx(0.4482666666666666)
    assert result.jarque_bera_asymptotic_p_value == pytest.approx(
        math.exp(-result.jarque_bera_statistic / 2)
    )


def test_shape_diagnostics_are_scale_invariant():
    base = analyze_return_distribution([-0.03, -0.01, 0.00, 0.02, 0.07])
    scaled = analyze_return_distribution([-0.06, -0.02, 0.00, 0.04, 0.14])

    assert scaled.mean_return == pytest.approx(2 * base.mean_return)
    assert scaled.sample_volatility == pytest.approx(2 * base.sample_volatility)
    assert scaled.skewness == pytest.approx(base.skewness)
    assert scaled.excess_kurtosis == pytest.approx(base.excess_kurtosis)
    assert scaled.jarque_bera_statistic == pytest.approx(base.jarque_bera_statistic)


def test_positive_outlier_produces_right_skew_and_excess_kurtosis():
    result = analyze_return_distribution([-0.01, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.10])

    assert result.skewness > 2
    assert result.excess_kurtosis > 3
    assert result.jarque_bera_asymptotic_p_value < 0.01


def test_result_is_strict_json_serializable():
    result = analyze_return_distribution(SYMMETRIC_RETURNS)
    payload = json.loads(json.dumps(result.to_dict(), allow_nan=False))

    assert payload["return_observations"] == 4
    assert payload["skewness"] == pytest.approx(0.0, abs=1e-15)
    assert payload["jarque_bera_asymptotic_p_value"] == pytest.approx(
        result.jarque_bera_asymptotic_p_value
    )


@pytest.mark.parametrize(
    "returns, message",
    [
        ([], "at least four"),
        ([0.01, 0.02, 0.03], "at least four"),
        ([0.01, 0.02, 0.03, "bad"], "numeric"),
        ([0.01, 0.02, 0.03, math.nan], "finite"),
        ([0.01, 0.02, 0.03, -1.0], "-100%"),
        ([0.01, 0.01, 0.01, 0.01], "non-constant"),
    ],
)
def test_invalid_returns_are_rejected(returns, message):
    with pytest.raises(ValueError, match=message):
        analyze_return_distribution(returns)
