import pytest

from ironwall.factor import calculate_factor_exposure


def test_factor_exposure_recovers_known_linear_relationship():
    factor_returns = (-0.02, -0.01, 0.0, 0.01, 0.02)
    asset_returns = tuple(0.001 + 1.5 * value for value in factor_returns)

    exposure = calculate_factor_exposure(asset_returns, factor_returns)

    assert exposure.observations == 5
    assert exposure.alpha == pytest.approx(0.001)
    assert exposure.beta == pytest.approx(1.5)
    assert exposure.r_squared == pytest.approx(1.0)
    assert exposure.to_dict()["beta"] == pytest.approx(1.5)


def test_unrelated_patterns_have_zero_beta_and_r_squared():
    exposure = calculate_factor_exposure(
        asset_returns=(1.0, -1.0, 0.0, -1.0, 1.0),
        factor_returns=(-2.0, -1.0, 0.0, 1.0, 2.0),
    )

    assert exposure.alpha == pytest.approx(0.0)
    assert exposure.beta == pytest.approx(0.0)
    assert exposure.r_squared == pytest.approx(0.0)


@pytest.mark.parametrize(
    "asset_returns, factor_returns, message",
    [
        ((0.01, 0.02), (0.02, 0.03), "at least three"),
        ((0.01, 0.02, 0.03), (0.01, 0.02, 0.03, 0.04), "aligned"),
        ((0.01, "bad", 0.03), (0.01, 0.02, 0.03), "asset returns.*numeric"),
        ((0.01, 0.02, 0.03), (0.01, float("nan"), 0.03), "factor returns.*finite"),
        ((0.01, 0.02, 0.03), (0.02, 0.02, 0.02), "factor returns must vary"),
        ((0.01, 0.01, 0.01), (0.01, 0.02, 0.03), "asset returns must vary"),
    ],
)
def test_invalid_factor_inputs_are_rejected(asset_returns, factor_returns, message):
    with pytest.raises(ValueError, match=message):
        calculate_factor_exposure(asset_returns, factor_returns)
