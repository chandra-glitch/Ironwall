# Serial-dependence diagnostics

Many risk calculations treat periodic returns as independent observations. Return ordering can
instead contain information: correlation in returns may indicate linear predictability, while
correlation in squared returns may reveal persistence in return magnitude (volatility clustering).

IRONWALL provides both diagnostics without converting them into an automatic pass/fail decision.

## Usage

Returns must be ordered from oldest to newest and sampled at equal intervals.

```python
from ironwall.serial_dependence import analyze_serial_dependence

returns = [0.01, -0.02, 0.015, -0.01, 0.03, -0.025]
result = analyze_serial_dependence(returns, max_lag=3)

for lag in result.lags:
    print(lag.lag, lag.return_autocorrelation, lag.squared_return_autocorrelation)

print(result.to_dict())
```

The immutable result is strict-JSON-ready. If all returns have the same absolute magnitude,
squared returns are constant and their autocorrelation is undefined. In that case,
`squared_return_autocorrelation_available` is `False` and each squared-return coefficient is
`None`, rather than a non-standard `NaN` value.

## Method

For an equally spaced series `Y` with `N` observations, IRONWALL uses the [NIST autocorrelation
definition](https://www.itl.nist.gov/div898/handbook/eda/section3/eda35c.htm):

```text
             sum(i=1..N-k) (Y[i] - mean(Y)) (Y[i+k] - mean(Y))
r[k] =       --------------------------------------------------
                    sum(i=1..N) (Y[i] - mean(Y))^2
```

The same calculation is applied separately to returns and squared returns for every lag from one
through `max_lag`. Inputs are internally scaled before moment calculations; because correlation is
scale-invariant, this avoids overflow without changing the coefficients.

Positive squared-return autocorrelation can be a descriptive signal of volatility persistence.
This use of lagged squared observations is motivated by Engle's foundational [ARCH
model](https://doi.org/10.2307/1912773), but this diagnostic is not an ARCH fit or hypothesis test.

## Interpretation and limitations

- A positive coefficient means observations separated by that lag tend to move together; a
  negative coefficient means they tend to move oppositely.
- Autocorrelation is descriptive, not proof of predictability or a trading opportunity.
- No p-values or confidence bands are reported. Sampling uncertainty depends on sample size, the
  data-generating process, and how many lags are inspected.
- High-lag estimates use progressively fewer paired observations and can be unstable.
- Squared-return autocorrelation is only a proxy for volatility clustering. It does not replace an
  ARCH/GARCH model, regime analysis, or residual diagnostics.
- Zero autocorrelation does not establish independence or rule out nonlinear dependence.
- The analysis assumes equally spaced observations and does not repair missing periods.
