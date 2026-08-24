import axios from "axios";
import type {
  Asset,
  AssetClass,
  BetaResponse,
  EfficientFrontierResponse,
  HoldingIn,
  MetricsResponse,
  Portfolio,
  PricePoint,
  RebalanceCheckResponse,
  RebalanceExecuteResponse,
  RiskResponse,
  ScenarioSimulateResponse,
  XirrResponse,
} from "./types";

// In production this is injected at build time via VITE_API_BASE_URL (see
// frontend/.env.example); it must never fall back to a hardcoded localhost
// URL once bundled, so the fallback below is a *development-only* default.
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

export const apiClient = axios.create({ baseURL: API_BASE_URL });

export const api = {
  // Assets
  listAssets: () => apiClient.get<Asset[]>("/api/v1/assets").then((r) => r.data),
  createAsset: (payload: { symbol: string; name: string; asset_class: AssetClass }) =>
    apiClient.post<Asset>("/api/v1/assets", payload).then((r) => r.data),
  getPrices: (symbol: string) => apiClient.get<PricePoint[]>(`/api/v1/assets/${symbol}/prices`).then((r) => r.data),
  ingestPrices: (symbol: string, prices: PricePoint[]) =>
    apiClient.post(`/api/v1/assets/${symbol}/prices`, { prices }).then((r) => r.data),

  // Portfolios
  createPortfolio: (payload: { name: string; base_currency?: string; holdings: HoldingIn[] }) =>
    apiClient.post<Portfolio>("/api/v1/portfolios", payload).then((r) => r.data),
  getPortfolio: (id: string) => apiClient.get<Portfolio>(`/api/v1/portfolios/${id}`).then((r) => r.data),
  replaceHoldings: (id: string, holdings: HoldingIn[]) =>
    apiClient.put<HoldingIn[]>(`/api/v1/portfolios/${id}/holdings`, holdings).then((r) => r.data),
  addCashFlow: (id: string, payload: { date: string; amount: number }) =>
    apiClient.post(`/api/v1/portfolios/${id}/cashflows`, payload).then((r) => r.data),

  getMetrics: (id: string) => apiClient.get<MetricsResponse>(`/api/v1/portfolios/${id}/metrics`).then((r) => r.data),
  getRisk: (id: string) => apiClient.get<RiskResponse>(`/api/v1/portfolios/${id}/risk`).then((r) => r.data),
  getBeta: (id: string) => apiClient.get<BetaResponse>(`/api/v1/portfolios/${id}/beta`).then((r) => r.data),
  getXirr: (id: string) => apiClient.get<XirrResponse>(`/api/v1/portfolios/${id}/xirr`).then((r) => r.data),

  checkRebalance: (id: string) =>
    apiClient.post<RebalanceCheckResponse>(`/api/v1/portfolios/${id}/rebalance/check`).then((r) => r.data),
  executeRebalance: (id: string) =>
    apiClient.post<RebalanceExecuteResponse>(`/api/v1/portfolios/${id}/rebalance/execute`).then((r) => r.data),

  // Optimizer & scenarios
  efficientFrontier: (payload: { asset_symbols: string[]; lookback_days?: number; n_points?: number }) =>
    apiClient.post<EfficientFrontierResponse>("/api/v1/optimize/efficient-frontier", payload).then((r) => r.data),
  simulateScenario: (payload: {
    portfolio_id: string;
    weights: Record<string, number>;
    lookback_days?: number;
    benchmark_symbol?: string;
  }) => apiClient.post<ScenarioSimulateResponse>("/api/v1/scenarios/simulate", payload).then((r) => r.data),
};
