"""Section 5.15 — Markowitz Mean-Variance Optimization (Efficient Frontier)."""
from __future__ import annotations

import numpy as np
from scipy.optimize import minimize

from .returns import portfolio_expected_return
from .risk import portfolio_variance


def minimum_variance_weights(
    cov_matrix: np.ndarray,
    expected_returns: np.ndarray,
    target_return: float | None = None,
) -> np.ndarray:
    """
    minimize   w^T . Sigma . w
    subject to sum(w) = 1, w^T . E(R) = targetReturn (if given), w_i >= 0
    Solved via SLSQP — Section 5.15.
    """
    n = len(expected_returns)
    cov_matrix = np.asarray(cov_matrix, dtype=np.float64)
    expected_returns = np.asarray(expected_returns, dtype=np.float64)

    constraints = [{"type": "eq", "fun": lambda w: np.sum(w) - 1.0}]
    if target_return is not None:
        constraints.append(
            {"type": "eq", "fun": lambda w: portfolio_expected_return(w, expected_returns) - target_return}
        )

    bounds = [(0.0, 1.0)] * n
    initial_guess = np.full(n, 1.0 / n)

    result = minimize(
        lambda w: portfolio_variance(w, cov_matrix),
        initial_guess,
        method="SLSQP",
        bounds=bounds,
        constraints=constraints,
        options={"maxiter": 500, "ftol": 1e-12},
    )
    if not result.success:
        raise ValueError(f"efficient-frontier optimization failed: {result.message}")
    return result.x


def efficient_frontier(
    cov_matrix: np.ndarray,
    expected_returns: np.ndarray,
    n_points: int = 15,
) -> list[dict]:
    """
    Sweeps target return across the achievable range and re-solves the
    minimum-variance problem at each point to trace the efficient frontier —
    Section 5.15.
    """
    expected_returns = np.asarray(expected_returns, dtype=np.float64)
    min_ret = float(np.min(expected_returns))
    max_ret = float(np.max(expected_returns))

    frontier = []
    for target_return in np.linspace(min_ret, max_ret, n_points):
        try:
            weights = minimum_variance_weights(cov_matrix, expected_returns, target_return)
        except ValueError:
            continue
        variance = portfolio_variance(weights, cov_matrix)
        frontier.append(
            {
                "target_return": float(target_return),
                "volatility": float(np.sqrt(variance)),
                "weights": weights.tolist(),
            }
        )
    return frontier
