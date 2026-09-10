"""Portfolio rebalance turnover and transaction-cost estimation."""

from __future__ import annotations

import math
from collections.abc import Mapping
from dataclasses import dataclass

__all__ = ["RebalanceAnalysis", "RebalanceTrade", "analyze_rebalance"]


@dataclass(frozen=True)
class RebalanceTrade:
    """One asset's required change from current to target allocation."""

    asset: str
    current_weight: float
    target_weight: float
    weight_change: float
    trade_value: float

    @property
    def side(self) -> str:
        if self.weight_change > 0.0:
            return "BUY"
        if self.weight_change < 0.0:
            return "SELL"
        return "HOLD"

    def to_dict(self) -> dict[str, str | float]:
        return {
            "asset": self.asset,
            "side": self.side,
            "current_weight": self.current_weight,
            "target_weight": self.target_weight,
            "weight_change": self.weight_change,
            "trade_value": self.trade_value,
        }


@dataclass(frozen=True)
class RebalanceAnalysis:
    """Turnover, cost estimate, and deterministic per-asset trades."""

    portfolio_value: float
    cost_bps: float
    one_way_turnover: float
    gross_trade_value: float
    estimated_transaction_cost: float
    trades: tuple[RebalanceTrade, ...]

    @property
    def trade_count(self) -> int:
        return sum(trade.side != "HOLD" for trade in self.trades)

    def to_dict(self) -> dict[str, object]:
        """Return a JSON-serializable representation of the analysis."""

        return {
            "portfolio_value": self.portfolio_value,
            "cost_bps": self.cost_bps,
            "one_way_turnover": self.one_way_turnover,
            "gross_trade_value": self.gross_trade_value,
            "estimated_transaction_cost": self.estimated_transaction_cost,
            "trade_count": self.trade_count,
            "trades": [trade.to_dict() for trade in self.trades],
        }


def _validated_weights(weights: Mapping[str, float], *, name: str) -> dict[str, float]:
    if not weights:
        raise ValueError(f"{name} weights must contain at least one asset.")

    parsed: dict[str, float] = {}
    for asset, value in weights.items():
        if not isinstance(asset, str) or not asset or asset.strip() != asset:
            raise ValueError(f"{name} weight asset names must be non-empty and unpadded.")
        if isinstance(value, bool):
            raise ValueError(f"{name} weights must be numeric values.")
        try:
            parsed_value = float(value)
        except (TypeError, ValueError) as error:
            raise ValueError(f"{name} weights must be numeric values.") from error
        if not math.isfinite(parsed_value) or parsed_value < 0.0:
            raise ValueError(f"{name} weights must be finite and non-negative.")
        parsed[asset] = parsed_value

    if not math.isclose(math.fsum(parsed.values()), 1.0, rel_tol=0.0, abs_tol=1e-6):
        raise ValueError(f"{name} weights must sum to 1.0.")
    return parsed


def _validated_positive_number(value: float, *, name: str) -> float:
    if isinstance(value, bool):
        raise ValueError(f"{name} must be a positive finite number.")
    try:
        parsed = float(value)
    except (TypeError, ValueError) as error:
        raise ValueError(f"{name} must be a positive finite number.") from error
    if not math.isfinite(parsed) or parsed <= 0.0:
        raise ValueError(f"{name} must be a positive finite number.")
    return parsed


def _validated_cost_bps(cost_bps: float) -> float:
    if isinstance(cost_bps, bool):
        raise ValueError("cost_bps must be finite and between 0 and 10,000.")
    try:
        parsed = float(cost_bps)
    except (TypeError, ValueError) as error:
        raise ValueError("cost_bps must be finite and between 0 and 10,000.") from error
    if not math.isfinite(parsed) or not 0.0 <= parsed <= 10_000.0:
        raise ValueError("cost_bps must be finite and between 0 and 10,000.")
    return parsed


def analyze_rebalance(
    current_weights: Mapping[str, float],
    target_weights: Mapping[str, float],
    *,
    portfolio_value: float,
    cost_bps: float = 0.0,
) -> RebalanceAnalysis:
    """Calculate allocation turnover, trade values, and proportional costs.

    Assets missing from either allocation are treated as having zero weight.
    ``cost_bps`` is applied to gross traded value across both buys and sells.
    """

    current = _validated_weights(current_weights, name="Current")
    target = _validated_weights(target_weights, name="Target")
    portfolio_value = _validated_positive_number(portfolio_value, name="portfolio_value")
    cost_bps = _validated_cost_bps(cost_bps)

    trades_list = []
    for asset in sorted(set(current) | set(target)):
        current_weight = current.get(asset, 0.0)
        target_weight = target.get(asset, 0.0)
        weight_change = target_weight - current_weight
        trades_list.append(
            RebalanceTrade(
                asset=asset,
                current_weight=current_weight,
                target_weight=target_weight,
                weight_change=weight_change,
                trade_value=weight_change * portfolio_value,
            )
        )
    trades = tuple(trades_list)
    gross_turnover = math.fsum(abs(trade.weight_change) for trade in trades)
    gross_trade_value = gross_turnover * portfolio_value

    return RebalanceAnalysis(
        portfolio_value=portfolio_value,
        cost_bps=cost_bps,
        one_way_turnover=0.5 * gross_turnover,
        gross_trade_value=gross_trade_value,
        estimated_transaction_cost=gross_trade_value * cost_bps / 10_000.0,
        trades=trades,
    )
