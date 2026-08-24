import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "../api/client";

export function RebalanceAlertBanner({ portfolioId }: { portfolioId: string }) {
  const queryClient = useQueryClient();

  const { data, isLoading } = useQuery({
    queryKey: ["rebalance", portfolioId],
    queryFn: () => api.checkRebalance(portfolioId),
  });

  const executeMutation = useMutation({
    mutationFn: () => api.executeRebalance(portfolioId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["rebalance", portfolioId] });
    },
  });

  if (isLoading) return null;
  if (!data) return null;

  if (!data.any_triggered) {
    return (
      <section className="panel banner banner-ok">
        <strong>✓ On target.</strong> No holding has drifted beyond its rebalance threshold.
      </section>
    );
  }

  return (
    <section className="panel banner banner-alert">
      <strong>⚠ Rebalance recommended.</strong> {data.drifts.filter((d) => d.triggered).length} holding(s) have
      drifted beyond threshold.
      <table className="data-table" style={{ marginTop: "0.75rem" }}>
        <thead>
          <tr>
            <th>Asset</th>
            <th>Current</th>
            <th>Target</th>
            <th>Drift</th>
            <th>Suggested Trade</th>
          </tr>
        </thead>
        <tbody>
          {data.drifts
            .filter((d) => d.triggered)
            .map((d) => (
              <tr key={d.symbol}>
                <td>{d.symbol}</td>
                <td>{(d.current_weight * 100).toFixed(1)}%</td>
                <td>{(d.target_weight * 100).toFixed(1)}%</td>
                <td>{(d.drift * 100).toFixed(1)}%</td>
                <td>
                  {d.trade_amount >= 0 ? "Buy " : "Sell "}
                  {new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR", maximumFractionDigits: 0 }).format(
                    Math.abs(d.trade_amount)
                  )}
                </td>
              </tr>
            ))}
        </tbody>
      </table>
      <button className="primary-button" onClick={() => executeMutation.mutate()} disabled={executeMutation.isPending}>
        {executeMutation.isPending ? "Recording…" : "Log Rebalance Event"}
      </button>
    </section>
  );
}
