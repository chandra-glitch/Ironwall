"""Long/short position exposure and leverage diagnostics."""

from __future__ import annotations

import math
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Literal

PositionSide = Literal["long", "short", "flat"]


@dataclass(frozen=True)
class PositionExposure:
    """One signed position expressed relative to portfolio net asset value."""

    asset: str
    notional: float
    side: PositionSide
    nav_fraction: float
    absolute_nav_fraction: float

    def to_dict(self) -> dict[str, str | float]:
        """Return strict-JSON-ready position values."""

        return {
            "asset": self.asset,
            "notional": self.notional,
            "side": self.side,
            "nav_fraction": self.nav_fraction,
            "absolute_nav_fraction": self.absolute_nav_fraction,
        }


@dataclass(frozen=True)
class PositionExposureAnalysis:
    """Aggregate signed exposure and leverage diagnostics."""

    net_asset_value: float
    position_count: int
    long_positions: int
    short_positions: int
    flat_positions: int
    long_exposure: float
    short_exposure: float
    gross_exposure: float
    net_exposure: float
    long_leverage: float
    short_leverage: float
    gross_leverage: float
    net_leverage: float
    positions: tuple[PositionExposure, ...]

    def to_dict(self) -> dict[str, object]:
        """Return strict-JSON-ready values in deterministic asset order."""

        return {
            "net_asset_value": self.net_asset_value,
            "position_count": self.position_count,
            "long_positions": self.long_positions,
            "short_positions": self.short_positions,
            "flat_positions": self.flat_positions,
            "long_exposure": self.long_exposure,
            "short_exposure": self.short_exposure,
            "gross_exposure": self.gross_exposure,
            "net_exposure": self.net_exposure,
            "long_leverage": self.long_leverage,
            "short_leverage": self.short_leverage,
            "gross_leverage": self.gross_leverage,
            "net_leverage": self.net_leverage,
            "positions": [position.to_dict() for position in self.positions],
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


def _validated_asset(asset: object) -> str:
    if not isinstance(asset, str) or not asset or asset.strip() != asset:
        raise ValueError("asset names must be non-empty strings without padding.")
    return asset


def _finite_sum(values: list[float], *, name: str) -> float:
    try:
        total = math.fsum(values)
    except OverflowError as error:
        raise ValueError(f"{name} exceeds the supported numeric range.") from error
    if not math.isfinite(total):
        raise ValueError(f"{name} exceeds the supported numeric range.")
    return total


def _finite_ratio(value: float, divisor: float, *, name: str) -> float:
    try:
        ratio = value / divisor
    except OverflowError as error:
        raise ValueError(f"{name} exceeds the supported numeric range.") from error
    if not math.isfinite(ratio):
        raise ValueError(f"{name} exceeds the supported numeric range.")
    return ratio


def analyze_position_exposure(
    positions: Mapping[str, float],
    net_asset_value: float,
) -> PositionExposureAnalysis:
    """Measure long, short, gross, and net exposure relative to positive NAV.

    Position notionals must use one base currency. Positive values are long positions, negative
    values are short positions, and zero values are retained as flat positions.
    """

    if not isinstance(positions, Mapping) or not positions:
        raise ValueError("positions must be a non-empty mapping of assets to signed notionals.")

    nav = _validated_number(net_asset_value, name="net_asset_value")
    if nav <= 0:
        raise ValueError("net_asset_value must be greater than zero.")

    parsed_positions: dict[str, float] = {}
    for raw_asset, raw_notional in positions.items():
        asset = _validated_asset(raw_asset)
        notional = _validated_number(raw_notional, name=f"notional for {asset!r}")
        parsed_positions[asset] = 0.0 if notional == 0 else notional

    long_values = [value for value in parsed_positions.values() if value > 0]
    short_values = [-value for value in parsed_positions.values() if value < 0]
    long_exposure = _finite_sum(long_values, name="long exposure")
    short_exposure = _finite_sum(short_values, name="short exposure")
    gross_exposure = _finite_sum(
        [long_exposure, short_exposure],
        name="gross exposure",
    )
    net_exposure = _finite_sum(
        [long_exposure, -short_exposure],
        name="net exposure",
    )

    position_details: list[PositionExposure] = []
    for asset in sorted(parsed_positions):
        notional = parsed_positions[asset]
        side: PositionSide = "long" if notional > 0 else "short" if notional < 0 else "flat"
        position_details.append(
            PositionExposure(
                asset=asset,
                notional=notional,
                side=side,
                nav_fraction=_finite_ratio(notional, nav, name=f"NAV fraction for {asset!r}"),
                absolute_nav_fraction=_finite_ratio(
                    abs(notional),
                    nav,
                    name=f"absolute NAV fraction for {asset!r}",
                ),
            )
        )

    return PositionExposureAnalysis(
        net_asset_value=nav,
        position_count=len(position_details),
        long_positions=len(long_values),
        short_positions=len(short_values),
        flat_positions=len(position_details) - len(long_values) - len(short_values),
        long_exposure=long_exposure,
        short_exposure=short_exposure,
        gross_exposure=gross_exposure,
        net_exposure=net_exposure,
        long_leverage=_finite_ratio(long_exposure, nav, name="long leverage"),
        short_leverage=_finite_ratio(short_exposure, nav, name="short leverage"),
        gross_leverage=_finite_ratio(gross_exposure, nav, name="gross leverage"),
        net_leverage=_finite_ratio(net_exposure, nav, name="net leverage"),
        positions=tuple(position_details),
    )
