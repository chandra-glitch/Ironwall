# Rebalance turnover and cost estimation

Moving from a current allocation to a target allocation creates trading activity and costs that
headline risk metrics do not show. IRONWALL can calculate deterministic buy and sell requirements,
portfolio turnover, gross traded value, and a proportional transaction-cost estimate.

```python
from ironwall.rebalance import analyze_rebalance

analysis = analyze_rebalance(
    current_weights={"JPM": 0.60, "BAC": 0.40},
    target_weights={"JPM": 0.40, "BAC": 0.60},
    portfolio_value=100_000,
    cost_bps=10,
)

print(analysis.to_dict())
```

The weight change for each asset is `target_weight - current_weight`; positive values are buys and
negative values are sells. Assets missing from either allocation are treated as zero-weight, so
the analysis supports opening and fully exiting positions.

IRONWALL reports one-way turnover using the standard half-sum convention:

```text
one_way_turnover = 0.5 * sum(abs(target_weight - current_weight))
gross_trade_value = portfolio_value * sum(abs(target_weight - current_weight))
estimated_transaction_cost = gross_trade_value * cost_bps / 10,000
```

Gross traded value counts both sides of a fully invested rebalance. In the example, selling
20,000 and buying 20,000 produces 20% one-way turnover, 40,000 of gross traded value, and an
estimated cost of 40 at 10 basis points.

Current and target weights are validated independently. Each allocation must contain at least one
asset, use non-negative finite weights, and sum to one within a small numerical tolerance. Asset
names must be non-empty and have no surrounding whitespace. Portfolio value must be positive and
finite; cost must be between 0 and 10,000 basis points.

## Interpretation and limitations

This is a static, proportional cost model. `cost_bps` is applied equally to buys and sells and can
represent an analyst-selected combination of commissions, spread, and simple slippage. The model
does not estimate market impact, fixed fees, taxes, bid-ask asymmetry, minimum trade sizes,
liquidity constraints, price movement during execution, or post-cost target drift.

Use instrument- and market-specific assumptions for real portfolios. The estimate is for planning
and comparison, not an execution instruction or guarantee of realized costs.
