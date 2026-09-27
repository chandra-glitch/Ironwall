import json
import math
import random
from decimal import Decimal

import pytest

from ironwall.operational_loss import analyze_operational_losses


def test_analysis_reports_frequency_severity_and_material_losses():
    result = analyze_operational_losses(
        {
            "Payment outage": 100,
            "Processing error": 300,
        },
        observation_years=2,
        materiality_threshold=250,
    )

    assert result.event_count == 2
    assert result.observation_years == 2
    assert result.total_loss == 400
    assert result.annualized_loss == 200
    assert result.annualized_event_frequency == 1
    assert result.mean_loss == 200
    assert result.median_loss == 200
    assert result.sample_loss_standard_deviation == pytest.approx(math.sqrt(20_000))
    assert result.largest_event_id == "Processing error"
    assert result.largest_loss == 300
    assert result.largest_loss_share == pytest.approx(0.75)
    assert result.material_event_count == 1
    assert result.material_loss == 300
    assert result.material_loss_share == pytest.approx(0.75)
    assert result.annualized_material_event_frequency == 0.5

    assert [event.event_id for event in result.events] == [
        "Processing error",
        "Payment outage",
    ]
    assert [event.is_material for event in result.events] == [True, False]
    assert sum(event.share_of_total_loss for event in result.events) == pytest.approx(1)


def test_equal_severity_events_use_event_id_as_deterministic_tie_breaker():
    result = analyze_operational_losses(
        {"Z event": 10, "A event": 10},
        observation_years=1,
    )

    assert [event.event_id for event in result.events] == ["A event", "Z event"]
    assert result.largest_event_id == "A event"


def test_single_event_has_undefined_sample_standard_deviation():
    result = analyze_operational_losses(
        {"Only event": 125},
        observation_years=0.5,
        materiality_threshold=200,
    )

    assert result.sample_loss_standard_deviation is None
    assert result.annualized_loss == 250
    assert result.annualized_event_frequency == 2
    assert result.material_event_count == 0
    assert result.material_loss == 0
    assert result.material_loss_share == 0
    assert result.annualized_material_event_frequency == 0


def test_threshold_is_inclusive():
    result = analyze_operational_losses(
        {"At threshold": 100, "Below": 99.99},
        observation_years=1,
        materiality_threshold=100,
    )

    assert result.material_event_count == 1
    assert result.events[0].event_id == "At threshold"
    assert result.events[0].is_material is True


def test_large_even_sample_median_does_not_overflow():
    result = analyze_operational_losses(
        {"Large": 1e308, "Smaller": 5e307},
        observation_years=1,
    )

    assert result.total_loss == pytest.approx(1.5e308)
    assert result.median_loss == pytest.approx(7.5e307)


def test_result_is_strict_json_ready():
    payload = analyze_operational_losses(
        {"A": 10, "B": 20},
        observation_years=2,
        materiality_threshold=15,
    ).to_dict()

    encoded = json.dumps(payload, allow_nan=False, sort_keys=True)

    assert payload["event_count"] == 2
    assert payload["sample_loss_standard_deviation"] == pytest.approx(math.sqrt(50))
    assert len(payload["events"]) == 2
    assert '"material_loss_share"' in encoded


def test_decimal_inputs_are_supported_without_precision_collapse():
    result = analyze_operational_losses(
        {"A": Decimal("12.5")},
        observation_years=Decimal("2.5"),
        materiality_threshold=Decimal("10"),
    )

    assert result.annualized_loss == 5
    assert result.events[0].is_material is True


def test_distinct_decimal_losses_cannot_collapse_to_the_same_float():
    with pytest.raises(ValueError, match="lose relative precision"):
        analyze_operational_losses(
            {
                "A": Decimal("1.00000000000000000001"),
                "B": Decimal("1"),
            },
            observation_years=1,
        )


def test_materiality_comparison_cannot_change_during_float_conversion():
    with pytest.raises(ValueError, match="materiality comparison loses precision"):
        analyze_operational_losses(
            {"A": Decimal("0.1")},
            observation_years=1,
            materiality_threshold=Decimal("0.100000000000000000001"),
        )


@pytest.mark.parametrize("loss_events", [None, [], {}, 1.0])
def test_loss_events_must_be_a_non_empty_mapping(loss_events):
    with pytest.raises(ValueError, match="non-empty mapping"):
        analyze_operational_losses(loss_events, observation_years=1)


@pytest.mark.parametrize("event_id", ["", " A", "A ", 1, True])
def test_invalid_event_ids_are_rejected(event_id):
    with pytest.raises(ValueError, match="event IDs"):
        analyze_operational_losses({event_id: 10}, observation_years=1)


@pytest.mark.parametrize(
    "loss",
    [0, -1, float("nan"), float("inf"), -float("inf"), "10", True, 10**1000],
)
def test_invalid_loss_amounts_are_rejected(loss):
    with pytest.raises(ValueError, match="loss amount"):
        analyze_operational_losses({"A": loss}, observation_years=1)


@pytest.mark.parametrize(
    "years",
    [0, -1, float("nan"), float("inf"), -float("inf"), "1", True, 10**1000],
)
def test_invalid_observation_years_are_rejected(years):
    with pytest.raises(ValueError, match="observation_years"):
        analyze_operational_losses({"A": 10}, observation_years=years)


@pytest.mark.parametrize(
    "threshold",
    [-1, float("nan"), float("inf"), -float("inf"), "1", True, 10**1000],
)
def test_invalid_materiality_thresholds_are_rejected(threshold):
    with pytest.raises(ValueError, match="materiality_threshold"):
        analyze_operational_losses(
            {"A": 10},
            observation_years=1,
            materiality_threshold=threshold,
        )


@pytest.mark.parametrize(
    "field, value",
    [
        ("loss", Decimal("1e-10000")),
        ("years", Decimal("1e-10000")),
        ("threshold", Decimal("1e-10000")),
    ],
)
def test_nonzero_decimal_inputs_cannot_silently_underflow(field, value):
    kwargs = {
        "loss_events": {"A": value if field == "loss" else 10},
        "observation_years": value if field == "years" else 1,
        "materiality_threshold": value if field == "threshold" else 0,
    }

    with pytest.raises(ValueError, match="loses material precision"):
        analyze_operational_losses(**kwargs)


def test_total_loss_overflow_is_rejected():
    with pytest.raises(ValueError, match="total operational loss exceeds"):
        analyze_operational_losses({"A": 1e308, "B": 1e308}, observation_years=1)


def test_annualized_loss_overflow_is_rejected():
    with pytest.raises(ValueError, match="annualized operational loss exceeds"):
        analyze_operational_losses({"A": 1e308}, observation_years=5e-324)


def test_annualized_loss_underflow_is_rejected():
    with pytest.raises(ValueError, match="annualized operational loss exceeds"):
        analyze_operational_losses({"A": 5e-324}, observation_years=1e308)


def test_annualized_frequency_overflow_is_rejected():
    with pytest.raises(ValueError, match="annualized event frequency exceeds"):
        analyze_operational_losses({"A": 5e-324}, observation_years=5e-324)


def test_event_share_underflow_is_rejected():
    with pytest.raises(ValueError, match="total-loss share for A exceeds"):
        analyze_operational_losses(
            {"A": 5e-324, "B": 1e308},
            observation_years=1,
        )


def test_randomized_results_reconcile():
    generator = random.Random(20260927)

    for case in range(1_000):
        event_count = generator.randint(1, 20)
        losses = {
            f"event-{index:02d}": 10 ** generator.uniform(-2, 6) for index in range(event_count)
        }
        years = generator.uniform(0.25, 20)
        threshold = 10 ** generator.uniform(-2, 6)

        result = analyze_operational_losses(
            losses,
            observation_years=years,
            materiality_threshold=threshold,
        )
        material = [loss for loss in losses.values() if loss >= threshold]

        assert result.event_count == event_count
        assert result.total_loss == pytest.approx(math.fsum(losses.values()))
        assert result.annualized_loss == pytest.approx(result.total_loss / years)
        assert result.annualized_event_frequency == pytest.approx(event_count / years)
        assert result.material_event_count == len(material)
        assert result.material_loss == pytest.approx(math.fsum(material))
        assert sum(event.share_of_total_loss for event in result.events) == pytest.approx(1)
        assert result.largest_loss == max(losses.values())
        assert [event.loss_amount for event in result.events] == sorted(
            losses.values(), reverse=True
        )
        assert all(
            event.is_material == (event.loss_amount >= threshold) for event in result.events
        ), case
