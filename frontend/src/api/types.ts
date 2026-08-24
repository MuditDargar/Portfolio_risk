// Hand-written types mirroring the backend Pydantic schemas (app/schemas.py).
// The SDD (Section 7.2) calls for a client generated from FastAPI's OpenAPI
// schema; these are written by hand instead to avoid pulling in an
// openapi-generator toolchain for a single-service API surface this small.
// Field names and shapes are kept in exact lockstep with app/schemas.py.

export type AssetClass = "equity" | "debt" | "gold" | "reit" | "cash" | "index";

export interface Asset {
  symbol: string;
  name: string;
  asset_class: AssetClass;
}

export interface PricePoint {
  date: string;
  close_price: number;
}

export interface HoldingIn {
  asset_symbol: string;
  quantity: number;
  target_weight: number;
  buy_price: number;
  buy_date: string;
}

export interface Holding extends HoldingIn {}

export interface Portfolio {
  id: string;
  name: string;
  base_currency: string;
  created_at: string;
  holdings: Holding[];
}

export interface MetricsResponse {
  expected_return: number;
  volatility: number;
  sharpe_ratio: number;
  sortino_ratio: number;
  beta: number;
  alpha: number;
  treynor_ratio: number;
  as_of: string;
}

export interface RiskResponse {
  parametric_var_95: number;
  historical_var_95: number;
  parametric_var_99: number;
  historical_var_99: number;
  cvar_95: number;
  max_drawdown: number;
  as_of: string;
}

export interface BetaResponse {
  benchmark_symbol: string;
  per_asset_beta: Record<string, number>;
  portfolio_beta: number;
  as_of: string;
}

export interface XirrResponse {
  xirr: number;
  cash_flow_count: number;
  as_of: string;
}

export interface Drift {
  symbol: string;
  current_weight: number;
  target_weight: number;
  drift: number;
  triggered: boolean;
  trade_amount: number;
}

export interface RebalanceCheckResponse {
  portfolio_value: number;
  drifts: Drift[];
  any_triggered: boolean;
  as_of: string;
}

export interface RebalanceExecuteResponse {
  event_id: string;
  drifts: Drift[];
  suggested_trades: Record<string, number>;
  triggered_at: string;
}

export interface FrontierPoint {
  target_return: number;
  volatility: number;
  weights: Record<string, number>;
}

export interface EfficientFrontierResponse {
  frontier: FrontierPoint[];
  current_portfolio: FrontierPoint | null;
}

export interface ScenarioSimulateResponse {
  expected_return: number;
  volatility: number;
  sharpe_ratio: number;
  beta: number | null;
}
