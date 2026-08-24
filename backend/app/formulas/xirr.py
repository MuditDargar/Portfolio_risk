"""Section 5.13 — XIRR (Irregular Cash Flows), solved via Newton-Raphson with a bisection fallback."""
from __future__ import annotations

from datetime import date
from typing import Sequence


def _xnpv(rate: float, cash_flows: Sequence[float], days: Sequence[float]) -> float:
    return sum(cf / (1.0 + rate) ** (d / 365.0) for cf, d in zip(cash_flows, days))


def _xnpv_derivative(rate: float, cash_flows: Sequence[float], days: Sequence[float]) -> float:
    return sum(
        -(d / 365.0) * cf / (1.0 + rate) ** (d / 365.0 + 1.0) for cf, d in zip(cash_flows, days)
    )


def xirr(
    dates: Sequence[date],
    amounts: Sequence[float],
    guess: float = 0.1,
    max_iterations: int = 100,
    tolerance: float = 1e-7,
) -> float:
    """
    Solve for r such that sum(CF_i / (1+r)^((d_i - d0)/365)) = 0 — Section 5.13.

    Uses Newton-Raphson, falling back to bisection if Newton-Raphson fails to
    converge (e.g. a poor initial guess sends it into a region with a
    near-zero derivative).
    """
    if len(dates) != len(amounts):
        raise ValueError("dates and amounts must have the same length")
    if len(dates) < 2:
        raise ValueError("XIRR requires at least two cash flows")

    d0 = min(dates)
    days = [(d - d0).days for d in dates]
    cash_flows = list(amounts)

    if not any(cf < 0 for cf in cash_flows) or not any(cf > 0 for cf in cash_flows):
        raise ValueError("XIRR requires at least one negative and one positive cash flow")

    rate = guess
    for _ in range(max_iterations):
        f = _xnpv(rate, cash_flows, days)
        if abs(f) < tolerance:
            return float(rate)
        fprime = _xnpv_derivative(rate, cash_flows, days)
        if fprime == 0:
            break
        next_rate = rate - f / fprime
        if next_rate <= -1.0:
            next_rate = (rate - 1.0) / 2.0
        rate = next_rate
    else:
        pass

    if abs(_xnpv(rate, cash_flows, days)) < tolerance:
        return float(rate)

    return _xirr_bisection(cash_flows, days, tolerance)


def _xirr_bisection(cash_flows: Sequence[float], days: Sequence[float], tolerance: float) -> float:
    low, high = -0.9999, 10.0
    f_low = _xnpv(low, cash_flows, days)
    f_high = _xnpv(high, cash_flows, days)
    if f_low * f_high > 0:
        raise ValueError("XIRR failed to converge: no sign change found in search range")
    for _ in range(200):
        mid = (low + high) / 2.0
        f_mid = _xnpv(mid, cash_flows, days)
        if abs(f_mid) < tolerance:
            return float(mid)
        if f_low * f_mid < 0:
            high = mid
            f_high = f_mid
        else:
            low = mid
            f_low = f_mid
    return float((low + high) / 2.0)
