"""Risk classification and human/machine-readable reporting."""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from ironwall.metrics import RiskMetrics, VaRBacktest


@dataclass(frozen=True)
class RiskReport:
    generated_at: str
    source: str
    risk_level: str
    metrics: RiskMetrics
    weights: dict[str, float] | None = None
    risk_contributions: dict[str, float] | None = None

    def to_dict(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "project": "IRONWALL",
            "generated_at": self.generated_at,
            "source": self.source,
            "risk_level": self.risk_level,
            "metrics": self.metrics.to_dict(),
        }
        if self.weights is not None:
            payload["weights"] = self.weights
        if self.risk_contributions is not None:
            payload["risk_contributions"] = self.risk_contributions
        return payload


@dataclass(frozen=True)
class VaRBacktestReport:
    generated_at: str
    source: str
    result: VaRBacktest

    def to_dict(self) -> dict[str, object]:
        return {
            "project": "IRONWALL",
            "report_type": "historical_var_backtest",
            "generated_at": self.generated_at,
            "source": self.source,
            "result": self.result.to_dict(),
        }


def classify_risk(metrics: RiskMetrics) -> str:
    """Apply transparent educational thresholds across four loss dimensions."""

    high_risk = (
        metrics.annualized_volatility >= 0.40
        or metrics.value_at_risk >= 0.05
        or metrics.conditional_value_at_risk >= 0.07
        or metrics.maximum_drawdown >= 0.20
    )
    if high_risk:
        return "HIGH"

    medium_risk = (
        metrics.annualized_volatility >= 0.20
        or metrics.value_at_risk >= 0.02
        or metrics.conditional_value_at_risk >= 0.03
        or metrics.maximum_drawdown >= 0.10
    )
    return "MEDIUM" if medium_risk else "LOW"


def build_report(
    metrics: RiskMetrics,
    *,
    source: str,
    weights: Mapping[str, float] | None = None,
    risk_contributions: Mapping[str, float] | None = None,
) -> RiskReport:
    return RiskReport(
        generated_at=datetime.now(timezone.utc).isoformat(),
        source=source,
        risk_level=classify_risk(metrics),
        metrics=metrics,
        weights=dict(weights) if weights is not None else None,
        risk_contributions=(dict(risk_contributions) if risk_contributions is not None else None),
    )


def build_var_backtest_report(result: VaRBacktest, *, source: str) -> VaRBacktestReport:
    return VaRBacktestReport(
        generated_at=datetime.now(timezone.utc).isoformat(),
        source=source,
        result=result,
    )


def render_markdown(report: RiskReport) -> str:
    metrics = report.metrics
    lines = [
        "# IRONWALL Risk Report",
        "",
        f"- **Generated (UTC):** {report.generated_at}",
        f"- **Source:** {report.source}",
        f"- **Risk level:** **{report.risk_level}**",
        f"- **Confidence:** {metrics.confidence:.1%}",
        "",
        "## Risk metrics",
        "",
        "| Metric | Result |",
        "|---|---:|",
        f"| Return observations | {metrics.return_observations} |",
        f"| Total return | {metrics.total_return:.2%} |",
        f"| Mean daily return | {metrics.mean_daily_return:.3%} |",
        f"| Annualized volatility | {metrics.annualized_volatility:.2%} |",
        f"| Historical VaR | {metrics.value_at_risk:.2%} |",
        f"| Historical CVaR | {metrics.conditional_value_at_risk:.2%} |",
        f"| Maximum drawdown | {metrics.maximum_drawdown:.2%} |",
        f"| Annualized Sharpe ratio | {metrics.sharpe_ratio:.2f} |",
    ]

    if report.weights is not None:
        lines.extend(
            [
                "",
                "## Portfolio allocation and volatility contribution",
                "",
                "| Asset | Weight | Risk contribution |",
                "|---|---:|---:|",
            ]
        )
        contributions = report.risk_contributions or {}
        for asset, weight in report.weights.items():
            lines.append(f"| {asset} | {weight:.2%} | {contributions.get(asset, 0.0):.2%} |")

    lines.extend(
        [
            "",
            "> VaR, CVaR, and drawdown are displayed as positive loss magnitudes.",
            "> The risk label is an educational heuristic, not financial advice.",
        ]
    )
    return "\n".join(lines) + "\n"


def render_var_backtest_markdown(report: VaRBacktestReport) -> str:
    result = report.result
    lines = [
        "# IRONWALL Historical VaR Backtest",
        "",
        f"- **Generated (UTC):** {report.generated_at}",
        f"- **Source:** {report.source}",
        f"- **Confidence:** {result.confidence:.1%}",
        f"- **Rolling window:** {result.window} returns",
        "",
        "## Exception coverage",
        "",
        "| Measure | Result |",
        "|---|---:|",
        f"| Out-of-sample forecasts | {result.forecast_observations} |",
        f"| Observed exceptions | {result.exceptions} |",
        f"| Expected exceptions | {result.expected_exceptions:.2f} |",
        f"| Observed exception rate | {result.exception_rate:.2%} |",
        f"| Expected exception rate | {result.expected_exception_rate:.2%} |",
        f"| Coverage ratio | {result.coverage_ratio:.2f}x |",
        f"| Kupiec LR statistic | {result.kupiec_statistic:.4f} |",
        f"| Kupiec p-value | {result.kupiec_p_value:.4f} |",
        "",
        "> A p-value below 0.05 suggests the observed exception frequency is inconsistent with",
        "> the requested VaR confidence. It is not, by itself, a complete model validation.",
    ]
    return "\n".join(lines) + "\n"


def save_report(report: RiskReport, path: str | Path) -> Path:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    suffix = output_path.suffix.lower()
    if suffix == ".json":
        output_path.write_text(
            json.dumps(report.to_dict(), indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    elif suffix in {".md", ".markdown"}:
        output_path.write_text(render_markdown(report), encoding="utf-8")
    else:
        raise ValueError("Report output must end in .json, .md, or .markdown.")
    return output_path


def save_var_backtest_report(report: VaRBacktestReport, path: str | Path) -> Path:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    suffix = output_path.suffix.lower()
    if suffix == ".json":
        output_path.write_text(
            json.dumps(report.to_dict(), indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    elif suffix in {".md", ".markdown"}:
        output_path.write_text(render_var_backtest_markdown(report), encoding="utf-8")
    else:
        raise ValueError("Backtest output must end in .json, .md, or .markdown.")
    return output_path
