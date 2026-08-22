from data.loader import load_market_data, calculate_returns
from risk.metrics import (
    calculate_volatility,
    calculate_var,
    calculate_cvar,
    calculate_max_drawdown
)
from risk.report import generate_report


DATA_FILE = "data/market_data.csv"


def main():

    print("\nStarting FINRISK-X...\n")

    # Load market data
    dates, prices = load_market_data(DATA_FILE)

    print(f"Loaded {len(prices)} price records.")

    # Calculate daily returns
    returns = calculate_returns(prices)

    print(f"Calculated {len(returns)} daily returns.")

    # Calculate risk metrics
    volatility = calculate_volatility(returns)

    var = calculate_var(
        returns,
        confidence=0.95
    )

    cvar = calculate_cvar(
        returns,
        confidence=0.95
    )

    max_drawdown = calculate_max_drawdown(prices)

    # Generate report
    report = generate_report(
        volatility,
        var,
        cvar,
        max_drawdown
    )

    print(report)


if __name__ == "__main__":
    main()