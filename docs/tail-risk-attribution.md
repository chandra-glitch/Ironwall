# Historical Expected Shortfall attribution

IRONWALL can decompose a portfolio's historical Expected Shortfall (CVaR) into additive asset
contributions. The result identifies the holdings that drove losses during the portfolio's worst
observations and the holdings that acted as hedges.

```python
from ironwall.tail_attribution import attribute_expected_shortfall

result = attribute_expected_shortfall(
    {
        "JPM": [-0.021, 0.008, -0.013, 0.006, -0.030],
        "BAC": [-0.012, 0.004, -0.020, 0.010, -0.018],
    },
    {"JPM": 0.6, "BAC": 0.4},
    confidence=0.95,
)

print(result.conditional_value_at_risk)
print(result.component_tail_losses)
print(result.component_shares)
```

## Methodology

For each aligned observation, IRONWALL first calculates the long-only portfolio return:

```text
portfolio_return_t = sum(weight_i * asset_return_i,t)
```

It then finds the linearly interpolated `(1 - confidence)` portfolio-return quantile and selects
every observation at or below that cutoff. Including equality means tied observations are treated
consistently, although the realized tail can contain more observations than the nominal tail
probability implies.

Each asset's signed tail-loss contribution is:

```text
component_tail_loss_i = -weight_i * mean(asset_return_i in portfolio-tail observations)
```

The component values add to `signed_tail_loss`, the negative mean portfolio return over the same
tail observations. When `signed_tail_loss` is positive, it also equals
`conditional_value_at_risk`, and component shares add to one. A negative component indicates that
the asset gained, on average, during bad portfolio observations and therefore reduced tail loss.
This conditional-expectation interpretation follows the Expected Shortfall allocation approach
described by [Tasche (2002)](https://arxiv.org/abs/cond-mat/0203558).

IRONWALL reports `conditional_value_at_risk` as a non-negative loss magnitude, consistent with its
other risk metrics. If even the selected tail observations have a positive mean return, CVaR is
zero, the signed component values remain available for transparency, and `component_shares` is
`None` because there is no positive tail loss to allocate.

## Input rules

- Provide at least two assets with at least two aligned, numeric, finite return observations.
- Returns must be greater than `-100%` and must refer to the same dates and frequency.
- Provide one finite, non-negative weight per asset; weights must sum to `1.0` within tolerance.
- `confidence` must be strictly between zero and one.
- Asset identifiers must be non-empty strings without surrounding whitespace.

## Interpretation and limitations

- A contribution is conditional on the portfolio's tail, not the asset's own worst observations.
- A contribution share above `100%` can be valid when another holding has a negative hedge
  contribution.
- Historical attribution is backward-looking and assumes the supplied weights were constant over
  every observation.
- Linear interpolation and inclusive cutoff ties make the estimator transparent but can produce a
  tail sample larger than exactly `(1 - confidence) * observations`.
- Sparse tails are unstable. Use a history long enough to contain multiple relevant stress
  observations and assess results alongside scenario tests and other risk measures.
- The calculation does not model liquidity, nonlinear instruments, transaction costs, regime
  changes, or future correlations.
