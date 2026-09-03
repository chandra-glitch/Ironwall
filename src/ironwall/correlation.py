"""Pearson correlation analysis for aligned asset-return series."""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence

__all__ = ["calculate_return_correlation_matrix"]


def _validated_aligned_returns(
    asset_returns: Mapping[str, Sequence[float]],
) -> tuple[tuple[str, ...], dict[str, tuple[float, ...]]]:
    assets = tuple(asset_returns)
    if len(assets) < 2:
        raise ValueError("Correlation analysis requires at least two assets.")

    parsed: dict[str, tuple[float, ...]] = {}
    observations: int | None = None
    for asset in assets:
        try:
            values = tuple(float(value) for value in asset_returns[asset])
        except (TypeError, ValueError) as exc:
            raise ValueError(f"Returns for {asset} must be numeric.") from exc
        if len(values) < 2:
            raise ValueError("Correlation analysis requires at least two return observations.")
        if any(not math.isfinite(value) for value in values):
            raise ValueError(f"Returns for {asset} must contain only finite values.")
        if observations is None:
            observations = len(values)
        elif len(values) != observations:
            raise ValueError("All asset return series must be aligned and have equal length.")
        parsed[asset] = values
    return assets, parsed


def calculate_return_correlation_matrix(
    asset_returns: Mapping[str, Sequence[float]],
) -> dict[str, dict[str, float]]:
    """Calculate a symmetric Pearson matrix from aligned periodic returns.

    Constant return series are rejected because their zero variance makes
    correlation undefined.
    """

    assets, parsed = _validated_aligned_returns(asset_returns)
    observations = len(parsed[assets[0]])
    means = {asset: math.fsum(parsed[asset]) / observations for asset in assets}
    centered = {asset: tuple(value - means[asset] for value in parsed[asset]) for asset in assets}
    sums_of_squares = {
        asset: math.fsum(value * value for value in centered[asset]) for asset in assets
    }
    zero_variance_assets = [asset for asset in assets if sums_of_squares[asset] == 0.0]
    if zero_variance_assets:
        raise ValueError(
            "Correlation is undefined for zero-variance assets: "
            + ", ".join(zero_variance_assets)
            + "."
        )

    matrix: dict[str, dict[str, float]] = {}
    for left in assets:
        row: dict[str, float] = {}
        for right in assets:
            if left == right:
                row[right] = 1.0
                continue
            cross_product = math.fsum(
                left_value * right_value
                for left_value, right_value in zip(centered[left], centered[right], strict=True)
            )
            denominator = math.sqrt(sums_of_squares[left] * sums_of_squares[right])
            correlation = cross_product / denominator
            row[right] = max(-1.0, min(1.0, correlation))
        matrix[left] = row
    return matrix
