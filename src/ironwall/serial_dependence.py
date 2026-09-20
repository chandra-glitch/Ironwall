"""Descriptive serial-dependence diagnostics for periodic returns."""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass


@dataclass(frozen=True)
class LagAutocorrelation:
    """Return and squared-return autocorrelation at one lag."""

    lag: int
    return_autocorrelation: float
    squared_return_autocorrelation: float | None

    def to_dict(self) -> dict[str, int | float | None]:
        """Return strict-JSON-ready values without rounding away precision."""

        return {
            "lag": self.lag,
            "return_autocorrelation": self.return_autocorrelation,
            "squared_return_autocorrelation": self.squared_return_autocorrelation,
        }


@dataclass(frozen=True)
class SerialDependenceAnalysis:
    """Autocorrelation diagnostics across the requested lag range."""

    return_observations: int
    max_lag: int
    squared_return_autocorrelation_available: bool
    lags: tuple[LagAutocorrelation, ...]

    def to_dict(
        self,
    ) -> dict[str, int | bool | list[dict[str, int | float | None]]]:
        """Return strict-JSON-ready values without rounding away precision."""

        return {
            "return_observations": self.return_observations,
            "max_lag": self.max_lag,
            "squared_return_autocorrelation_available": (
                self.squared_return_autocorrelation_available
            ),
            "lags": [result.to_dict() for result in self.lags],
        }


def _validated_returns(returns: Sequence[float]) -> tuple[float, ...]:
    try:
        parsed = tuple(float(value) for value in returns)
    except (TypeError, ValueError, OverflowError) as error:
        raise ValueError("returns must contain only finite numeric values.") from error
    if len(parsed) < 3:
        raise ValueError("serial-dependence analysis requires at least three returns.")
    if any(not math.isfinite(value) for value in parsed):
        raise ValueError("returns must contain only finite numeric values.")
    if any(value <= -1 for value in parsed):
        raise ValueError("returns cannot be less than or equal to -100%.")
    return parsed


def _validated_max_lag(max_lag: int, *, observations: int) -> int:
    if isinstance(max_lag, bool) or not isinstance(max_lag, int):
        raise ValueError("max_lag must be an integer.")
    if not 1 <= max_lag < observations:
        raise ValueError("max_lag must be at least 1 and smaller than the return sample.")
    return max_lag


def _autocorrelations(values: Sequence[float], *, max_lag: int) -> tuple[float, ...] | None:
    """Calculate the NIST autocorrelation definition with overflow-safe scaling."""

    scale = max(abs(value) for value in values)
    if scale == 0.0:
        return None

    scaled = tuple(value / scale for value in values)
    mean = math.fsum(scaled) / len(scaled)
    centered = tuple(value - mean for value in scaled)
    denominator = math.fsum(value * value for value in centered)
    if denominator == 0.0:
        return None

    results: list[float] = []
    for lag in range(1, max_lag + 1):
        numerator = math.fsum(
            earlier * later for earlier, later in zip(centered[:-lag], centered[lag:], strict=True)
        )
        coefficient = numerator / denominator
        if not math.isfinite(coefficient):
            raise ValueError("autocorrelation exceeds the finite numeric range.")
        results.append(max(-1.0, min(1.0, coefficient)))
    return tuple(results)


def analyze_serial_dependence(
    returns: Sequence[float],
    *,
    max_lag: int = 1,
) -> SerialDependenceAnalysis:
    """Calculate return and squared-return autocorrelation through ``max_lag``.

    Return autocorrelation describes linear dependence in the level of the return series.
    Squared-return autocorrelation is a descriptive signal for persistence in return magnitude.
    It is reported as ``None`` when every observed return has the same absolute magnitude.
    """

    parsed = _validated_returns(returns)
    max_lag = _validated_max_lag(max_lag, observations=len(parsed))
    return_correlations = _autocorrelations(parsed, max_lag=max_lag)
    if return_correlations is None:
        raise ValueError("serial-dependence analysis requires non-constant returns.")

    magnitude_scale = max(abs(value) for value in parsed)
    scaled_squares = tuple((value / magnitude_scale) ** 2 for value in parsed)
    squared_correlations = _autocorrelations(scaled_squares, max_lag=max_lag)

    return SerialDependenceAnalysis(
        return_observations=len(parsed),
        max_lag=max_lag,
        squared_return_autocorrelation_available=squared_correlations is not None,
        lags=tuple(
            LagAutocorrelation(
                lag=lag,
                return_autocorrelation=return_correlations[lag - 1],
                squared_return_autocorrelation=(
                    None if squared_correlations is None else squared_correlations[lag - 1]
                ),
            )
            for lag in range(1, max_lag + 1)
        ),
    )
