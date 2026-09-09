"""Benchmark-relative tracking error and information ratio analysis."""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass

from ironwall.metrics import TRADING_DAYS_PER_YEAR

__all__ = ["ActiveRiskMetrics", "analyze_active_risk"]


@dataclass(frozen=True)
class ActiveRiskMetrics:
    """Benchmark-relative statistics for aligned periodic returns."""

    return_observations: int
    mean_active_return: float
    annualized_mean_active_return: float
    tracking_error: float
    annualized_tracking_error: float
    information_ratio: float | None

    def to_dict(self) -> dict[str, float | int | None]:
        """Return a JSON-serializable representation of the metrics."""

        return {
            "return_observations": self.return_observations,
            "mean_active_return": self.mean_active_return,
            "annualized_mean_active_return": self.annualized_mean_active_return,
            "tracking_error": self.tracking_error,
            "annualized_tracking_error": self.annualized_tracking_error,
            "information_ratio": self.information_ratio,
        }


def analyze_active_risk(
    portfolio_returns: Sequence[float],
    benchmark_returns: Sequence[float],
    *,
    periods_per_year: int = TRADING_DAYS_PER_YEAR,
) -> ActiveRiskMetrics:
    """Measure active return variability and benchmark-relative efficiency.

    Returns are aligned by position and must contain at least two observations.
    Tracking error is the sample standard deviation of portfolio return minus
    benchmark return. The information ratio is ``None`` when tracking error is
    zero, avoiding a non-finite result.
    """

    portfolio = tuple(float(value) for value in portfolio_returns)
    benchmark = tuple(float(value) for value in benchmark_returns)
    if len(portfolio) != len(benchmark):
        raise ValueError("Portfolio and benchmark returns must have the same length.")
    if len(portfolio) < 2:
        raise ValueError("Active risk analysis requires at least two aligned observations.")
    if any(not math.isfinite(value) for value in portfolio) or any(
        not math.isfinite(value) for value in benchmark
    ):
        raise ValueError("Portfolio and benchmark returns must contain only finite values.")
    if any(value <= -1.0 for value in portfolio) or any(value <= -1.0 for value in benchmark):
        raise ValueError("Portfolio and benchmark returns must be greater than -100%.")
    if (
        isinstance(periods_per_year, bool)
        or not isinstance(periods_per_year, int)
        or periods_per_year <= 0
    ):
        raise ValueError("periods_per_year must be a positive integer.")

    active_returns = tuple(
        portfolio_return - benchmark_return
        for portfolio_return, benchmark_return in zip(portfolio, benchmark, strict=True)
    )
    mean_active_return = math.fsum(active_returns) / len(active_returns)
    tracking_error = math.sqrt(
        math.fsum((value - mean_active_return) ** 2 for value in active_returns)
        / (len(active_returns) - 1)
    )
    annualization_factor = math.sqrt(periods_per_year)
    information_ratio = None
    if tracking_error > 0.0:
        information_ratio = mean_active_return / tracking_error * annualization_factor

    return ActiveRiskMetrics(
        return_observations=len(active_returns),
        mean_active_return=mean_active_return,
        annualized_mean_active_return=mean_active_return * periods_per_year,
        tracking_error=tracking_error,
        annualized_tracking_error=tracking_error * annualization_factor,
        information_ratio=information_ratio,
    )
