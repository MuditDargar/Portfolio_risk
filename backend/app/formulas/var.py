"""Section 5.9 — Value at Risk (VaR), Section 5.10 — Conditional VaR / Expected Shortfall."""
from __future__ import annotations

import numpy as np

# z-scores for common confidence levels — Section 5.9.
Z_SCORES = {
    0.90: 1.282,
    0.95: 1.645,
    0.99: 2.326,
}


def z_score_for_confidence(confidence: float) -> float:
    if confidence in Z_SCORES:
        return Z_SCORES[confidence]
    # Fall back to a normal-distribution quantile for confidence levels not in the table.
    from scipy.stats import norm

    return float(norm.ppf(confidence))


def parametric_var(
    portfolio_value: float,
    volatility: float,
    confidence: float = 0.95,
    horizon_days: int = 1,
) -> float:
    """VaR = PortfolioValue * Z_alpha * sigma_p * sqrt(t) — Section 5.9."""
    z = z_score_for_confidence(confidence)
    return float(portfolio_value * z * volatility * np.sqrt(horizon_days))


def historical_var(returns: np.ndarray, portfolio_value: float, confidence: float = 0.95) -> float:
    """Loss at the alpha-th percentile of the sorted historical P&L distribution — Section 5.9."""
    returns = np.asarray(returns, dtype=np.float64)
    if returns.size == 0:
        return 0.0
    losses = -returns * portfolio_value
    var = np.percentile(losses, confidence * 100.0)
    return float(max(var, 0.0))


def conditional_var(returns: np.ndarray, portfolio_value: float, confidence: float = 0.95) -> float:
    """CVaR = E[Loss | Loss > VaR] — Section 5.10."""
    returns = np.asarray(returns, dtype=np.float64)
    if returns.size == 0:
        return 0.0
    losses = -returns * portfolio_value
    var = historical_var(returns, portfolio_value, confidence)
    tail = losses[losses >= var]
    if tail.size == 0:
        return var
    return float(np.mean(tail))
