import { useMutation } from "@tanstack/react-query";
import { seedDemoPortfolio } from "../api/seedDemoData";

export function GetStarted({ onCreated }: { onCreated: (portfolioId: string) => void }) {
  const mutation = useMutation({
    mutationFn: seedDemoPortfolio,
    onSuccess: onCreated,
  });

  return (
    <div className="get-started">
      <h1>Portfolio Risk &amp; Rebalancing Dashboard</h1>
      <p>
        A formula-driven finance engine — Sharpe, Sortino, Treynor, Alpha, Beta, VaR, CVaR, Max Drawdown, XIRR, and
        Markowitz mean-variance optimization, computed live from your holdings.
      </p>
      <button className="primary-button" onClick={() => mutation.mutate()} disabled={mutation.isPending}>
        {mutation.isPending ? "Seeding demo portfolio…" : "Create Demo Portfolio"}
      </button>
      {mutation.error && <p className="error-text">Failed to create demo portfolio. Is the API reachable?</p>}
    </div>
  );
}
