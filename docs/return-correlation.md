# Asset-return correlation analysis

IRONWALL can calculate a Pearson correlation matrix from aligned asset returns. Correlations are
computed from returns rather than price levels, which avoids interpreting shared price trends as
evidence that two assets move together period by period.

```python
from ironwall.correlation import calculate_return_correlation_matrix
from ironwall.data import load_portfolio_prices
from ironwall.portfolio import calculate_asset_returns

portfolio = load_portfolio_prices("data/sample_portfolio.csv")
returns = calculate_asset_returns(portfolio.asset_prices)
matrix = calculate_return_correlation_matrix(returns)

print(matrix["JPM"]["BAC"])
```

## Interpretation

- `1.0` means the two return series moved together perfectly.
- `0.0` means no linear relationship was observed.
- `-1.0` means the two return series moved in perfectly opposite directions.
- The matrix is symmetric and every diagonal value is `1.0`.

Every asset must contain the same number of finite return observations. Series with fewer than
two observations are rejected. A constant series is also rejected because Pearson correlation is
undefined when either asset has zero variance.

Correlation measures historical linear co-movement. It does not establish causation, remain
stable across market regimes, or predict future diversification benefits.
