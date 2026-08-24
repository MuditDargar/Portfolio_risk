"""Asset & price-history endpoints — supports FR-1 and FR-2 (not literally
listed in Section 6's table, but required scaffolding for it: without a way
to register assets and ingest their price history, none of the Section 6
metric endpoints have data to compute against)."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..models.orm import Asset, PricePoint
from ..schemas import AssetCreate, AssetOut, PriceIngestRequest, PricePointOut

router = APIRouter(prefix="/api/v1/assets", tags=["assets"])


@router.post("", response_model=AssetOut, status_code=201)
def create_asset(payload: AssetCreate, db: Session = Depends(get_db)):
    existing = db.get(Asset, payload.symbol)
    if existing:
        raise HTTPException(status_code=409, detail=f"asset {payload.symbol} already exists")
    asset = Asset(symbol=payload.symbol, name=payload.name, asset_class=payload.asset_class)
    db.add(asset)
    db.commit()
    db.refresh(asset)
    return asset


@router.get("", response_model=list[AssetOut])
def list_assets(db: Session = Depends(get_db)):
    return db.execute(select(Asset)).scalars().all()


@router.get("/{symbol}/prices", response_model=list[PricePointOut])
def get_prices(symbol: str, db: Session = Depends(get_db)):
    if db.get(Asset, symbol) is None:
        raise HTTPException(status_code=404, detail=f"asset {symbol} not found")
    return (
        db.execute(select(PricePoint).where(PricePoint.asset_symbol == symbol).order_by(PricePoint.date))
        .scalars()
        .all()
    )


@router.post("/{symbol}/prices", status_code=201)
def ingest_prices(symbol: str, payload: PriceIngestRequest, db: Session = Depends(get_db)):
    asset = db.get(Asset, symbol)
    if asset is None:
        raise HTTPException(status_code=404, detail=f"asset {symbol} not found")

    existing_dates = {
        row.date
        for row in db.execute(select(PricePoint).where(PricePoint.asset_symbol == symbol)).scalars().all()
    }
    inserted = 0
    for point in payload.prices:
        if point.date in existing_dates:
            continue
        db.add(PricePoint(asset_symbol=symbol, date=point.date, close_price=point.close_price))
        inserted += 1
    db.commit()
    return {"inserted": inserted, "skipped_duplicates": len(payload.prices) - inserted}
