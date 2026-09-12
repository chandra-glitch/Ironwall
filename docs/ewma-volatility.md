# EWMA volatility forecast

IRONWALL can produce a recency-sensitive, one-period volatility forecast from a chronological
return series. Unlike equal-weight sample volatility, exponentially weighted moving average
(EWMA) volatility gives progressively more influence to recent squared returns.

```python
from ironwall.ewma import forecast_ewma_volatility

forecast = forecast_ewma_volatility(
    [0.012, -0.008, 0.004, -0.019, 0.011],
    decay_factor=0.94,
    periods_per_year=252,
)

print(forecast.periodic_volatility)
print(forecast.annualized_volatility)
print(forecast.to_dict())
```

## Methodology

Returns must be ordered from oldest to newest. For `T` observations and decay factor `lambda`,
IRONWALL assigns each squared return the finite-history normalized weight:

```text
raw_weight_i = lambda ** (T - i)
weight_i = raw_weight_i / sum(raw_weight)
variance_forecast = sum(weight_i * return_i ** 2)
```

The implementation accumulates the numerator and denominator recursively to avoid constructing
a separate weight vector. Normalizing the finite history makes the supplied weights sum to one;
with a long history, the latest return's weight approaches `1 - lambda`, matching the familiar
RiskMetrics-style EWMA recurrence.

The model assumes a zero conditional return mean, so it averages squared returns rather than
demeaned squared deviations. Consequently, a constant nonzero return series still represents
risk under this model. The reported half-life is `log(0.5) / log(lambda)`: after that many periods,
an observation has half the relative weight of the latest observation.

The default daily decay factor is `0.94`, the value selected for one-day volatility and correlation
forecasts in the [RiskMetrics Technical Document, Fourth Edition](https://www.msci.com/documents/10199/5915b101-4206-4ba0-aee2-3449d5c7e95a).
Annualized volatility uses square-root-of-time scaling with `252` periods by default.

## Input rules

- Provide at least two numeric, finite returns in chronological order.
- Returns at or below `-100%` are rejected as economically impossible simple returns.
- `decay_factor` must be strictly between zero and one. Smaller values react faster to recent
  shocks; values closer to one retain historical information longer.
- `periods_per_year` must be a positive integer and should match the return frequency.

## Limitations

- EWMA is a volatility forecast, not a complete VaR estimate or a guarantee of future risk.
- The zero-mean assumption can be unsuitable for longer-horizon or strongly trending returns.
- The model uses one symmetric response to positive and negative shocks and does not capture
  leverage effects, jumps, structural breaks, or changing decay rates.
- Square-root-of-time annualization assumes a stable variance process across the scaling horizon.
- Results depend on the selected decay factor, data frequency, history length, and data quality.
