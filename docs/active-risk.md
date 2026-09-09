# Tracking error and information ratio

Absolute risk metrics do not show how closely a portfolio follows its benchmark. IRONWALL can
measure the variability of active returns and the average active return earned per unit of that
benchmark-relative risk.

```python
from ironwall.active_risk import analyze_active_risk

metrics = analyze_active_risk(
    portfolio_returns=[0.02, 0.01, -0.01, 0.03],
    benchmark_returns=[0.01, 0.00, -0.02, 0.01],
    periods_per_year=252,
)

print(metrics.to_dict())
```

For each aligned period, active return is `portfolio_return - benchmark_return`. IRONWALL uses
sample standard deviation for periodic tracking error:

```text
tracking_error = sample_standard_deviation(active_returns)
```

Annualized tracking error and information ratio are:

```text
annualized_tracking_error = tracking_error * sqrt(periods_per_year)
information_ratio = mean(active_returns) / tracking_error * sqrt(periods_per_year)
```

`annualized_mean_active_return` is the arithmetic periodic mean multiplied by
`periods_per_year`; it is not a compounded return. If active returns have zero sample variation,
tracking error is zero and the information ratio is reported as `None` rather than infinity.

The portfolio and benchmark series must be pre-aligned, have equal lengths, and contain at least
two finite returns greater than -100%. `periods_per_year` must be a positive integer.

## Interpretation and limitations

A lower tracking error means a portfolio followed its selected benchmark more closely. A positive
information ratio indicates positive average active return, while a negative value indicates
underperformance relative to that benchmark. Comparisons require the same return frequency,
annualization convention, and an appropriate benchmark.

The square-root-of-time rule assumes active returns are sufficiently stable and weakly dependent.
Results are sensitive to benchmark choice, stale or misaligned prices, outliers, and the analysis
window. These historical statistics do not measure liquidity, tail losses, transaction costs, or
future manager skill and should not be treated as investment advice.
