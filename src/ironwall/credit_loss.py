"""Deterministic expected and independent credit-loss diagnostics."""

from __future__ import annotations

import math
from collections.abc import Mapping
from dataclasses import dataclass
from decimal import Decimal
from numbers import Real


@dataclass(frozen=True)
class CreditExposureLoss:
    """Loss measures for one obligor over the supplied risk horizon."""

    obligor: str
    exposure_at_default: float
    probability_of_default: float
    loss_given_default: float
    loss_if_default: float
    expected_loss: float
    loss_standard_deviation: float
    exposure_weight: float
    expected_loss_contribution: float | None
    loss_variance_contribution: float | None

    def to_dict(self) -> dict[str, object]:
        """Return strict-JSON-ready exposure values."""

        return {
            "obligor": self.obligor,
            "exposure_at_default": self.exposure_at_default,
            "probability_of_default": self.probability_of_default,
            "loss_given_default": self.loss_given_default,
            "loss_if_default": self.loss_if_default,
            "expected_loss": self.expected_loss,
            "loss_standard_deviation": self.loss_standard_deviation,
            "exposure_weight": self.exposure_weight,
            "expected_loss_contribution": self.expected_loss_contribution,
            "loss_variance_contribution": self.loss_variance_contribution,
        }


@dataclass(frozen=True)
class CreditLossAnalysis:
    """Portfolio credit-loss measures under an independent-default model."""

    exposure_count: int
    total_exposure_at_default: float
    expected_loss: float
    expected_loss_rate: float
    exposure_weighted_probability_of_default: float
    exposure_weighted_loss_given_default: float
    independent_unexpected_loss: float
    exposures: tuple[CreditExposureLoss, ...]

    def to_dict(self) -> dict[str, object]:
        """Return strict-JSON-ready values in deterministic obligor order."""

        return {
            "exposure_count": self.exposure_count,
            "total_exposure_at_default": self.total_exposure_at_default,
            "expected_loss": self.expected_loss,
            "expected_loss_rate": self.expected_loss_rate,
            "exposure_weighted_probability_of_default": (
                self.exposure_weighted_probability_of_default
            ),
            "exposure_weighted_loss_given_default": (self.exposure_weighted_loss_given_default),
            "independent_unexpected_loss": self.independent_unexpected_loss,
            "exposures": [exposure.to_dict() for exposure in self.exposures],
        }


def _validated_number(
    value: object,
    *,
    name: str,
    strictly_positive: bool = False,
    unit_interval: bool = False,
) -> float:
    if isinstance(value, bool) or not isinstance(value, (Real, Decimal)):
        raise ValueError(f"{name} must be a real numeric value, not boolean or text.")
    try:
        if strictly_positive and value <= 0:
            raise ValueError(f"{name} values must be greater than zero.")
        if unit_interval and not 0 <= value <= 1:
            raise ValueError(f"{name} values must be between 0 and 1 inclusive.")
    except (ArithmeticError, TypeError) as error:
        raise ValueError(f"{name} must be numeric and finite.") from error

    try:
        parsed = float(value)
    except (TypeError, ValueError, OverflowError) as error:
        raise ValueError(f"{name} must be numeric and finite.") from error
    if not math.isfinite(parsed):
        raise ValueError(f"{name} must be numeric and finite.")
    if parsed == 0 and value != 0:
        raise ValueError(f"{name} loses material precision when converted to float.")
    if unit_interval and parsed == 1 and value != 1:
        raise ValueError(f"{name} loses material precision when converted to float.")
    return parsed


def _validated_mapping(
    values: Mapping[str, float],
    *,
    name: str,
    strictly_positive: bool = False,
    unit_interval: bool = False,
) -> dict[str, float]:
    if not isinstance(values, Mapping) or not values:
        raise ValueError(f"{name} must be a non-empty mapping by obligor.")

    parsed: dict[str, float] = {}
    for obligor, raw_value in values.items():
        if not isinstance(obligor, str) or not obligor:
            raise ValueError(f"{name} obligor names must be non-empty strings.")
        if obligor != obligor.strip():
            raise ValueError(f"{name} obligor names cannot contain surrounding whitespace.")

        value = _validated_number(
            raw_value,
            name=f"{name} for {obligor}",
            strictly_positive=strictly_positive,
            unit_interval=unit_interval,
        )
        parsed[obligor] = value
    return parsed


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
    if not math.isfinite(result) or (result == 0 and all(value != 0 for value in values)):
        raise ValueError(f"{name} exceeds the supported numeric range.")
    return 0.0 if result == 0 else result


def _finite_ratio(numerator: float, denominator: float, *, name: str) -> float:
    try:
        result = numerator / denominator
    except (OverflowError, ZeroDivisionError) as error:
        raise ValueError(f"{name} exceeds the supported numeric range.") from error
    if not math.isfinite(result) or (result == 0 and numerator != 0):
        raise ValueError(f"{name} exceeds the supported numeric range.")
    return 0.0 if result == 0 else result


def _require_matching_obligors(
    exposure_at_default: Mapping[str, float],
    probability_of_default: Mapping[str, float],
    loss_given_default: Mapping[str, float],
) -> None:
    expected = set(exposure_at_default)
    for name, values in (
        ("probability_of_default", probability_of_default),
        ("loss_given_default", loss_given_default),
    ):
        missing = expected - set(values)
        extra = set(values) - expected
        if missing or extra:
            details: list[str] = []
            if missing:
                details.append(f"missing {', '.join(sorted(missing))}")
            if extra:
                details.append(f"unknown {', '.join(sorted(extra))}")
            raise ValueError(
                f"{name} obligors must match exposure_at_default: {'; '.join(details)}."
            )


def analyze_credit_loss(
    exposure_at_default: Mapping[str, float],
    probability_of_default: Mapping[str, float],
    loss_given_default: Mapping[str, float],
) -> CreditLossAnalysis:
    """Aggregate one-horizon credit losses from aligned PD, LGD, and EAD inputs.

    Expected loss is ``EAD * PD * LGD``. Unexpected loss is the standard deviation of
    the portfolio loss under Bernoulli defaults that are assumed mutually independent.
    All exposure amounts must use one currency and unit, and all parameters must refer
    to the same risk horizon and scenario.
    """

    ead = _validated_mapping(
        exposure_at_default,
        name="exposure_at_default",
        strictly_positive=True,
    )
    pd = _validated_mapping(
        probability_of_default,
        name="probability_of_default",
        unit_interval=True,
    )
    lgd = _validated_mapping(
        loss_given_default,
        name="loss_given_default",
        unit_interval=True,
    )
    _require_matching_obligors(ead, pd, lgd)

    obligors = tuple(sorted(ead))
    total_ead = _finite_sum([ead[obligor] for obligor in obligors], name="total EAD")
    expected_losses: dict[str, float] = {}
    loss_if_default: dict[str, float] = {}
    loss_standard_deviations: dict[str, float] = {}
    weighted_pd_terms: list[float] = []
    weighted_lgd_terms: list[float] = []

    for obligor in obligors:
        loss_if_default[obligor] = _finite_product(
            [ead[obligor], lgd[obligor]],
            name=f"loss if {obligor} defaults",
        )
        expected_losses[obligor] = _finite_product(
            [loss_if_default[obligor], pd[obligor]],
            name=f"expected loss for {obligor}",
        )
        variance_probability = _finite_product(
            [pd[obligor], 1.0 - pd[obligor]],
            name=f"default variance probability for {obligor}",
        )
        loss_standard_deviations[obligor] = _finite_product(
            [loss_if_default[obligor], math.sqrt(variance_probability)],
            name=f"loss standard deviation for {obligor}",
        )
        weighted_pd_terms.append(
            _finite_product(
                [ead[obligor], pd[obligor]],
                name=f"EAD-weighted PD for {obligor}",
            )
        )
        weighted_lgd_terms.append(
            _finite_product(
                [ead[obligor], lgd[obligor]],
                name=f"EAD-weighted LGD for {obligor}",
            )
        )

    expected_loss = _finite_sum(list(expected_losses.values()), name="expected loss")
    try:
        independent_unexpected_loss = math.hypot(
            *(loss_standard_deviations[obligor] for obligor in obligors)
        )
    except OverflowError as error:
        raise ValueError(
            "independent unexpected loss exceeds the supported numeric range."
        ) from error
    if not math.isfinite(independent_unexpected_loss):
        raise ValueError("independent unexpected loss exceeds the supported numeric range.")

    exposures: list[CreditExposureLoss] = []
    for obligor in obligors:
        expected_loss_contribution = (
            _finite_ratio(
                expected_losses[obligor],
                expected_loss,
                name=f"expected-loss contribution for {obligor}",
            )
            if expected_loss > 0
            else None
        )
        loss_variance_contribution = None
        if independent_unexpected_loss > 0:
            normalized_standard_deviation = _finite_ratio(
                loss_standard_deviations[obligor],
                independent_unexpected_loss,
                name=f"normalized loss standard deviation for {obligor}",
            )
            loss_variance_contribution = _finite_product(
                [normalized_standard_deviation, normalized_standard_deviation],
                name=f"loss-variance contribution for {obligor}",
            )

        exposures.append(
            CreditExposureLoss(
                obligor=obligor,
                exposure_at_default=ead[obligor],
                probability_of_default=pd[obligor],
                loss_given_default=lgd[obligor],
                loss_if_default=loss_if_default[obligor],
                expected_loss=expected_losses[obligor],
                loss_standard_deviation=loss_standard_deviations[obligor],
                exposure_weight=_finite_ratio(
                    ead[obligor],
                    total_ead,
                    name=f"exposure weight for {obligor}",
                ),
                expected_loss_contribution=expected_loss_contribution,
                loss_variance_contribution=loss_variance_contribution,
            )
        )

    return CreditLossAnalysis(
        exposure_count=len(exposures),
        total_exposure_at_default=total_ead,
        expected_loss=expected_loss,
        expected_loss_rate=_finite_ratio(
            expected_loss,
            total_ead,
            name="expected loss rate",
        ),
        exposure_weighted_probability_of_default=_finite_ratio(
            _finite_sum(weighted_pd_terms, name="EAD-weighted PD"),
            total_ead,
            name="exposure-weighted probability of default",
        ),
        exposure_weighted_loss_given_default=_finite_ratio(
            _finite_sum(weighted_lgd_terms, name="EAD-weighted LGD"),
            total_ead,
            name="exposure-weighted loss given default",
        ),
        independent_unexpected_loss=independent_unexpected_loss,
        exposures=tuple(exposures),
    )
