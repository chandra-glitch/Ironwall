import json
import math

import pytest

from ironwall.ewma import forecast_ewma_volatility


def test_ewma_forecast_uses_normalized_exponential_weights():
    result = forecast_ewma_volatility(
        [0.01, -0.02, 0.04],
        decay_factor=0.5,
        periods_per_year=4,
    )
    expected_variance = (0.25 * 0.01**2 + 0.5 * 0.02**2 + 0.04**2) / 1.75

    assert result.periodic_variance == pytest.approx(expected_variance)
    assert result.periodic_volatility == pytest.approx(math.sqrt(expected_variance))
    assert result.annualized_volatility == pytest.approx(2 * math.sqrt(expected_variance))
    assert result.latest_return_weight == pytest.approx(1 / 1.75)
    assert result.periods_per_year == 4


def test_recent_shock_receives_more_weight_than_old_shock():
    old_shock = forecast_ewma_volatility(
        [0.10, 0.0, 0.0, 0.0],
        decay_factor=0.8,
    )
    recent_shock = forecast_ewma_volatility(
        [0.0, 0.0, 0.0, 0.10],
        decay_factor=0.8,
    )

    assert recent_shock.periodic_variance > old_shock.periodic_variance
    assert recent_shock.periodic_variance / old_shock.periodic_variance == pytest.approx(1 / 0.8**3)


def test_defaults_match_daily_riskmetrics_convention():
    result = forecast_ewma_volatility([0.01, -0.015, 0.02])

    assert result.return_observations == 3
    assert result.decay_factor == 0.94
    assert result.periods_per_year == 252
    assert result.half_life_periods == pytest.approx(math.log(0.5) / math.log(0.94))
    assert result.annualized_volatility == pytest.approx(
        result.periodic_volatility * math.sqrt(252)
    )


def test_zero_mean_assumption_treats_constant_nonzero_returns_as_risk():
    result = forecast_ewma_volatility([0.01, 0.01, 0.01])

    assert result.periodic_variance == pytest.approx(0.01**2)
    assert result.periodic_volatility == pytest.approx(0.01)


def test_zero_returns_are_json_serializable():
    result = forecast_ewma_volatility([0.0, 0.0, 0.0])
    payload = json.loads(json.dumps(result.to_dict(), allow_nan=False))

    assert payload["periodic_variance"] == 0.0
    assert payload["periodic_volatility"] == 0.0
    assert payload["annualized_volatility"] == 0.0


@pytest.mark.parametrize(
    "returns, message",
    [
        ([], "at least two"),
        ([0.01], "at least two"),
        ([0.01, "bad"], "numeric"),
        ([0.01, float("nan")], "finite"),
        ([0.01, -1.0], "-100%"),
        ([0.01, 1e308], "too large"),
    ],
)
def test_invalid_returns_are_rejected(returns, message):
    with pytest.raises(ValueError, match=message):
        forecast_ewma_volatility(returns)


@pytest.mark.parametrize("decay_factor", [0.0, 1.0, -0.1, 1.1, float("nan")])
def test_invalid_decay_factors_are_rejected(decay_factor):
    with pytest.raises(ValueError, match="decay_factor"):
        forecast_ewma_volatility([0.01, 0.02], decay_factor=decay_factor)


@pytest.mark.parametrize("periods_per_year", [0, -1, 252.5, True, 10**1000])
def test_invalid_annualization_periods_are_rejected(periods_per_year):
    with pytest.raises(ValueError, match="positive integer|too large"):
        forecast_ewma_volatility(
            [0.01, 0.02],
            periods_per_year=periods_per_year,
        )
