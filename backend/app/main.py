from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from . import database
from .api import assets, health, optimize, portfolios, scenarios
from .config import get_settings
from .models import orm  # noqa: F401 — ensures models are registered on Base.metadata

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    database.Base.metadata.create_all(bind=database.engine)
    yield


app = FastAPI(title="Portfolio Risk & Rebalancing Dashboard API", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(assets.router)
app.include_router(portfolios.router)
app.include_router(optimize.router)
app.include_router(scenarios.router)
