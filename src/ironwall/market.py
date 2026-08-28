"""Optional Yahoo Finance downloader used by the command-line interface."""

from __future__ import annotations

import csv
import math
import re
from collections.abc import Sequence
from datetime import date
from pathlib import Path

TICKER_PATTERN = re.compile(r"^[A-Z0-9][A-Z0-9.\-]{0,14}$")


def _validated_tickers(tickers: Sequence[str]) -> tuple[str, ...]:
    normalized = tuple(ticker.strip().upper() for ticker in tickers)
    if not normalized:
        raise ValueError("At least one ticker is required.")
    if len(set(normalized)) != len(normalized):
        raise ValueError("Ticker symbols must be unique.")
    invalid = [ticker for ticker in normalized if not TICKER_PATTERN.fullmatch(ticker)]
    if invalid:
        raise ValueError(f"Invalid ticker symbol: {invalid[0]!r}.")
    return normalized


def _validated_date_range(start: str, end: str) -> tuple[str, str]:
    try:
        start_date = date.fromisoformat(start)
        end_date = date.fromisoformat(end)
    except ValueError as exc:
        raise ValueError("start and end must use ISO format YYYY-MM-DD.") from exc
    if start_date >= end_date:
        raise ValueError("start must be earlier than end.")
    return start_date.isoformat(), end_date.isoformat()


def download_market_data(
    tickers: Sequence[str],
    *,
    start: str,
    end: str,
    output_path: str | Path,
) -> int:
    """Download adjusted closes and save a validated-compatible CSV."""

    normalized = _validated_tickers(tickers)
    start, end = _validated_date_range(start, end)
    try:
        import yfinance as yf
    except ImportError as exc:
        raise RuntimeError(
            'Live downloads require the market extra: pip install -e ".[market]"'
        ) from exc

    query: str | list[str] = normalized[0] if len(normalized) == 1 else list(normalized)
    data = yf.download(
        query,
        start=start,
        end=end,
        auto_adjust=True,
        progress=False,
    )
    if data is None or data.empty:
        raise RuntimeError("No market data was returned for the requested tickers and dates.")

    try:
        close = data["Close"]
    except KeyError as exc:
        raise RuntimeError("Downloaded data does not contain adjusted closing prices.") from exc
    rows: list[list[str | float]] = []
    if len(normalized) == 1:
        series = close.iloc[:, 0] if getattr(close, "ndim", 1) == 2 else close
        for index, value in series.dropna().items():
            price = float(value)
            if math.isfinite(price) and price > 0:
                rows.append([index.date().isoformat(), price])
        header = ["Date", "Close"]
    else:
        frame = close
        missing = [ticker for ticker in normalized if ticker not in frame.columns]
        if missing:
            raise RuntimeError(f"Downloaded data is missing ticker {missing[0]}.")
        frame = frame.loc[:, list(normalized)].dropna(how="any")
        for index, values in frame.iterrows():
            prices = [float(values[ticker]) for ticker in normalized]
            if all(math.isfinite(price) and price > 0 for price in prices):
                rows.append([index.date().isoformat(), *prices])
        header = ["Date", *normalized]

    if len(rows) < 3:
        raise RuntimeError("Fewer than three complete market observations were downloaded.")

    destination = Path(output_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("w", encoding="utf-8", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(header)
        writer.writerows(rows)
    return len(rows)
