# Fixed-income interest-rate sensitivity

IRONWALL can value deterministic positive cash flows at a flat annual yield and measure their
sensitivity to a parallel yield change. The result includes Macaulay duration, modified duration,
convexity, DV01, exact shocked value, and a duration-convexity approximation for comparison.

The Basel Committee's [Interest rate risk in the banking
book](https://www.bis.org/publications/201604-standards-interest-rate-risk-banking-book)
describes how interest-rate changes alter the present value of future cash flows. It also notes that
modified duration measures marginal value sensitivity to parallel yield shifts and that results depend
on precise cash flows and discount rates. This module is a transparent instrument-level diagnostic,
not the Basel IRRBB standardised framework or a regulatory capital calculation.

## Usage

Payment times are years from the valuation date. Amounts must use one currency and unit. Yields and
shocks are decimals, so `0.04` is 4% and the default `0.01` shock is +100 basis points.

```python
from ironwall.interest_rate_risk import analyze_fixed_income_sensitivity

analysis = analyze_fixed_income_sensitivity(
    {
        1: 5,
        2: 5,
        3: 5,
        4: 5,
        5: 105,
    },
    annual_yield=0.04,
    compounds_per_year=1,
    rate_shock=0.01,
)

print(analysis.modified_duration_years)
print(analysis.dv01)
print(analysis.exact_price_change)
print(analysis.to_dict())
```

## Method

For payment time `t`, cash flow `CF`, nominal annual yield `y`, and compounding frequency `m`:

```text
PV(CF_t)          = CF_t / (1 + y/m)^(m*t)
instrument value = sum(PV(CF_t))
price weight_t    = PV(CF_t) / instrument value

Macaulay duration = sum(t * price weight_t)
modified duration = Macaulay duration / (1 + y/m)
convexity          = sum(price weight_t * t * (t + 1/m) / (1 + y/m)^2)
DV01               = instrument value * modified duration * 0.0001
```

DV01 is reported as the positive first-order value loss for a one-basis-point yield increase. For a
parallel shock `dy`, the second-order approximation is:

```text
estimated percentage change = -modified duration * dy + 0.5 * convexity * dy^2
```

IRONWALL also discounts every cash flow at `y + dy` to report the exact value change under the same
flat-yield assumptions. `duration_convexity_error` equals the approximated currency change minus
the exact currency change. Cash-flow details are sorted by payment time and expose each present
value and price weight for auditability.

## Validation and limitations

- Cash-flow times must be unique, finite, and greater than zero; amounts must be finite and
  strictly positive.
- The compounding frequency must be a positive integer. Current and shocked yields must each
  produce a positive periodic discount base.
- Arithmetic outside floating-point range is rejected instead of producing invalid JSON values.
- One flat yield discounts every cash flow. Real term structures generally require maturity-specific
  zero rates, and non-parallel curve moves require key-rate or full revaluation analysis.
- The cash flows are assumed fixed. Callable or puttable bonds, prepayments, defaults, recoveries,
  floating-rate resets, inflation linkage, and other behavioural or embedded options are not modelled.
- Duration is a local linear measure. Convexity improves the approximation, but exact repricing is
  more reliable for large shocks within this simplified model.
- DV01 and shocked values exclude accrued interest, settlement conventions, taxes, transaction
  costs, liquidity effects, credit-spread changes, and currency conversion.
- Results are descriptive risk diagnostics, not prices, forecasts, trading advice, or evidence of
  regulatory compliance.
