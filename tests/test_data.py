from datetime import date

import pytest

from ironwall.data import load_portfolio_prices, load_price_series


def test_load_price_series(tmp_path):
    csv_path = tmp_path / "prices.csv"
    csv_path.write_text(
        "Date,Close\n2026-01-01,100\n2026-01-02,102.5\n2026-01-03,101\n",
        encoding="utf-8",
    )

    series = load_price_series(csv_path)

    assert series.dates == (
        date(2026, 1, 1),
        date(2026, 1, 2),
        date(2026, 1, 3),
    )
    assert series.prices == (100.0, 102.5, 101.0)


@pytest.mark.parametrize(
    "content, message",
    [
        ("Date,Open\n2026-01-01,100\n", "Date and Close"),
        (
            "Date,Close\n2026-01-02,100\n2026-01-01,101\n2026-01-03,102\n",
            "strictly increasing",
        ),
        (
            "Date,Close\n2026-01-01,100\n2026-01-02,0\n2026-01-03,102\n",
            "positive finite",
        ),
        (
            "Date,Close\nnot-a-date,100\n2026-01-02,101\n2026-01-03,102\n",
            "ISO format",
        ),
    ],
)
def test_load_price_series_rejects_bad_data(tmp_path, content, message):
    csv_path = tmp_path / "bad.csv"
    csv_path.write_text(content, encoding="utf-8")

    with pytest.raises(ValueError, match=message):
        load_price_series(csv_path)


def test_load_portfolio_prices(tmp_path):
    csv_path = tmp_path / "portfolio.csv"
    csv_path.write_text(
        "Date,JPM,BAC\n2026-01-01,100,50\n2026-01-02,102,51\n2026-01-03,101,52\n",
        encoding="utf-8",
    )

    portfolio = load_portfolio_prices(csv_path)

    assert portfolio.asset_prices == {
        "JPM": (100.0, 102.0, 101.0),
        "BAC": (50.0, 51.0, 52.0),
    }


def test_load_portfolio_requires_two_assets(tmp_path):
    csv_path = tmp_path / "portfolio.csv"
    csv_path.write_text(
        "Date,JPM\n2026-01-01,100\n2026-01-02,102\n2026-01-03,101\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="at least two asset"):
        load_portfolio_prices(csv_path)


@pytest.mark.parametrize(
    "loader, content, message",
    [
        (
            load_price_series,
            "Date,Close,Volume\n2026-01-01,100,10\n2026-01-02,101,11\n2026-01-03,102,12\n",
            "exactly Date and Close",
        ),
        (
            load_price_series,
            "Date,Close\n2026-01-01,100,unexpected\n2026-01-02,101\n2026-01-03,102\n",
            "Row 2: contains more values",
        ),
        (
            load_portfolio_prices,
            "Date,JPM,BAC\n2026-01-01,100,50,unexpected\n2026-01-02,101,51\n2026-01-03,102,52\n",
            "Row 2: contains more values",
        ),
        (
            load_portfolio_prices,
            "Date,JPM,JPM\n2026-01-01,100,50\n2026-01-02,101,51\n2026-01-03,102,52\n",
            "must be unique",
        ),
        (
            load_portfolio_prices,
            "Date, JPM,BAC\n2026-01-01,100,50\n2026-01-02,101,51\n2026-01-03,102,52\n",
            "leading or trailing whitespace",
        ),
        (
            load_portfolio_prices,
            "Date,JPM,\n2026-01-01,100,50\n2026-01-02,101,51\n2026-01-03,102,52\n",
            "must be non-empty",
        ),
    ],
)
def test_loaders_reject_malformed_csv_shapes(tmp_path, loader, content, message):
    csv_path = tmp_path / "malformed.csv"
    csv_path.write_text(content, encoding="utf-8")

    with pytest.raises(ValueError, match=message):
        loader(csv_path)


def test_data_errors_use_physical_line_numbers(tmp_path):
    csv_path = tmp_path / "prices.csv"
    csv_path.write_text(
        "Date,Close\n2026-01-01,100\n\n2026-01-03,not-a-price\n2026-01-04,102\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="Row 4: Close must be numeric"):
        load_price_series(csv_path)
