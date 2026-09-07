"""Maximum-drawdown episode analysis for price and wealth series."""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass

__all__ = ["DrawdownEpisode", "find_maximum_drawdown_episode"]


@dataclass(frozen=True)
class DrawdownEpisode:
    """Timing and magnitude of a maximum peak-to-trough decline."""

    peak_index: int
    trough_index: int
    recovery_index: int | None
    peak_value: float
    trough_value: float
    maximum_drawdown: float

    @property
    def recovered(self) -> bool:
        """Whether the series returned to its pre-drawdown peak."""

        return self.recovery_index is not None

    @property
    def periods_to_trough(self) -> int:
        """Number of observation intervals from peak to trough."""

        return self.trough_index - self.peak_index

    @property
    def periods_to_recovery(self) -> int | None:
        """Number of observation intervals from trough to recovery."""

        if self.recovery_index is None:
            return None
        return self.recovery_index - self.trough_index

    def to_dict(self) -> dict[str, bool | float | int | None]:
        """Return a JSON-serializable representation of the episode."""

        return {
            "peak_index": self.peak_index,
            "trough_index": self.trough_index,
            "recovery_index": self.recovery_index,
            "peak_value": self.peak_value,
            "trough_value": self.trough_value,
            "maximum_drawdown": self.maximum_drawdown,
            "recovered": self.recovered,
            "periods_to_trough": self.periods_to_trough,
            "periods_to_recovery": self.periods_to_recovery,
        }


def find_maximum_drawdown_episode(values: Sequence[float]) -> DrawdownEpisode | None:
    """Locate the largest peak-to-trough decline and its first recovery.

    Values must be a price or wealth series with at least two positive, finite
    observations. The earliest episode is returned when multiple drawdowns have
    equal maximum depth. A non-decreasing series has no drawdown and returns
    ``None``.
    """

    parsed = tuple(float(value) for value in values)
    if len(parsed) < 2:
        raise ValueError("Drawdown episode analysis requires at least two observations.")
    if any(not math.isfinite(value) or value <= 0 for value in parsed):
        raise ValueError("Drawdown episode values must be positive and finite.")

    running_peak_index = 0
    running_peak_value = parsed[0]
    maximum_drawdown = 0.0
    episode_peak_index = 0
    episode_trough_index = 0

    for index, value in enumerate(parsed[1:], start=1):
        if value >= running_peak_value:
            running_peak_index = index
            running_peak_value = value
            continue

        drawdown = (running_peak_value - value) / running_peak_value
        if drawdown > maximum_drawdown:
            maximum_drawdown = drawdown
            episode_peak_index = running_peak_index
            episode_trough_index = index

    if maximum_drawdown == 0.0:
        return None

    peak_value = parsed[episode_peak_index]
    recovery_index = next(
        (
            index
            for index in range(episode_trough_index + 1, len(parsed))
            if parsed[index] >= peak_value
        ),
        None,
    )
    return DrawdownEpisode(
        peak_index=episode_peak_index,
        trough_index=episode_trough_index,
        recovery_index=recovery_index,
        peak_value=peak_value,
        trough_value=parsed[episode_trough_index],
        maximum_drawdown=maximum_drawdown,
    )
