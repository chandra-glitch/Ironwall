"""Long-only portfolio aggregation and volatility risk attribution."""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from ironwall.metrics import (
    RiskMetrics,
    analyze_returns,
    build_wealth_index,
    calculate_mean,
    calculate_returns,
)


@dataclass(frozen=True)
class PortfolioRiskAnalysis:
    """Portfolio metrics plus normalized weights and volatility contributions."""

    metrics: RiskMetrics
    weights: dict[str, float]
    risk_contributions: dict[str, float]


def validate_weights(
    weights: Mapping[str, float],
    assets: Sequence[str],
) -> dict[str, float]:
    asset_set = set(assets)
    if len(asset_set) < 2:
        raise ValueError("Portfolio analysis requires at least two assets.")
    missing = asset_set - set(weights)
    extra = set(weights) - asset_set
    if missing or extra:
        details = []
        if missing:
            details.append(f"missing weights for {', '.join(sorted(missing))}")
        if extra:
            details.append(f"unknown assets {', '.join(sorted(extra))}")
        raise ValueError("Invalid portfolio weights: " + "; ".join(details) + ".")

    parsed = {asset: float(weights[asset]) for asset in assets}
    if any(not math.isfinite(value) or value < 0 for value in parsed.values()):
        raise ValueError("Portfolio weights must be finite and non-negative.")
    if not math.isclose(sum(parsed.values()), 1.0, rel_tol=0.0, abs_tol=1e-6):
        raise ValueError("Portfolio weights must sum to 1.0.")
    return parsed


def calculate_asset_returns(
    asset_prices: Mapping[str, Sequence[float]],
) -> dict[str, tuple[float, ...]]:
    if len(asset_prices) < 2:
        raise ValueError("Portfolio analysis requires at least two assets.")
    returns = {asset: calculate_returns(prices) for asset, prices in asset_prices.items()}
    lengths = {len(values) for values in returns.values()}
    if len(lengths) != 1:
        raise ValueError("All portfolio assets must have aligned price observations.")
    return returns


def calculate_portfolio_returns(
    asset_returns: Mapping[str, Sequence[float]],
    weights: Mapping[str, float],
) -> tuple[float, ...]:
    parsed_weights = validate_weights(weights, tuple(asset_returns))
    lengths = {len(values) for values in asset_returns.values()}
    if len(lengths) != 1 or not lengths or next(iter(lengths)) < 2:
        raise ValueError("Asset return series must be aligned and contain at least two rows.")
    observations = next(iter(lengths))
    return tuple(
        sum(parsed_weights[asset] * float(asset_returns[asset][index]) for asset in asset_returns)
        for index in range(observations)
    )


def calculate_risk_contributions(
    asset_returns: Mapping[str, Sequence[float]],
    weights: Mapping[str, float],
) -> dict[str, float]:
    """Calculate each asset's Euler contribution to portfolio variance."""

    assets = tuple(asset_returns)
    parsed_weights = validate_weights(weights, assets)
    lengths = {len(values) for values in asset_returns.values()}
    if len(lengths) != 1 or not lengths or next(iter(lengths)) < 2:
        raise ValueError("Risk contributions require aligned return series.")
    observations = next(iter(lengths))
    means = {asset: calculate_mean(asset_returns[asset]) for asset in assets}

    covariance: dict[tuple[str, str], float] = {}
    for left in assets:
        for right in assets:
            covariance[(left, right)] = sum(
                (float(asset_returns[left][index]) - means[left])
                * (float(asset_returns[right][index]) - means[right])
                for index in range(observations)
            ) / (observations - 1)

    covariance_times_weights = {
        asset: sum(covariance[(asset, other)] * parsed_weights[other] for other in assets)
        for asset in assets
    }
    portfolio_variance = sum(
        parsed_weights[asset] * covariance_times_weights[asset] for asset in assets
    )
    if portfolio_variance <= 1e-20:
        return {asset: 0.0 for asset in assets}
    return {
        asset: parsed_weights[asset] * covariance_times_weights[asset] / portfolio_variance
        for asset in assets
    }


def analyze_portfolio(
    asset_prices: Mapping[str, Sequence[float]],
    weights: Mapping[str, float],
    *,
    confidence: float = 0.95,
    periods_per_year: int = 252,
    annual_risk_free_rate: float = 0.0,
) -> PortfolioRiskAnalysis:
    assets = tuple(asset_prices)
    parsed_weights = validate_weights(weights, assets)
    asset_returns = calculate_asset_returns(asset_prices)
    portfolio_returns = calculate_portfolio_returns(asset_returns, parsed_weights)
    metrics = analyze_returns(
        portfolio_returns,
        confidence=confidence,
        periods_per_year=periods_per_year,
        annual_risk_free_rate=annual_risk_free_rate,
        wealth_index=build_wealth_index(portfolio_returns),
    )
    return PortfolioRiskAnalysis(
        metrics=metrics,
        weights=parsed_weights,
        risk_contributions=calculate_risk_contributions(asset_returns, parsed_weights),
    )
