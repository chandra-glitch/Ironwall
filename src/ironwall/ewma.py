"""Recency-sensitive volatility forecasts using a transparent EWMA model."""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass

from ironwall.metrics import TRADING_DAYS_PER_YEAR

DEFAULT_DECAY_FACTOR = 0.94


@dataclass(frozen=True)
class EWMAVolatilityForecast:
    """One-period EWMA variance and volatility forecast."""

    return_observations: int
    decay_factor: float
    periods_per_year: int
    half_life_periods: float
    latest_return_weight: float
    periodic_variance: float
    periodic_volatility: float
    annualized_volatility: float

    def to_dict(self) -> dict[str, int | float]:
        """Return JSON-ready forecast values without rounding away precision."""

        return {
            "return_observations": self.return_observations,
            "decay_factor": self.decay_factor,
            "periods_per_year": self.periods_per_year,
            "half_life_periods": self.half_life_periods,
            "latest_return_weight": self.latest_return_weight,
            "periodic_variance": self.periodic_variance,
            "periodic_volatility": self.periodic_volatility,
            "annualized_volatility": self.annualized_volatility,
        }


def _validate_returns(returns: Sequence[float]) -> tuple[float, ...]:
    try:
        parsed = tuple(float(value) for value in returns)
    except (TypeError, ValueError) as error:
        raise ValueError("EWMA returns must contain only numeric values.") from error
    if len(parsed) < 2:
        raise ValueError("EWMA volatility requires at least two return observations.")
    if any(not math.isfinite(value) for value in parsed):
        raise ValueError("EWMA returns must contain only finite values.")
    if any(value <= -1 for value in parsed):
        raise ValueError("Returns cannot be less than or equal to -100%.")
    return parsed


def _validate_decay_factor(decay_factor: float) -> float:
    try:
        parsed = float(decay_factor)
    except (TypeError, ValueError) as error:
        raise ValueError("decay_factor must be numeric.") from error
    if not math.isfinite(parsed) or not 0 < parsed < 1:
        raise ValueError("decay_factor must be finite and strictly between 0 and 1.")
    return parsed


def _validate_periods_per_year(periods_per_year: int) -> int:
    if (
        isinstance(periods_per_year, bool)
        or not isinstance(periods_per_year, int)
        or periods_per_year <= 0
    ):
        raise ValueError("periods_per_year must be a positive integer.")
    return periods_per_year


def forecast_ewma_volatility(
    returns: Sequence[float],
    *,
    decay_factor: float = DEFAULT_DECAY_FACTOR,
    periods_per_year: int = TRADING_DAYS_PER_YEAR,
) -> EWMAVolatilityForecast:
    """Forecast next-period volatility from returns ordered oldest to newest."""

    parsed_returns = _validate_returns(returns)
    decay_factor = _validate_decay_factor(decay_factor)
    periods_per_year = _validate_periods_per_year(periods_per_year)

    weighted_squared_returns = 0.0
    total_weight = 0.0
    for period_return in parsed_returns:
        squared_return = period_return * period_return
        if not math.isfinite(squared_return):
            raise ValueError("EWMA returns are too large to square safely.")
        weighted_squared_returns = decay_factor * weighted_squared_returns + squared_return
        total_weight = decay_factor * total_weight + 1.0

    variance = weighted_squared_returns / total_weight
    if not math.isfinite(variance):
        raise ValueError("EWMA variance could not be represented as a finite number.")
    volatility = math.sqrt(variance)
    try:
        annualized_volatility = volatility * math.sqrt(periods_per_year)
    except OverflowError as error:
        raise ValueError("periods_per_year is too large to annualize safely.") from error
    if not math.isfinite(annualized_volatility):
        raise ValueError("Annualized EWMA volatility must be finite.")

    return EWMAVolatilityForecast(
        return_observations=len(parsed_returns),
        decay_factor=decay_factor,
        periods_per_year=periods_per_year,
        half_life_periods=math.log(0.5) / math.log(decay_factor),
        latest_return_weight=1.0 / total_weight,
        periodic_variance=variance,
        periodic_volatility=volatility,
        annualized_volatility=annualized_volatility,
    )
