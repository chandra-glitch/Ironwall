# Downside deviation and Sortino ratio

Standard deviation treats gains and losses as equally risky. IRONWALL can instead measure only
returns that fall below a chosen minimum acceptable return and use that downside deviation to
calculate the Sortino ratio.

```python
from ironwall.downside import analyze_downside_risk

metrics = analyze_downside_risk(
    [0.02, -0.01, 0.03, -0.02],
    target_return=0.0,
    periods_per_year=252,
)

print(metrics.to_dict())
```

`target_return` is a per-period threshold in decimal form. For daily returns, `0.001` means a
minimum acceptable daily return of 0.1%, not an annual target.

IRONWALL uses target downside deviation over all `N` observations:

```text
downside_deviation = sqrt(sum(min(return - target, 0)^2) / N)
```

The annualized Sortino ratio is:

```text
sortino_ratio = (mean_return - target) / downside_deviation * sqrt(periods_per_year)
```

The result includes the return count, count below target, target, per-period and annualized
downside deviation, and Sortino ratio. If no observation falls below the target, downside
deviation is zero and the ratio is reported as `None` rather than a non-finite value.

Inputs require at least two finite periodic returns greater than -100%. The target must also be
finite and greater than -100%, and `periods_per_year` must be a positive integer.

## Interpretation and limitations

A higher Sortino ratio indicates more excess return per unit of observed downside deviation. A
negative value means the average periodic return was below the selected target. Results from
different frequencies or targets should not be compared directly.

Square-root-of-time annualization assumes returns are sufficiently stable and weakly dependent.
The metric does not describe tail severity, drawdown duration, liquidity, or future performance,
and a short sample can make it unstable. It should be used with VaR, expected shortfall, drawdown,
and qualitative risk review rather than as a standalone investment decision.
