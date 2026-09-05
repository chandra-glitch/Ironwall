# Monte Carlo VaR and CVaR

IRONWALL can estimate forward-horizon loss distributions by fitting a Gaussian model to
historical log returns and drawing reproducible simulations.

```python
from ironwall.monte_carlo import estimate_monte_carlo_var

estimate = estimate_monte_carlo_var(
    returns=(-0.02, 0.01, 0.015, -0.01, 0.005),
    confidence=0.99,
    simulations=50_000,
    horizon_periods=10,
    seed=42,
)

print(estimate.value_at_risk)
print(estimate.conditional_value_at_risk)
```

## Methodology

1. Convert historical simple returns to log returns.
2. Estimate their sample mean and sample standard deviation.
3. Assume independent Gaussian log returns across the requested horizon.
4. Draw terminal log returns using the horizon-scaled mean and volatility.
5. Convert simulations back to compounded simple returns.
6. Report interpolated VaR and tail-average CVaR as positive loss magnitudes.

The default seed is `0`, making repeated runs reproducible. Set `seed=None` only when a different
random sample on each run is intentional. `horizon_periods` uses the same frequency as the input
returns, so ten daily periods represent ten trading days when the observations are daily.

## Model-risk limitations

Gaussian, independent returns can understate fat tails, volatility clustering, serial dependence,
and market discontinuities. Results are sensitive to the historical window, simulation count,
confidence level, and horizon. The estimate excludes liquidity, transaction costs, and position
changes and must not be treated as a forecast or investment advice.
