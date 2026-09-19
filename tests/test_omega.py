import json

import pytest

from ironwall.omega import analyze_omega_ratio


def test_omega_ratio_compares_all_gains_and_shortfalls():
    result = analyze_omega_ratio([-0.03, -0.01, 0.0, 0.02, 0.06])

    assert result.return_observations == 5
    assert result.threshold == 0.0
    assert result.gain_observations == 2
    assert result.shortfall_observations == 2
    assert result.at_threshold_observations == 1
    assert result.upside_potential == pytest.approx(0.016)
    assert result.downside_shortfall == pytest.approx(0.008)
    assert result.omega_ratio == pytest.approx(2.0)
    assert result.ratio_status == "finite"


def test_nonzero_threshold_changes_gain_and_shortfall_magnitudes():
    result = analyze_omega_ratio(
        [-0.03, -0.01, 0.0, 0.02, 0.06],
        threshold=0.01,
    )

    assert result.gain_observations == 2
    assert result.shortfall_observations == 3
    assert result.at_threshold_observations == 0
    assert result.upside_potential == pytest.approx(0.012)
    assert result.downside_shortfall == pytest.approx(0.014)
    assert result.omega_ratio == pytest.approx(6 / 7)


def test_no_shortfalls_produces_json_safe_unbounded_status():
    result = analyze_omega_ratio([0.01, 0.02, 0.03])

    assert result.downside_shortfall == 0.0
    assert result.omega_ratio is None
    assert result.ratio_status == "unbounded"


def test_returns_equal_to_threshold_produce_undefined_status():
    result = analyze_omega_ratio([0.01, 0.01], threshold=0.01)

    assert result.upside_potential == 0.0
    assert result.downside_shortfall == 0.0
    assert result.omega_ratio is None
    assert result.ratio_status == "undefined"


def test_no_gains_produces_zero_finite_ratio():
    result = analyze_omega_ratio([-0.03, -0.01])

    assert result.omega_ratio == 0.0
    assert result.ratio_status == "finite"


def test_result_is_strict_json_ready():
    payload = analyze_omega_ratio([-0.02, 0.01, 0.03]).to_dict()

    encoded = json.dumps(payload, allow_nan=False, sort_keys=True)

    assert payload["return_observations"] == 3
    assert payload["ratio_status"] == "finite"
    assert '"omega_ratio"' in encoded


@pytest.mark.parametrize(
    "returns",
    [
        [],
        [0.01],
        [0.01, "invalid"],
        [0.01, float("nan")],
        [0.01, float("inf")],
        [0.01, -1.0],
    ],
)
def test_invalid_returns_are_rejected(returns):
    with pytest.raises(ValueError, match="returns|at least"):
        analyze_omega_ratio(returns)


@pytest.mark.parametrize("threshold", [-1.0, float("nan"), float("inf"), "invalid"])
def test_invalid_thresholds_are_rejected(threshold):
    with pytest.raises(ValueError, match="threshold"):
        analyze_omega_ratio([-0.01, 0.01], threshold=threshold)


def test_overflowing_deviations_are_rejected():
    with pytest.raises(ValueError, match="numeric range"):
        analyze_omega_ratio([1e308, 1e308])
