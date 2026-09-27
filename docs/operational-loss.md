# Operational-loss event analysis

IRONWALL can summarize the observed frequency, severity, and concentration of named
operational-loss events. The analysis reports historical total and annualized loss, annualized
event frequency, central tendency and dispersion, largest-event concentration, and the portion of
losses at or above a user-selected materiality threshold.

The Basel Committee's current [Principles for the Sound Management of Operational
Risk](https://www.bis.org/publications/202103-guidelines-revisions-principles-sound-management-operational-risk)
emphasize identifying, assessing, monitoring, and reporting operational risk. This module provides
a small, auditable loss-event diagnostic for that broader process. It is not an operational-risk
capital calculation, control assessment, scenario model, or regulatory-compliance determination.

## Usage

Each key is a stable event identifier and each value is a strictly positive net loss amount. All
amounts must use one currency, unit, and consistent treatment of recoveries. `observation_years`
may be fractional. An event is material when its loss is greater than or equal to the supplied
threshold.

```python
from ironwall.operational_loss import analyze_operational_losses

analysis = analyze_operational_losses(
    {
        "payment-outage-2025-03": 125_000,
        "processing-error-2025-11": 480_000,
        "vendor-disruption-2026-02": 90_000,
    },
    observation_years=2.5,
    materiality_threshold=100_000,
)

print(analysis.total_loss)
print(analysis.annualized_event_frequency)
print(analysis.largest_loss_share)
print(analysis.to_dict())
```

Events are returned from largest to smallest loss, with event ID as a deterministic tie-breaker.
`sample_loss_standard_deviation` is `None` for a single event because sample dispersion is then
undefined. Results are strict-JSON-ready.

## Method

For positive observed losses `L_1, ..., L_n` over `Y` years and materiality threshold `T`:

```text
total loss                       = sum(L_i)
annualized historical loss       = total loss / Y
annualized event frequency       = n / Y
mean severity                    = total loss / n
sample severity standard deviation = sqrt(sum((L_i - mean)^2) / (n - 1))
largest-event share              = max(L_i) / total loss
material loss                    = sum(L_i where L_i >= T)
material-loss share              = material loss / total loss
annualized material frequency    = count(L_i >= T) / Y
```

The annualized values are arithmetic historical averages. They are not forecasts and do not imply
that event arrivals are independent, stationary, or Poisson distributed.

## Validation and limitations

- Event IDs must be unique, non-empty, whitespace-clean strings. Mapping keys provide uniqueness.
- Loss amounts and observation years must be positive and finite. The threshold must be finite and
  non-negative.
- Arithmetic overflow, underflow, and non-finite results are rejected instead of silently dropping
  small events or emitting invalid JSON.
- The caller must define whether amounts are gross or net of insurance, restitution, and other
  recoveries, and must apply that definition consistently.
- The supplied history may be incomplete because of reporting thresholds, control changes,
  acquisitions, inflation, currency conversion, or delayed discovery. Threshold statistics cannot
  correct that selection bias.
- Means, medians, standard deviations, and simple annualization do not estimate extreme tails,
  event dependence, scenario losses, or loss-distribution parameters. Sparse histories can make
  every reported statistic unstable.
- The diagnostic does not assign Basel event types or business lines, assess controls, estimate
  capital, or replace internal governance, expert scenarios, external data, or regulatory rules.
- Results are descriptive analytics, not forecasts, accounting advice, insurance valuations, or
  evidence of regulatory compliance.
