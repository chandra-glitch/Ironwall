"""Deterministic one-period stress scenarios for long-only portfolios."""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from ironwall.portfolio import validate_weights


@dataclass(frozen=True)
class StressScenarioResult:
    """Portfolio and asset-level impacts from one stress scenario."""

    portfolio_return: float
    loss: float
    asset_impacts: dict[str, float]

    def to_dict(self) -> dict[str, float | dict[str, float]]:
        """Return a JSON-ready representation without rounding precision."""

        return {
            "portfolio_return": self.portfolio_return,
            "loss": self.loss,
            "asset_impacts": dict(self.asset_impacts),
        }


def _validate_shocks(
    shocks: Mapping[str, float],
    assets: Sequence[str],
) -> dict[str, float]:
    asset_set = set(assets)
    missing = asset_set - set(shocks)
    extra = set(shocks) - asset_set
    if missing or extra:
        details = []
        if missing:
            details.append(f"missing shocks for {', '.join(sorted(missing))}")
        if extra:
            details.append(f"unknown assets {', '.join(sorted(extra))}")
        raise ValueError("Invalid scenario shocks: " + "; ".join(details) + ".")

    parsed: dict[str, float] = {}
    for asset in assets:
        try:
            shock = float(shocks[asset])
        except (TypeError, ValueError) as exc:
            raise ValueError(f"Scenario shock for {asset} must be numeric.") from exc
        if not math.isfinite(shock):
            raise ValueError(f"Scenario shock for {asset} must be finite.")
        if shock < -1.0:
            raise ValueError(f"Scenario shock for {asset} cannot be below -100%.")
        parsed[asset] = shock
    return parsed


def run_stress_scenario(
    weights: Mapping[str, float],
    shocks: Mapping[str, float],
) -> StressScenarioResult:
    """Apply asset shocks and return their weighted portfolio impacts.

    Shocks use decimal simple-return form, so ``-0.20`` represents a 20%
    decline. A total loss of ``-1.0`` is valid, but lower values are not.
    """

    assets = tuple(weights)
    parsed_weights = validate_weights(weights, assets)
    parsed_shocks = _validate_shocks(shocks, assets)
    asset_impacts = {asset: parsed_weights[asset] * parsed_shocks[asset] for asset in assets}
    portfolio_return = math.fsum(asset_impacts.values())
    return StressScenarioResult(
        portfolio_return=portfolio_return,
        loss=max(0.0, -portfolio_return),
        asset_impacts=asset_impacts,
    )
