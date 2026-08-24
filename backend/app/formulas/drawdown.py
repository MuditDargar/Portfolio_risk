"""Section 5.11 — Maximum Drawdown, Section 5.12 — CAGR."""
from __future__ import annotations

import numpy as np


def max_drawdown(values: np.ndarray) -> float:
    """MDD = min_t [ (Value(t) - PeakValue(0..t)) / PeakValue(0..t) ] — Section 5.11."""
    values = np.asarray(values, dtype=np.float64)
    if values.size == 0:
        return 0.0
    running_peak = np.maximum.accumulate(values)
    drawdowns = np.where(running_peak > 0, (values - running_peak) / running_peak, 0.0)
    return float(np.min(drawdowns))


def cagr(beginning_value: float, ending_value: float, years: float) -> float:
    """CAGR = (EndingValue / BeginningValue)^(1/n) - 1 — Section 5.12."""
    if beginning_value <= 0 or years <= 0:
        return 0.0
    return float((ending_value / beginning_value) ** (1.0 / years) - 1.0)
