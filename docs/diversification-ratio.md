# Portfolio diversification ratio

IRONWALL can measure how much volatility a long-only portfolio avoids by combining assets
whose returns do not move together perfectly.

```python
from ironwall.diversification import analyze_diversification

analysis = analyze_diversification(
    {
        "JPM": [0.012, -0.008, 0.004, 0.006],
        "TLT": [-0.003, 0.005, 0.001, -0.002],
    },
    {"JPM": 0.6, "TLT": 0.4},
)

print(analysis.diversification_ratio)
print(analysis.volatility_reduction)
print(analysis.to_dict())
```

## Methodology

For asset volatilities `sigma_i`, long-only weights `w_i`, and portfolio volatility
`sigma_p`, the diversification ratio is:

```text
diversification ratio = sum(w_i * sigma_i) / sigma_p
```

IRONWALL also reports the same benefit as a fractional volatility reduction:

```text
volatility reduction = 1 - sigma_p / sum(w_i * sigma_i)
```

All volatilities are sample standard deviations of the supplied periodic returns. The ratio
is independent of annualization as long as every asset uses the same observation frequency.
A ratio near `1` indicates little observed volatility benefit, while a value above `1`
indicates that co-movement between the assets reduced portfolio volatility.

The function requires at least two aligned observations per asset, matching non-negative
weights that sum to one, finite returns, and no return at or below `-100%`. If portfolio
volatility is zero, the ratio is returned as `None` instead of non-finite JSON. In that case,
the reduction is `1.0` when the weighted standalone volatility is positive. If all weighted
asset volatilities are also zero, both derived metrics are `None`.

## Limitations

- The analysis is historical and does not predict future correlations or volatility.
- Results are sensitive to the observation window, sampling frequency, and data quality.
- Standard deviation treats gains and losses symmetrically and does not capture tail dependence.
- Static weights are assumed throughout the return sample; trading costs and rebalancing are ignored.
- Only long-only portfolios are supported, so the ratio should not be used to evaluate leveraged or
  short portfolios without a methodology designed for those exposures.
