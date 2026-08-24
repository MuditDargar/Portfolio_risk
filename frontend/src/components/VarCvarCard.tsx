import type { RiskResponse } from "../api/types";

function inr(value: number): string {
  return new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR", maximumFractionDigits: 0 }).format(
    value
  );
}

export function VarCvarCard({ risk }: { risk: RiskResponse }) {
  return (
    <div className="panel">
      <h3>Value at Risk &amp; Tail Risk</h3>
      <table className="data-table">
        <thead>
          <tr>
            <th>Metric</th>
            <th>95% confidence</th>
            <th>99% confidence</th>
          </tr>
        </thead>
        <tbody>
          <tr>
            <td>Parametric VaR (1-day)</td>
            <td>{inr(risk.parametric_var_95)}</td>
            <td>{inr(risk.parametric_var_99)}</td>
          </tr>
          <tr>
            <td>Historical VaR</td>
            <td>{inr(risk.historical_var_95)}</td>
            <td>{inr(risk.historical_var_99)}</td>
          </tr>
          <tr>
            <td>Conditional VaR (CVaR)</td>
            <td>{inr(risk.cvar_95)}</td>
            <td>—</td>
          </tr>
        </tbody>
      </table>
      <div className="stat-hint" style={{ marginTop: "0.75rem" }}>
        Max Drawdown: <strong>{(risk.max_drawdown * 100).toFixed(2)}%</strong>
      </div>
    </div>
  );
}
