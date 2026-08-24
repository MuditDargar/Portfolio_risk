"""
Service layer: pulls holdings/price history from the database, assembles the
arrays the Section 5 formula engine expects, and applies the Redis/in-memory
covariance-matrix cache described in Section 2.
"""
from __future__ import annotations

import hashlib
from datetime import datetime, timezone

import numpy as np
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from .cache import cache_get, cache_set
from .config import get_settings
from .formulas import capm, drawdown, optimizer, ratios, rebalance as rebalance_formulas, returns as returns_formulas
from .formulas import risk as risk_formulas
from .formulas import var as var_formulas
from .formulas import xirr as xirr_formulas
from .models.orm import CashFlow, Holding, Portfolio, PricePoint, RebalanceEvent

settings = get_settings()

DEFAULT_BENCHMARK_SYMBOL = "NIFTY50"
TRADING_PERIODS_PER_YEAR = 252


def get_portfolio_or_404(db: Session, portfolio_id: str) -> Portfolio:
    portfolio = db.get(Portfolio, portfolio_id)
    if portfolio is None:
        raise HTTPException(status_code=404, detail=f"portfolio {portfolio_id} not found")
    return portfolio


def get_price_series(db: Session, symbol: str, lookback_days: int) -> tuple[list, np.ndarray]:
    rows = (
        db.execute(
            select(PricePoint)
            .where(PricePoint.asset_symbol == symbol)
            .order_by(PricePoint.date.desc())
            .limit(lookback_days)
        )
        .scalars()
        .all()
    )
    rows = list(reversed(rows))
    if len(rows) < 2:
        raise HTTPException(
            status_code=422,
            detail=f"asset {symbol} needs at least 2 price points, has {len(rows)}",
        )
    dates = [r.date for r in rows]
    prices = np.array([float(r.close_price) for r in rows], dtype=np.float64)
    return dates, prices


def get_latest_price(db: Session, symbol: str) -> float:
    row = (
        db.execute(
            select(PricePoint).where(PricePoint.asset_symbol == symbol).order_by(PricePoint.date.desc()).limit(1)
        )
        .scalars()
        .first()
    )
    if row is None:
        raise HTTPException(status_code=422, detail=f"asset {symbol} has no price history")
    return float(row.close_price)


def _holdings_hash(holdings: list[Holding]) -> str:
    payload = "|".join(sorted(f"{h.asset_symbol}:{h.quantity}:{h.target_weight}" for h in holdings))
    return hashlib.sha256(payload.encode()).hexdigest()[:16]


def build_returns_matrix(
    db: Session, symbols: list[str], lookback_days: int
) -> tuple[np.ndarray, np.ndarray]:
    """Returns (returns_matrix[n_periods, n_assets], mean_period_return[n_assets])."""
    all_returns = []
    min_length = None
    for symbol in symbols:
        _, prices = get_price_series(db, symbol, lookback_days)
        asset_returns = returns_formulas.price_series_to_returns(prices)
        all_returns.append(asset_returns)
        min_length = len(asset_returns) if min_length is None else min(min_length, len(asset_returns))

    if min_length is None or min_length < 2:
        raise HTTPException(status_code=422, detail="insufficient overlapping price history across assets")

    # Align all series to the same (most recent) window length.
    aligned = np.column_stack([r[-min_length:] for r in all_returns])
    mean_returns = np.mean(aligned, axis=0)
    return aligned, mean_returns


def get_cached_covariance(
    db: Session, portfolio: Portfolio, symbols: list[str], lookback_days: int
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Returns (returns_matrix, cov_matrix, mean_period_returns), using the cache when possible."""
    cache_key = f"cov:{portfolio.id}:{_holdings_hash(portfolio.holdings)}:{lookback_days}"
    cached = cache_get(cache_key)
    returns_matrix, mean_returns = build_returns_matrix(db, symbols, lookback_days)
    if cached is not None and cached.get("symbols") == symbols:
        cov_matrix = np.array(cached["cov_matrix"])
    else:
        cov_matrix = risk_formulas.covariance_matrix(returns_matrix)
        cache_set(cache_key, {"symbols": symbols, "cov_matrix": cov_matrix.tolist()})
    return returns_matrix, cov_matrix, mean_returns


def current_weights_and_value(db: Session, portfolio: Portfolio) -> tuple[dict[str, float], float, dict[str, float]]:
    """Returns (current_weight_by_symbol, total_portfolio_value, latest_price_by_symbol)."""
    latest_prices: dict[str, float] = {}
    market_values: dict[str, float] = {}
    for holding in portfolio.holdings:
        latest_price = get_latest_price(db, holding.asset_symbol)
        latest_prices[holding.asset_symbol] = latest_price
        market_values[holding.asset_symbol] = latest_price * float(holding.quantity)

    total_value = sum(market_values.values())
    if total_value <= 0:
        raise HTTPException(status_code=422, detail="portfolio has zero market value")
    current_weights = {symbol: value / total_value for symbol, value in market_values.items()}
    return current_weights, total_value, latest_prices


def compute_metrics(db: Session, portfolio: Portfolio, lookback_days: int = TRADING_PERIODS_PER_YEAR) -> dict:
    if not portfolio.holdings:
        raise HTTPException(status_code=422, detail="portfolio has no holdings")

    symbols = [h.asset_symbol for h in portfolio.holdings]
    current_weights, _, _ = current_weights_and_value(db, portfolio)
    weights = np.array([current_weights[s] for s in symbols])

    returns_matrix, cov_matrix, mean_period_returns = get_cached_covariance(db, portfolio, symbols, lookback_days)
    annualized_asset_returns = np.array(
        [returns_formulas.annualize_return(r) for r in mean_period_returns]
    )

    expected_return = returns_formulas.portfolio_expected_return(weights, annualized_asset_returns)
    period_volatility = risk_formulas.portfolio_volatility(weights, cov_matrix)
    annual_volatility = returns_formulas.annualize_volatility(period_volatility)

    portfolio_period_returns = returns_matrix @ weights
    sharpe = ratios.sharpe_ratio(expected_return, settings.risk_free_rate, annual_volatility)
    sortino = ratios.sortino_ratio(expected_return, settings.risk_free_rate, portfolio_period_returns)

    benchmark_dates, benchmark_prices = get_price_series(db, DEFAULT_BENCHMARK_SYMBOL, lookback_days)
    benchmark_returns = returns_formulas.price_series_to_returns(benchmark_prices)
    n = min(len(portfolio_period_returns), len(benchmark_returns))
    portfolio_beta = capm.beta(portfolio_period_returns[-n:], benchmark_returns[-n:])
    market_return = returns_formulas.annualize_return(returns_formulas.mean_return(benchmark_returns))
    alpha = capm.jensens_alpha(expected_return, settings.risk_free_rate, portfolio_beta, market_return)
    treynor = ratios.treynor_ratio(expected_return, settings.risk_free_rate, portfolio_beta)

    return {
        "expected_return": expected_return,
        "volatility": annual_volatility,
        "sharpe_ratio": sharpe,
        "sortino_ratio": sortino,
        "beta": portfolio_beta,
        "alpha": alpha,
        "treynor_ratio": treynor,
        "as_of": datetime.now(timezone.utc),
    }


def compute_risk(db: Session, portfolio: Portfolio, lookback_days: int = TRADING_PERIODS_PER_YEAR) -> dict:
    if not portfolio.holdings:
        raise HTTPException(status_code=422, detail="portfolio has no holdings")

    symbols = [h.asset_symbol for h in portfolio.holdings]
    current_weights, total_value, _ = current_weights_and_value(db, portfolio)
    weights = np.array([current_weights[s] for s in symbols])

    returns_matrix, cov_matrix, _ = get_cached_covariance(db, portfolio, symbols, lookback_days)
    period_volatility = risk_formulas.portfolio_volatility(weights, cov_matrix)
    portfolio_period_returns = returns_matrix @ weights

    values = total_value * np.cumprod(1.0 + np.concatenate([[0.0], portfolio_period_returns]))

    return {
        "parametric_var_95": var_formulas.parametric_var(total_value, period_volatility, confidence=0.95),
        "historical_var_95": var_formulas.historical_var(portfolio_period_returns, total_value, confidence=0.95),
        "parametric_var_99": var_formulas.parametric_var(total_value, period_volatility, confidence=0.99),
        "historical_var_99": var_formulas.historical_var(portfolio_period_returns, total_value, confidence=0.99),
        "cvar_95": var_formulas.conditional_var(portfolio_period_returns, total_value, confidence=0.95),
        "max_drawdown": drawdown.max_drawdown(values),
        "as_of": datetime.now(timezone.utc),
    }


def compute_beta(
    db: Session,
    portfolio: Portfolio,
    benchmark_symbol: str = DEFAULT_BENCHMARK_SYMBOL,
    lookback_days: int = TRADING_PERIODS_PER_YEAR,
) -> dict:
    if not portfolio.holdings:
        raise HTTPException(status_code=422, detail="portfolio has no holdings")

    _, benchmark_prices = get_price_series(db, benchmark_symbol, lookback_days)
    benchmark_returns = returns_formulas.price_series_to_returns(benchmark_prices)

    per_asset_beta = {}
    for holding in portfolio.holdings:
        _, prices = get_price_series(db, holding.asset_symbol, lookback_days)
        asset_returns = returns_formulas.price_series_to_returns(prices)
        n = min(len(asset_returns), len(benchmark_returns))
        per_asset_beta[holding.asset_symbol] = capm.beta(asset_returns[-n:], benchmark_returns[-n:])

    current_weights, _, _ = current_weights_and_value(db, portfolio)
    portfolio_beta = sum(current_weights[s] * b for s, b in per_asset_beta.items())

    return {
        "benchmark_symbol": benchmark_symbol,
        "per_asset_beta": per_asset_beta,
        "portfolio_beta": portfolio_beta,
        "as_of": datetime.now(timezone.utc),
    }


def compute_xirr(db: Session, portfolio: Portfolio) -> dict:
    cash_flows = (
        db.execute(select(CashFlow).where(CashFlow.portfolio_id == portfolio.id).order_by(CashFlow.date))
        .scalars()
        .all()
    )
    if len(cash_flows) < 1:
        raise HTTPException(status_code=422, detail="portfolio has no recorded cash flows")

    _, current_value, _ = current_weights_and_value(db, portfolio)
    dates = [cf.date for cf in cash_flows] + [datetime.now(timezone.utc).date()]
    amounts = [-float(cf.amount) for cf in cash_flows] + [current_value]

    result = xirr_formulas.xirr(dates, amounts)
    return {"xirr": result, "cash_flow_count": len(cash_flows), "as_of": datetime.now(timezone.utc)}


def check_rebalance(
    db: Session, portfolio: Portfolio, abs_threshold: float = 0.05, rel_threshold: float = 0.25
) -> dict:
    if not portfolio.holdings:
        raise HTTPException(status_code=422, detail="portfolio has no holdings")

    current_weights, total_value, _ = current_weights_and_value(db, portfolio)
    holdings_map = {
        h.asset_symbol: (current_weights[h.asset_symbol], float(h.target_weight)) for h in portfolio.holdings
    }

    drift_results = rebalance_formulas.check_portfolio_drift(
        holdings_map, total_value, abs_threshold, rel_threshold
    )
    return {
        "portfolio_value": total_value,
        "drifts": [d.__dict__ for d in drift_results],
        "any_triggered": any(d.triggered for d in drift_results),
        "as_of": datetime.now(timezone.utc),
    }


def execute_rebalance(
    db: Session, portfolio: Portfolio, abs_threshold: float = 0.05, rel_threshold: float = 0.25
) -> dict:
    check = check_rebalance(db, portfolio, abs_threshold, rel_threshold)
    drifts = check["drifts"]
    suggested_trades = {d["symbol"]: d["trade_amount"] for d in drifts if d["triggered"]}

    event = RebalanceEvent(
        portfolio_id=portfolio.id,
        drifts={d["symbol"]: d["drift"] for d in drifts},
        suggested_trades={k: str(v) for k, v in suggested_trades.items()},
    )
    db.add(event)
    db.commit()
    db.refresh(event)

    return {
        "event_id": event.id,
        "drifts": drifts,
        "suggested_trades": suggested_trades,
        "triggered_at": event.triggered_at,
    }


def compute_efficient_frontier(
    db: Session,
    symbols: list[str],
    lookback_days: int = TRADING_PERIODS_PER_YEAR,
    n_points: int = 15,
) -> list[dict]:
    returns_matrix, mean_period_returns = build_returns_matrix(db, symbols, lookback_days)
    cov_matrix = risk_formulas.covariance_matrix(returns_matrix)
    annualized_returns = np.array([returns_formulas.annualize_return(r) for r in mean_period_returns])
    frontier = optimizer.efficient_frontier(cov_matrix, annualized_returns, n_points)
    return [
        {
            "target_return": p["target_return"],
            "volatility": p["volatility"],
            "weights": dict(zip(symbols, p["weights"])),
        }
        for p in frontier
    ]


def simulate_scenario(
    db: Session,
    portfolio: Portfolio,
    weights_by_symbol: dict[str, float],
    lookback_days: int = TRADING_PERIODS_PER_YEAR,
    benchmark_symbol: str | None = None,
) -> dict:
    symbols = list(weights_by_symbol.keys())
    weights = np.array([weights_by_symbol[s] for s in symbols])

    returns_matrix, mean_period_returns = build_returns_matrix(db, symbols, lookback_days)
    cov_matrix = risk_formulas.covariance_matrix(returns_matrix)
    annualized_returns = np.array([returns_formulas.annualize_return(r) for r in mean_period_returns])

    expected_return = returns_formulas.portfolio_expected_return(weights, annualized_returns)
    period_volatility = risk_formulas.portfolio_volatility(weights, cov_matrix)
    annual_volatility = returns_formulas.annualize_volatility(period_volatility)
    sharpe = ratios.sharpe_ratio(expected_return, settings.risk_free_rate, annual_volatility)

    beta_value = None
    if benchmark_symbol:
        _, benchmark_prices = get_price_series(db, benchmark_symbol, lookback_days)
        benchmark_returns = returns_formulas.price_series_to_returns(benchmark_prices)
        portfolio_period_returns = returns_matrix @ weights
        n = min(len(portfolio_period_returns), len(benchmark_returns))
        beta_value = capm.beta(portfolio_period_returns[-n:], benchmark_returns[-n:])

    return {
        "expected_return": expected_return,
        "volatility": annual_volatility,
        "sharpe_ratio": sharpe,
        "beta": beta_value,
    }
