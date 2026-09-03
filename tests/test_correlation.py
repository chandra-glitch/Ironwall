import pytest

from ironwall.correlation import calculate_return_correlation_matrix


def test_correlation_matrix_is_symmetric_with_unit_diagonal():
    matrix = calculate_return_correlation_matrix(
        {
            "JPM": (-0.02, 0.0, 0.02),
            "BAC": (-0.04, 0.0, 0.04),
            "GLD": (0.02, 0.0, -0.02),
        }
    )

    assert matrix["JPM"]["JPM"] == 1.0
    assert matrix["BAC"]["BAC"] == 1.0
    assert matrix["GLD"]["GLD"] == 1.0
    assert matrix["JPM"]["BAC"] == pytest.approx(1.0)
    assert matrix["BAC"]["JPM"] == matrix["JPM"]["BAC"]
    assert matrix["JPM"]["GLD"] == pytest.approx(-1.0)
    assert matrix["GLD"]["JPM"] == matrix["JPM"]["GLD"]


def test_uncorrelated_return_patterns_produce_zero():
    matrix = calculate_return_correlation_matrix(
        {
            "A": (-1.0, 0.0, 1.0),
            "B": (1.0, 0.0, 1.0),
        }
    )

    assert matrix["A"]["B"] == pytest.approx(0.0, abs=1e-15)
    assert matrix["B"]["A"] == pytest.approx(0.0, abs=1e-15)


@pytest.mark.parametrize(
    "asset_returns, message",
    [
        ({"JPM": (0.01, 0.02)}, "at least two assets"),
        ({"JPM": (0.01,), "BAC": (0.02,)}, "at least two return observations"),
        ({"JPM": (0.01, 0.02), "BAC": (0.02, 0.03, 0.04)}, "aligned"),
        ({"JPM": (0.01, "bad"), "BAC": (0.02, 0.03)}, "must be numeric"),
        ({"JPM": (0.01, float("inf")), "BAC": (0.02, 0.03)}, "finite"),
        ({"JPM": (0.01, 0.01), "BAC": (0.02, 0.03)}, "zero-variance assets: JPM"),
    ],
)
def test_invalid_return_series_are_rejected(asset_returns, message):
    with pytest.raises(ValueError, match=message):
        calculate_return_correlation_matrix(asset_returns)
