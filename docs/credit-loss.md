# Credit expected-loss analysis

IRONWALL can aggregate deterministic one-horizon credit-risk inputs across named obligors. It
reports expected loss, an exposure-weighted PD and LGD, and portfolio loss standard deviation under
an explicit independent-default assumption.

The current [Basel Framework credit-risk
standard](https://www.bis.org/committees/bcbs/basel-framework/standard/cre) identifies probability
of default (PD), loss given default (LGD), exposure at default (EAD), and maturity as core IRB risk
components. A BIS study on [credit loss
rates](https://www.bis.org/publications/working-paper-1101-insights-credit-loss-rates-global-database)
expresses expected credit loss as PD multiplied by LGD and EAD. This module implements that basic
identity as a transparent diagnostic; it is not the Basel IRB framework, an accounting impairment
model, or a regulatory capital calculation.

## Usage

Each mapping must contain exactly the same obligor names. EAD amounts must use one currency and
unit. PD and LGD are decimals between zero and one and must use the same horizon and scenario.

```python
from ironwall.credit_loss import analyze_credit_loss

analysis = analyze_credit_loss(
    exposure_at_default={
        "Borrower A": 1_000_000,
        "Borrower B": 500_000,
    },
    probability_of_default={
        "Borrower A": 0.02,
        "Borrower B": 0.05,
    },
    loss_given_default={
        "Borrower A": 0.45,
        "Borrower B": 0.60,
    },
)

print(analysis.expected_loss)
print(analysis.independent_unexpected_loss)
print(analysis.to_dict())
```

## Method

For obligor `i`, let `EAD_i` be exposure at default, `PD_i` the probability of default, and `LGD_i`
the fractional loss if default occurs:

```text
loss if default_i          = EAD_i * LGD_i
expected loss_i            = EAD_i * PD_i * LGD_i
loss standard deviation_i  = EAD_i * LGD_i * sqrt(PD_i * (1 - PD_i))

portfolio expected loss    = sum(expected loss_i)
expected loss rate         = portfolio expected loss / sum(EAD_i)
independent unexpected loss = sqrt(sum(loss standard deviation_i^2))
```

`independent_unexpected_loss` is the standard deviation of portfolio loss when each obligor's
default is modelled as an independent Bernoulli event. Per-obligor expected-loss contributions sum
to one when expected loss is positive. Loss-variance contributions sum to one when unexpected loss
is positive. A contribution is `None` when its denominator is zero.

## Validation and limitations

- Obligor names must be non-empty, whitespace-clean strings and identical across all three inputs.
- EAD must be positive and finite. PD and LGD must be finite values in the inclusive `[0, 1]`
  interval.
- Arithmetic overflow and underflow are rejected instead of silently emitting invalid or truncated
  risk measures.
- Inputs are treated as already calibrated. The module does not estimate PD, LGD, EAD, maturity,
  discount rates, credit conversion factors, collateral effects, guarantees, or recoveries.
- Defaults are assumed independent. Real credit portfolios can exhibit material systematic and
  name-to-name dependence, so this assumption can severely understate tail risk and diversification
  breakdown during stress.
- The result is not Value at Risk, Expected Shortfall, an economic-capital number, a provision, or a
  confidence bound. A loss standard deviation must not be interpreted as a maximum loss.
- Horizon, scenario, currency, and exposure definitions must be consistent across obligors. The
  calculation does not incorporate migration risk, prepayment, drawdowns, netting, wrong-way risk,
  macroeconomic forecasts, or lifetime expected-credit-loss staging.
- Results are descriptive diagnostics, not lending decisions, prices, forecasts, accounting advice,
  or evidence of regulatory compliance.
