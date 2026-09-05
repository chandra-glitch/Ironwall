import pytest

from ironwall.monte_carlo import estimate_monte_carlo_var


def test_seeded_monte_carlo_estimate_is_reproducible_and_serializable():
    returns = (-0.03, 0.01, 0.02, -0.01, 0.015, -0.02)

    first = estimate_monte_carlo_var(returns, simulations=500, seed=42)
    second = estimate_monte_carlo_var(returns, simulations=500, seed=42)

    assert first == second
    assert first.value_at_risk > 0.0
    assert first.conditional_value_at_risk >= first.value_at_risk
    assert first.to_dict()["simulations"] == 500
    assert first.to_dict()["seed"] == 42


def test_constant_log_return_compounds_over_horizon():
    estimate = estimate_monte_carlo_var(
        (-0.01, -0.01, -0.01),
        simulations=100,
        horizon_periods=2,
        seed=7,
    )

    assert estimate.mean_terminal_return == pytest.approx(-0.0199)
    assert estimate.value_at_risk == pytest.approx(0.0199)
    assert estimate.conditional_value_at_risk == pytest.approx(0.0199)


@pytest.mark.parametrize(
    "returns, options, message",
    [
        ((0.01,), {}, "at least two"),
        ((0.01, "bad"), {}, "numeric"),
        ((0.01, float("inf")), {}, "finite"),
        ((0.01, -1.0), {}, "greater than -100%"),
        ((0.01, 0.02), {"confidence": 1.0}, "strictly between"),
        ((0.01, 0.02), {"simulations": 99}, "at least 100"),
        ((0.01, 0.02), {"simulations": 100.0}, "integer"),
        ((0.01, 0.02), {"horizon_periods": 0}, "at least 1"),
        ((0.01, 0.02), {"seed": True}, "integer or None"),
    ],
)
def test_invalid_monte_carlo_inputs_are_rejected(returns, options, message):
    with pytest.raises(ValueError, match=message):
        estimate_monte_carlo_var(returns, **options)
