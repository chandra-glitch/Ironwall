"""Command-line entry point for reproducible IRONWALL analyses."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from datetime import date, timedelta
from pathlib import Path

from ironwall.data import load_portfolio_prices, load_price_series
from ironwall.market import download_market_data
from ironwall.metrics import analyze_prices
from ironwall.portfolio import analyze_portfolio
from ironwall.report import build_report, render_markdown, save_report


def _add_analysis_options(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--confidence", type=float, default=0.95)
    parser.add_argument("--periods-per-year", type=int, default=252)
    parser.add_argument("--risk-free-rate", type=float, default=0.0)
    parser.add_argument("--output", type=Path, help="Optional .json or .md report path")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="ironwall",
        description="Transparent single-asset and portfolio risk analytics.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    analyze_parser = subparsers.add_parser("analyze", help="Analyze a Date,Close CSV")
    analyze_parser.add_argument("--csv", type=Path, required=True)
    _add_analysis_options(analyze_parser)

    portfolio_parser = subparsers.add_parser("portfolio", help="Analyze a wide Date,TICKER... CSV")
    portfolio_parser.add_argument("--csv", type=Path, required=True)
    portfolio_parser.add_argument(
        "--weights",
        required=True,
        help="Comma-separated weights, for example JPM=0.5,BAC=0.3,GS=0.2",
    )
    _add_analysis_options(portfolio_parser)

    fetch_parser = subparsers.add_parser("fetch", help="Download adjusted closing prices")
    fetch_parser.add_argument("tickers", nargs="+")
    fetch_parser.add_argument(
        "--start",
        default=(date.today() - timedelta(days=730)).isoformat(),
    )
    fetch_parser.add_argument(
        "--end",
        default=(date.today() + timedelta(days=1)).isoformat(),
        help="Exclusive end date (default: tomorrow)",
    )
    fetch_parser.add_argument("--output", type=Path, required=True)
    return parser


def parse_weights(value: str) -> dict[str, float]:
    weights: dict[str, float] = {}
    for item in value.split(","):
        if "=" not in item:
            raise ValueError("Each weight must use ASSET=value format.")
        asset, raw_weight = (part.strip() for part in item.split("=", 1))
        if not asset or asset in weights:
            raise ValueError("Weight asset names must be non-empty and unique.")
        try:
            weights[asset] = float(raw_weight)
        except ValueError as exc:
            raise ValueError(f"Weight for {asset} must be numeric.") from exc
    return weights


def _emit_report(report, output: Path | None) -> None:
    print(render_markdown(report))
    if output is not None:
        saved_path = save_report(report, output)
        print(f"Saved report: {saved_path}")


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        if args.command == "analyze":
            series = load_price_series(args.csv)
            metrics = analyze_prices(
                series.prices,
                confidence=args.confidence,
                periods_per_year=args.periods_per_year,
                annual_risk_free_rate=args.risk_free_rate,
            )
            _emit_report(build_report(metrics, source=str(args.csv)), args.output)
        elif args.command == "portfolio":
            portfolio = load_portfolio_prices(args.csv)
            analysis = analyze_portfolio(
                portfolio.asset_prices,
                parse_weights(args.weights),
                confidence=args.confidence,
                periods_per_year=args.periods_per_year,
                annual_risk_free_rate=args.risk_free_rate,
            )
            report = build_report(
                analysis.metrics,
                source=str(args.csv),
                weights=analysis.weights,
                risk_contributions=analysis.risk_contributions,
            )
            _emit_report(report, args.output)
        elif args.command == "fetch":
            rows = download_market_data(
                args.tickers,
                start=args.start,
                end=args.end,
                output_path=args.output,
            )
            print(f"Saved {rows} aligned observations to {args.output}")
        else:
            parser.error("Unknown command")
    except (OSError, RuntimeError, ValueError) as exc:
        print(f"IRONWALL error: {exc}", file=sys.stderr)
        return 2
    return 0
