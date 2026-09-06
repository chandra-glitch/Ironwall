import pytest

from ironwall.concentration import analyze_weight_concentration


def test_equal_weight_portfolio_has_minimum_concentration():
    result = analyze_weight_concentration({"JPM": 0.25, "BAC": 0.25, "GS": 0.25, "MS": 0.25})

    assert result.asset_count == 4
    assert result.largest_weight == pytest.approx(0.25)
    assert result.herfindahl_index == pytest.approx(0.25)
    assert result.effective_number_of_assets == pytest.approx(4.0)
    assert result.normalized_herfindahl_index == pytest.approx(0.0)


def test_concentrated_portfolio_reports_effective_holdings():
    result = analyze_weight_concentration({"JPM": 0.7, "BAC": 0.2, "GS": 0.1})

    assert result.largest_weight == pytest.approx(0.7)
    assert result.herfindahl_index == pytest.approx(0.54)
    assert result.effective_number_of_assets == pytest.approx(1.0 / 0.54)
    assert result.normalized_herfindahl_index == pytest.approx(0.31)


def test_fully_concentrated_portfolio_reaches_upper_bound():
    result = analyze_weight_concentration({"JPM": 1.0, "BAC": 0.0})

    assert result.herfindahl_index == pytest.approx(1.0)
    assert result.effective_number_of_assets == pytest.approx(1.0)
    assert result.normalized_herfindahl_index == pytest.approx(1.0)


def test_concentration_metrics_are_json_ready():
    result = analyze_weight_concentration({"JPM": 0.6, "BAC": 0.4})

    assert result.to_dict() == {
        "asset_count": 2,
        "largest_weight": pytest.approx(0.6),
        "herfindahl_index": pytest.approx(0.52),
        "effective_number_of_assets": pytest.approx(1.0 / 0.52),
        "normalized_herfindahl_index": pytest.approx(0.04),
    }


@pytest.mark.parametrize(
    "weights, message",
    [
        ({"JPM": 1.0}, "at least two assets"),
        ({"JPM": 0.6, "BAC": 0.3}, "sum to 1.0"),
        ({"JPM": 1.1, "BAC": -0.1}, "non-negative"),
        ({"JPM": float("inf"), "BAC": 0.0}, "finite"),
        ({"JPM": float("nan"), "BAC": 0.0}, "finite"),
    ],
)
def test_invalid_weights_are_rejected(weights, message):
    with pytest.raises(ValueError, match=message):
        analyze_weight_concentration(weights)
