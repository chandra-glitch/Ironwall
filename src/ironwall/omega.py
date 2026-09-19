"""Target-aware Omega performance analysis for empirical returns."""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Literal

OmegaStatus = Literal["finite", "unbounded", "undefined"]


@dataclass(frozen=True)
class OmegaAnalysis:
    """Empirical gains and shortfalls around a selected return threshold."""

    return_observations: int
    threshold: float
    gain_observations: int
    shortfall_observations: int
    at_threshold_observations: int
    upside_potential: float
    downside_shortfall: float
    omega_ratio: float | None
    ratio_status: OmegaStatus

    def to_dict(self) -> dict[str, int | float | str | None]:
        """Return strict-JSON-ready values without rounding away precision."""

        return {
            "return_observations": self.return_observations,
            "threshold": self.threshold,
            "gain_observations": self.gain_observations,
            "shortfall_observations": self.shortfall_observations,
            "at_threshold_observations": self.at_threshold_observations,
            "upside_potential": self.upside_potential,
            "downside_shortfall": self.downside_shortfall,
            "omega_ratio": self.omega_ratio,
            "ratio_status": self.ratio_status,
        }


def _validated_returns(returns: Sequence[float]) -> tuple[float, ...]:
    try:
        parsed = tuple(float(value) for value in returns)
    except (TypeError, ValueError) as error:
        raise ValueError("returns must contain only numeric values.") from error
    if len(parsed) < 2:
        raise ValueError("Omega analysis requires at least two returns.")
    if any(not math.isfinite(value) for value in parsed):
        raise ValueError("returns must contain only finite values.")
    if any(value <= -1 for value in parsed):
        raise ValueError("returns cannot be less than or equal to -100%.")
    return parsed


def _validated_threshold(threshold: float) -> float:
    try:
        parsed = float(threshold)
    except (TypeError, ValueError) as error:
        raise ValueError("threshold must be numeric.") from error
    if not math.isfinite(parsed) or parsed <= -1:
        raise ValueError("threshold must be finite and greater than -100%.")
    return parsed


def _mean_deviation(values: Sequence[float], *, observations: int) -> float:
    try:
        result = math.fsum(values) / observations
    except OverflowError as error:
        raise ValueError("return deviations exceed the finite numeric range.") from error
    if not math.isfinite(result):
        raise ValueError("return deviations exceed the finite numeric range.")
    return result


def analyze_omega_ratio(
    returns: Sequence[float],
    *,
    threshold: float = 0.0,
) -> OmegaAnalysis:
    """Calculate the empirical Omega ratio around ``threshold``.

    The numerator is the mean positive return deviation above the threshold. The denominator
    is the mean shortfall below it. Observations exactly at the threshold contribute zero to
    both sides.
    """

    parsed = _validated_returns(returns)
    threshold = _validated_threshold(threshold)
    upside_deviations = tuple(max(value - threshold, 0.0) for value in parsed)
    downside_deviations = tuple(max(threshold - value, 0.0) for value in parsed)
    upside_potential = _mean_deviation(upside_deviations, observations=len(parsed))
    downside_shortfall = _mean_deviation(downside_deviations, observations=len(parsed))

    omega_ratio: float | None
    ratio_status: OmegaStatus
    if downside_shortfall == 0.0:
        omega_ratio = None
        ratio_status = "unbounded" if upside_potential > 0.0 else "undefined"
    else:
        omega_ratio = upside_potential / downside_shortfall
        if not math.isfinite(omega_ratio):
            raise ValueError("Omega ratio exceeds the finite numeric range.")
        ratio_status = "finite"

    gain_observations = sum(value > threshold for value in parsed)
    shortfall_observations = sum(value < threshold for value in parsed)
    return OmegaAnalysis(
        return_observations=len(parsed),
        threshold=threshold,
        gain_observations=gain_observations,
        shortfall_observations=shortfall_observations,
        at_threshold_observations=len(parsed) - gain_observations - shortfall_observations,
        upside_potential=upside_potential,
        downside_shortfall=downside_shortfall,
        omega_ratio=omega_ratio,
        ratio_status=ratio_status,
    )
