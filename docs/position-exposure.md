# Long/short position exposure

Portfolio return volatility does not reveal how much capital is deployed or whether offsetting long
and short positions conceal large gross exposure. IRONWALL can summarize signed position notionals
against a supplied portfolio net asset value (NAV).

The gross-exposure convention follows the core principle in [Article 7 of Commission Delegated
Regulation (EU) No 231/2013](https://eur-lex.europa.eu/legal-content/EN/TXT/HTML/?uri=CELEX%3A32013R0231):
gross exposure starts from the sum of absolute position values. IRONWALL's calculation is a
simplified diagnostic, not an AIFMD, Basel, margin, or regulatory-capital calculation.

## Usage

All position notionals and NAV must use the same base currency. Positive notionals are long,
negative notionals are short, and zero notionals are retained as flat positions.

```python
from ironwall.position_exposure import analyze_position_exposure

analysis = analyze_position_exposure(
    {
        "JPM": 1_200_000,
        "BAC": 600_000,
        "SPY_HEDGE": -800_000,
    },
    net_asset_value=1_000_000,
)

print(analysis.gross_leverage)
print(analysis.net_leverage)
print(analysis.to_dict())
```

## Method

Short exposure is reported as a positive magnitude:

```text
long exposure  = sum(positive notionals)
short exposure = sum(abs(negative notionals))
gross exposure = long exposure + short exposure
net exposure   = long exposure - short exposure

long leverage  = long exposure / NAV
short leverage = short exposure / NAV
gross leverage = gross exposure / NAV
net leverage   = net exposure / NAV
```

A market-neutral portfolio can have zero net exposure while retaining material gross exposure. For
example, a 50% long and 50% short book has zero net leverage but 1.0 gross leverage. The signed
`nav_fraction` and absolute `absolute_nav_fraction` fields make each position's contribution
auditable.

## Validation and limitations

- The positions mapping must be non-empty and asset names cannot be blank or whitespace-padded.
- Position notionals must be finite; NAV must be finite and strictly positive.
- Aggregates and ratios that exceed floating-point range are rejected instead of producing invalid
  JSON values.
- Values are returned in sorted asset order for reproducible downstream reports.
- NAV is supplied rather than inferred because cash, liabilities, accrued fees, and financing terms
  are not represented by a position-notional mapping.
- The calculation assumes all inputs have already been converted to one base currency.
- It does not convert derivatives to underlying-equivalent exposure, apply regulatory cash
  exclusions, recognize netting or hedging arrangements, model liquidity, or calculate margin.
- Gross and net leverage are descriptive diagnostics, not limits, recommendations, or evidence of
  regulatory compliance.
