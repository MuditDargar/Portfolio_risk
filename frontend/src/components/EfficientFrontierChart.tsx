import { useQuery } from "@tanstack/react-query";
import {
  CartesianGrid,
  Legend,
  ResponsiveContainer,
  Scatter,
  ScatterChart,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { api } from "../api/client";
import type { Holding, MetricsResponse } from "../api/types";

export function EfficientFrontierChart({ holdings, metrics }: { holdings: Holding[]; metrics: MetricsResponse }) {
  const symbols = holdings.map((h) => h.asset_symbol);

  const { data, isLoading, error } = useQuery({
    queryKey: ["efficient-frontier", symbols],
    queryFn: () => api.efficientFrontier({ asset_symbols: symbols, n_points: 15 }),
    enabled: symbols.length >= 2,
  });

  if (symbols.length < 2) {
    return <section className="panel">Add at least 2 holdings to compute an efficient frontier.</section>;
  }
  if (isLoading) return <section className="panel">Computing efficient frontier…</section>;
  if (error || !data) return <section className="panel error-text">Failed to compute efficient frontier.</section>;

  const frontierPoints = data.frontier.map((p) => ({
    volatility: +(p.volatility * 100).toFixed(2),
    return: +(p.target_return * 100).toFixed(2),
  }));
  const currentPoint = [{ volatility: +(metrics.volatility * 100).toFixed(2), return: +(metrics.expected_return * 100).toFixed(2) }];

  return (
    <section className="panel">
      <h3>Efficient Frontier</h3>
      <p className="stat-hint">Markowitz mean-variance optimization — lowest risk achievable at each return level.</p>
      <ResponsiveContainer width="100%" height={300}>
        <ScatterChart margin={{ top: 10, right: 20, bottom: 10, left: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
          <XAxis
            type="number"
            dataKey="volatility"
            name="Volatility"
            unit="%"
            tick={{ fontSize: 11 }}
            label={{ value: "Volatility (%)", position: "insideBottom", offset: -5, fontSize: 12 }}
          />
          <YAxis
            type="number"
            dataKey="return"
            name="Expected Return"
            unit="%"
            tick={{ fontSize: 11 }}
            label={{ value: "Expected Return (%)", angle: -90, position: "insideLeft", fontSize: 12 }}
          />
          <Tooltip cursor={{ strokeDasharray: "3 3" }} formatter={(v) => `${v}%`} />
          <Legend />
          <Scatter name="Efficient Frontier" data={frontierPoints} fill="#6366f1" line shape="circle" />
          <Scatter name="Current Portfolio" data={currentPoint} fill="#ef4444" shape="star" />
        </ScatterChart>
      </ResponsiveContainer>
    </section>
  );
}
