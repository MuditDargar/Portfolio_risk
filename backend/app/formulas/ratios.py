"""Section 5.4 — Sharpe Ratio, Section 5.5 — Sortino Ratio, Section 5.8 — Treynor Ratio."""
from __future__ import annotations

import numpy as np


def sharpe_ratio(portfolio_return: float, risk_free_rate: float, volatility: float) -> float:
    """Sharpe = (Rp - Rf) / sigma_p — Section 5.4."""
    if volatility == 0:
        return 0.0
    return float((portfolio_return - risk_free_rate) / volatility)


def downside_deviation(returns: np.ndarray, target: float = 0.0) -> float:
    """sigma_d = sqrt(mean(min(R_i - T, 0)^2)) — Section 5.5."""
    returns = np.asarray(returns, dtype=np.float64)
    if returns.size == 0:
        return 0.0
    downside = np.minimum(returns - target, 0.0)
    return float(np.sqrt(np.mean(downside ** 2)))


def sortino_ratio(
    portfolio_return: float,
    risk_free_rate: float,
    returns: np.ndarray,
    target: float = 0.0,
) -> float:
    """Sortino = (Rp - Rf) / sigma_d — Section 5.5."""
    sigma_d = downside_deviation(returns, target)
    if sigma_d == 0:
        return 0.0
    return float((portfolio_return - risk_free_rate) / sigma_d)


def treynor_ratio(portfolio_return: float, risk_free_rate: float, beta: float) -> float:
    """Treynor = (Rp - Rf) / beta_p — Section 5.8."""
    if beta == 0:
        return 0.0
    return float((portfolio_return - risk_free_rate) / beta)
