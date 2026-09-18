"""Reproducible bootstrap intervals for historical tail-risk estimates."""

from __future__ import annotations

import math
import random
from collections.abc import Sequence
from dataclasses import dataclass

from ironwall.metrics import calculate_cvar, calculate_var


@dataclass(frozen=True)
class BootstrapInterval:
    """A point estimate and percentile-bootstrap confidence interval."""

    estimate: float
    lower_bound: float
    upper_bound: float

    def to_dict(self) -> dict[str, float]:
        """Return JSON-ready values without discarding precision."""

        return {
            "estimate": self.estimate,
            "lower_bound": self.lower_bound,
            "upper_bound": self.upper_bound,
        }


@dataclass(frozen=True)
class BootstrapRiskResult:
    """Bootstrap uncertainty for historical VaR and Expected Shortfall."""

    return_observations: int
    risk_confidence: float
    interval_confidence: float
    resamples: int
    seed: int
    value_at_risk: BootstrapInterval
    conditional_value_at_risk: BootstrapInterval

    def to_dict(self) -> dict[str, object]:
        """Return a nested, JSON-ready representation of the result."""

        return {
            "return_observations": self.return_observations,
            "risk_confidence": self.risk_confidence,
            "interval_confidence": self.interval_confidence,
            "resamples": self.resamples,
            "seed": self.seed,
            "value_at_risk": self.value_at_risk.to_dict(),
            "conditional_value_at_risk": self.conditional_value_at_risk.to_dict(),
        }


def _validate_probability(value: float, *, name: str) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError) as error:
        raise ValueError(f"{name} must be numeric.") from error
    if not math.isfinite(parsed) or not 0 < parsed < 1:
        raise ValueError(f"{name} must be strictly between 0 and 1.")
    return parsed


def _validate_returns(returns: Sequence[float]) -> tuple[float, ...]:
    try:
        parsed = tuple(float(value) for value in returns)
    except (TypeError, ValueError) as error:
        raise ValueError("returns must contain only numeric values.") from error
    if len(parsed) < 2:
        raise ValueError("bootstrap risk analysis requires at least two returns.")
    if any(not math.isfinite(value) for value in parsed):
        raise ValueError("returns must contain only finite values.")
    if any(value <= -1 for value in parsed):
        raise ValueError("returns cannot be less than or equal to -100%.")
    return parsed


def _quantile(values: Sequence[float], probability: float) -> float:
    ordered = sorted(values)
    position = (len(ordered) - 1) * probability
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return ordered[lower]
    upper_weight = position - lower
    return ordered[lower] * (1 - upper_weight) + ordered[upper] * upper_weight


def _interval(
    estimates: Sequence[float],
    *,
    point_estimate: float,
    interval_confidence: float,
) -> BootstrapInterval:
    tail_probability = (1 - interval_confidence) / 2
    return BootstrapInterval(
        estimate=point_estimate,
        lower_bound=_quantile(estimates, tail_probability),
        upper_bound=_quantile(estimates, 1 - tail_probability),
    )


def bootstrap_historical_risk(
    returns: Sequence[float],
    *,
    confidence: float = 0.95,
    interval_confidence: float = 0.95,
    resamples: int = 10_000,
    seed: int = 0,
) -> BootstrapRiskResult:
    """Estimate percentile-bootstrap intervals for historical VaR and CVaR.

    Each bootstrap sample contains the same number of observations as ``returns`` and is
    drawn with replacement. A local random-number generator keeps seeded results reproducible
    without modifying Python's global random state.
    """

    parsed = _validate_returns(returns)
    confidence = _validate_probability(confidence, name="confidence")
    interval_confidence = _validate_probability(
        interval_confidence,
        name="interval_confidence",
    )
    if isinstance(resamples, bool) or not isinstance(resamples, int) or resamples < 100:
        raise ValueError("resamples must be an integer greater than or equal to 100.")
    if isinstance(seed, bool) or not isinstance(seed, int):
        raise ValueError("seed must be an integer.")

    generator = random.Random(seed)
    var_estimates: list[float] = []
    cvar_estimates: list[float] = []
    for _ in range(resamples):
        sample = generator.choices(parsed, k=len(parsed))
        var_estimates.append(calculate_var(sample, confidence))
        cvar_estimates.append(calculate_cvar(sample, confidence))

    return BootstrapRiskResult(
        return_observations=len(parsed),
        risk_confidence=confidence,
        interval_confidence=interval_confidence,
        resamples=resamples,
        seed=seed,
        value_at_risk=_interval(
            var_estimates,
            point_estimate=calculate_var(parsed, confidence),
            interval_confidence=interval_confidence,
        ),
        conditional_value_at_risk=_interval(
            cvar_estimates,
            point_estimate=calculate_cvar(parsed, confidence),
            interval_confidence=interval_confidence,
        ),
    )
