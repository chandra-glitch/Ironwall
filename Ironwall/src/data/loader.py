import csv


def load_market_data(file_path):
    dates = []
    prices = []

    with open(file_path, "r") as file:
        reader = csv.DictReader(file)

        for row in reader:
            dates.append(row["Date"])
            prices.append(float(row["Close"]))

    return dates, prices


def calculate_returns(prices):
    returns = []

    for i in range(1, len(prices)):
        previous_price = prices[i - 1]
        current_price = prices[i]

        daily_return = (current_price - previous_price) / previous_price

        returns.append(daily_return)

    return returns
