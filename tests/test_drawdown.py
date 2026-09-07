import json

import pytest

from ironwall.drawdown import find_maximum_drawdown_episode
from ironwall.metrics import calculate_max_drawdown


def test_recovered_drawdown_reports_timing_and_magnitude():
    values = [100, 120, 90, 105, 120, 130]

    episode = find_maximum_drawdown_episode(values)

    assert episode is not None
    assert episode.peak_index == 1
    assert episode.trough_index == 2
    assert episode.recovery_index == 4
    assert episode.peak_value == pytest.approx(120)
    assert episode.trough_value == pytest.approx(90)
    assert episode.maximum_drawdown == pytest.approx(0.25)
    assert episode.maximum_drawdown == pytest.approx(calculate_max_drawdown(values))
    assert episode.periods_to_trough == 1
    assert episode.periods_to_recovery == 2
    assert episode.recovered is True


def test_unrecovered_drawdown_uses_null_recovery_fields():
    episode = find_maximum_drawdown_episode([100, 120, 80, 100])

    assert episode is not None
    assert episode.maximum_drawdown == pytest.approx(1 / 3)
    assert episode.recovery_index is None
    assert episode.periods_to_recovery is None
    assert episode.recovered is False


def test_later_deeper_episode_uses_its_own_peak():
    episode = find_maximum_drawdown_episode([100, 80, 110, 77, 110])

    assert episode is not None
    assert episode.peak_index == 2
    assert episode.trough_index == 3
    assert episode.recovery_index == 4
    assert episode.maximum_drawdown == pytest.approx(0.30)


def test_non_decreasing_series_has_no_drawdown_episode():
    assert find_maximum_drawdown_episode([100, 100, 110, 110]) is None


def test_drawdown_episode_is_json_ready():
    episode = find_maximum_drawdown_episode([100, 75, 100])

    assert episode is not None
    assert json.loads(json.dumps(episode.to_dict())) == {
        "maximum_drawdown": 0.25,
        "peak_index": 0,
        "peak_value": 100.0,
        "periods_to_recovery": 1,
        "periods_to_trough": 1,
        "recovered": True,
        "recovery_index": 2,
        "trough_index": 1,
        "trough_value": 75.0,
    }


@pytest.mark.parametrize(
    "values, message",
    [
        ([100], "at least two observations"),
        ([100, 0], "positive and finite"),
        ([100, -1], "positive and finite"),
        ([100, float("inf")], "positive and finite"),
        ([100, float("nan")], "positive and finite"),
    ],
)
def test_invalid_drawdown_series_is_rejected(values, message):
    with pytest.raises(ValueError, match=message):
        find_maximum_drawdown_episode(values)
