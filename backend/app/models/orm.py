"""
SQLAlchemy ORM models — persistence layer for the Section 3 data model.

Two deliberate extensions beyond the SDD's literal Pydantic snippets, both
required to satisfy the Functional Requirements in Section 4:
  - `Portfolio` itself is modeled explicitly (Section 3 only shows entities
    that reference a `portfolio_id`, implying a parent Portfolio exists).
  - `Holding` gains `buy_price` and `buy_date` columns, since FR-1 requires
    "quantity, buy price, and buy date" but Section 3's snippet only lists
    `quantity` and `target_weight`.
  - `Asset.asset_class` gains an `index` value so a benchmark (e.g. NIFTY 50,
    used for CAPM beta in FR-5) can be stored as a regular Asset.
"""
import uuid
from datetime import date, datetime, timezone

from sqlalchemy import Date, DateTime, ForeignKey, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from ..database import Base


def _uuid() -> str:
    return str(uuid.uuid4())


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Portfolio(Base):
    __tablename__ = "portfolios"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    name: Mapped[str] = mapped_column(String(120))
    base_currency: Mapped[str] = mapped_column(String(3), default="INR")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)

    holdings: Mapped[list["Holding"]] = relationship(back_populates="portfolio", cascade="all, delete-orphan")
    cash_flows: Mapped[list["CashFlow"]] = relationship(back_populates="portfolio", cascade="all, delete-orphan")
    rebalance_events: Mapped[list["RebalanceEvent"]] = relationship(
        back_populates="portfolio", cascade="all, delete-orphan"
    )


class Asset(Base):
    __tablename__ = "assets"

    symbol: Mapped[str] = mapped_column(String(20), primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    asset_class: Mapped[str] = mapped_column(String(20))  # equity|debt|gold|reit|cash|index

    prices: Mapped[list["PricePoint"]] = relationship(back_populates="asset", cascade="all, delete-orphan")


class Holding(Base):
    __tablename__ = "holdings"
    __table_args__ = (UniqueConstraint("portfolio_id", "asset_symbol", name="uq_holding_portfolio_asset"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    portfolio_id: Mapped[str] = mapped_column(String(36), ForeignKey("portfolios.id"))
    asset_symbol: Mapped[str] = mapped_column(String(20), ForeignKey("assets.symbol"))
    quantity: Mapped[float] = mapped_column(Numeric(18, 6))
    target_weight: Mapped[float] = mapped_column(Numeric(6, 5))
    buy_price: Mapped[float] = mapped_column(Numeric(18, 6))
    buy_date: Mapped[date] = mapped_column(Date)

    portfolio: Mapped[Portfolio] = relationship(back_populates="holdings")
    asset: Mapped[Asset] = relationship()


class PricePoint(Base):
    __tablename__ = "price_points"
    __table_args__ = (UniqueConstraint("asset_symbol", "date", name="uq_price_asset_date"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    asset_symbol: Mapped[str] = mapped_column(String(20), ForeignKey("assets.symbol"))
    date: Mapped[date] = mapped_column(Date)
    close_price: Mapped[float] = mapped_column(Numeric(18, 6))

    asset: Mapped[Asset] = relationship(back_populates="prices")


class CashFlow(Base):
    __tablename__ = "cash_flows"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    portfolio_id: Mapped[str] = mapped_column(String(36), ForeignKey("portfolios.id"))
    date: Mapped[date] = mapped_column(Date)
    amount: Mapped[float] = mapped_column(Numeric(18, 6))  # + deposit / - withdrawal

    portfolio: Mapped[Portfolio] = relationship(back_populates="cash_flows")


class RebalanceEvent(Base):
    __tablename__ = "rebalance_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    portfolio_id: Mapped[str] = mapped_column(String(36), ForeignKey("portfolios.id"))
    triggered_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
    drifts: Mapped[dict] = mapped_column(JSON)  # symbol -> drift at trigger time
    suggested_trades: Mapped[dict] = mapped_column(JSON)  # symbol -> Decimal-as-string

    portfolio: Mapped[Portfolio] = relationship(back_populates="rebalance_events")
