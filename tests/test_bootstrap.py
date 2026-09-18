import json
import random

import pytest

from ironwall.bootstrap import bootstrap_historical_risk
from ironwall.metrics import calculate_cvar, calculate_var

RETURNS = (-0.08, -0.04, -0.02, -0.01, 0.0, 0.01, 0.02, 0.03)


def test_point_estimates_match_historical_risk_metrics():
    result = bootstrap_historical_risk(
        RETURNS,
        confidence=0.80,
        interval_confidence=0.90,
        resamples=400,
        seed=17,
    )

    assert result.value_at_risk.estimate == pytest.approx(calculate_var(RETURNS, 0.80))
    assert result.conditional_value_at_risk.estimate == pytest.approx(calculate_cvar(RETURNS, 0.80))
    assert result.value_at_risk.lower_bound <= result.value_at_risk.upper_bound
    assert (
        result.conditional_value_at_risk.lower_bound <= result.conditional_value_at_risk.upper_bound
    )


def test_seeded_results_are_reproducible_without_changing_global_random_state():
    random.seed(1729)
    expected_next_value = random.random()
    random.seed(1729)

    first = bootstrap_historical_risk(RETURNS, resamples=200, seed=42)
    observed_next_value = random.random()
    second = bootstrap_historical_risk(RETURNS, resamples=200, seed=42)

    assert first == second
    assert observed_next_value == expected_next_value


def test_constant_losses_produce_collapsed_intervals():
    result = bootstrap_historical_risk(
        [-0.02] * 6,
        confidence=0.95,
        interval_confidence=0.95,
        resamples=100,
        seed=1,
    )

    assert result.value_at_risk.estimate == pytest.approx(0.02)
    assert result.value_at_risk.lower_bound == pytest.approx(0.02)
    assert result.value_at_risk.upper_bound == pytest.approx(0.02)
    assert result.conditional_value_at_risk.estimate == pytest.approx(0.02)
    assert result.conditional_value_at_risk.lower_bound == pytest.approx(0.02)
    assert result.conditional_value_at_risk.upper_bound == pytest.approx(0.02)


def test_result_is_strict_json_ready():
    result = bootstrap_historical_risk(RETURNS, resamples=100, seed=9)
    payload = result.to_dict()

    encoded = json.dumps(payload, allow_nan=False, sort_keys=True)

    assert payload["return_observations"] == len(RETURNS)
    assert payload["risk_confidence"] == 0.95
    assert payload["interval_confidence"] == 0.95
    assert payload["resamples"] == 100
    assert payload["seed"] == 9
    assert '"conditional_value_at_risk"' in encoded


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
        bootstrap_historical_risk(returns, resamples=100)


@pytest.mark.parametrize("name", ["confidence", "interval_confidence"])
@pytest.mark.parametrize("value", [0, 1, -0.1, 1.1, float("nan"), "invalid"])
def test_invalid_probabilities_are_rejected(name, value):
    arguments = {name: value, "resamples": 100}

    with pytest.raises(ValueError, match=name):
        bootstrap_historical_risk(RETURNS, **arguments)


@pytest.mark.parametrize("resamples", [99, 100.5, True])
def test_invalid_resample_counts_are_rejected(resamples):
    with pytest.raises(ValueError, match="resamples"):
        bootstrap_historical_risk(RETURNS, resamples=resamples)


@pytest.mark.parametrize("seed", [1.5, "7", True])
def test_invalid_seeds_are_rejected(seed):
    with pytest.raises(ValueError, match="seed"):
        bootstrap_historical_risk(RETURNS, resamples=100, seed=seed)
