import math


def calculate_mean(values):
    if not values:
        return 0

    return sum(values) / len(values)


def calculate_volatility(returns):
    if len(returns) < 2:
        return 0

    mean = calculate_mean(returns)

    squared_differences = []

    for value in returns:
        difference = value - mean
        squared_differences.append(difference ** 2)

    variance = sum(squared_differences) / (len(returns) - 1)

    return math.sqrt(variance)


def calculate_var(returns, confidence=0.95):
    sorted_returns = sorted(returns)

    index = int((1 - confidence) * len(sorted_returns))

    if index >= len(sorted_returns):
        index = len(sorted_returns) - 1

    return sorted_returns[index]


def calculate_cvar(returns, confidence=0.95):
    sorted_returns = sorted(returns)

    cutoff_index = int((1 - confidence) * len(sorted_returns))

    if cutoff_index < 1:
        cutoff_index = 1

    worst_returns = sorted_returns[:cutoff_index]

    return calculate_mean(worst_returns)


def calculate_max_drawdown(prices):
    if not prices:
        return 0

    peak = prices[0]
    max_drawdown = 0

    for price in prices:

        if price > peak:
            peak = price

        drawdown = (price - peak) / peak

        if drawdown < max_drawdown:
            max_drawdown = drawdown

    return max_drawdown