# Return-distribution diagnostics

IRONWALL can summarize the shape of a periodic return sample before a user relies on a model that
assumes approximately Gaussian returns. The analysis reports skewness, excess kurtosis, and the
Jarque-Bera statistic with a clearly labelled asymptotic p-value.

~~~python
from ironwall.distribution import analyze_return_distribution

diagnostics = analyze_return_distribution(
    [-0.018, 0.006, -0.011, 0.004, 0.009, -0.025, 0.013, 0.002]
)

print(diagnostics.skewness)
print(diagnostics.excess_kurtosis)
print(diagnostics.jarque_bera_asymptotic_p_value)
print(diagnostics.to_dict())
~~~

## Methodology

For a sample of `n` returns, IRONWALL calculates the mean and the second, third, and fourth central
moments using a divisor of `n`. It reports:

~~~text
skewness = third_central_moment / second_central_moment ** 1.5
excess_kurtosis = fourth_central_moment / second_central_moment ** 2 - 3
JB = n / 6 * (skewness ** 2 + excess_kurtosis ** 2 / 4)
~~~

This is the [NIST Jarque-Bera definition](https://www.itl.nist.gov/div898/software/dataplot/refman1/auxillar/jarqbera.htm),
originally developed by [Jarque and Bera (1987)](https://doi.org/10.2307/1403192). Under the
large-sample normal null, the statistic is asymptotically chi-squared with two degrees of freedom.
For two degrees of freedom, the survival probability is `exp(-JB / 2)`; IRONWALL exposes that value
as `jarque_bera_asymptotic_p_value`.

The implementation normalizes centered returns before calculating powers. This preserves the
standardized moments while reducing avoidable overflow and underflow. `sample_volatility` uses the
`n - 1` denominator and is included as a scale reference; skewness, kurtosis, and the JB statistic
are dimensionless.

## Input rules

- Provide at least four numeric, finite periodic returns.
- Returns at or below `-100%` are rejected, consistently with the rest of IRONWALL.
- The observations must not all be equal because standardized moments require positive variance.
- Use returns from one consistent frequency and data-generation process.

## Interpretation

- Negative skewness indicates a longer or more influential left tail in the observed sample;
  positive skewness indicates right-tail asymmetry.
- Positive excess kurtosis indicates more fourth-moment weight away from the mean than a Gaussian
  distribution; negative values indicate less.
- A small asymptotic p-value is evidence against the joint Gaussian skewness and kurtosis
  assumptions. It is not proof of a particular alternative distribution.
- Moment estimates can be dominated by a few observations, so inspect the data and sample length
  alongside these numbers.

## Limitations

- NIST cautions that the chi-square approximation requires a fairly large sample and uses simulated
  critical values below 2,000 observations. Do not treat the asymptotic p-value as a calibrated
  small-sample decision rule.
- Financial returns can be serially dependent or volatility-clustered. This diagnostic does not
  adjust for autocorrelation, conditional heteroskedasticity, or structural breaks.
- Passing this diagnostic does not prove normality, and failing it does not select a replacement
  model.
- The analysis is historical and does not predict future tail risk, liquidity, or losses.
