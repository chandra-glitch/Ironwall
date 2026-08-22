from datetime import datetime


def generate_report(
    volatility,
    var,
    cvar,
    max_drawdown
):

    if var < -0.05 or max_drawdown < -0.10:
        risk_level = "HIGH"

    elif var < -0.02 or max_drawdown < -0.05:
        risk_level = "MEDIUM"

    else:
        risk_level = "LOW"

    report = f"""
========================================
          FINRISK-X RISK REPORT
========================================

Generated: {datetime.now()}

RISK LEVEL
----------
{risk_level}

RISK METRICS
------------

Annualized Volatility:
{volatility * (252 ** 0.5):.2%}

95% Value at Risk:
{var:.2%}

95% Conditional VaR:
{cvar:.2%}

Maximum Drawdown:
{max_drawdown:.2%}

========================================
"""

    return report