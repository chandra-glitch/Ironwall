"""Single-factor ordinary least-squares exposure analysis."""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass

__all__ = ["FactorExposure", "calculate_factor_exposure"]


@dataclass(frozen=True)
class FactorExposure:
    """OLS sensitivity of an asset's returns to one factor return series."""

    observations: int
    alpha: float
    beta: float
    r_squared: float

    def to_dict(self) -> dict[str, int | float]:
        """Return a JSON-ready representation without rounding precision."""

        return {
            "observations": self.observations,
            "alpha": self.alpha,
            "beta": self.beta,
            "r_squared": self.r_squared,
        }


def _validated_returns(values: Sequence[float], *, name: str) -> tuple[float, ...]:
    try:
        parsed = tuple(float(value) for value in values)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} must contain only numeric values.") from exc
    if len(parsed) < 3:
        raise ValueError("Factor exposure requires at least three aligned return observations.")
    if any(not math.isfinite(value) for value in parsed):
        raise ValueError(f"{name} must contain only finite values.")
    return parsed


def calculate_factor_exposure(
    asset_returns: Sequence[float],
    factor_returns: Sequence[float],
) -> FactorExposure:
    """Regress periodic asset returns on one aligned factor return series.

    ``alpha`` is the per-period intercept, ``beta`` is factor sensitivity,
    and ``r_squared`` is the fraction of asset-return variance explained by
    the fitted single-factor model.
    """

    asset = _validated_returns(asset_returns, name="asset returns")
    factor = _validated_returns(factor_returns, name="factor returns")
    if len(asset) != len(factor):
        raise ValueError("Asset and factor return series must be aligned and have equal length.")

    observations = len(asset)
    asset_mean = math.fsum(asset) / observations
    factor_mean = math.fsum(factor) / observations
    centered_asset = tuple(value - asset_mean for value in asset)
    centered_factor = tuple(value - factor_mean for value in factor)
    asset_sum_squares = math.fsum(value * value for value in centered_asset)
    factor_sum_squares = math.fsum(value * value for value in centered_factor)
    if factor_sum_squares == 0.0:
        raise ValueError("factor returns must vary to estimate an exposure.")
    if asset_sum_squares == 0.0:
        raise ValueError("asset returns must vary to calculate R-squared.")

    cross_product = math.fsum(
        asset_value * factor_value
        for asset_value, factor_value in zip(centered_asset, centered_factor, strict=True)
    )
    beta = cross_product / factor_sum_squares
    alpha = asset_mean - beta * factor_mean
    r_squared = (cross_product * cross_product) / (asset_sum_squares * factor_sum_squares)
    return FactorExposure(
        observations=observations,
        alpha=alpha,
        beta=beta,
        r_squared=max(0.0, min(1.0, r_squared)),
    )
