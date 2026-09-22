# Risk-limit evaluation

Risk metrics are easier to act on when they can be compared with explicit, pre-approved limits.
IRONWALL can evaluate any selected non-negative, upper-bound risk measures and produce an auditable
breach summary.

The European Central Bank's [supervisory statement on governance and risk
appetite](https://www.bankingsupervision.europa.eu/ecb/pub/pdf/ssm_supervisory_statement_on_governance_and_risk_appetite_201606.en.pdf)
describes risk dashboards that compare exposures with limits, retain sufficient headroom, and
report breaches promptly. This module provides the deterministic calculation layer for that kind
of monitoring; it does not set an institution's limits or escalation policy.

## Usage

The keys in `limits` select which values are assessed, so the complete dictionary returned by
`RiskMetrics.to_dict()` can be supplied directly.

```python
from ironwall.metrics import analyze_returns
from ironwall.risk_limits import evaluate_risk_limits

metrics = analyze_returns([-0.03, 0.01, -0.02, 0.025, -0.01])
limits = {
    "annualized_volatility": 0.30,
    "value_at_risk": 0.025,
    "conditional_value_at_risk": 0.04,
    "maximum_drawdown": 0.15,
}

result = evaluate_risk_limits(metrics.to_dict(), limits)
print(result.status)
print(result.breached_metrics)
print(result.to_dict())
```

Every assessed value and its limit must use the same units and horizon. For example, compare an
annualized volatility value with an annualized volatility limit, and a one-day VaR with a one-day
VaR limit at the same confidence level.

## Method

For each configured metric:

```text
utilization ratio = observed value / limit
headroom          = limit - observed value
breached          = observed value > limit
```

A value exactly equal to the limit has `1.0` utilization and zero headroom, but is not marked as a
breach because it does not exceed the configured upper bound. Negative headroom identifies the
amount by which a limit has been exceeded.

Metrics are returned in sorted name order so reports are reproducible regardless of mapping order.
If a valid ratio is larger than floating-point JSON can represent, `utilization_ratio` is `None`
and `utilization_status` is `"above_numeric_range"`; the direct value-versus-limit comparison still
reports the breach correctly.

## Validation and limitations

- Limits must be finite and strictly positive.
- Observed values must be finite and non-negative.
- Metric names must be non-empty strings without surrounding whitespace.
- Every configured limit must have an observed value; additional unconfigured values are ignored.
- The evaluator supports upper-bound measures where larger values mean more risk. It is not suitable
  for lower-bound capital, liquidity, return, or coverage requirements without transforming them.
- Limits are user-supplied governance inputs, not regulatory defaults or investment advice.
- The result does not send alerts, enforce trades, define escalation owners, or replace independent
  limit calibration and review.
