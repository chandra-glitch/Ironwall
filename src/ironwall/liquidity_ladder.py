"""Deterministic cash-flow ladder and liquidity shortfall diagnostics."""

from __future__ import annotations

import math
from collections.abc import Mapping
from dataclasses import dataclass


@dataclass(frozen=True)
class LiquidityBucket:
    """Projected liquidity after one dated net cash-flow bucket."""

    day: int
    net_cash_flow: float
    cumulative_net_cash_flow: float
    projected_liquidity: float
    liquidity_shortfall: float
    is_shortfall: bool

    def to_dict(self) -> dict[str, int | float | bool]:
        """Return strict-JSON-ready bucket values."""

        return {
            "day": self.day,
            "net_cash_flow": self.net_cash_flow,
            "cumulative_net_cash_flow": self.cumulative_net_cash_flow,
            "projected_liquidity": self.projected_liquidity,
            "liquidity_shortfall": self.liquidity_shortfall,
            "is_shortfall": self.is_shortfall,
        }


@dataclass(frozen=True)
class LiquidityLadderAnalysis:
    """Aggregate liquidity diagnostics across ordered cash-flow buckets."""

    initial_liquidity: float
    bucket_count: int
    total_inflows: float
    total_outflows: float
    net_cash_flow: float
    ending_liquidity: float
    minimum_liquidity: float
    minimum_liquidity_day: int
    maximum_shortfall: float
    first_shortfall_day: int | None
    shortfall_bucket_count: int
    survives_horizon: bool
    buckets: tuple[LiquidityBucket, ...]

    def to_dict(self) -> dict[str, object]:
        """Return strict-JSON-ready values in ascending day order."""

        return {
            "initial_liquidity": self.initial_liquidity,
            "bucket_count": self.bucket_count,
            "total_inflows": self.total_inflows,
            "total_outflows": self.total_outflows,
            "net_cash_flow": self.net_cash_flow,
            "ending_liquidity": self.ending_liquidity,
            "minimum_liquidity": self.minimum_liquidity,
            "minimum_liquidity_day": self.minimum_liquidity_day,
            "maximum_shortfall": self.maximum_shortfall,
            "first_shortfall_day": self.first_shortfall_day,
            "shortfall_bucket_count": self.shortfall_bucket_count,
            "survives_horizon": self.survives_horizon,
            "buckets": [bucket.to_dict() for bucket in self.buckets],
        }


def _validated_number(value: object, *, name: str) -> float:
    if isinstance(value, bool):
        raise ValueError(f"{name} must be numeric, not boolean.")
    try:
        parsed = float(value)
    except (TypeError, ValueError, OverflowError) as error:
        raise ValueError(f"{name} must be numeric and finite.") from error
    if not math.isfinite(parsed):
        raise ValueError(f"{name} must be numeric and finite.")
    return parsed


def _validated_day(value: object) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ValueError("cash-flow bucket days must be positive integers.")
    return value


def _finite_sum(values: list[float], *, name: str) -> float:
    try:
        total = math.fsum(values)
    except (OverflowError, ValueError) as error:
        raise ValueError(f"{name} exceeds the supported numeric range.") from error
    if not math.isfinite(total):
        raise ValueError(f"{name} exceeds the supported numeric range.")
    return 0.0 if total == 0 else total


def analyze_liquidity_ladder(
    net_cash_flows: Mapping[int, float],
    initial_liquidity: float,
) -> LiquidityLadderAnalysis:
    """Project a liquidity buffer through positive-integer day buckets.

    Positive cash flows are inflows and negative cash flows are outflows. All amounts must use
    the same currency and unit. A projected balance of zero is depleted but is not a shortfall;
    a shortfall begins when the projected balance becomes negative.
    """

    if not isinstance(net_cash_flows, Mapping) or not net_cash_flows:
        raise ValueError("net_cash_flows must be a non-empty mapping of days to cash flows.")

    opening_balance = _validated_number(initial_liquidity, name="initial_liquidity")
    if opening_balance < 0:
        raise ValueError("initial_liquidity must be greater than or equal to zero.")

    parsed_cash_flows: dict[int, float] = {}
    for raw_day, raw_cash_flow in net_cash_flows.items():
        day = _validated_day(raw_day)
        cash_flow = _validated_number(raw_cash_flow, name=f"cash flow for day {day}")
        parsed_cash_flows[day] = 0.0 if cash_flow == 0 else cash_flow

    ordered_cash_flows = sorted(parsed_cash_flows.items())
    cash_flow_values = [cash_flow for _, cash_flow in ordered_cash_flows]
    total_inflows = _finite_sum(
        [cash_flow for cash_flow in cash_flow_values if cash_flow > 0],
        name="total inflows",
    )
    total_outflows = _finite_sum(
        [-cash_flow for cash_flow in cash_flow_values if cash_flow < 0],
        name="total outflows",
    )
    net_cash_flow = _finite_sum(cash_flow_values, name="net cash flow")

    prefix_cash_flows: list[float] = []
    bucket_details: list[LiquidityBucket] = []
    minimum_liquidity = opening_balance
    minimum_liquidity_day = 0
    maximum_shortfall = 0.0
    first_shortfall_day: int | None = None
    shortfall_bucket_count = 0

    for day, cash_flow in ordered_cash_flows:
        prefix_cash_flows.append(cash_flow)
        cumulative_cash_flow = _finite_sum(
            prefix_cash_flows,
            name=f"cumulative cash flow through day {day}",
        )
        projected_liquidity = _finite_sum(
            [opening_balance, cumulative_cash_flow],
            name=f"projected liquidity on day {day}",
        )
        is_shortfall = projected_liquidity < 0
        liquidity_shortfall = -projected_liquidity if is_shortfall else 0.0

        if projected_liquidity < minimum_liquidity:
            minimum_liquidity = projected_liquidity
            minimum_liquidity_day = day
        if is_shortfall:
            shortfall_bucket_count += 1
            maximum_shortfall = max(maximum_shortfall, liquidity_shortfall)
            if first_shortfall_day is None:
                first_shortfall_day = day

        bucket_details.append(
            LiquidityBucket(
                day=day,
                net_cash_flow=cash_flow,
                cumulative_net_cash_flow=cumulative_cash_flow,
                projected_liquidity=projected_liquidity,
                liquidity_shortfall=liquidity_shortfall,
                is_shortfall=is_shortfall,
            )
        )

    return LiquidityLadderAnalysis(
        initial_liquidity=opening_balance,
        bucket_count=len(bucket_details),
        total_inflows=total_inflows,
        total_outflows=total_outflows,
        net_cash_flow=net_cash_flow,
        ending_liquidity=bucket_details[-1].projected_liquidity,
        minimum_liquidity=minimum_liquidity,
        minimum_liquidity_day=minimum_liquidity_day,
        maximum_shortfall=maximum_shortfall,
        first_shortfall_day=first_shortfall_day,
        shortfall_bucket_count=shortfall_bucket_count,
        survives_horizon=first_shortfall_day is None,
        buckets=tuple(bucket_details),
    )
