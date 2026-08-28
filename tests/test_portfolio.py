import pytest

from ironwall.portfolio import (
    analyze_portfolio,
    calculate_asset_returns,
    calculate_portfolio_returns,
    calculate_risk_contributions,
    validate_weights,
)

PRICES = {
    "JPM": [100, 110, 99, 108],
    "BAC": [100, 100, 110, 105],
}
WEIGHTS = {"JPM": 0.6, "BAC": 0.4}


def test_portfolio_returns_use_supplied_weights():
    returns = calculate_asset_returns(PRICES)
    portfolio_returns = calculate_portfolio_returns(returns, WEIGHTS)

    assert portfolio_returns == pytest.approx(
        (
            0.06,
            -0.02,
            0.0363636364,
        )
    )


def test_risk_contributions_sum_to_one():
    returns = calculate_asset_returns(PRICES)
    contributions = calculate_risk_contributions(returns, WEIGHTS)

    assert sum(contributions.values()) == pytest.approx(1.0)
    assert set(contributions) == {"JPM", "BAC"}


def test_complete_portfolio_analysis():
    analysis = analyze_portfolio(PRICES, WEIGHTS)

    assert analysis.weights == WEIGHTS
    assert analysis.metrics.return_observations == 3
    assert analysis.metrics.maximum_drawdown > 0
    assert sum(analysis.risk_contributions.values()) == pytest.approx(1.0)


@pytest.mark.parametrize(
    "weights, message",
    [
        ({"JPM": 0.6}, "missing weights"),
        ({"JPM": 0.6, "BAC": 0.5}, "sum to 1.0"),
        ({"JPM": 1.1, "BAC": -0.1}, "non-negative"),
        ({"JPM": 0.6, "BAC": 0.4, "GS": 0.0}, "unknown assets"),
    ],
)
def test_invalid_weights_are_rejected(weights, message):
    with pytest.raises(ValueError, match=message):
        validate_weights(weights, tuple(PRICES))
