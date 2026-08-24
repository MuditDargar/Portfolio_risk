import { useQueries } from "@tanstack/react-query";
import { useMemo } from "react";
import {
  Area,
  AreaChart,
  CartesianGrid,
  ReferenceArea,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { api } from "../api/client";
import type { Holding } from "../api/types";

// Reconstructs a portfolio value time series from each held asset's price
// history at *current* quantities (Section 3's Holding model is a single
// lot per asset, not a lot-by-lot transaction ledger, so this is the
// faithful history available without adding tax-lot tracking — explicitly
// out of scope per SDD Section 1.3).
export function DrawdownChart({ holdings }: { holdings: Holding[] }) {
  const priceQueries = useQueries({
    queries: holdings.map((h) => ({
      queryKey: ["prices", h.asset_symbol],
      queryFn: () => api.getPrices(h.asset_symbol),
    })),
  });

  const loading = priceQueries.some((q) => q.isLoading);
  const allLoaded = priceQueries.every((q) => q.data);

  const { series, peakDate, troughDate, maxDrawdownPct } = useMemo(() => {
    if (!allLoaded) return { series: [], peakDate: null as string | null, troughDate: null as string | null, maxDrawdownPct: 0 };

    const dateSets = priceQueries.map((q) => new Set((q.data ?? []).map((p) => p.date)));
    const commonDates = [...dateSets[0]].filter((d) => dateSets.every((s) => s.has(d))).sort();

    const priceByDateBySymbol = holdings.map((_, i) => {
      const map = new Map<string, number>();
      (priceQueries[i].data ?? []).forEach((p) => map.set(p.date, p.close_price));
      return map;
    });

    let runningPeak = -Infinity;
    let worstDrawdown = 0;
    let peak: string | null = null;
    let trough: string | null = null;
    let peakAtTrough: string | null = null;

    const points = commonDates.map((date) => {
      const value = holdings.reduce((sum, h, i) => sum + h.quantity * (priceByDateBySymbol[i].get(date) ?? 0), 0);
      if (value > runningPeak) {
        runningPeak = value;
        peak = date;
      }
      const drawdown = runningPeak > 0 ? (value - runningPeak) / runningPeak : 0;
      if (drawdown < worstDrawdown) {
        worstDrawdown = drawdown;
        trough = date;
        peakAtTrough = peak;
      }
      return { date, value: Math.round(value) };
    });

    return { series: points, peakDate: peakAtTrough, troughDate: trough, maxDrawdownPct: worstDrawdown };
  }, [allLoaded, holdings, priceQueries]);

  if (loading) return <section className="panel">Loading price history…</section>;
  if (series.length === 0) return <section className="panel">Not enough overlapping price history to chart.</section>;

  return (
    <section className="panel">
      <h3>Portfolio Value &amp; Drawdown</h3>
      <p className="stat-hint">
        Max drawdown over this window: <strong>{(maxDrawdownPct * 100).toFixed(2)}%</strong>
        {peakDate && troughDate && ` (peak ${peakDate} → trough ${troughDate})`}
      </p>
      <ResponsiveContainer width="100%" height={260}>
        <AreaChart data={series}>
          <defs>
            <linearGradient id="valueGradient" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#6366f1" stopOpacity={0.4} />
              <stop offset="95%" stopColor="#6366f1" stopOpacity={0} />
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
          <XAxis dataKey="date" tick={{ fontSize: 11 }} minTickGap={40} />
          <YAxis tick={{ fontSize: 11 }} width={70} tickFormatter={(v) => `₹${(v / 1000).toFixed(0)}k`} />
          <Tooltip formatter={(v) => `₹${Number(v).toLocaleString("en-IN")}`} />
          {peakDate && troughDate && (
            <ReferenceArea x1={peakDate} x2={troughDate} fill="#ef4444" fillOpacity={0.12} />
          )}
          <Area type="monotone" dataKey="value" stroke="#6366f1" fill="url(#valueGradient)" strokeWidth={2} />
        </AreaChart>
      </ResponsiveContainer>
    </section>
  );
}
