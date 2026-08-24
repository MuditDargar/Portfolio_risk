from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from .. import service
from ..database import get_db
from ..schemas import ScenarioSimulateRequest, ScenarioSimulateResponse

router = APIRouter(prefix="/api/v1/scenarios", tags=["scenarios"])


@router.post("/simulate", response_model=ScenarioSimulateResponse)
def simulate(payload: ScenarioSimulateRequest, db: Session = Depends(get_db)):
    portfolio = service.get_portfolio_or_404(db, payload.portfolio_id)
    return service.simulate_scenario(
        db, portfolio, payload.weights, payload.lookback_days, payload.benchmark_symbol
    )
