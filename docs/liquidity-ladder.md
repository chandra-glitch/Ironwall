# Liquidity cash-flow ladder

Market-risk statistics do not show whether available cash can cover obligations as they mature.
IRONWALL can project a supplied liquidity buffer through deterministic net cash-flow buckets and
identify the first funding shortfall, its maximum size, and any later recovery.

This diagnostic is motivated by Principle 5 of the Basel Committee's [Principles for Sound
Liquidity Risk Management and
Supervision](https://www.bis.org/publications/200809-guidelines-principles-sound-liquidity-risk-management-and-supervision),
which calls for cash-flow projections across appropriate time horizons. It is a transparent
cash-flow ladder, not a regulatory Liquidity Coverage Ratio (LCR) or Net Stable Funding Ratio
(NSFR) calculation.

## Usage

All amounts must use the same currency and unit. Dictionary keys are positive integer days;
positive amounts are inflows and negative amounts are outflows.

```python
from ironwall.liquidity_ladder import analyze_liquidity_ladder

analysis = analyze_liquidity_ladder(
    {
        1: -1_200_000,
        7: 500_000,
        30: 900_000,
    },
    initial_liquidity=1_000_000,
)

print(analysis.first_shortfall_day)
print(analysis.maximum_shortfall)
print(analysis.to_dict())
```

## Method

For each ascending day bucket:

```text
cumulative net cash flow = sum(net cash flows through the bucket)
projected liquidity      = initial liquidity + cumulative net cash flow
liquidity shortfall      = max(0, -projected liquidity)
```

`first_shortfall_day` is the earliest bucket with negative projected liquidity.
`maximum_shortfall` is the greatest funding deficit observed over the supplied horizon. A balance
of exactly zero is depleted but is not classified as a shortfall. `minimum_liquidity_day` is `0`
when the opening buffer is the lowest balance; otherwise it is the earliest bucket attaining the
minimum.

Inflows, outflows, the net cash flow, and the ending balance are reported separately so the ladder
can be reconciled. Bucket results are returned in ascending day order even when the input mapping
is not ordered.

## Validation and limitations

- The cash-flow mapping must be non-empty and bucket days must be positive integers.
- Cash flows and the initial buffer must be finite; the initial buffer cannot be negative.
- Aggregates outside floating-point range are rejected instead of producing invalid JSON values.
- Each bucket is a net amount. Aggregate same-day inflows and outflows before calling the function
  if gross flow information is required elsewhere.
- The calculation assumes all amounts have already been converted to one base currency and that
  cash is freely transferable across the represented entity.
- Results depend entirely on the supplied timing and amount assumptions. The model does not infer
  behavioural deposit runoff, contingent draws, collateral or margin calls, funding renewals,
  intraday timing, asset-sale capacity, haircuts, or market liquidity.
- The ladder is deterministic and does not replace liquidity stress testing, a contingency funding
  plan, governance limits, or jurisdiction-specific regulatory calculations.
