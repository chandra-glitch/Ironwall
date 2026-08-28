import json

from ironwall.metrics import RiskMetrics
from ironwall.report import build_report, classify_risk, render_markdown, save_report


def make_metrics(**overrides):
    values = {
        "return_observations": 50,
        "confidence": 0.95,
        "total_return": 0.05,
        "mean_daily_return": 0.001,
        "annualized_volatility": 0.10,
        "value_at_risk": 0.01,
        "conditional_value_at_risk": 0.015,
        "maximum_drawdown": 0.04,
        "sharpe_ratio": 1.2,
    }
    values.update(overrides)
    return RiskMetrics(**values)


def test_classifier_uses_multiple_risk_dimensions():
    assert classify_risk(make_metrics()) == "LOW"
    assert classify_risk(make_metrics(annualized_volatility=0.25)) == "MEDIUM"
    assert classify_risk(make_metrics(conditional_value_at_risk=0.08)) == "HIGH"


def test_markdown_report_contains_conventions_and_portfolio_details():
    report = build_report(
        make_metrics(),
        source="sample.csv",
        weights={"JPM": 0.7, "BAC": 0.3},
        risk_contributions={"JPM": 0.8, "BAC": 0.2},
    )

    markdown = render_markdown(report)

    assert "# IRONWALL Risk Report" in markdown
    assert "| JPM | 70.00% | 80.00% |" in markdown
    assert "positive loss magnitudes" in markdown


def test_save_json_report(tmp_path):
    report = build_report(make_metrics(), source="sample.csv")
    output = save_report(report, tmp_path / "report.json")
    payload = json.loads(output.read_text(encoding="utf-8"))

    assert payload["project"] == "IRONWALL"
    assert payload["risk_level"] == "LOW"
    assert payload["metrics"]["confidence"] == 0.95


def test_save_report_rejects_unknown_format(tmp_path):
    report = build_report(make_metrics(), source="sample.csv")

    try:
        save_report(report, tmp_path / "report.txt")
    except ValueError as exc:
        assert ".json" in str(exc)
    else:
        raise AssertionError("Expected unsupported report format to fail")
