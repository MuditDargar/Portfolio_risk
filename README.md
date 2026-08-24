# Portfolio Risk & Rebalancing Dashboard

A formula-driven full-stack finance engine: portfolio construction, risk metrics
(Sharpe, Sortino, Treynor, Alpha, Beta, VaR, CVaR, Max Drawdown, XIRR),
rebalancing drift detection, and Markowitz mean-variance optimization
(efficient frontier). Every number is produced by a closed-form formula or a
deterministic numerical method (Newton-Raphson, SLSQP quadratic programming)
— no ML or AI in the computation path. Full spec: `Portfolio_Risk_Dashboard_SDD.docx`.

## Stack

| Layer | Choice |
|---|---|
| Backend | FastAPI + Pydantic v2, Python 3.12 |
| Formula engine | NumPy + SciPy (pure, unit-tested functions in `backend/app/formulas/`) |
| Database | PostgreSQL in production, SQLite for local dev (via `DATABASE_URL`) |
| Cache | Redis if `REDIS_URL` is set, else an in-process fallback |
| Frontend | React 19 + TypeScript (Vite), TanStack Query, Recharts, axios |

## Project layout

```
backend/
  app/
    formulas/     # Section 5 — pure functions, one module per metric family
    api/           # FastAPI routers
    models/orm.py  # SQLAlchemy models
    service.py     # wires DB + formulas + cache together
    schemas.py     # request/response Pydantic models
  tests/           # formula unit tests + full API integration test
frontend/
  src/
    api/           # typed client + demo-data seeder
    components/    # dashboard components (Section 7 component tree)
```

## Local development

**Backend** (Python 3.12+; a venv is already set up under `backend/venv`):

```bash
cd backend
python3.12 -m venv venv && ./venv/bin/pip install -r requirements-dev.txt
cp .env.example .env          # defaults to local SQLite, no other setup needed
./venv/bin/uvicorn app.main:app --reload --port 8000
```

API docs at `http://localhost:8000/docs`. Run tests: `./venv/bin/python -m pytest tests/ -v` (30 tests: 24 formula unit tests cross-checked against the SDD's worked examples, 6 end-to-end API integration tests).

**Frontend**:

```bash
cd frontend
npm install
cp .env.example .env.local    # VITE_API_BASE_URL=http://localhost:8000
npm run dev
```

Open `http://localhost:5173` and click **Create Demo Portfolio** — there's no
external market-data feed (out of scope per the SDD), so the app seeds a
small synthetic asset universe with deterministic price history to give you
something real to explore immediately.

**Full local stack with Postgres + Redis** (matches the SDD's Section 2 architecture exactly):

```bash
docker compose up --build
```

## Deployment (free tier)

- **Frontend → Vercel**: import the repo, set root directory to `frontend`, framework preset "Vite". Set `VITE_API_BASE_URL` to the deployed backend URL.
- **Backend → Render**: `render.yaml` at the repo root configures the free web service. Set `DATABASE_URL` to a free-tier Postgres connection string (Render's own free Postgres expires after 30 days — use [Neon](https://neon.tech) or [Supabase](https://supabase.com) instead, both have no-expiry free tiers). `REDIS_URL` is optional.
- **Database → Neon or Supabase** (Postgres, free tier).

No production secrets are committed. See `backend/.env.example` and `frontend/.env.example` for the full list of required environment variables.

## Notes on deliberate gaps between the SDD and the implementation

- The SDD's Section 3 Pydantic snippets don't model `Portfolio` itself (only entities that reference a `portfolio_id`) and omit `buy_price`/`buy_date` from `Holding` even though FR-1 requires them — both are added in `backend/app/models/orm.py`.
- `Asset.asset_class` gains an `index` value so a benchmark (e.g. NIFTY 50) can be stored and priced like any other asset, needed for CAPM beta (FR-5).
- Section 6 doesn't list asset/price-ingestion endpoints even though FR-2 requires them — `POST/GET /api/v1/assets` and `POST/GET /api/v1/assets/{symbol}/prices` were added as necessary scaffolding.
- The XIRR worked example in Section 5.13 ("~15.8%") is a loose approximation; the implementation is verified independently against `scipy.optimize.brentq` on the same cash flows (~18.88%) — see the test docstring in `backend/tests/test_formulas.py`.
