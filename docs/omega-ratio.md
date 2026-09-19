# Omega ratio analysis

The Sharpe ratio summarizes performance using only mean return and volatility. The Omega ratio
instead compares every observed gain above a selected return threshold with every shortfall below
that threshold. This makes the result sensitive to the complete empirical return distribution,
including skewness and tail shape.

## Usage

```python
from ironwall.omega import analyze_omega_ratio

returns = [-0.03, -0.01, 0.0, 0.02, 0.06]
result = analyze_omega_ratio(returns, threshold=0.0)

print(result.omega_ratio)  # 2.0
print(result.to_dict())
```

The threshold and returns must use the same periodic units. For example, compare daily returns
with a daily target, not an annual target.

## Method

For returns `r` and threshold `t`, the empirical calculation is:

```text
upside potential   = mean(max(r - t, 0))
downside shortfall = mean(max(t - r, 0))
Omega              = upside potential / downside shortfall
```

This discrete calculation is equivalent to comparing the areas above and below the threshold in
the empirical cumulative return distribution. It follows Keating and Shadwick's [*A Universal
Performance Measure*](https://oxfordstrat.com/coasdfASD32/uploads/2016/03/A-Universal-Performance-Measure.pdf).

An Omega ratio above `1` means the sample's gains above the target outweigh its shortfalls below
the target. A value below `1` means shortfalls dominate. The ratio must always be interpreted
together with the chosen threshold.

## Zero-shortfall cases

Strict JSON cannot represent infinity. If the sample has upside but no observations below the
threshold, `omega_ratio` is `None` and `ratio_status` is `"unbounded"`. If every observation is
exactly at the threshold, the ratio is `None` with an `"undefined"` status. The reported upside
and downside components make both cases auditable.

## Limitations

- The result is entirely sample-dependent and does not predict the future return distribution.
- Return order is discarded, so Omega does not measure drawdowns, recovery time, or serial risk.
- Short histories may miss rare losses and materially overstate the ratio.
- Results from different return frequencies or thresholds are not directly comparable.
- Transaction costs, liquidity constraints, taxes, and changing market regimes are not included.
