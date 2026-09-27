"""Deterministic historical operational-loss event diagnostics."""

from __future__ import annotations

import math
from collections.abc import Mapping
from dataclasses import dataclass
from decimal import Decimal
from numbers import Real


@dataclass(frozen=True)
class OperationalLossEvent:
    """Contribution of one observed operational-loss event."""

    event_id: str
    loss_amount: float
    share_of_total_loss: float
    is_material: bool

    def to_dict(self) -> dict[str, object]:
        """Return strict-JSON-ready event values."""

        return {
            "event_id": self.event_id,
            "loss_amount": self.loss_amount,
            "share_of_total_loss": self.share_of_total_loss,
            "is_material": self.is_material,
        }


@dataclass(frozen=True)
class OperationalLossAnalysis:
    """Historical frequency, severity, and material-loss diagnostics."""

    event_count: int
    observation_years: float
    materiality_threshold: float
    total_loss: float
    annualized_loss: float
    annualized_event_frequency: float
    mean_loss: float
    median_loss: float
    sample_loss_standard_deviation: float | None
    largest_event_id: str
    largest_loss: float
    largest_loss_share: float
    material_event_count: int
    material_loss: float
    material_loss_share: float
    annualized_material_event_frequency: float
    events: tuple[OperationalLossEvent, ...]

    def to_dict(self) -> dict[str, object]:
        """Return strict-JSON-ready values in deterministic severity order."""

        return {
            "event_count": self.event_count,
            "observation_years": self.observation_years,
            "materiality_threshold": self.materiality_threshold,
            "total_loss": self.total_loss,
            "annualized_loss": self.annualized_loss,
            "annualized_event_frequency": self.annualized_event_frequency,
            "mean_loss": self.mean_loss,
            "median_loss": self.median_loss,
            "sample_loss_standard_deviation": self.sample_loss_standard_deviation,
            "largest_event_id": self.largest_event_id,
            "largest_loss": self.largest_loss,
            "largest_loss_share": self.largest_loss_share,
            "material_event_count": self.material_event_count,
            "material_loss": self.material_loss,
            "material_loss_share": self.material_loss_share,
            "annualized_material_event_frequency": (self.annualized_material_event_frequency),
            "events": [event.to_dict() for event in self.events],
        }


def _validated_number(
    value: object,
    *,
    name: str,
    allow_zero: bool,
) -> float:
    if isinstance(value, bool) or not isinstance(value, (Real, Decimal)):
        raise ValueError(f"{name} must be a real numeric value, not boolean or text.")
    try:
        invalid_sign = value < 0 if allow_zero else value <= 0
    except (ArithmeticError, TypeError) as error:
        raise ValueError(f"{name} must be numeric and finite.") from error
    if invalid_sign:
        qualifier = "non-negative" if allow_zero else "greater than zero"
        raise ValueError(f"{name} must be {qualifier}.")

    try:
        parsed = float(value)
    except (TypeError, ValueError, OverflowError) as error:
        raise ValueError(f"{name} must be numeric and finite.") from error
    if not math.isfinite(parsed):
        raise ValueError(f"{name} must be numeric and finite.")
    if parsed == 0 and value != 0:
        raise ValueError(f"{name} loses material precision when converted to float.")
    return 0.0 if parsed == 0 else parsed


def _validated_losses(loss_events: Mapping[str, float]) -> dict[str, float]:
    if not isinstance(loss_events, Mapping) or not loss_events:
        raise ValueError("loss_events must be a non-empty mapping by event ID.")

    parsed: dict[str, float] = {}
    original_by_parsed_value: dict[float, object] = {}
    for event_id, raw_loss in loss_events.items():
        if not isinstance(event_id, str) or not event_id:
            raise ValueError("Operational-loss event IDs must be non-empty strings.")
        if event_id != event_id.strip():
            raise ValueError("Operational-loss event IDs cannot contain surrounding whitespace.")
        loss = _validated_number(
            raw_loss,
            name=f"loss amount for {event_id}",
            allow_zero=False,
        )
        if loss in original_by_parsed_value and raw_loss != original_by_parsed_value[loss]:
            raise ValueError(
                "Distinct loss amounts lose relative precision when converted to float."
            )
        original_by_parsed_value[loss] = raw_loss
        parsed[event_id] = loss
    return parsed


def _finite_sum(values: list[float], *, name: str) -> float:
    try:
        result = math.fsum(values)
    except (OverflowError, ValueError) as error:
        raise ValueError(f"{name} exceeds the supported numeric range.") from error
    if not math.isfinite(result):
        raise ValueError(f"{name} exceeds the supported numeric range.")
    return 0.0 if result == 0 else result


def _finite_ratio(numerator: float | int, denominator: float, *, name: str) -> float:
    try:
        result = numerator / denominator
    except (OverflowError, ZeroDivisionError) as error:
        raise ValueError(f"{name} exceeds the supported numeric range.") from error
    if not math.isfinite(result) or (result == 0 and numerator != 0):
        raise ValueError(f"{name} exceeds the supported numeric range.")
    return 0.0 if result == 0 else result


def _median(losses: list[float]) -> float:
    ordered = sorted(losses)
    midpoint = len(ordered) // 2
    if len(ordered) % 2:
        return ordered[midpoint]
    lower = ordered[midpoint - 1]
    upper = ordered[midpoint]
    return lower + (upper - lower) / 2.0


def _sample_standard_deviation(losses: list[float]) -> float | None:
    if len(losses) < 2:
        return None

    scale = max(losses)
    normalized = [loss / scale for loss in losses]
    normalized_mean = math.fsum(normalized) / len(normalized)
    normalized_variance = math.fsum((loss - normalized_mean) ** 2 for loss in normalized) / (
        len(normalized) - 1
    )
    result = scale * math.sqrt(normalized_variance)
    if not math.isfinite(result) or (result == 0 and normalized_variance != 0):
        raise ValueError("sample loss standard deviation exceeds the supported numeric range.")
    return 0.0 if result == 0 else result


def _material_event_ids(
    loss_events: Mapping[str, float],
    parsed_losses: Mapping[str, float],
    raw_threshold: object,
    parsed_threshold: float,
) -> set[str]:
    material: set[str] = set()
    for event_id, parsed_loss in parsed_losses.items():
        try:
            raw_is_material = loss_events[event_id] >= raw_threshold
        except (ArithmeticError, TypeError) as error:
            raise ValueError(
                "Loss amounts and materiality_threshold must be comparable."
            ) from error
        parsed_is_material = parsed_loss >= parsed_threshold
        if raw_is_material != parsed_is_material:
            raise ValueError("The materiality comparison loses precision when converted to float.")
        if raw_is_material:
            material.add(event_id)
    return material


def analyze_operational_losses(
    loss_events: Mapping[str, float],
    observation_years: float,
    *,
    materiality_threshold: float = 0.0,
) -> OperationalLossAnalysis:
    """Summarize observed operational-loss frequency, severity, and concentration.

    Loss amounts must be positive net amounts in one currency and unit. The supplied
    observation period annualizes historical totals and counts arithmetically; it does
    not turn them into forecasts. Events at or above ``materiality_threshold`` are
    reported as material.
    """

    losses = _validated_losses(loss_events)
    years = _validated_number(
        observation_years,
        name="observation_years",
        allow_zero=False,
    )
    threshold = _validated_number(
        materiality_threshold,
        name="materiality_threshold",
        allow_zero=True,
    )
    material_event_ids = _material_event_ids(
        loss_events,
        losses,
        materiality_threshold,
        threshold,
    )

    ordered_losses = sorted(losses.items(), key=lambda item: (-item[1], item[0]))
    loss_values = [loss for _, loss in ordered_losses]
    total_loss = _finite_sum(loss_values, name="total operational loss")
    material_values = [loss for event_id, loss in ordered_losses if event_id in material_event_ids]
    material_loss = _finite_sum(material_values, name="material operational loss")

    events = tuple(
        OperationalLossEvent(
            event_id=event_id,
            loss_amount=loss,
            share_of_total_loss=_finite_ratio(
                loss,
                total_loss,
                name=f"total-loss share for {event_id}",
            ),
            is_material=event_id in material_event_ids,
        )
        for event_id, loss in ordered_losses
    )

    return OperationalLossAnalysis(
        event_count=len(events),
        observation_years=years,
        materiality_threshold=threshold,
        total_loss=total_loss,
        annualized_loss=_finite_ratio(
            total_loss,
            years,
            name="annualized operational loss",
        ),
        annualized_event_frequency=_finite_ratio(
            len(events),
            years,
            name="annualized event frequency",
        ),
        mean_loss=_finite_ratio(total_loss, len(events), name="mean operational loss"),
        median_loss=_median(loss_values),
        sample_loss_standard_deviation=_sample_standard_deviation(loss_values),
        largest_event_id=events[0].event_id,
        largest_loss=events[0].loss_amount,
        largest_loss_share=events[0].share_of_total_loss,
        material_event_count=len(material_values),
        material_loss=material_loss,
        material_loss_share=_finite_ratio(
            material_loss,
            total_loss,
            name="material-loss share",
        ),
        annualized_material_event_frequency=_finite_ratio(
            len(material_values),
            years,
            name="annualized material-event frequency",
        ),
        events=events,
    )
