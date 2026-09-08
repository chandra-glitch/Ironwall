"""Target downside deviation and Sortino ratio analysis."""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass

from ironwall.metrics import TRADING_DAYS_PER_YEAR

__all__ = ["DownsideRiskMetrics", "analyze_downside_risk"]


@dataclass(frozen=True)
class DownsideRiskMetrics:
    """Downside-only risk statistics for periodic returns."""

    return_observations: int
    downside_observations: int
    target_return: float
    downside_deviation: float
    annualized_downside_deviation: float
    sortino_ratio: float | None

    def to_dict(self) -> dict[str, float | int | None]:
        """Return a JSON-serializable representation of the metrics."""

        return {
            "return_observations": self.return_observations,
            "downside_observations": self.downside_observations,
            "target_return": self.target_return,
            "downside_deviation": self.downside_deviation,
            "annualized_downside_deviation": self.annualized_downside_deviation,
            "sortino_ratio": self.sortino_ratio,
        }


def analyze_downside_risk(
    returns: Sequence[float],
    *,
    target_return: float = 0.0,
    periods_per_year: int = TRADING_DAYS_PER_YEAR,
) -> DownsideRiskMetrics:
    """Measure shortfall volatility and risk-adjusted return below a target.

    ``target_return`` is a per-period minimum acceptable return. Downside
    deviation uses every supplied observation in its denominator. The Sortino
    ratio is returned as ``None`` when downside deviation is zero, avoiding a
    non-finite result.
    """

    parsed_returns = tuple(float(value) for value in returns)
    if len(parsed_returns) < 2:
        raise ValueError("Downside risk analysis requires at least two return observations.")
    if any(not math.isfinite(value) for value in parsed_returns):
        raise ValueError("Downside risk returns must contain only finite values.")
    if any(value <= -1.0 for value in parsed_returns):
        raise ValueError("Downside risk returns must be greater than -100%.")

    target_return = float(target_return)
    if not math.isfinite(target_return) or target_return <= -1.0:
        raise ValueError("target_return must be finite and greater than -100%.")
    if (
        isinstance(periods_per_year, bool)
        or not isinstance(periods_per_year, int)
        or periods_per_year <= 0
    ):
        raise ValueError("periods_per_year must be a positive integer.")

    shortfalls = tuple(min(value - target_return, 0.0) for value in parsed_returns)
    downside_deviation = math.sqrt(
        math.fsum(shortfall * shortfall for shortfall in shortfalls) / len(parsed_returns)
    )
    annualization_factor = math.sqrt(periods_per_year)
    mean_return = math.fsum(parsed_returns) / len(parsed_returns)
    sortino_ratio = None
    if downside_deviation > 0.0:
        sortino_ratio = (mean_return - target_return) / downside_deviation * annualization_factor

    return DownsideRiskMetrics(
        return_observations=len(parsed_returns),
        downside_observations=sum(value < target_return for value in parsed_returns),
        target_return=target_return,
        downside_deviation=downside_deviation,
        annualized_downside_deviation=downside_deviation * annualization_factor,
        sortino_ratio=sortino_ratio,
    )
