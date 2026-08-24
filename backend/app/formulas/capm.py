"""Section 5.6 — CAPM Beta & Expected Return, Section 5.7 — Jensen's Alpha."""
from __future__ import annotations

import numpy as np


def beta(asset_returns: np.ndarray, market_returns: np.ndarray) -> float:
    """beta_i = Cov(Ri, Rm) / Var(Rm) — Section 5.6."""
    asset_returns = np.asarray(asset_returns, dtype=np.float64)
    market_returns = np.asarray(market_returns, dtype=np.float64)
    if asset_returns.shape != market_returns.shape:
        raise ValueError("asset_returns and market_returns must be the same length")
    if asset_returns.size < 2:
        raise ValueError("need at least 2 observations to compute beta")
    cov = np.cov(asset_returns, market_returns, ddof=1)[0, 1]
    market_var = np.var(market_returns, ddof=1)
    if market_var == 0:
        return 0.0
    return float(cov / market_var)


def capm_expected_return(risk_free_rate: float, beta_i: float, market_return: float) -> float:
    """E(Ri)_CAPM = Rf + beta_i * (E(Rm) - Rf) — Section 5.6."""
    return float(risk_free_rate + beta_i * (market_return - risk_free_rate))


def jensens_alpha(
    portfolio_return: float,
    risk_free_rate: float,
    beta_p: float,
    market_return: float,
) -> float:
    """alpha_p = Rp - [Rf + beta_p * (Rm - Rf)] — Section 5.7."""
    predicted = capm_expected_return(risk_free_rate, beta_p, market_return)
    return float(portfolio_return - predicted)
