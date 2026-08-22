from src.risk.metrics import (
    calculate_mean,
    calculate_volatility,
    calculate_var,
    calculate_max_drawdown
)


def test_mean():
    values = [1, 2, 3, 4, 5]

    result = calculate_mean(values)

    assert result == 3


def test_volatility():
    returns = [0.01, 0.02, 0.03]

    result = calculate_volatility(returns)

    assert result > 0


def test_var():
    returns = [
        -0.10,
        -0.05,
        -0.02,
        0.01,
        0.03
    ]

    result = calculate_var(returns)

    assert result <= 0


def test_drawdown():
    prices = [100, 120, 90]

    result = calculate_max_drawdown(prices)

    assert result == -0.25