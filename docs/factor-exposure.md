# Single-factor exposure analysis

IRONWALL can estimate how strongly an asset's periodic returns moved with one aligned factor or
benchmark return series. The calculation uses ordinary least squares with an intercept.

```python
from ironwall.factor import calculate_factor_exposure

exposure = calculate_factor_exposure(
    asset_returns=(-0.029, -0.014, 0.001, 0.016, 0.031),
    factor_returns=(-0.02, -0.01, 0.0, 0.01, 0.02),
)

print(exposure.beta)  # 1.5
print(exposure.alpha)  # 0.001 per observation
print(exposure.r_squared)  # 1.0
```

## Interpretation

- `beta` measures sensitivity: a beta of `1.5` means a 1% factor move was associated with an
  estimated 1.5% asset move, before the intercept.
- `alpha` is the fitted per-period return when the factor return is zero.
- `r_squared` is the proportion of observed asset-return variance explained by the model.

The asset and factor series must contain at least three aligned, finite observations. Both must
vary; otherwise beta or R-squared is undefined. Inputs should use the same return frequency and
return convention. For a CAPM-style regression, provide excess returns after subtracting the
matching risk-free rate from both series.

Factor exposure describes an in-sample linear relationship. It does not establish causation,
remain stable across market regimes, or predict future returns.
