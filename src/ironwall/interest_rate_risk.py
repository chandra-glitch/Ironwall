"""Fixed-income present value, duration, convexity, and DV01 diagnostics."""

from __future__ import annotations

import math
from collections.abc import Mapping
from dataclasses import dataclass


@dataclass(frozen=True)
class DiscountedCashFlow:
    """One contractual cash flow and its contribution to instrument value."""

    time_years: float
    cash_flow: float
    present_value: float
    price_weight: float

    def to_dict(self) -> dict[str, float]:
        """Return strict-JSON-ready cash-flow values."""

        return {
            "time_years": self.time_years,
            "cash_flow": self.cash_flow,
            "present_value": self.present_value,
            "price_weight": self.price_weight,
        }


@dataclass(frozen=True)
class InterestRateSensitivityAnalysis:
    """Value and parallel-yield sensitivity for fixed positive cash flows."""

    annual_yield: float
    compounds_per_year: int
    rate_shock: float
    shocked_annual_yield: float
    cash_flow_count: int
    maturity_years: float
    present_value: float
    macaulay_duration_years: float
    modified_duration_years: float
    convexity_years_squared: float
    dv01: float
    shocked_present_value: float
    exact_price_change: float
    exact_price_change_percentage: float
    duration_convexity_price_change: float
    duration_convexity_price_change_percentage: float
    duration_convexity_error: float
    cash_flows: tuple[DiscountedCashFlow, ...]

    def to_dict(self) -> dict[str, object]:
        """Return strict-JSON-ready values in ascending payment-time order."""

        return {
            "annual_yield": self.annual_yield,
            "compounds_per_year": self.compounds_per_year,
            "rate_shock": self.rate_shock,
            "shocked_annual_yield": self.shocked_annual_yield,
            "cash_flow_count": self.cash_flow_count,
            "maturity_years": self.maturity_years,
            "present_value": self.present_value,
            "macaulay_duration_years": self.macaulay_duration_years,
            "modified_duration_years": self.modified_duration_years,
            "convexity_years_squared": self.convexity_years_squared,
            "dv01": self.dv01,
            "shocked_present_value": self.shocked_present_value,
            "exact_price_change": self.exact_price_change,
            "exact_price_change_percentage": self.exact_price_change_percentage,
            "duration_convexity_price_change": self.duration_convexity_price_change,
            "duration_convexity_price_change_percentage": (
                self.duration_convexity_price_change_percentage
            ),
            "duration_convexity_error": self.duration_convexity_error,
            "cash_flows": [cash_flow.to_dict() for cash_flow in self.cash_flows],
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


def _validated_frequency(value: object) -> tuple[int, float]:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ValueError("compounds_per_year must be a positive integer.")
    try:
        as_float = float(value)
    except OverflowError as error:
        raise ValueError("compounds_per_year exceeds the supported numeric range.") from error
    if not math.isfinite(as_float):
        raise ValueError("compounds_per_year exceeds the supported numeric range.")
    return value, as_float


def _finite_sum(values: list[float], *, name: str) -> float:
    try:
        result = math.fsum(values)
    except (OverflowError, ValueError) as error:
        raise ValueError(f"{name} exceeds the supported numeric range.") from error
    if not math.isfinite(result):
        raise ValueError(f"{name} exceeds the supported numeric range.")
    return 0.0 if result == 0 else result


def _finite_product(values: list[float], *, name: str) -> float:
    try:
        result = math.prod(values)
    except OverflowError as error:
        raise ValueError(f"{name} exceeds the supported numeric range.") from error
    if not math.isfinite(result):
        raise ValueError(f"{name} exceeds the supported numeric range.")
    return 0.0 if result == 0 else result


def _finite_ratio(numerator: float, denominator: float, *, name: str) -> float:
    try:
        result = numerator / denominator
    except (OverflowError, ZeroDivisionError) as error:
        raise ValueError(f"{name} exceeds the supported numeric range.") from error
    if not math.isfinite(result):
        raise ValueError(f"{name} exceeds the supported numeric range.")
    return 0.0 if result == 0 else result


def _validated_cash_flows(cash_flows: Mapping[float, float]) -> tuple[tuple[float, float], ...]:
    if not isinstance(cash_flows, Mapping) or not cash_flows:
        raise ValueError("cash_flows must be a non-empty mapping of payment times to amounts.")

    parsed: dict[float, float] = {}
    for raw_time, raw_amount in cash_flows.items():
        time_years = _validated_number(raw_time, name="cash-flow time")
        if time_years <= 0:
            raise ValueError("cash-flow times must be greater than zero years.")
        if time_years in parsed:
            raise ValueError("cash-flow times must be unique after numeric conversion.")

        amount = _validated_number(raw_amount, name=f"cash flow at {time_years:g} years")
        if amount <= 0:
            raise ValueError("cash-flow amounts must be greater than zero.")
        parsed[time_years] = amount

    return tuple(sorted(parsed.items()))


def _discount_cash_flows(
    cash_flows: tuple[tuple[float, float], ...],
    annual_yield: float,
    frequency: float,
    *,
    rate_name: str,
) -> tuple[list[float], float, float]:
    periodic_yield = annual_yield / frequency
    if not math.isfinite(periodic_yield) or periodic_yield <= -1:
        raise ValueError(f"{rate_name} must be greater than -compounds_per_year.")

    discount_base = 1.0 + periodic_yield
    if not math.isfinite(discount_base) or discount_base <= 0:
        raise ValueError(f"{rate_name} must produce a positive finite discount base.")

    log_discount_per_year = _finite_product(
        [frequency, math.log1p(periodic_yield)],
        name=f"{rate_name} discount exponent",
    )
    present_values: list[float] = []
    for time_years, amount in cash_flows:
        log_discount = _finite_product(
            [-time_years, log_discount_per_year],
            name=f"discount exponent at {time_years:g} years",
        )
        try:
            discount_factor = math.exp(log_discount)
        except OverflowError as error:
            raise ValueError(
                f"present value at {time_years:g} years exceeds the supported numeric range."
            ) from error
        if not math.isfinite(discount_factor) or discount_factor == 0:
            raise ValueError(
                f"present value at {time_years:g} years exceeds the supported numeric range."
            )
        present_values.append(
            _finite_product(
                [amount, discount_factor],
                name=f"present value at {time_years:g} years",
            )
        )

    total_present_value = _finite_sum(present_values, name=f"value at {rate_name}")
    if total_present_value <= 0:
        raise ValueError(f"value at {rate_name} must be greater than zero.")
    return present_values, total_present_value, discount_base


def analyze_fixed_income_sensitivity(
    cash_flows: Mapping[float, float],
    annual_yield: float,
    *,
    compounds_per_year: int = 1,
    rate_shock: float = 0.01,
) -> InterestRateSensitivityAnalysis:
    """Measure parallel-yield sensitivity for deterministic positive cash flows.

    Payment times are expressed in years, yields and shocks are decimals, and all cash-flow
    amounts must use the same currency and unit. Periodic compounding is applied at the supplied
    frequency. The default shock is a positive 100-basis-point parallel yield shift.
    """

    parsed_cash_flows = _validated_cash_flows(cash_flows)
    yield_value = _validated_number(annual_yield, name="annual_yield")
    shock = _validated_number(rate_shock, name="rate_shock")
    frequency_count, frequency = _validated_frequency(compounds_per_year)

    present_values, present_value, discount_base = _discount_cash_flows(
        parsed_cash_flows,
        yield_value,
        frequency,
        rate_name="annual_yield",
    )
    shocked_yield = _finite_sum([yield_value, shock], name="shocked annual yield")
    _, shocked_present_value, _ = _discount_cash_flows(
        parsed_cash_flows,
        shocked_yield,
        frequency,
        rate_name="shocked annual yield",
    )

    discounted_cash_flows: list[DiscountedCashFlow] = []
    duration_terms: list[float] = []
    convexity_terms: list[float] = []
    discount_base_squared = _finite_product(
        [discount_base, discount_base],
        name="discount base squared",
    )
    for (time_years, amount), cash_flow_present_value in zip(
        parsed_cash_flows,
        present_values,
        strict=True,
    ):
        price_weight = _finite_ratio(
            cash_flow_present_value,
            present_value,
            name=f"price weight at {time_years:g} years",
        )
        duration_terms.append(
            _finite_product(
                [time_years, price_weight],
                name=f"duration contribution at {time_years:g} years",
            )
        )
        convexity_numerator = _finite_product(
            [time_years, time_years + (1.0 / frequency), price_weight],
            name=f"convexity contribution at {time_years:g} years",
        )
        convexity_terms.append(
            _finite_ratio(
                convexity_numerator,
                discount_base_squared,
                name=f"convexity contribution at {time_years:g} years",
            )
        )
        discounted_cash_flows.append(
            DiscountedCashFlow(
                time_years=time_years,
                cash_flow=amount,
                present_value=cash_flow_present_value,
                price_weight=price_weight,
            )
        )

    macaulay_duration = _finite_sum(duration_terms, name="Macaulay duration")
    modified_duration = _finite_ratio(
        macaulay_duration,
        discount_base,
        name="modified duration",
    )
    convexity = _finite_sum(convexity_terms, name="convexity")
    dv01 = _finite_product(
        [present_value, modified_duration, 0.0001],
        name="DV01",
    )

    exact_price_change = _finite_sum(
        [shocked_present_value, -present_value],
        name="exact price change",
    )
    exact_price_change_percentage = _finite_ratio(
        exact_price_change,
        present_value,
        name="exact price change percentage",
    )
    linear_change = _finite_product(
        [-modified_duration, shock],
        name="duration price-change term",
    )
    shock_squared = _finite_product([shock, shock], name="rate shock squared")
    convexity_change = _finite_product(
        [0.5, convexity, shock_squared],
        name="convexity price-change term",
    )
    duration_convexity_percentage = _finite_sum(
        [linear_change, convexity_change],
        name="duration-convexity price change percentage",
    )
    duration_convexity_change = _finite_product(
        [present_value, duration_convexity_percentage],
        name="duration-convexity price change",
    )
    duration_convexity_error = _finite_sum(
        [duration_convexity_change, -exact_price_change],
        name="duration-convexity approximation error",
    )

    return InterestRateSensitivityAnalysis(
        annual_yield=yield_value,
        compounds_per_year=frequency_count,
        rate_shock=shock,
        shocked_annual_yield=shocked_yield,
        cash_flow_count=len(discounted_cash_flows),
        maturity_years=discounted_cash_flows[-1].time_years,
        present_value=present_value,
        macaulay_duration_years=macaulay_duration,
        modified_duration_years=modified_duration,
        convexity_years_squared=convexity,
        dv01=dv01,
        shocked_present_value=shocked_present_value,
        exact_price_change=exact_price_change,
        exact_price_change_percentage=exact_price_change_percentage,
        duration_convexity_price_change=duration_convexity_change,
        duration_convexity_price_change_percentage=duration_convexity_percentage,
        duration_convexity_error=duration_convexity_error,
        cash_flows=tuple(discounted_cash_flows),
    )
