"""API request/response schemas (Pydantic v2) — Sections 3 & 6."""
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field, field_validator

AssetClass = Literal["equity", "debt", "gold", "reit", "cash", "index"]


class AssetCreate(BaseModel):
    symbol: str
    name: str
    asset_class: AssetClass


class AssetOut(BaseModel):
    symbol: str
    name: str
    asset_class: AssetClass

    model_config = {"from_attributes": True}


class PricePointIn(BaseModel):
    date: date
    close_price: Decimal = Field(gt=0)


class PriceIngestRequest(BaseModel):
    prices: list[PricePointIn]


class PricePointOut(BaseModel):
    date: date
    close_price: Decimal

    model_config = {"from_attributes": True}


class HoldingIn(BaseModel):
    asset_symbol: str
    quantity: Decimal = Field(gt=0)
    target_weight: float = Field(ge=0, le=1)
    buy_price: Decimal = Field(gt=0)
    buy_date: date


class HoldingOut(BaseModel):
    asset_symbol: str
    quantity: Decimal
    target_weight: float
    buy_price: Decimal
    buy_date: date

    model_config = {"from_attributes": True}


class PortfolioCreate(BaseModel):
    name: str
    base_currency: str = "INR"
    holdings: list[HoldingIn] = Field(default_factory=list)

    @field_validator("holdings")
    @classmethod
    def weights_sum_to_one(cls, holdings: list[HoldingIn]) -> list[HoldingIn]:
        if holdings:
            total = sum(h.target_weight for h in holdings)
            if abs(total - 1.0) > 1e-6:
                raise ValueError(f"target_weight across holdings must sum to 1.0, got {total}")
        return holdings


class PortfolioOut(BaseModel):
    id: str
    name: str
    base_currency: str
    created_at: datetime
    holdings: list[HoldingOut]

    model_config = {"from_attributes": True}


class CashFlowIn(BaseModel):
    date: date
    amount: Decimal  # positive = deposit, negative = withdrawal


class MetricsResponse(BaseModel):
    expected_return: float
    volatility: float
    sharpe_ratio: float
    sortino_ratio: float
    beta: float
    alpha: float
    treynor_ratio: float
    as_of: datetime


class RiskResponse(BaseModel):
    parametric_var_95: float
    historical_var_95: float
    parametric_var_99: float
    historical_var_99: float
    cvar_95: float
    max_drawdown: float
    as_of: datetime


class BetaResponse(BaseModel):
    benchmark_symbol: str
    per_asset_beta: dict[str, float]
    portfolio_beta: float
    as_of: datetime


class XirrResponse(BaseModel):
    xirr: float
    cash_flow_count: int
    as_of: datetime


class DriftOut(BaseModel):
    symbol: str
    current_weight: float
    target_weight: float
    drift: float
    triggered: bool
    trade_amount: float


class RebalanceCheckResponse(BaseModel):
    portfolio_value: float
    drifts: list[DriftOut]
    any_triggered: bool
    as_of: datetime


class RebalanceExecuteResponse(BaseModel):
    event_id: str
    drifts: list[DriftOut]
    suggested_trades: dict[str, float]
    triggered_at: datetime


class EfficientFrontierRequest(BaseModel):
    asset_symbols: list[str] = Field(min_length=2)
    lookback_days: int = Field(default=252, gt=1)
    n_points: int = Field(default=15, ge=2, le=100)
    benchmark_symbol: str | None = None


class FrontierPoint(BaseModel):
    target_return: float
    volatility: float
    weights: dict[str, float]


class EfficientFrontierResponse(BaseModel):
    frontier: list[FrontierPoint]
    current_portfolio: FrontierPoint | None = None


class ScenarioSimulateRequest(BaseModel):
    portfolio_id: str
    weights: dict[str, float] = Field(..., description="asset_symbol -> hypothetical weight")
    lookback_days: int = Field(default=252, gt=1)
    benchmark_symbol: str | None = None

    @field_validator("weights")
    @classmethod
    def weights_sum_to_one(cls, weights: dict[str, float]) -> dict[str, float]:
        total = sum(weights.values())
        if abs(total - 1.0) > 1e-6:
            raise ValueError(f"weights must sum to 1.0, got {total}")
        return weights


class ScenarioSimulateResponse(BaseModel):
    expected_return: float
    volatility: float
    sharpe_ratio: float
    beta: float | None = None
