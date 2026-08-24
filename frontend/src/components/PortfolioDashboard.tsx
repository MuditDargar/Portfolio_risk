import { useQuery } from "@tanstack/react-query";
import { api } from "../api/client";
import { AllocationSliders } from "./AllocationSliders";
import { DrawdownChart } from "./DrawdownChart";
import { EfficientFrontierChart } from "./EfficientFrontierChart";
import { HoldingsEditor } from "./HoldingsEditor";
import { MetricsPanel } from "./MetricsPanel";
import { RebalanceAlertBanner } from "./RebalanceAlertBanner";

export function PortfolioDashboard({ portfolioId, onReset }: { portfolioId: string; onReset: () => void }) {
  const portfolioQuery = useQuery({
    queryKey: ["portfolio", portfolioId],
    queryFn: () => api.getPortfolio(portfolioId),
  });
  const metricsQuery = useQuery({
    queryKey: ["metrics", portfolioId],
    queryFn: () => api.getMetrics(portfolioId),
  });
  const riskQuery = useQuery({
    queryKey: ["risk", portfolioId],
    queryFn: () => api.getRisk(portfolioId),
  });
  const xirrQuery = useQuery({
    queryKey: ["xirr", portfolioId],
    queryFn: () => api.getXirr(portfolioId),
    retry: false,
  });

  if (portfolioQuery.isLoading || metricsQuery.isLoading || riskQuery.isLoading) {
    return <div className="loading-screen">Loading portfolio…</div>;
  }

  if (portfolioQuery.error || !portfolioQuery.data) {
    return (
      <div className="loading-screen">
        <p>Could not load this portfolio.</p>
        <button className="primary-button" onClick={onReset}>
          Start Over
        </button>
      </div>
    );
  }

  const portfolio = portfolioQuery.data;

  return (
    <div className="dashboard">
      <header className="dashboard-header">
        <div>
          <h1>{portfolio.name}</h1>
          <p className="stat-hint">
            Base currency: {portfolio.base_currency} · {portfolio.holdings.length} holdings
            {xirrQuery.data && <> · XIRR: {(xirrQuery.data.xirr * 100).toFixed(2)}%</>}
          </p>
        </div>
        <button className="secondary-button" onClick={onReset}>
          Reset Demo
        </button>
      </header>

      <RebalanceAlertBanner portfolioId={portfolioId} />

      {metricsQuery.data && riskQuery.data && <MetricsPanel metrics={metricsQuery.data} risk={riskQuery.data} />}

      <div className="dashboard-grid">
        <HoldingsEditor portfolioId={portfolioId} holdings={portfolio.holdings} />
        <AllocationSliders
          key={portfolio.holdings.map((h) => `${h.asset_symbol}:${h.target_weight}`).join("|")}
          portfolioId={portfolioId}
          holdings={portfolio.holdings}
        />
      </div>

      <DrawdownChart holdings={portfolio.holdings} />

      {metricsQuery.data && <EfficientFrontierChart holdings={portfolio.holdings} metrics={metricsQuery.data} />}
    </div>
  );
}
