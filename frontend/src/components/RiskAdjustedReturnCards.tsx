import type { MetricsResponse } from "../api/types";

function pct(value: number): string {
  return `${(value * 100).toFixed(2)}%`;
}

export function RiskAdjustedReturnCards({ metrics }: { metrics: MetricsResponse }) {
  const cards = [
    { label: "Sharpe Ratio", value: metrics.sharpe_ratio.toFixed(2), hint: "Risk-adjusted return vs. total volatility" },
    { label: "Sortino Ratio", value: metrics.sortino_ratio.toFixed(2), hint: "Risk-adjusted return vs. downside volatility only" },
    { label: "Treynor Ratio", value: metrics.treynor_ratio.toFixed(3), hint: "Excess return per unit of beta" },
    { label: "Jensen's Alpha", value: pct(metrics.alpha), hint: "Return above CAPM prediction" },
  ];

  return (
    <div className="card-grid">
      {cards.map((c) => (
        <div className="stat-card" key={c.label}>
          <div className="stat-label">{c.label}</div>
          <div className="stat-value">{c.value}</div>
          <div className="stat-hint">{c.hint}</div>
        </div>
      ))}
    </div>
  );
}
