"""Historical Expected Shortfall attribution for long-only portfolios."""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from ironwall.portfolio import validate_weights


@dataclass(frozen=True)
class TailRiskAttribution:
    """Portfolio tail loss and each asset's additive contribution."""

    return_observations: int
    confidence: float
    cutoff_return: float
    tail_observations: int
    mean_tail_return: float
    signed_tail_loss: float
    conditional_value_at_risk: float
    component_tail_losses: dict[str, float]
    component_shares: dict[str, float] | None

    def to_dict(self) -> dict[str, int | float | dict[str, float] | None]:
        """Return JSON-ready attribution values without rounding away precision."""

        return {
            "return_observations": self.return_observations,
            "confidence": self.confidence,
            "cutoff_return": self.cutoff_return,
            "tail_observations": self.tail_observations,
            "mean_tail_return": self.mean_tail_return,
            "signed_tail_loss": self.signed_tail_loss,
            "conditional_value_at_risk": self.conditional_value_at_risk,
            "component_tail_losses": dict(self.component_tail_losses),
            "component_shares": (
                dict(self.component_shares) if self.component_shares is not None else None
            ),
        }


def _validate_confidence(confidence: float) -> float:
    try:
        parsed = float(confidence)
    except (TypeError, ValueError) as error:
        raise ValueError("confidence must be numeric.") from error
    if not math.isfinite(parsed) or not 0 < parsed < 1:
        raise ValueError("confidence must be finite and strictly between 0 and 1.")
    return parsed


def _validate_asset_returns(
    asset_returns: Mapping[str, Sequence[float]],
) -> dict[str, tuple[float, ...]]:
    if len(asset_returns) < 2:
        raise ValueError("Tail attribution requires at least two assets.")

    parsed: dict[str, tuple[float, ...]] = {}
    for asset, returns in asset_returns.items():
        if not isinstance(asset, str) or not asset or asset != asset.strip():
            raise ValueError(
                "Asset names must be non-empty strings without surrounding whitespace."
            )
        try:
            values = tuple(float(value) for value in returns)
        except (TypeError, ValueError) as error:
            raise ValueError(f"Returns for {asset} must contain only numeric values.") from error
        if any(not math.isfinite(value) for value in values):
            raise ValueError(f"Returns for {asset} must contain only finite values.")
        if any(value <= -1 for value in values):
            raise ValueError("Returns cannot be less than or equal to -100%.")
        parsed[asset] = values

    lengths = {len(values) for values in parsed.values()}
    if len(lengths) != 1:
        raise ValueError("Asset return series must have aligned observations.")
    if not lengths or next(iter(lengths)) < 2:
        raise ValueError("Tail attribution requires at least two return observations.")
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


def _mean(values: Sequence[float]) -> float:
    return math.fsum(value / len(values) for value in values)


def attribute_expected_shortfall(
    asset_returns: Mapping[str, Sequence[float]],
    weights: Mapping[str, float],
    *,
    confidence: float = 0.95,
) -> TailRiskAttribution:
    """Attribute historical portfolio Expected Shortfall to its assets.

    Asset return observations must be aligned in time. Contributions are weighted
    conditional mean losses over observations at or below the interpolated
    portfolio-return cutoff. Negative contributions identify assets that hedged the
    portfolio during those observations.
    """

    parsed_returns = _validate_asset_returns(asset_returns)
    assets = tuple(parsed_returns)
    try:
        parsed_weights = validate_weights(weights, assets)
    except (TypeError, ValueError, OverflowError) as error:
        raise ValueError(str(error) or "Invalid portfolio weights.") from error
    confidence = _validate_confidence(confidence)

    observations = len(next(iter(parsed_returns.values())))
    portfolio_returns = tuple(
        math.fsum(parsed_weights[asset] * parsed_returns[asset][index] for asset in assets)
        for index in range(observations)
    )
    cutoff_return = _quantile(portfolio_returns, 1 - confidence)
    tail_indices = tuple(
        index
        for index, period_return in enumerate(portfolio_returns)
        if period_return <= cutoff_return
    )
    mean_tail_return = _mean(tuple(portfolio_returns[index] for index in tail_indices))
    signed_tail_loss = -mean_tail_return
    conditional_value_at_risk = max(0.0, signed_tail_loss)

    component_tail_losses = {
        asset: -parsed_weights[asset]
        * _mean(tuple(parsed_returns[asset][index] for index in tail_indices))
        for asset in assets
    }
    component_shares = None
    if signed_tail_loss > 0:
        component_shares = {
            asset: component_tail_losses[asset] / signed_tail_loss for asset in assets
        }

    return TailRiskAttribution(
        return_observations=observations,
        confidence=confidence,
        cutoff_return=cutoff_return,
        tail_observations=len(tail_indices),
        mean_tail_return=mean_tail_return,
        signed_tail_loss=signed_tail_loss,
        conditional_value_at_risk=conditional_value_at_risk,
        component_tail_losses=component_tail_losses,
        component_shares=component_shares,
    )
