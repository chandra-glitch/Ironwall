import csv
import sys
from datetime import datetime
from types import SimpleNamespace

import pytest

from ironwall.market import download_market_data


class FakeSeries:
    ndim = 1

    def dropna(self):
        return self

    def items(self):
        return iter(
            [
                (datetime(2026, 1, 2), 100.0),
                (datetime(2026, 1, 5), 102.0),
                (datetime(2026, 1, 6), 101.0),
            ]
        )


class FakeFrame:
    columns = ("JPM", "BAC")

    @property
    def loc(self):
        return self

    def __getitem__(self, key):
        return self

    def dropna(self, how):
        assert how == "any"
        return self

    def iterrows(self):
        return iter(
            [
                (datetime(2026, 1, 2), {"JPM": 100.0, "BAC": 50.0}),
                (datetime(2026, 1, 5), {"JPM": 102.0, "BAC": 50.5}),
                (datetime(2026, 1, 6), {"JPM": 101.0, "BAC": 49.8}),
            ]
        )


class FakeDownload:
    empty = False

    def __init__(self, close):
        self.close = close

    def __getitem__(self, key):
        if key != "Close":
            raise KeyError(key)
        return self.close


def install_fake_yfinance(monkeypatch, close):
    fake_module = SimpleNamespace(download=lambda *args, **kwargs: FakeDownload(close))
    monkeypatch.setitem(sys.modules, "yfinance", fake_module)


def test_download_single_ticker_creates_analyzable_csv(tmp_path, monkeypatch):
    install_fake_yfinance(monkeypatch, FakeSeries())
    output = tmp_path / "jpm.csv"

    rows = download_market_data(
        ["jpm"],
        start="2026-01-01",
        end="2026-02-01",
        output_path=output,
    )

    assert rows == 3
    with output.open(encoding="utf-8", newline="") as file:
        saved = list(csv.reader(file))
    assert saved[0] == ["Date", "Close"]
    assert saved[1] == ["2026-01-02", "100.0"]


def test_download_multiple_tickers_creates_portfolio_csv(tmp_path, monkeypatch):
    install_fake_yfinance(monkeypatch, FakeFrame())
    output = tmp_path / "banks.csv"

    rows = download_market_data(
        ["JPM", "BAC"],
        start="2026-01-01",
        end="2026-02-01",
        output_path=output,
    )

    assert rows == 3
    with output.open(encoding="utf-8", newline="") as file:
        saved = list(csv.reader(file))
    assert saved[0] == ["Date", "JPM", "BAC"]
    assert saved[-1] == ["2026-01-06", "101.0", "49.8"]


def test_provider_failure_is_reported_without_creating_output(tmp_path, monkeypatch):
    def fail_download(*args, **kwargs):
        raise ConnectionError("provider unavailable")

    monkeypatch.setitem(sys.modules, "yfinance", SimpleNamespace(download=fail_download))
    output = tmp_path / "jpm.csv"

    with pytest.raises(RuntimeError, match="Market data download failed: provider unavailable"):
        download_market_data(
            ["JPM"],
            start="2026-01-01",
            end="2026-02-01",
            output_path=output,
        )

    assert not output.exists()


def test_failed_atomic_replace_preserves_existing_download(tmp_path, monkeypatch):
    install_fake_yfinance(monkeypatch, FakeSeries())
    output = tmp_path / "jpm.csv"
    output.write_text("previous valid data\n", encoding="utf-8")

    def fail_replace(source, destination):
        raise OSError("simulated replacement failure")

    monkeypatch.setattr("ironwall.market.os.replace", fail_replace)

    with pytest.raises(OSError, match="simulated replacement failure"):
        download_market_data(
            ["JPM"],
            start="2026-01-01",
            end="2026-02-01",
            output_path=output,
        )

    assert output.read_text(encoding="utf-8") == "previous valid data\n"
    assert not list(tmp_path.glob(".jpm.csv.*.tmp"))
