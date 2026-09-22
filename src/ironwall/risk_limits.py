"""Deterministic upper-bound monitoring for non-negative risk metrics."""

from __future__ import annotations

import math
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Literal

LimitAnalysisStatus = Literal["within_limits", "breached"]
UtilizationStatus = Literal["finite", "above_numeric_range"]


@dataclass(frozen=True)
class RiskLimitAssessment:
    """One observed risk metric compared with its configured upper bound."""

    metric: str
    value: float
    limit: float
    utilization_ratio: float | None
    utilization_status: UtilizationStatus
    headroom: float
    breached: bool

    def to_dict(self) -> dict[str, str | float | bool | None]:
        """Return strict-JSON-ready values without rounding away precision."""

        return {
            "metric": self.metric,
            "value": self.value,
            "limit": self.limit,
            "utilization_ratio": self.utilization_ratio,
            "utilization_status": self.utilization_status,
            "headroom": self.headroom,
            "breached": self.breached,
        }


@dataclass(frozen=True)
class RiskLimitAnalysis:
    """Portfolio of configured risk-limit assessments."""

    assessed_metrics: int
    breach_count: int
    status: LimitAnalysisStatus
    breached_metrics: tuple[str, ...]
    assessments: tuple[RiskLimitAssessment, ...]

    def to_dict(
        self,
    ) -> dict[
        str,
        int | str | list[str] | list[dict[str, str | float | bool | None]],
    ]:
        """Return strict-JSON-ready values in deterministic metric order."""

        return {
            "assessed_metrics": self.assessed_metrics,
            "breach_count": self.breach_count,
            "status": self.status,
            "breached_metrics": list(self.breached_metrics),
            "assessments": [assessment.to_dict() for assessment in self.assessments],
        }


def _validated_metric_name(metric: object) -> str:
    if not isinstance(metric, str) or not metric or metric.strip() != metric:
        raise ValueError("risk-limit metric names must be non-empty strings without padding.")
    return metric


def _validated_number(value: object, *, metric: str, is_limit: bool) -> float:
    description = "limit" if is_limit else "value"
    if isinstance(value, bool):
        raise ValueError(f"{description} for {metric!r} must be numeric, not boolean.")
    try:
        parsed = float(value)
    except (TypeError, ValueError, OverflowError) as error:
        raise ValueError(f"{description} for {metric!r} must be numeric and finite.") from error
    if not math.isfinite(parsed):
        raise ValueError(f"{description} for {metric!r} must be numeric and finite.")
    if is_limit and parsed <= 0:
        raise ValueError(f"limit for {metric!r} must be greater than zero.")
    if not is_limit and parsed < 0:
        raise ValueError(f"value for {metric!r} must be non-negative.")
    return parsed


def _utilization(value: float, limit: float) -> tuple[float | None, UtilizationStatus]:
    try:
        utilization = value / limit
    except OverflowError:
        return None, "above_numeric_range"
    if not math.isfinite(utilization):
        return None, "above_numeric_range"
    return utilization, "finite"


def evaluate_risk_limits(
    values: Mapping[str, float],
    limits: Mapping[str, float],
) -> RiskLimitAnalysis:
    """Compare selected non-negative risk values with strict upper bounds.

    The keys in ``limits`` select the metrics to assess, so ``values`` may safely contain
    additional metrics. A value exactly equal to its limit consumes all available capacity but
    is not a breach; a breach occurs only when the value exceeds the limit.
    """

    if not isinstance(values, Mapping):
        raise ValueError("values must be a mapping of metric names to numbers.")
    if not isinstance(limits, Mapping) or not limits:
        raise ValueError("limits must be a non-empty mapping of metric names to numbers.")

    parsed_limits: dict[str, float] = {}
    for raw_metric, raw_limit in limits.items():
        metric = _validated_metric_name(raw_metric)
        parsed_limits[metric] = _validated_number(raw_limit, metric=metric, is_limit=True)

    missing = set(parsed_limits) - set(values)
    if missing:
        raise ValueError(f"missing values for risk limits: {', '.join(sorted(missing))}.")

    assessments: list[RiskLimitAssessment] = []
    for metric in sorted(parsed_limits):
        value = _validated_number(values[metric], metric=metric, is_limit=False)
        limit = parsed_limits[metric]
        utilization_ratio, utilization_status = _utilization(value, limit)
        assessments.append(
            RiskLimitAssessment(
                metric=metric,
                value=value,
                limit=limit,
                utilization_ratio=utilization_ratio,
                utilization_status=utilization_status,
                headroom=limit - value,
                breached=value > limit,
            )
        )

    breached_metrics = tuple(assessment.metric for assessment in assessments if assessment.breached)
    return RiskLimitAnalysis(
        assessed_metrics=len(assessments),
        breach_count=len(breached_metrics),
        status="breached" if breached_metrics else "within_limits",
        breached_metrics=breached_metrics,
        assessments=tuple(assessments),
    )
