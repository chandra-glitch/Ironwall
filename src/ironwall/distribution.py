"""Historical return-distribution diagnostics with stable moment calculations."""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass


@dataclass(frozen=True)
class ReturnDistributionDiagnostics:
    """Shape diagnostics for a periodic return sample."""

    return_observations: int
    mean_return: float
    sample_volatility: float
    skewness: float
    excess_kurtosis: float
    jarque_bera_statistic: float
    jarque_bera_asymptotic_p_value: float

    def to_dict(self) -> dict[str, int | float]:
        """Return JSON-ready diagnostic values without rounding away precision."""

        return {
            "return_observations": self.return_observations,
            "mean_return": self.mean_return,
            "sample_volatility": self.sample_volatility,
            "skewness": self.skewness,
            "excess_kurtosis": self.excess_kurtosis,
            "jarque_bera_statistic": self.jarque_bera_statistic,
            "jarque_bera_asymptotic_p_value": self.jarque_bera_asymptotic_p_value,
        }


def _validate_returns(returns: Sequence[float]) -> tuple[float, ...]:
    try:
        parsed = tuple(float(value) for value in returns)
    except (TypeError, ValueError, OverflowError) as error:
        raise ValueError("Distribution returns must contain only numeric values.") from error
    if len(parsed) < 4:
        raise ValueError("Return-distribution analysis requires at least four observations.")
    if any(not math.isfinite(value) for value in parsed):
        raise ValueError("Distribution returns must contain only finite values.")
    if any(value <= -1 for value in parsed):
        raise ValueError("Returns cannot be less than or equal to -100%.")
    return parsed


def analyze_return_distribution(
    returns: Sequence[float],
) -> ReturnDistributionDiagnostics:
    """Calculate standardized moments and the asymptotic Jarque-Bera diagnostic."""

    parsed = _validate_returns(returns)
    observation_count = len(parsed)
    mean_return = math.fsum(value / observation_count for value in parsed)
    centered = tuple(value - mean_return for value in parsed)
    scale = max(abs(value) for value in centered)
    if scale == 0:
        raise ValueError("Return-distribution analysis requires non-constant returns.")

    normalized = tuple(value / scale for value in centered)
    second_moment = math.fsum(value**2 / observation_count for value in normalized)
    if second_moment <= 0:
        raise ValueError("Return-distribution variance must be positive.")
    third_moment = math.fsum(value**3 / observation_count for value in normalized)
    fourth_moment = math.fsum(value**4 / observation_count for value in normalized)

    sample_volatility = scale * math.sqrt(
        second_moment * observation_count / (observation_count - 1)
    )
    skewness = third_moment / second_moment**1.5
    excess_kurtosis = fourth_moment / second_moment**2 - 3
    jarque_bera_statistic = observation_count / 6 * (skewness**2 + excess_kurtosis**2 / 4)
    jarque_bera_asymptotic_p_value = math.exp(-jarque_bera_statistic / 2)

    diagnostics = (
        mean_return,
        sample_volatility,
        skewness,
        excess_kurtosis,
        jarque_bera_statistic,
        jarque_bera_asymptotic_p_value,
    )
    if any(not math.isfinite(value) for value in diagnostics):
        raise ValueError("Return-distribution diagnostics must be finite.")

    return ReturnDistributionDiagnostics(
        return_observations=observation_count,
        mean_return=mean_return,
        sample_volatility=sample_volatility,
        skewness=skewness,
        excess_kurtosis=excess_kurtosis,
        jarque_bera_statistic=jarque_bera_statistic,
        jarque_bera_asymptotic_p_value=jarque_bera_asymptotic_p_value,
    )
