"""Portfolio weight concentration risk metrics."""

from __future__ import annotations

import math
from collections.abc import Mapping
from dataclasses import dataclass

from ironwall.portfolio import validate_weights

__all__ = ["ConcentrationMetrics", "analyze_weight_concentration"]


@dataclass(frozen=True)
class ConcentrationMetrics:
    """Concentration statistics for a validated long-only allocation."""

    asset_count: int
    largest_weight: float
    herfindahl_index: float
    effective_number_of_assets: float
    normalized_herfindahl_index: float

    def to_dict(self) -> dict[str, int | float]:
        """Return a JSON-serializable representation of the metrics."""

        return {
            "asset_count": self.asset_count,
            "largest_weight": self.largest_weight,
            "herfindahl_index": self.herfindahl_index,
            "effective_number_of_assets": self.effective_number_of_assets,
            "normalized_herfindahl_index": self.normalized_herfindahl_index,
        }


def analyze_weight_concentration(weights: Mapping[str, float]) -> ConcentrationMetrics:
    """Measure allocation concentration using Herfindahl statistics.

    Weights must describe at least two assets, be finite and non-negative, and
    sum to one. Zero-weight assets are permitted so a fully concentrated
    allocation can still be measured.
    """

    parsed_weights = validate_weights(weights, tuple(weights))
    asset_count = len(parsed_weights)
    herfindahl_index = math.fsum(weight * weight for weight in parsed_weights.values())
    equal_weight_floor = 1.0 / asset_count
    normalized_index = (herfindahl_index - equal_weight_floor) / (1.0 - equal_weight_floor)

    return ConcentrationMetrics(
        asset_count=asset_count,
        largest_weight=max(parsed_weights.values()),
        herfindahl_index=herfindahl_index,
        effective_number_of_assets=1.0 / herfindahl_index,
        normalized_herfindahl_index=max(0.0, min(1.0, normalized_index)),
    )
