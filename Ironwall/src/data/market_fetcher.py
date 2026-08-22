import yfinance as yf

data = yf.download(
    "JPM",
    start="2024-01-01",
    end="2026-01-01"
)

print(data.head())