import json

import pytest

from ironwall.diversification import analyze_diversification


def test_perfectly_correlated_assets_provide_no_volatility_reduction():
    returns = {
        "JPM": [0.01, -0.01, 0.0],
        "BAC": [0.01, -0.01, 0.0],
    }

    result = analyze_diversification(returns, {"JPM": 0.6, "BAC": 0.4})

    assert result.asset_count == 2
    assert result.return_observations == 3
    assert result.weighted_average_asset_volatility == pytest.approx(0.01)
    assert result.portfolio_volatility == pytest.approx(0.01)
    assert result.diversification_ratio == pytest.approx(1.0)
    assert result.volatility_reduction == pytest.approx(0.0)


def test_offsetting_returns_show_diversification_benefit():
    returns = {
        "JPM": [0.02, -0.02, 0.0],
        "TLT": [-0.01, 0.01, 0.0],
    }

    result = analyze_diversification(returns, {"JPM": 0.5, "TLT": 0.5})

    assert result.asset_volatilities == pytest.approx({"JPM": 0.02, "TLT": 0.01})
    assert result.weighted_average_asset_volatility == pytest.approx(0.015)
    assert result.portfolio_volatility == pytest.approx(0.005)
    assert result.diversification_ratio == pytest.approx(3.0)
    assert result.volatility_reduction == pytest.approx(2 / 3)


def test_zero_volatility_portfolio_uses_json_safe_ratio():
    returns = {
        "JPM": [0.01, -0.01],
        "TLT": [-0.01, 0.01],
    }

    result = analyze_diversification(returns, {"JPM": 0.5, "TLT": 0.5})

    assert result.portfolio_volatility == 0.0
    assert result.diversification_ratio is None
    assert result.volatility_reduction == pytest.approx(1.0)
    assert json.loads(json.dumps(result.to_dict()))["diversification_ratio"] is None


def test_constant_assets_have_undefined_diversification_metrics():
    returns = {
        "CASH_A": [0.001, 0.001, 0.001],
        "CASH_B": [0.002, 0.002, 0.002],
    }

    result = analyze_diversification(returns, {"CASH_A": 0.5, "CASH_B": 0.5})

    assert result.weighted_average_asset_volatility == 0.0
    assert result.portfolio_volatility == 0.0
    assert result.diversification_ratio is None
    assert result.volatility_reduction is None


@pytest.mark.parametrize(
    "returns, weights, message",
    [
        ({"JPM": [0.01, 0.02]}, {"JPM": 1.0}, "at least two assets"),
        (
            {"JPM": [0.01, 0.02], "TLT": [0.0, 0.01]},
            {"JPM": 1.0},
            "missing weights",
        ),
        (
            {"JPM": [0.01, 0.02], "TLT": [0.0, 0.01]},
            {"JPM": 0.7, "TLT": 0.4},
            "sum to 1.0",
        ),
        (
            {"JPM": [0.01, 0.02], "TLT": [0.0, 0.01, 0.02]},
            {"JPM": 0.5, "TLT": 0.5},
            "aligned",
        ),
        (
            {"JPM": [0.01], "TLT": [0.02]},
            {"JPM": 0.5, "TLT": 0.5},
            "at least two observations",
        ),
        (
            {"JPM": [0.01, float("nan")], "TLT": [0.0, 0.01]},
            {"JPM": 0.5, "TLT": 0.5},
            "finite values",
        ),
        (
            {"JPM": [0.01, -1.0], "TLT": [0.0, 0.01]},
            {"JPM": 0.5, "TLT": 0.5},
            "-100%",
        ),
    ],
)
def test_invalid_inputs_are_rejected(returns, weights, message):
    with pytest.raises(ValueError, match=message):
        analyze_diversification(returns, weights)
