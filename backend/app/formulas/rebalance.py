"""Section 5.14 — Rebalancing Drift & Trigger Logic."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class DriftResult:
    symbol: str
    current_weight: float
    target_weight: float
    drift: float
    triggered: bool
    trade_amount: float


def compute_drift(
    symbol: str,
    current_weight: float,
    target_weight: float,
    portfolio_value: float,
    abs_threshold: float = 0.05,
    rel_threshold: float = 0.25,
) -> DriftResult:
    """
    drift_i = |currentWeight_i - targetWeight_i|
    trigger_i = drift_i > absThreshold OR |currentWeight_i/targetWeight_i - 1| > relThreshold
    tradeAmount_i = (targetWeight_i - currentWeight_i) * PortfolioValue
    — Section 5.14.
    """
    drift = abs(current_weight - target_weight)
    rel_drift = abs(current_weight / target_weight - 1.0) if target_weight != 0 else float("inf")
    triggered = drift > abs_threshold or rel_drift > rel_threshold
    trade_amount = (target_weight - current_weight) * portfolio_value
    return DriftResult(
        symbol=symbol,
        current_weight=current_weight,
        target_weight=target_weight,
        drift=drift,
        triggered=triggered,
        trade_amount=trade_amount,
    )


def check_portfolio_drift(
    holdings: dict[str, tuple[float, float]],
    portfolio_value: float,
    abs_threshold: float = 0.05,
    rel_threshold: float = 0.25,
) -> list[DriftResult]:
    """holdings: symbol -> (current_weight, target_weight)."""
    return [
        compute_drift(symbol, current_w, target_w, portfolio_value, abs_threshold, rel_threshold)
        for symbol, (current_w, target_w) in holdings.items()
    ]
