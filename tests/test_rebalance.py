import json

import pytest

from ironwall.rebalance import analyze_rebalance


def test_rebalance_calculates_turnover_trades_and_cost():
    result = analyze_rebalance(
        {"JPM": 0.6, "BAC": 0.4},
        {"JPM": 0.4, "BAC": 0.6},
        portfolio_value=100_000,
        cost_bps=10,
    )
    trades = {trade.asset: trade for trade in result.trades}

    assert result.one_way_turnover == pytest.approx(0.2)
    assert result.gross_trade_value == pytest.approx(40_000)
    assert result.estimated_transaction_cost == pytest.approx(40)
    assert result.trade_count == 2
    assert trades["JPM"].side == "SELL"
    assert trades["JPM"].weight_change == pytest.approx(-0.2)
    assert trades["JPM"].trade_value == pytest.approx(-20_000)
    assert trades["BAC"].side == "BUY"
    assert trades["BAC"].trade_value == pytest.approx(20_000)


def test_rebalance_supports_asset_entries_and_exits():
    result = analyze_rebalance(
        {"JPM": 1.0},
        {"GS": 1.0},
        portfolio_value=1_000,
        cost_bps=25,
    )

    assert [trade.asset for trade in result.trades] == ["GS", "JPM"]
    assert [trade.side for trade in result.trades] == ["BUY", "SELL"]
    assert result.one_way_turnover == pytest.approx(1.0)
    assert result.gross_trade_value == pytest.approx(2_000)
    assert result.estimated_transaction_cost == pytest.approx(5.0)


def test_unchanged_allocation_has_no_turnover():
    weights = {"JPM": 0.7, "BAC": 0.3}

    result = analyze_rebalance(weights, weights, portfolio_value=50_000, cost_bps=15)

    assert result.one_way_turnover == pytest.approx(0.0)
    assert result.gross_trade_value == pytest.approx(0.0)
    assert result.estimated_transaction_cost == pytest.approx(0.0)
    assert result.trade_count == 0
    assert all(trade.side == "HOLD" for trade in result.trades)


def test_rebalance_analysis_is_json_ready():
    result = analyze_rebalance(
        {"JPM": 0.75, "BAC": 0.25},
        {"JPM": 0.5, "BAC": 0.5},
        portfolio_value=10_000,
    )

    payload = json.loads(json.dumps(result.to_dict()))
    assert payload["one_way_turnover"] == pytest.approx(0.25)
    assert payload["gross_trade_value"] == pytest.approx(5_000)
    assert payload["trade_count"] == 2
    assert {trade["side"] for trade in payload["trades"]} == {"BUY", "SELL"}


@pytest.mark.parametrize(
    "current, target, portfolio_value, cost_bps, message",
    [
        ({}, {"JPM": 1.0}, 1_000, 0, "Current weights"),
        ({"JPM": 1.0}, {}, 1_000, 0, "Target weights"),
        ({"JPM": 0.9}, {"JPM": 1.0}, 1_000, 0, "Current weights must sum"),
        ({"JPM": 1.0}, {"JPM": 0.9}, 1_000, 0, "Target weights must sum"),
        ({"JPM": 1.1, "BAC": -0.1}, {"JPM": 1.0}, 1_000, 0, "non-negative"),
        ({"JPM": float("inf")}, {"JPM": 1.0}, 1_000, 0, "finite"),
        ({"JPM": float("nan")}, {"JPM": 1.0}, 1_000, 0, "finite"),
        ({" JPM": 1.0}, {"JPM": 1.0}, 1_000, 0, "asset names"),
        ({"JPM": True}, {"JPM": 1.0}, 1_000, 0, "numeric values"),
        ({"JPM": 1.0}, {"JPM": 1.0}, 0, 0, "portfolio_value"),
        ({"JPM": 1.0}, {"JPM": 1.0}, float("inf"), 0, "portfolio_value"),
        ({"JPM": 1.0}, {"JPM": 1.0}, True, 0, "portfolio_value"),
        ({"JPM": 1.0}, {"JPM": 1.0}, 1_000, -1, "cost_bps"),
        ({"JPM": 1.0}, {"JPM": 1.0}, 1_000, float("nan"), "cost_bps"),
        ({"JPM": 1.0}, {"JPM": 1.0}, 1_000, 10_001, "cost_bps"),
        ({"JPM": 1.0}, {"JPM": 1.0}, 1_000, True, "cost_bps"),
    ],
)
def test_invalid_rebalance_inputs_are_rejected(
    current,
    target,
    portfolio_value,
    cost_bps,
    message,
):
    with pytest.raises(ValueError, match=message):
        analyze_rebalance(
            current,
            target,
            portfolio_value=portfolio_value,
            cost_bps=cost_bps,
        )
