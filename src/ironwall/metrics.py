"""Transparent historical risk metrics with explicit validation."""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass

TRADING_DAYS_PER_YEAR = 252


@dataclass(frozen=True)
class RiskMetrics:
    """Risk measurements using positive numbers to represent losses."""

    return_observations: int
    confidence: float
    total_return: float
    mean_daily_return: float
    annualized_volatility: float
    value_at_risk: float
    conditional_value_at_risk: float
    maximum_drawdown: float
    sharpe_ratio: float

    def to_dict(self) -> dict[str, int | float]:
        """Return JSON-ready metric values without rounding away precision."""

        return {
            "return_observations": self.return_observations,
            "confidence": self.confidence,
            "total_return": self.total_return,
            "mean_daily_return": self.mean_daily_return,
            "annualized_volatility": self.annualized_volatility,
            "value_at_risk": self.value_at_risk,
            "conditional_value_at_risk": self.conditional_value_at_risk,
            "maximum_drawdown": self.maximum_drawdown,
            "sharpe_ratio": self.sharpe_ratio,
        }


def _validated_values(
    values: Sequence[float],
    *,
    name: str,
    minimum_length: int = 1,
    strictly_positive: bool = False,
) -> tuple[float, ...]:
    parsed = tuple(float(value) for value in values)
    if len(parsed) < minimum_length:
        raise ValueError(f"{name} requires at least {minimum_length} observations.")
    for value in parsed:
        if not math.isfinite(value):
            raise ValueError(f"{name} must contain only finite values.")
        if strictly_positive and value <= 0:
            raise ValueError(f"{name} must contain only positive values.")
    return parsed


def _validate_confidence(confidence: float) -> float:
    confidence = float(confidence)
    if not math.isfinite(confidence) or not 0 < confidence < 1:
        raise ValueError("confidence must be strictly between 0 and 1.")
    return confidence


def calculate_mean(values: Sequence[float]) -> float:
    parsed = _validated_values(values, name="mean")
    return sum(parsed) / len(parsed)


def calculate_returns(prices: Sequence[float]) -> tuple[float, ...]:
    parsed = _validated_values(
        prices,
        name="price series",
        minimum_length=2,
        strictly_positive=True,
    )
    return tuple(
        (current - previous) / previous
        for previous, current in zip(parsed, parsed[1:], strict=False)
    )


def calculate_volatility(returns: Sequence[float]) -> float:
    """Calculate sample standard deviation of periodic returns."""

    parsed = _validated_values(returns, name="volatility", minimum_length=2)
    mean_return = calculate_mean(parsed)
    variance = sum((value - mean_return) ** 2 for value in parsed) / (len(parsed) - 1)
    return math.sqrt(variance)


def _quantile(values: Sequence[float], probability: float) -> float:
    if not 0 <= probability <= 1:
        raise ValueError("quantile probability must be between 0 and 1.")
    ordered = sorted(_validated_values(values, name="quantile"))
    position = (len(ordered) - 1) * probability
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return ordered[lower]
    weight = position - lower
    return ordered[lower] * (1 - weight) + ordered[upper] * weight


def calculate_var(returns: Sequence[float], confidence: float = 0.95) -> float:
    """Historical Value at Risk as a positive loss magnitude."""

    confidence = _validate_confidence(confidence)
    loss_quantile = _quantile(returns, 1 - confidence)
    return max(0.0, -loss_quantile)


def calculate_cvar(returns: Sequence[float], confidence: float = 0.95) -> float:
    """Historical expected shortfall as a positive loss magnitude."""

    confidence = _validate_confidence(confidence)
    parsed = _validated_values(returns, name="CVaR returns")
    cutoff = _quantile(parsed, 1 - confidence)
    tail = tuple(value for value in parsed if value <= cutoff)
    return max(0.0, -calculate_mean(tail))


def calculate_max_drawdown(prices: Sequence[float]) -> float:
    """Maximum peak-to-trough decline as a positive loss magnitude."""

    parsed = _validated_values(
        prices,
        name="drawdown price series",
        strictly_positive=True,
    )
    peak = parsed[0]
    maximum = 0.0
    for price in parsed:
        peak = max(peak, price)
        maximum = max(maximum, (peak - price) / peak)
    return maximum


def build_wealth_index(returns: Sequence[float], initial_value: float = 100.0) -> tuple[float, ...]:
    parsed = _validated_values(returns, name="wealth-index returns")
    if not math.isfinite(initial_value) or initial_value <= 0:
        raise ValueError("initial_value must be a positive finite number.")
    wealth = [float(initial_value)]
    for period_return in parsed:
        if period_return <= -1:
            raise ValueError("returns cannot be less than or equal to -100%.")
        wealth.append(wealth[-1] * (1 + period_return))
    return tuple(wealth)


def analyze_returns(
    returns: Sequence[float],
    *,
    confidence: float = 0.95,
    periods_per_year: int = TRADING_DAYS_PER_YEAR,
    annual_risk_free_rate: float = 0.0,
    wealth_index: Sequence[float] | None = None,
) -> RiskMetrics:
    """Calculate a complete risk snapshot from aligned periodic returns."""

    parsed = _validated_values(returns, name="risk analysis", minimum_length=2)
    if any(value <= -1 for value in parsed):
        raise ValueError("returns cannot be less than or equal to -100%.")
    confidence = _validate_confidence(confidence)
    if periods_per_year <= 0:
        raise ValueError("periods_per_year must be positive.")
    if annual_risk_free_rate <= -1 or not math.isfinite(annual_risk_free_rate):
        raise ValueError("annual_risk_free_rate must be finite and greater than -100%.")

    daily_volatility = calculate_volatility(parsed)
    daily_risk_free_rate = (1 + annual_risk_free_rate) ** (1 / periods_per_year) - 1
    sharpe_ratio = 0.0
    if daily_volatility > 0:
        sharpe_ratio = (
            (calculate_mean(parsed) - daily_risk_free_rate)
            / daily_volatility
            * math.sqrt(periods_per_year)
        )

    curve = (
        _validated_values(
            wealth_index,
            name="wealth index",
            minimum_length=2,
            strictly_positive=True,
        )
        if wealth_index is not None
        else build_wealth_index(parsed)
    )
    if len(curve) != len(parsed) + 1:
        raise ValueError("wealth_index must contain exactly one more value than returns.")

    return RiskMetrics(
        return_observations=len(parsed),
        confidence=confidence,
        total_return=math.prod(1 + value for value in parsed) - 1,
        mean_daily_return=calculate_mean(parsed),
        annualized_volatility=daily_volatility * math.sqrt(periods_per_year),
        value_at_risk=calculate_var(parsed, confidence),
        conditional_value_at_risk=calculate_cvar(parsed, confidence),
        maximum_drawdown=calculate_max_drawdown(curve),
        sharpe_ratio=sharpe_ratio,
    )


def analyze_prices(
    prices: Sequence[float],
    *,
    confidence: float = 0.95,
    periods_per_year: int = TRADING_DAYS_PER_YEAR,
    annual_risk_free_rate: float = 0.0,
) -> RiskMetrics:
    parsed = _validated_values(
        prices,
        name="price analysis",
        minimum_length=3,
        strictly_positive=True,
    )
    return analyze_returns(
        calculate_returns(parsed),
        confidence=confidence,
        periods_per_year=periods_per_year,
        annual_risk_free_rate=annual_risk_free_rate,
        wealth_index=parsed,
    )
