"""Section 5.1 — Portfolio Expected Return, and shared return-series helpers."""
from __future__ import annotations

import numpy as np


def price_series_to_returns(prices: np.ndarray) -> np.ndarray:
    """Simple period-over-period returns from a price series."""
    prices = np.asarray(prices, dtype=np.float64)
    if prices.size < 2:
        return np.array([], dtype=np.float64)
    return prices[1:] / prices[:-1] - 1.0


def mean_return(returns: np.ndarray) -> float:
    returns = np.asarray(returns, dtype=np.float64)
    if returns.size == 0:
        return 0.0
    return float(np.mean(returns))


def annualize_return(period_return: float, periods_per_year: int = 252) -> float:
    """Compounds a per-period mean return to an annualized return."""
    return float((1.0 + period_return) ** periods_per_year - 1.0)


def annualize_volatility(period_volatility: float, periods_per_year: int = 252) -> float:
    return float(period_volatility * np.sqrt(periods_per_year))


def portfolio_expected_return(weights: np.ndarray, expected_returns: np.ndarray) -> float:
    """E(Rp) = sum(w_i * E(R_i))  — Section 5.1."""
    w = np.asarray(weights, dtype=np.float64)
    r = np.asarray(expected_returns, dtype=np.float64)
    if w.shape != r.shape:
        raise ValueError("weights and expected_returns must have the same shape")
    return float(np.dot(w, r))
