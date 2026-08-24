from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from .. import service
from ..database import get_db
from ..models.orm import Asset, CashFlow, Holding, Portfolio
from ..schemas import (
    BetaResponse,
    CashFlowIn,
    HoldingIn,
    HoldingOut,
    MetricsResponse,
    PortfolioCreate,
    PortfolioOut,
    RebalanceCheckResponse,
    RebalanceExecuteResponse,
    RiskResponse,
    XirrResponse,
)

router = APIRouter(prefix="/api/v1/portfolios", tags=["portfolios"])


@router.post("", response_model=PortfolioOut, status_code=201)
def create_portfolio(payload: PortfolioCreate, db: Session = Depends(get_db)):
    for holding in payload.holdings:
        if db.get(Asset, holding.asset_symbol) is None:
            raise HTTPException(status_code=422, detail=f"unknown asset symbol: {holding.asset_symbol}")

    portfolio = Portfolio(name=payload.name, base_currency=payload.base_currency)
    db.add(portfolio)
    db.flush()

    for holding in payload.holdings:
        db.add(
            Holding(
                portfolio_id=portfolio.id,
                asset_symbol=holding.asset_symbol,
                quantity=holding.quantity,
                target_weight=holding.target_weight,
                buy_price=holding.buy_price,
                buy_date=holding.buy_date,
            )
        )
    db.commit()
    db.refresh(portfolio)
    return portfolio


@router.get("/{portfolio_id}", response_model=PortfolioOut)
def get_portfolio(portfolio_id: str, db: Session = Depends(get_db)):
    return service.get_portfolio_or_404(db, portfolio_id)


@router.put("/{portfolio_id}/holdings", response_model=list[HoldingOut])
def replace_holdings(portfolio_id: str, holdings: list[HoldingIn], db: Session = Depends(get_db)):
    portfolio = service.get_portfolio_or_404(db, portfolio_id)
    total_weight = sum(h.target_weight for h in holdings)
    if holdings and abs(total_weight - 1.0) > 1e-6:
        raise HTTPException(status_code=422, detail=f"target_weight across holdings must sum to 1.0, got {total_weight}")
    for holding in holdings:
        if db.get(Asset, holding.asset_symbol) is None:
            raise HTTPException(status_code=422, detail=f"unknown asset symbol: {holding.asset_symbol}")

    for existing in list(portfolio.holdings):
        db.delete(existing)
    db.flush()

    for holding in holdings:
        db.add(
            Holding(
                portfolio_id=portfolio.id,
                asset_symbol=holding.asset_symbol,
                quantity=holding.quantity,
                target_weight=holding.target_weight,
                buy_price=holding.buy_price,
                buy_date=holding.buy_date,
            )
        )
    db.commit()
    db.refresh(portfolio)
    return portfolio.holdings


@router.post("/{portfolio_id}/cashflows", status_code=201)
def add_cash_flow(portfolio_id: str, payload: CashFlowIn, db: Session = Depends(get_db)):
    portfolio = service.get_portfolio_or_404(db, portfolio_id)
    cash_flow = CashFlow(portfolio_id=portfolio.id, date=payload.date, amount=payload.amount)
    db.add(cash_flow)
    db.commit()
    return {"status": "recorded"}


@router.get("/{portfolio_id}/metrics", response_model=MetricsResponse)
def get_metrics(portfolio_id: str, db: Session = Depends(get_db)):
    portfolio = service.get_portfolio_or_404(db, portfolio_id)
    return service.compute_metrics(db, portfolio)


@router.get("/{portfolio_id}/risk", response_model=RiskResponse)
def get_risk(portfolio_id: str, db: Session = Depends(get_db)):
    portfolio = service.get_portfolio_or_404(db, portfolio_id)
    return service.compute_risk(db, portfolio)


@router.get("/{portfolio_id}/beta", response_model=BetaResponse)
def get_beta(
    portfolio_id: str,
    benchmark_symbol: str = Query(default=service.DEFAULT_BENCHMARK_SYMBOL),
    db: Session = Depends(get_db),
):
    portfolio = service.get_portfolio_or_404(db, portfolio_id)
    return service.compute_beta(db, portfolio, benchmark_symbol)


@router.get("/{portfolio_id}/xirr", response_model=XirrResponse)
def get_xirr(portfolio_id: str, db: Session = Depends(get_db)):
    portfolio = service.get_portfolio_or_404(db, portfolio_id)
    return service.compute_xirr(db, portfolio)


@router.post("/{portfolio_id}/rebalance/check", response_model=RebalanceCheckResponse)
def rebalance_check(
    portfolio_id: str,
    abs_threshold: float = Query(default=0.05, ge=0, le=1),
    rel_threshold: float = Query(default=0.25, ge=0),
    db: Session = Depends(get_db),
):
    portfolio = service.get_portfolio_or_404(db, portfolio_id)
    return service.check_rebalance(db, portfolio, abs_threshold, rel_threshold)


@router.post("/{portfolio_id}/rebalance/execute", response_model=RebalanceExecuteResponse)
def rebalance_execute(
    portfolio_id: str,
    abs_threshold: float = Query(default=0.05, ge=0, le=1),
    rel_threshold: float = Query(default=0.25, ge=0),
    db: Session = Depends(get_db),
):
    portfolio = service.get_portfolio_or_404(db, portfolio_id)
    return service.execute_rebalance(db, portfolio, abs_threshold, rel_threshold)
