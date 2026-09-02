# Deterministic portfolio stress testing

IRONWALL can apply a one-period shock to every asset in a long-only portfolio and attribute the
resulting return to each position. This complements historical VaR by answering explicit
"what-if" questions without assigning probabilities to the scenario.

```python
from ironwall.stress import run_stress_scenario

result = run_stress_scenario(
    weights={"JPM": 0.50, "BAC": 0.30, "GS": 0.20},
    shocks={"JPM": -0.30, "BAC": -0.20, "GS": 0.05},
)

print(result.portfolio_return)  # -0.20
print(result.loss)  #  0.20
print(result.asset_impacts)  # weighted impact from each asset
```

## Conventions

- Shocks are decimal simple returns: `-0.30` means a 30% decline.
- Shock keys must exactly match the assets in the weight mapping.
- Weights must be finite, non-negative, and sum to 1.0.
- A `-1.0` shock represents a total loss; values below -100% are rejected.
- `portfolio_return` is the weighted sum of asset shocks.
- `loss` is a positive loss magnitude and is zero when the scenario produces a gain.
- `asset_impacts` sum to `portfolio_return`, making the result directly auditable.

This is a deterministic sensitivity calculation, not a forecast. It does not estimate scenario
probability, liquidity effects, trading costs, or changes in correlations during market stress.
