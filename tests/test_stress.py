import pytest

from ironwall.stress import run_stress_scenario

WEIGHTS = {"JPM": 0.6, "BAC": 0.4}


def test_stress_scenario_calculates_weighted_asset_impacts():
    result = run_stress_scenario(WEIGHTS, {"JPM": -0.25, "BAC": 0.05})

    assert result.asset_impacts == pytest.approx({"JPM": -0.15, "BAC": 0.02})
    assert result.portfolio_return == pytest.approx(-0.13)
    assert result.loss == pytest.approx(0.13)
    assert sum(result.asset_impacts.values()) == pytest.approx(result.portfolio_return)


def test_scenario_gain_has_zero_loss_magnitude():
    result = run_stress_scenario(WEIGHTS, {"JPM": 0.10, "BAC": 0.05})

    assert result.portfolio_return == pytest.approx(0.08)
    assert result.loss == 0.0


def test_total_loss_boundary_is_supported_and_serializable():
    result = run_stress_scenario(WEIGHTS, {"JPM": -1.0, "BAC": -1.0})

    assert result.loss == pytest.approx(1.0)
    assert result.to_dict() == {
        "portfolio_return": pytest.approx(-1.0),
        "loss": pytest.approx(1.0),
        "asset_impacts": pytest.approx({"JPM": -0.6, "BAC": -0.4}),
    }


@pytest.mark.parametrize(
    "shocks, message",
    [
        ({"JPM": -0.2}, "missing shocks"),
        ({"JPM": -0.2, "BAC": 0.0, "GS": 0.0}, "unknown assets"),
        ({"JPM": "severe", "BAC": 0.0}, "must be numeric"),
        ({"JPM": float("nan"), "BAC": 0.0}, "must be finite"),
        ({"JPM": -1.01, "BAC": 0.0}, "below -100%"),
    ],
)
def test_invalid_scenario_shocks_are_rejected(shocks, message):
    with pytest.raises(ValueError, match=message):
        run_stress_scenario(WEIGHTS, shocks)


def test_invalid_portfolio_weights_are_rejected():
    with pytest.raises(ValueError, match="sum to 1.0"):
        run_stress_scenario({"JPM": 0.6, "BAC": 0.3}, {"JPM": -0.2, "BAC": -0.1})
