"""CSV loading and validation for market price data."""

from __future__ import annotations

import csv
import math
from dataclasses import dataclass
from datetime import date
from pathlib import Path


@dataclass(frozen=True)
class PriceSeries:
    """A validated, chronologically ordered closing-price series."""

    dates: tuple[date, ...]
    prices: tuple[float, ...]


@dataclass(frozen=True)
class PortfolioPrices:
    """Aligned closing prices for two or more assets."""

    dates: tuple[date, ...]
    asset_prices: dict[str, tuple[float, ...]]


def _parse_date(value: str | None, *, row_number: int) -> date:
    if value is None or not value.strip():
        raise ValueError(f"Row {row_number}: Date is required.")
    try:
        return date.fromisoformat(value.strip())
    except ValueError as exc:
        raise ValueError(
            f"Row {row_number}: Date must use ISO format YYYY-MM-DD, got {value!r}."
        ) from exc


def _parse_price(value: str | None, *, column: str, row_number: int) -> float:
    if value is None or not value.strip():
        raise ValueError(f"Row {row_number}: {column} is required.")
    try:
        price = float(value)
    except ValueError as exc:
        raise ValueError(f"Row {row_number}: {column} must be numeric.") from exc
    if not math.isfinite(price) or price <= 0:
        raise ValueError(f"Row {row_number}: {column} must be a positive finite number.")
    return price


def _validate_date_order(dates: list[date], current: date, *, row_number: int) -> None:
    if dates and current <= dates[-1]:
        raise ValueError(f"Row {row_number}: dates must be strictly increasing with no duplicates.")


def _validate_row_width(row: dict[str | None, object], *, row_number: int) -> None:
    if None in row:
        raise ValueError(f"Row {row_number}: contains more values than the CSV header.")


def _validate_single_asset_header(fieldnames: list[str] | None) -> None:
    if fieldnames != ["Date", "Close"]:
        raise ValueError("Single-asset CSV header must contain exactly Date and Close columns.")


def _validated_portfolio_assets(fieldnames: list[str] | None) -> tuple[str, ...]:
    if not fieldnames or fieldnames[0] != "Date":
        raise ValueError("Portfolio CSV must start with a Date column.")
    if any(not name for name in fieldnames):
        raise ValueError("Portfolio CSV column names must be non-empty.")
    if any(name != name.strip() for name in fieldnames):
        raise ValueError("Portfolio CSV column names cannot have leading or trailing whitespace.")

    assets = tuple(fieldnames[1:])
    if len(assets) < 2:
        raise ValueError("Portfolio CSV must contain at least two asset columns.")
    if len(set(assets)) != len(assets):
        raise ValueError("Portfolio asset column names must be unique.")
    return assets


def load_price_series(path: str | Path) -> PriceSeries:
    """Load a ``Date,Close`` CSV and reject malformed or unsafe observations."""

    csv_path = Path(path)
    dates: list[date] = []
    prices: list[float] = []

    with csv_path.open("r", encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file)
        _validate_single_asset_header(reader.fieldnames)

        for row in reader:
            row_number = reader.line_num
            _validate_row_width(row, row_number=row_number)
            current_date = _parse_date(row.get("Date"), row_number=row_number)
            _validate_date_order(dates, current_date, row_number=row_number)
            dates.append(current_date)
            prices.append(_parse_price(row.get("Close"), column="Close", row_number=row_number))

    if len(prices) < 3:
        raise ValueError("At least three price observations are required for risk analysis.")

    return PriceSeries(tuple(dates), tuple(prices))


def load_portfolio_prices(path: str | Path) -> PortfolioPrices:
    """Load a wide CSV in the form ``Date,JPM,BAC,GS`` with aligned prices."""

    csv_path = Path(path)
    dates: list[date] = []

    with csv_path.open("r", encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file)
        assets = _validated_portfolio_assets(reader.fieldnames)

        asset_prices: dict[str, list[float]] = {asset: [] for asset in assets}
        for row in reader:
            row_number = reader.line_num
            _validate_row_width(row, row_number=row_number)
            current_date = _parse_date(row.get("Date"), row_number=row_number)
            _validate_date_order(dates, current_date, row_number=row_number)
            dates.append(current_date)
            for asset in assets:
                asset_prices[asset].append(
                    _parse_price(row.get(asset), column=asset, row_number=row_number)
                )

    if len(dates) < 3:
        raise ValueError("At least three aligned price observations are required.")

    return PortfolioPrices(
        dates=tuple(dates),
        asset_prices={asset: tuple(values) for asset, values in asset_prices.items()},
    )
