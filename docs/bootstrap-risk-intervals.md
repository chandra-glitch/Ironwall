# Bootstrap intervals for historical tail risk

Historical Value at Risk (VaR) and Expected Shortfall are estimates from a finite return sample.
The point estimates alone do not show how much they may change if a different sample were
observed. `bootstrap_historical_risk` adds reproducible percentile-bootstrap intervals around
IRONWALL's existing historical VaR and Conditional VaR calculations.

## Usage

```python
from ironwall.bootstrap import bootstrap_historical_risk

returns = [-0.035, 0.012, -0.018, 0.006, -0.051, 0.021, -0.009, 0.014]
result = bootstrap_historical_risk(
    returns,
    confidence=0.95,
    interval_confidence=0.90,
    resamples=10_000,
    seed=2026,
)

print(result.to_dict())
```

The result contains the original-sample estimate plus lower and upper percentile bounds for
both VaR and Conditional VaR. All loss values follow IRONWALL's convention of positive numbers
representing losses. The output is JSON-ready and retains the sample count, both confidence
levels, resample count, and seed needed to reproduce the calculation.

## Method

For a return series with `n` observations, the implementation:

1. draws `n` returns with replacement from the original series;
2. calculates historical VaR and Conditional VaR using IRONWALL's existing conventions;
3. repeats the process `resamples` times; and
4. takes equal-tailed empirical percentiles from the bootstrap estimates.

The method uses a local seeded random-number generator, so it does not alter Python's global
random state. At least 100 resamples are required; the default is 10,000.

This is the nonparametric resampling method introduced in [Efron (1979), *Bootstrap Methods:
Another Look at the Jackknife*](https://doi.org/10.1214/aos/1176344552).

## Interpretation and limitations

The interval describes sampling uncertainty under the empirical return distribution. It is not
a guaranteed range for future losses and does not account for model error, liquidity risk, or
structural market changes.

Individual-return resampling treats observations as independent and identically distributed.
That assumption can be inappropriate when returns contain autocorrelation or volatility
clustering; a block-bootstrap method is preferable in those cases. Percentile intervals can also
be unstable for extreme confidence levels or short histories because very few observations
describe the tail. Compare results across seeds and resample counts, and retain a sufficiently
long, relevant history before relying on the bounds.
