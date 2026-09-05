"""Reproducible Gaussian log-return Monte Carlo risk estimates."""

from __future__ import annotations

import math
import random
from collections.abc import Sequence
from dataclasses import dataclass

__all__ = ["MonteCarloRiskEstimate", "estimate_monte_carlo_var"]


@dataclass(frozen=True)
class MonteCarloRiskEstimate:
    """Loss estimates and assumptions for one Monte Carlo run."""

    confidence: float
    simulations: int
    horizon_periods: int
    seed: int | None
    value_at_risk: float
    conditional_value_at_risk: float
    mean_terminal_return: float

    def to_dict(self) -> dict[str, int | float | None]:
        """Return a JSON-ready representation without rounding precision."""

        return {
            "confidence": self.confidence,
            "simulations": self.simulations,
            "horizon_periods": self.horizon_periods,
            "seed": self.seed,
            "value_at_risk": self.value_at_risk,
            "conditional_value_at_risk": self.conditional_value_at_risk,
            "mean_terminal_return": self.mean_terminal_return,
        }


def _validated_returns(returns: Sequence[float]) -> tuple[float, ...]:
    try:
        parsed = tuple(float(value) for value in returns)
    except (TypeError, ValueError) as exc:
        raise ValueError("Monte Carlo returns must contain only numeric values.") from exc
    if len(parsed) < 2:
        raise ValueError("Monte Carlo estimation requires at least two return observations.")
    if any(not math.isfinite(value) for value in parsed):
        raise ValueError("Monte Carlo returns must contain only finite values.")
    if any(value <= -1.0 for value in parsed):
        raise ValueError("Monte Carlo simple returns must be greater than -100%.")
    return parsed


def _validated_confidence(confidence: float) -> float:
    try:
        parsed = float(confidence)
    except (TypeError, ValueError) as exc:
        raise ValueError("confidence must be numeric.") from exc
    if not math.isfinite(parsed) or not 0.0 < parsed < 1.0:
        raise ValueError("confidence must be strictly between 0 and 1.")
    return parsed


def _validated_integer(value: int, *, name: str, minimum: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
        raise ValueError(f"{name} must be an integer of at least {minimum}.")
    return value


def _interpolated_quantile(ordered_values: Sequence[float], probability: float) -> float:
    position = (len(ordered_values) - 1) * probability
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return ordered_values[lower]
    weight = position - lower
    return ordered_values[lower] * (1.0 - weight) + ordered_values[upper] * weight


def estimate_monte_carlo_var(
    returns: Sequence[float],
    *,
    confidence: float = 0.95,
    simulations: int = 10_000,
    horizon_periods: int = 1,
    seed: int | None = 0,
) -> MonteCarloRiskEstimate:
    """Estimate VaR and CVaR from simulated terminal simple returns.

    Historical simple returns are converted to log returns and fitted with a
    Gaussian distribution. Independent log returns are aggregated over the
    requested horizon before conversion back to terminal simple returns.
    """

    parsed_returns = _validated_returns(returns)
    parsed_confidence = _validated_confidence(confidence)
    parsed_simulations = _validated_integer(simulations, name="simulations", minimum=100)
    parsed_horizon = _validated_integer(horizon_periods, name="horizon_periods", minimum=1)
    if seed is not None and (isinstance(seed, bool) or not isinstance(seed, int)):
        raise ValueError("seed must be an integer or None.")

    log_returns = tuple(math.log1p(value) for value in parsed_returns)
    log_mean = math.fsum(log_returns) / len(log_returns)
    log_variance = math.fsum((value - log_mean) ** 2 for value in log_returns) / (
        len(log_returns) - 1
    )
    try:
        terminal_log_mean = parsed_horizon * log_mean
        terminal_log_volatility = math.sqrt(parsed_horizon * log_variance)
    except OverflowError as exc:
        raise ValueError("horizon_periods is too large for a stable simulation.") from exc
    if not math.isfinite(terminal_log_mean) or not math.isfinite(terminal_log_volatility):
        raise ValueError("Historical returns and horizon produce non-finite simulation inputs.")

    generator = random.Random(seed)
    try:
        terminal_returns = tuple(
            math.expm1(generator.gauss(terminal_log_mean, terminal_log_volatility))
            for _ in range(parsed_simulations)
        )
    except OverflowError as exc:
        raise ValueError("Simulated terminal returns overflowed; reduce the horizon.") from exc

    ordered_returns = tuple(sorted(terminal_returns))
    cutoff = _interpolated_quantile(ordered_returns, 1.0 - parsed_confidence)
    tail_returns = tuple(value for value in ordered_returns if value <= cutoff)
    value_at_risk = max(0.0, -cutoff)
    conditional_value_at_risk = max(0.0, -math.fsum(tail_returns) / len(tail_returns))
    return MonteCarloRiskEstimate(
        confidence=parsed_confidence,
        simulations=parsed_simulations,
        horizon_periods=parsed_horizon,
        seed=seed,
        value_at_risk=value_at_risk,
        conditional_value_at_risk=conditional_value_at_risk,
        mean_terminal_return=math.fsum(terminal_returns) / parsed_simulations,
    )
