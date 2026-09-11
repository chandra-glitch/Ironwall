"""Portfolio diversification benefit measured from aligned asset returns."""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from ironwall.metrics import calculate_volatility
from ironwall.portfolio import validate_weights


@dataclass(frozen=True)
class DiversificationAnalysis:
    """Volatility-based diversification metrics for a long-only portfolio."""

    asset_count: int
    return_observations: int
    asset_volatilities: dict[str, float]
    weighted_average_asset_volatility: float
    portfolio_volatility: float
    diversification_ratio: float | None
    volatility_reduction: float | None

    def to_dict(self) -> dict[str, int | float | dict[str, float] | None]:
        """Return JSON-ready values without rounding away precision."""

        return {
            "asset_count": self.asset_count,
            "return_observations": self.return_observations,
            "asset_volatilities": self.asset_volatilities,
            "weighted_average_asset_volatility": self.weighted_average_asset_volatility,
            "portfolio_volatility": self.portfolio_volatility,
            "diversification_ratio": self.diversification_ratio,
            "volatility_reduction": self.volatility_reduction,
        }


def _validate_asset_returns(
    asset_returns: Mapping[str, Sequence[float]],
) -> dict[str, tuple[float, ...]]:
    if len(asset_returns) < 2:
        raise ValueError("Diversification analysis requires at least two assets.")

    parsed: dict[str, tuple[float, ...]] = {}
    for asset, values in asset_returns.items():
        try:
            returns = tuple(float(value) for value in values)
        except (TypeError, ValueError) as error:
            raise ValueError(f"Returns for {asset} must be numeric.") from error
        if len(returns) < 2:
            raise ValueError("Asset return series must contain at least two observations.")
        if any(not math.isfinite(value) for value in returns):
            raise ValueError("Asset return series must contain only finite values.")
        if any(value <= -1 for value in returns):
            raise ValueError("Asset returns cannot be less than or equal to -100%.")
        parsed[asset] = returns

    if len({len(values) for values in parsed.values()}) != 1:
        raise ValueError("Asset return series must be aligned.")
    return parsed


def _calculate_sample_volatility(returns: Sequence[float]) -> float:
    if all(value == returns[0] for value in returns[1:]):
        return 0.0
    return calculate_volatility(returns)


def analyze_diversification(
    asset_returns: Mapping[str, Sequence[float]],
    weights: Mapping[str, float],
) -> DiversificationAnalysis:
    """Measure the volatility benefit obtained by combining portfolio assets."""

    parsed_returns = _validate_asset_returns(asset_returns)
    assets = tuple(parsed_returns)
    parsed_weights = validate_weights(weights, assets)
    observations = len(next(iter(parsed_returns.values())))

    asset_volatilities = {
        asset: _calculate_sample_volatility(parsed_returns[asset]) for asset in assets
    }
    weighted_average_volatility = math.fsum(
        parsed_weights[asset] * asset_volatilities[asset] for asset in assets
    )
    portfolio_returns = tuple(
        math.fsum(parsed_weights[asset] * parsed_returns[asset][index] for asset in assets)
        for index in range(observations)
    )
    portfolio_volatility = _calculate_sample_volatility(portfolio_returns)

    diversification_ratio = (
        weighted_average_volatility / portfolio_volatility if portfolio_volatility > 0 else None
    )
    volatility_reduction = (
        1 - portfolio_volatility / weighted_average_volatility
        if weighted_average_volatility > 0
        else None
    )

    return DiversificationAnalysis(
        asset_count=len(assets),
        return_observations=observations,
        asset_volatilities=asset_volatilities,
        weighted_average_asset_volatility=weighted_average_volatility,
        portfolio_volatility=portfolio_volatility,
        diversification_ratio=diversification_ratio,
        volatility_reduction=volatility_reduction,
    )
