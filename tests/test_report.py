import json

from ironwall.metrics import RiskMetrics, VaRBacktest
from ironwall.report import (
    build_report,
    build_var_backtest_report,
    classify_risk,
    render_markdown,
    render_var_backtest_markdown,
    save_report,
    save_var_backtest_report,
)


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


def test_var_backtest_report_is_machine_and_human_readable(tmp_path):
    result = VaRBacktest(
        confidence=0.95,
        window=10,
        forecast_observations=20,
        exceptions=2,
        expected_exceptions=1.0,
        exception_rate=0.10,
        expected_exception_rate=0.05,
        coverage_ratio=2.0,
        kupiec_statistic=0.5,
        kupiec_p_value=0.4795,
    )
    report = build_var_backtest_report(result, source="sample.csv")

    markdown = render_var_backtest_markdown(report)
    output = save_var_backtest_report(report, tmp_path / "backtest.json")
    payload = json.loads(output.read_text(encoding="utf-8"))

    assert "Observed exceptions | 2" in markdown
    assert payload["report_type"] == "historical_var_backtest"
    assert payload["result"]["kupiec_p_value"] == 0.4795
