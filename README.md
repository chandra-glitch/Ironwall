# IRONWALL

[![CI](https://github.com/chandra-glitch/Ironwall/actions/workflows/ci.yml/badge.svg)](https://github.com/chandra-glitch/Ironwall/actions/workflows/ci.yml)

**Autonomous Financial Risk Intelligence and Stress-Testing Platform**

IRONWALL is a transparent Python toolkit for analysing individual assets and weighted
portfolios. It validates price data, calculates historical downside risk, attributes portfolio
volatility, and produces reports suitable for both people and downstream applications.

> This project is for education and research. It does not provide financial advice.

## Current capabilities

- Strict validation for single-asset and aligned portfolio CSV files
- Daily returns, total return, annualized volatility and Sharpe ratio
- Historical Value at Risk (VaR) and Conditional VaR / Expected Shortfall
- Rolling historical VaR backtesting with a Kupiec unconditional coverage test
- Maximum drawdown using a portfolio wealth curve
- Long-only weighted portfolio analysis
- Euler volatility-risk contribution by asset
- Real adjusted-close downloads through Yahoo Finance
- Markdown and JSON reports with UTC timestamps
- Automated tests, linting and GitHub Actions CI

## Architecture

~~~mermaid
flowchart TD
    A[CSV or Yahoo Finance] --> B[Validation]
    B --> C[Return engine]
    C --> D[Risk metrics]
    D --> E[Risk classification]
    E --> F[Console, JSON or Markdown]
~~~

The calculations are deliberately implemented in readable Python so every assumption can be
inspected. Yahoo Finance is optional and is used only to acquire data.

## Quick start on Windows

~~~powershell
git clone https://github.com/chandra-glitch/Ironwall.git
cd Ironwall
py -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e ".[dev,market]"
~~~

Analyse the included synthetic single-asset dataset:

~~~powershell
ironwall analyze --csv data/sample_market_data.csv
~~~

Backtest whether rolling 95% historical VaR forecasts achieve their expected coverage:

~~~powershell
ironwall backtest --csv data/sample_market_data.csv --window 10 `
  --output results/var-backtest.md
~~~

Analyse the example banking portfolio:

~~~powershell
ironwall portfolio --csv data/sample_portfolio.csv `
  --weights JPM=0.50,BAC=0.30,GS=0.20 `
  --output results/bank_portfolio.json
~~~

Download real adjusted closing prices and analyse them:

~~~powershell
ironwall fetch JPM --start 2024-01-01 --output data/downloads/JPM.csv
ironwall analyze --csv data/downloads/JPM.csv --output results/JPM-risk.md
~~~

For multiple tickers, the fetch command creates the wide CSV expected by portfolio analysis:

~~~powershell
ironwall fetch JPM BAC GS --start 2024-01-01 --output data/downloads/banks.csv
ironwall portfolio --csv data/downloads/banks.csv --weights JPM=0.5,BAC=0.3,GS=0.2
~~~

## Metric conventions

| Metric | Convention |
|---|---|
| VaR | Interpolated historical return quantile, displayed as a positive loss |
| CVaR | Mean of observations at or below the VaR cutoff, displayed as a positive loss |
| VaR backtest | One-step forecasts from prior returns only; exceptions are losses beyond VaR |
| Kupiec test | Likelihood-ratio test of whether the observed exception rate matches confidence |
| Volatility | Sample return standard deviation multiplied by the square root of 252 |
| Drawdown | Largest peak-to-trough decline, displayed as a positive loss |
| Risk contribution | Euler contribution to portfolio variance; contributions sum to 100% |

The LOW, MEDIUM and HIGH labels use transparent educational thresholds across volatility, VaR,
CVaR and drawdown. They are not trading signals or regulatory risk limits.

The exception-coverage statistic follows the likelihood-ratio method introduced by
[Kupiec (1995)](https://doi.org/10.3905/jod.1995.407942). Tail tests have limited power with
small out-of-sample datasets, so treat the included short sample as a software demonstration and
use a substantially longer history for model validation.

## Input formats

Single-asset CSV:

~~~csv
Date,Close
2026-01-02,100.0
2026-01-05,102.0
2026-01-06,101.0
~~~

Portfolio CSV:

~~~csv
Date,JPM,BAC,GS
2026-01-02,100.0,50.0,200.0
2026-01-05,102.0,50.5,203.0
2026-01-06,101.0,49.8,202.0
~~~

Dates must be unique and strictly increasing. Prices must be positive and finite. Portfolio rows
must contain a price for every asset so all returns remain aligned.

## Repository layout

- **src/ironwall/** — application package and CLI
- **data/** — small synthetic datasets safe to commit
- **tests/** — unit and integration tests
- **results/** — locally generated reports, ignored by Git
- **.github/workflows/ci.yml** — automated lint and test checks

## Development

~~~powershell
python -m pip install -e ".[dev]"
ruff check .
pytest
~~~

## Roadmap

- Monte Carlo VaR and scenario stress tests
- Rolling portfolio risk windows and backtest visualizations
- Factor exposure and correlation analysis
- FastAPI service and interactive dashboard
- Model-risk documentation and reproducible research notebooks

## Disclaimer

IRONWALL is an educational research project. Outputs depend on data quality and modelling
assumptions, may be incomplete or inaccurate, and must not be treated as investment advice.
