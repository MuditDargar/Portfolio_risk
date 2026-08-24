from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from .. import service
from ..database import get_db
from ..schemas import EfficientFrontierRequest, EfficientFrontierResponse

router = APIRouter(prefix="/api/v1/optimize", tags=["optimize"])


@router.post("/efficient-frontier", response_model=EfficientFrontierResponse)
def efficient_frontier(payload: EfficientFrontierRequest, db: Session = Depends(get_db)):
    frontier = service.compute_efficient_frontier(
        db, payload.asset_symbols, payload.lookback_days, payload.n_points
    )
    return {"frontier": frontier, "current_portfolio": None}
