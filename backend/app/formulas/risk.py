"""Section 5.2 — Portfolio Variance & Volatility, Section 5.3 — Covariance & Correlation."""
from __future__ import annotations

import numpy as np


def covariance_matrix(returns_matrix: np.ndarray) -> np.ndarray:
    """
    Section 5.3 — Cov(i,j) = 1/(n-1) * sum_t (R_i,t - Rbar_i)(R_j,t - Rbar_j)

    returns_matrix: shape (n_periods, n_assets) — each column is one asset's return series.
    Returns the (n_assets, n_assets) sample covariance matrix.
    """
    returns_matrix = np.asarray(returns_matrix, dtype=np.float64)
    if returns_matrix.ndim != 2:
        raise ValueError("returns_matrix must be 2D: (n_periods, n_assets)")
    if returns_matrix.shape[0] < 2:
        raise ValueError("need at least 2 return observations to compute covariance")
    # rowvar=False: each column is a variable (asset), each row an observation (period)
    cov = np.cov(returns_matrix, rowvar=False, ddof=1)
    # np.cov collapses to a 0-d scalar for a single-asset (1-column) input
    # instead of a 1x1 matrix; normalize so callers can always rely on a
    # proper (n_assets, n_assets) 2D array, including n_assets == 1.
    return np.atleast_2d(cov)


def correlation_matrix(returns_matrix: np.ndarray) -> np.ndarray:
    """rho_ij = Cov(i,j) / (sigma_i * sigma_j)  — Section 5.3."""
    cov = covariance_matrix(returns_matrix)
    std = np.sqrt(np.diag(cov))
    denom = np.outer(std, std)
    with np.errstate(divide="ignore", invalid="ignore"):
        corr = np.where(denom > 0, cov / denom, 0.0)
    np.fill_diagonal(corr, 1.0)
    return corr


def portfolio_variance(weights: np.ndarray, cov_matrix: np.ndarray) -> float:
    """sigma_p^2 = w^T . Sigma . w  — Section 5.2 (matrix form)."""
    w = np.asarray(weights, dtype=np.float64)
    sigma = np.asarray(cov_matrix, dtype=np.float64)
    variance = float(w @ sigma @ w)
    # Guard against tiny negative values from floating-point noise.
    return max(variance, 0.0)


def portfolio_volatility(weights: np.ndarray, cov_matrix: np.ndarray) -> float:
    """sigma_p = sqrt(sigma_p^2)  — Section 5.2."""
    return float(np.sqrt(portfolio_variance(weights, cov_matrix)))


def two_asset_variance(w1: float, w2: float, sigma1: float, sigma2: float, rho: float) -> float:
    """sigma_p^2 = w1^2*sigma1^2 + w2^2*sigma2^2 + 2*w1*w2*rho*sigma1*sigma2 — Section 5.2 (two-asset form)."""
    return float(
        w1 ** 2 * sigma1 ** 2
        + w2 ** 2 * sigma2 ** 2
        + 2 * w1 * w2 * rho * sigma1 * sigma2
    )
