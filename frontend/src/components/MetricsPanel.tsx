import type { MetricsResponse, RiskResponse } from "../api/types";
import { RiskAdjustedReturnCards } from "./RiskAdjustedReturnCards";
import { VarCvarCard } from "./VarCvarCard";

function pct(value: number): string {
  return `${(value * 100).toFixed(2)}%`;
}

export function MetricsPanel({ metrics, risk }: { metrics: MetricsResponse; risk: RiskResponse }) {
  return (
    <section className="panel">
      <div className="headline-row">
        <div>
          <div className="stat-label">Expected Return</div>
          <div className="stat-value large">{pct(metrics.expected_return)}</div>
        </div>
        <div>
          <div className="stat-label">Volatility</div>
          <div className="stat-value large">{pct(metrics.volatility)}</div>
        </div>
        <div>
          <div className="stat-label">Portfolio Beta</div>
          <div className="stat-value large">{metrics.beta.toFixed(2)}</div>
        </div>
      </div>
      <RiskAdjustedReturnCards metrics={metrics} />
      <VarCvarCard risk={risk} />
    </section>
  );
}
