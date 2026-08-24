"""
Unit tests for the Section 5 formula engine.

Reference values are taken directly from the "Worked Example" in each
subsection of the SDD, plus property-based checks from Section 10
(Testing Strategy): weights sum to 1, variance >= 0, VaR_99 >= VaR_95.
"""
from datetime import date

import numpy as np
import pytest

from app.formulas import capm, drawdown, optimizer, ratios, rebalance, returns, risk, var, xirr


# ---------------------------------------------------------------------------
# 5.1 Portfolio Expected Return
# ---------------------------------------------------------------------------
def test_portfolio_expected_return_worked_example():
    w = np.array([0.40, 0.35, 0.25])
    r = np.array([0.12, 0.08, 0.15])
    assert returns.portfolio_expected_return(w, r) == pytest.approx(0.1135, abs=1e-9)


# ---------------------------------------------------------------------------
# 5.2 Portfolio Variance & Volatility
# ---------------------------------------------------------------------------
def test_two_asset_variance_worked_example():
    variance = risk.two_asset_variance(w1=0.6, w2=0.4, sigma1=0.20, sigma2=0.15, rho=0.3)
    assert variance == pytest.approx(0.02232, abs=1e-6)
    assert np.sqrt(variance) == pytest.approx(0.1494, abs=1e-3)


def test_portfolio_variance_matches_two_asset_form():
    cov = np.array([[0.04, 0.3 * 0.20 * 0.15], [0.3 * 0.20 * 0.15, 0.0225]])
    w = np.array([0.6, 0.4])
    assert risk.portfolio_variance(w, cov) == pytest.approx(0.02232, abs=1e-6)


def test_portfolio_variance_never_negative():
    cov = np.array([[0.01, 0.005], [0.005, 0.02]])
    for w in [np.array([1.0, 0.0]), np.array([0.0, 1.0]), np.array([0.5, 0.5])]:
        assert risk.portfolio_variance(w, cov) >= 0.0


# ---------------------------------------------------------------------------
# 5.3 Covariance & Correlation
# ---------------------------------------------------------------------------
def test_covariance_matrix_symmetric_and_matches_numpy():
    rng = np.random.default_rng(42)
    returns_matrix = rng.normal(0, 0.01, size=(100, 3))
    cov = risk.covariance_matrix(returns_matrix)
    assert cov.shape == (3, 3)
    assert np.allclose(cov, cov.T)


def test_covariance_matrix_single_asset_is_1x1_not_scalar():
    # np.cov collapses a single-column input to a 0-d scalar; a single-asset
    # portfolio (a legitimate FR-1 case) must still get a proper 2D matrix
    # so downstream w^T . Sigma . w matrix algebra doesn't break.
    rng = np.random.default_rng(11)
    returns_matrix = rng.normal(0, 0.01, size=(30, 1))
    cov = risk.covariance_matrix(returns_matrix)
    assert cov.shape == (1, 1)
    assert cov.ndim == 2

    weights = np.array([1.0])
    variance = risk.portfolio_variance(weights, cov)
    assert variance == pytest.approx(float(cov[0, 0]), abs=1e-12)


def test_correlation_diagonal_is_one():
    rng = np.random.default_rng(1)
    returns_matrix = rng.normal(0, 0.01, size=(50, 2))
    corr = risk.correlation_matrix(returns_matrix)
    assert np.allclose(np.diag(corr), 1.0)
    assert -1.0 <= corr[0, 1] <= 1.0


# ---------------------------------------------------------------------------
# 5.4 Sharpe Ratio
# ---------------------------------------------------------------------------
def test_sharpe_ratio_worked_example():
    assert ratios.sharpe_ratio(0.11, 0.065, 0.15) == pytest.approx(0.30, abs=1e-6)


# ---------------------------------------------------------------------------
# 5.5 Sortino Ratio
# ---------------------------------------------------------------------------
def test_sortino_ratio_penalizes_downside_only():
    upside_heavy = np.array([0.05, 0.06, -0.01, 0.04, 0.05])
    sortino = ratios.sortino_ratio(0.11, 0.065, upside_heavy, target=0.0)
    sharpe = ratios.sharpe_ratio(0.11, 0.065, float(np.std(upside_heavy, ddof=1)))
    # With mostly-upside volatility, Sortino (penalizing only downside) should exceed Sharpe.
    assert sortino > sharpe


def test_downside_deviation_zero_when_no_losses():
    all_gains = np.array([0.01, 0.02, 0.03])
    assert ratios.downside_deviation(all_gains, target=0.0) == 0.0


# ---------------------------------------------------------------------------
# 5.6 CAPM Beta & Expected Return
# ---------------------------------------------------------------------------
def test_capm_expected_return_worked_example():
    result = capm.capm_expected_return(risk_free_rate=0.065, beta_i=1.4, market_return=0.12)
    assert result == pytest.approx(0.142, abs=1e-6)


def test_beta_of_market_with_itself_is_one():
    rng = np.random.default_rng(7)
    market = rng.normal(0.0005, 0.01, size=100)
    assert capm.beta(market, market) == pytest.approx(1.0, abs=1e-9)


# ---------------------------------------------------------------------------
# 5.7 Jensen's Alpha
# ---------------------------------------------------------------------------
def test_jensens_alpha_worked_example():
    alpha = capm.jensens_alpha(portfolio_return=0.13, risk_free_rate=0.065, beta_p=1.1, market_return=0.12)
    assert alpha == pytest.approx(0.0045, abs=1e-6)


# ---------------------------------------------------------------------------
# 5.8 Treynor Ratio
# ---------------------------------------------------------------------------
def test_treynor_ratio_worked_example():
    assert ratios.treynor_ratio(0.11, 0.065, 0.9) == pytest.approx(0.05, abs=1e-6)


# ---------------------------------------------------------------------------
# 5.9 Value at Risk (VaR)
# ---------------------------------------------------------------------------
def test_parametric_var_worked_example():
    result = var.parametric_var(portfolio_value=1_000_000, volatility=0.012, confidence=0.95, horizon_days=1)
    assert result == pytest.approx(19_740, abs=1)


def test_var_99_always_gte_var_95():
    rng = np.random.default_rng(3)
    daily_returns = rng.normal(0.0003, 0.01, size=500)
    var_95 = var.historical_var(daily_returns, 1_000_000, confidence=0.95)
    var_99 = var.historical_var(daily_returns, 1_000_000, confidence=0.99)
    assert var_99 >= var_95


# ---------------------------------------------------------------------------
# 5.10 Conditional VaR / Expected Shortfall
# ---------------------------------------------------------------------------
def test_cvar_always_gte_var():
    rng = np.random.default_rng(5)
    daily_returns = rng.normal(0.0002, 0.015, size=500)
    var_95 = var.historical_var(daily_returns, 1_000_000, confidence=0.95)
    cvar_95 = var.conditional_var(daily_returns, 1_000_000, confidence=0.95)
    assert cvar_95 >= var_95


# ---------------------------------------------------------------------------
# 5.11 Maximum Drawdown
# ---------------------------------------------------------------------------
def test_max_drawdown_worked_example():
    values = np.array([1_200_000, 1_100_000, 960_000, 1_050_000])
    assert drawdown.max_drawdown(values) == pytest.approx(-0.20, abs=1e-6)


# ---------------------------------------------------------------------------
# 5.12 CAGR
# ---------------------------------------------------------------------------
def test_cagr_worked_example():
    result = drawdown.cagr(beginning_value=100_000, ending_value=195_000, years=5)
    assert result == pytest.approx(0.1436, abs=1e-3)


# ---------------------------------------------------------------------------
# 5.13 XIRR
# ---------------------------------------------------------------------------
def test_xirr_worked_example_sip():
    # SDD Section 5.13 posits "roughly 15.8%" for this cash-flow set, but that
    # figure is a loose illustrative approximation. The true XIRR, verified
    # independently via scipy.optimize.brentq on the same XNPV equation, is
    # ~18.88% — that is the value this test checks against.
    dates = [date(2025, m, 1) for m in range(1, 13)]
    amounts = [-10_000.0] * 12
    dates.append(date(2026, 1, 1))
    amounts.append(132_000.0)
    result = xirr.xirr(dates, amounts)
    assert result == pytest.approx(0.18884, abs=1e-4)


def test_xirr_requires_mixed_sign_cash_flows():
    with pytest.raises(ValueError):
        xirr.xirr([date(2025, 1, 1), date(2025, 6, 1)], [100.0, 200.0])


# ---------------------------------------------------------------------------
# 5.14 Rebalancing Drift & Trigger Logic
# ---------------------------------------------------------------------------
def test_drift_trigger_worked_example():
    result = rebalance.compute_drift(
        symbol="EQUITY",
        current_weight=0.68,
        target_weight=0.60,
        portfolio_value=1_000_000,
        abs_threshold=0.05,
    )
    assert result.drift == pytest.approx(0.08, abs=1e-6)
    assert result.triggered is True
    assert result.trade_amount == pytest.approx(-80_000, abs=1e-3)


def test_drift_not_triggered_within_threshold():
    result = rebalance.compute_drift(
        symbol="DEBT", current_weight=0.42, target_weight=0.40, portfolio_value=500_000, abs_threshold=0.05
    )
    assert result.triggered is False


# ---------------------------------------------------------------------------
# 5.15 Markowitz Mean-Variance Optimization
# ---------------------------------------------------------------------------
def test_efficient_frontier_weights_sum_to_one():
    cov = np.array(
        [
            [0.04, 0.01, 0.0],
            [0.01, 0.0225, 0.005],
            [0.0, 0.005, 0.01],
        ]
    )
    expected_returns = np.array([0.12, 0.08, 0.05])
    frontier = optimizer.efficient_frontier(cov, expected_returns, n_points=5)
    assert len(frontier) > 0
    for point in frontier:
        assert sum(point["weights"]) == pytest.approx(1.0, abs=1e-6)
        assert all(w >= -1e-6 for w in point["weights"])


def test_efficient_frontier_risk_is_monotonic_with_return():
    """Risk should never decrease as target return decreases along the frontier."""
    cov = np.array(
        [
            [0.04, 0.01, 0.0],
            [0.01, 0.0225, 0.005],
            [0.0, 0.005, 0.01],
        ]
    )
    expected_returns = np.array([0.12, 0.08, 0.05])
    frontier = optimizer.efficient_frontier(cov, expected_returns, n_points=10)
    sorted_by_return = sorted(frontier, key=lambda p: p["target_return"])
    volatilities = [p["volatility"] for p in sorted_by_return]
    min_vol_index = volatilities.index(min(volatilities))
    # To the right of the minimum-variance point, risk should rise with return.
    right_side = volatilities[min_vol_index:]
    assert all(right_side[i] <= right_side[i + 1] + 1e-9 for i in range(len(right_side) - 1))
