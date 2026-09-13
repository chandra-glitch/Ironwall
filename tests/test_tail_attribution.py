import json
import math

import pytest

from ironwall.tail_attribution import attribute_expected_shortfall

ASSET_RETURNS = {
    "JPM": [-0.10, 0.02, -0.04, 0.01],
    "BAC": [-0.02, -0.01, 0.00, 0.03],
}
WEIGHTS = {"JPM": 0.6, "BAC": 0.4}


def test_expected_shortfall_is_attributed_additively():
    result = attribute_expected_shortfall(ASSET_RETURNS, WEIGHTS, confidence=0.5)

    assert result.return_observations == 4
    assert result.tail_observations == 2
    assert result.cutoff_return == pytest.approx(-0.008)
    assert result.mean_tail_return == pytest.approx(-0.046)
    assert result.signed_tail_loss == pytest.approx(0.046)
    assert result.conditional_value_at_risk == pytest.approx(0.046)
    assert result.component_tail_losses == pytest.approx({"JPM": 0.042, "BAC": 0.004})
    assert sum(result.component_tail_losses.values()) == pytest.approx(result.signed_tail_loss)
    assert result.component_shares is not None
    assert sum(result.component_shares.values()) == pytest.approx(1.0)


def test_negative_component_identifies_tail_hedge():
    result = attribute_expected_shortfall(
        {
            "risk_asset": [-0.10, -0.04, 0.02, 0.03],
            "hedge": [0.05, 0.01, 0.01, 0.02],
        },
        {"risk_asset": 0.8, "hedge": 0.2},
        confidence=0.5,
    )

    assert result.conditional_value_at_risk == pytest.approx(0.05)
    assert result.component_tail_losses == pytest.approx({"risk_asset": 0.056, "hedge": -0.006})
    assert result.component_shares == pytest.approx({"risk_asset": 1.12, "hedge": -0.12})


def test_all_observations_tied_at_cutoff_are_included():
    result = attribute_expected_shortfall(
        {
            "JPM": [-0.10, -0.10, 0.10, 0.20],
            "BAC": [-0.10, -0.10, 0.10, 0.20],
        },
        {"JPM": 0.5, "BAC": 0.5},
        confidence=0.75,
    )

    assert result.cutoff_return == pytest.approx(-0.10)
    assert result.tail_observations == 2
    assert result.conditional_value_at_risk == pytest.approx(0.10)


def test_gain_only_tail_preserves_signed_components_without_allocating_risk():
    result = attribute_expected_shortfall(
        {"JPM": [0.01, 0.02, 0.03], "BAC": [0.02, 0.03, 0.04]},
        {"JPM": 0.5, "BAC": 0.5},
    )

    assert result.mean_tail_return == pytest.approx(0.015)
    assert result.signed_tail_loss == pytest.approx(-0.015)
    assert result.conditional_value_at_risk == 0.0
    assert sum(result.component_tail_losses.values()) == pytest.approx(-0.015)
    assert result.component_shares is None


def test_result_is_strict_json_serializable():
    result = attribute_expected_shortfall(ASSET_RETURNS, WEIGHTS, confidence=0.5)
    payload = json.loads(json.dumps(result.to_dict(), allow_nan=False))

    assert payload["tail_observations"] == 2
    assert payload["component_tail_losses"]["JPM"] == pytest.approx(0.042)
    assert payload["component_shares"]["BAC"] == pytest.approx(0.004 / 0.046)


@pytest.mark.parametrize(
    "asset_returns, weights, confidence, message",
    [
        ({"JPM": [0.01, 0.02]}, {"JPM": 1.0}, 0.95, "at least two assets"),
        (
            {"JPM": [0.01, 0.02], "BAC": [0.01]},
            WEIGHTS,
            0.95,
            "aligned observations",
        ),
        (
            {"JPM": [0.01], "BAC": [0.02]},
            WEIGHTS,
            0.95,
            "at least two return observations",
        ),
        (
            {"JPM": [0.01, "bad"], "BAC": [0.01, 0.02]},
            WEIGHTS,
            0.95,
            "numeric",
        ),
        (
            {"JPM": [0.01, math.inf], "BAC": [0.01, 0.02]},
            WEIGHTS,
            0.95,
            "finite",
        ),
        (
            {"JPM": [0.01, -1.0], "BAC": [0.01, 0.02]},
            WEIGHTS,
            0.95,
            "-100%",
        ),
        (ASSET_RETURNS, {"JPM": 0.5, "BAC": 0.4}, 0.95, "sum to 1.0"),
        (ASSET_RETURNS, WEIGHTS, 0.0, "strictly between"),
        (ASSET_RETURNS, WEIGHTS, 1.0, "strictly between"),
        (ASSET_RETURNS, WEIGHTS, math.nan, "strictly between"),
    ],
)
def test_invalid_inputs_are_rejected(asset_returns, weights, confidence, message):
    with pytest.raises(ValueError, match=message):
        attribute_expected_shortfall(asset_returns, weights, confidence=confidence)
