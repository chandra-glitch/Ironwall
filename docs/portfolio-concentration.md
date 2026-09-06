# Portfolio concentration risk

IRONWALL can measure how strongly a long-only portfolio's capital is concentrated in a small
number of positions. Holding count alone is not enough: a portfolio with ten equally weighted
positions is less concentrated than a ten-position portfolio dominated by one holding.

```python
from ironwall.concentration import analyze_weight_concentration

metrics = analyze_weight_concentration(
    {
        "JPM": 0.70,
        "BAC": 0.20,
        "GS": 0.10,
    }
)

print(metrics.to_dict())
```

The result contains:

- `asset_count`: the number of supplied assets, including zero-weight positions.
- `largest_weight`: the portfolio's largest single allocation.
- `herfindahl_index`: the sum of squared weights, `HHI = sum(w_i²)`. For `n` assets it ranges
  from `1/n` for equal weights to `1` for a single-position allocation.
- `effective_number_of_assets`: `1 / HHI`. This translates the observed concentration into the
  number of equally weighted positions that would produce the same HHI.
- `normalized_herfindahl_index`: `(HHI - 1/n) / (1 - 1/n)`, placing concentration between `0`
  for equal weights and `1` for a single-position allocation while accounting for asset count.

Inputs use the same validation as IRONWALL portfolio analysis: at least two assets are required,
weights must be finite and non-negative, and they must sum to one within a small numerical
tolerance. Zero weights are allowed.

## Interpretation and limitations

Higher HHI and lower effective holdings indicate greater allocation concentration. IRONWALL does
not assign universal low, medium, or high labels because suitable limits depend on mandate,
liquidity, investment horizon, and governance policy.

These are weight-only measures. They do not capture return correlation, volatility, factor
exposure, liquidity, issuer relationships, or sector and geographic overlap. Use them alongside
portfolio risk attribution and other exposure analysis rather than as a standalone risk verdict.
