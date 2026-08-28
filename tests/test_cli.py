import json
from pathlib import Path

from ironwall.cli import main, parse_weights

ROOT = Path(__file__).resolve().parents[1]


def test_parse_weights():
    assert parse_weights("JPM=0.5,BAC=0.3,GS=0.2") == {
        "JPM": 0.5,
        "BAC": 0.3,
        "GS": 0.2,
    }


def test_single_asset_cli_writes_json_report(tmp_path, capsys):
    output = tmp_path / "risk.json"

    exit_code = main(
        [
            "analyze",
            "--csv",
            str(ROOT / "data" / "sample_market_data.csv"),
            "--output",
            str(output),
        ]
    )

    assert exit_code == 0
    assert "Risk level" in capsys.readouterr().out
    assert json.loads(output.read_text(encoding="utf-8"))["project"] == "IRONWALL"


def test_portfolio_cli_runs(capsys):
    exit_code = main(
        [
            "portfolio",
            "--csv",
            str(ROOT / "data" / "sample_portfolio.csv"),
            "--weights",
            "JPM=0.5,BAC=0.3,GS=0.2",
        ]
    )

    assert exit_code == 0
    assert "Risk contribution" in capsys.readouterr().out


def test_cli_returns_error_for_invalid_weights(capsys):
    exit_code = main(
        [
            "portfolio",
            "--csv",
            str(ROOT / "data" / "sample_portfolio.csv"),
            "--weights",
            "JPM=1.0",
        ]
    )

    assert exit_code == 2
    assert "missing weights" in capsys.readouterr().err


def test_fetch_validates_before_loading_optional_dependency(tmp_path, capsys):
    exit_code = main(
        [
            "fetch",
            "bad ticker!",
            "--start",
            "2025-01-01",
            "--end",
            "2026-01-01",
            "--output",
            str(tmp_path / "market.csv"),
        ]
    )

    assert exit_code == 2
    assert "Invalid ticker" in capsys.readouterr().err
