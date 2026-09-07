# Maximum-drawdown episodes

Maximum drawdown measures loss depth, but the path of that loss also matters. IRONWALL can locate
the peak and trough of the worst drawdown and determine whether and when the series recovered its
previous peak.

```python
from ironwall.drawdown import find_maximum_drawdown_episode

episode = find_maximum_drawdown_episode([100, 120, 90, 105, 120, 130])

if episode is not None:
    print(episode.to_dict())
```

For this example, the maximum drawdown is 25%. The peak is at index `1`, the trough at index `2`,
and the first recovery at index `4`. The decline takes one observation interval and the recovery
takes two.

The result contains:

- `peak_index` and `peak_value`: the last running peak before the maximum decline.
- `trough_index` and `trough_value`: the first observation reaching the maximum loss depth.
- `recovery_index`: the first later observation at or above the peak, or `None` if unrecovered.
- `maximum_drawdown`: the peak-to-trough loss as a positive fraction.
- `periods_to_trough` and `periods_to_recovery`: observation intervals for each phase.
- `recovered`: whether a recovery exists in the supplied series.

Indices are zero-based positions, so callers with dated observations can map them back to their
own timestamps. A non-decreasing series returns `None` because it contains no drawdown episode.
If equally deep maximum drawdowns occur, the earliest episode is returned.

## Interpretation and limitations

Recovery time exposes a risk dimension that loss magnitude alone misses: two assets can have the
same maximum drawdown while spending very different lengths of time below their peaks. Results are
path-dependent and sensitive to observation frequency, data gaps, and the selected analysis
window. An unrecovered episode means only that recovery was not observed before the supplied data
ended; it does not predict future performance.

Inputs must contain at least two positive, finite price or wealth observations. This analysis does
not adjust for cash flows, inflation, liquidity, or benchmark performance and is not a forecast or
investment recommendation.
