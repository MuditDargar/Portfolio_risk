import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { api } from "../api/client";
import type { Holding, HoldingIn } from "../api/types";

export function HoldingsEditor({ portfolioId, holdings }: { portfolioId: string; holdings: Holding[] }) {
  const queryClient = useQueryClient();
  const [draft, setDraft] = useState<HoldingIn[]>(holdings);
  const [error, setError] = useState<string | null>(null);

  const mutation = useMutation({
    mutationFn: (payload: HoldingIn[]) => api.replaceHoldings(portfolioId, payload),
    onSuccess: () => {
      setError(null);
      queryClient.invalidateQueries({ queryKey: ["portfolio", portfolioId] });
      queryClient.invalidateQueries({ queryKey: ["metrics", portfolioId] });
      queryClient.invalidateQueries({ queryKey: ["risk", portfolioId] });
      queryClient.invalidateQueries({ queryKey: ["beta", portfolioId] });
      queryClient.invalidateQueries({ queryKey: ["rebalance", portfolioId] });
    },
    onError: (e: unknown) => {
      const detail = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      setError(detail ?? "Failed to save holdings");
    },
  });

  const totalWeight = draft.reduce((sum, h) => sum + Number(h.target_weight), 0);

  function updateField(index: number, field: keyof HoldingIn, value: string) {
    setDraft((prev) => {
      const next = [...prev];
      const numericFields: (keyof HoldingIn)[] = ["quantity", "target_weight", "buy_price"];
      next[index] = {
        ...next[index],
        [field]: numericFields.includes(field) ? Number(value) : value,
      };
      return next;
    });
  }

  return (
    <section className="panel">
      <h3>Holdings</h3>
      <table className="data-table">
        <thead>
          <tr>
            <th>Asset</th>
            <th>Quantity</th>
            <th>Target Weight</th>
            <th>Buy Price</th>
            <th>Buy Date</th>
          </tr>
        </thead>
        <tbody>
          {draft.map((h, i) => (
            <tr key={h.asset_symbol}>
              <td>{h.asset_symbol}</td>
              <td>
                <input
                  type="number"
                  min={0}
                  step="any"
                  value={h.quantity}
                  onChange={(e) => updateField(i, "quantity", e.target.value)}
                />
              </td>
              <td>
                <input
                  type="number"
                  min={0}
                  max={1}
                  step="0.01"
                  value={h.target_weight}
                  onChange={(e) => updateField(i, "target_weight", e.target.value)}
                />
              </td>
              <td>
                <input
                  type="number"
                  min={0}
                  step="any"
                  value={h.buy_price}
                  onChange={(e) => updateField(i, "buy_price", e.target.value)}
                />
              </td>
              <td>{h.buy_date}</td>
            </tr>
          ))}
        </tbody>
      </table>
      <div className="stat-hint" style={{ marginTop: "0.5rem" }}>
        Target weight total: {(totalWeight * 100).toFixed(1)}% {Math.abs(totalWeight - 1) > 1e-6 && "(must sum to 100%)"}
      </div>
      {error && <div className="error-text">{error}</div>}
      <button
        className="primary-button"
        disabled={mutation.isPending || Math.abs(totalWeight - 1) > 1e-6}
        onClick={() => mutation.mutate(draft)}
      >
        {mutation.isPending ? "Saving…" : "Save Holdings"}
      </button>
    </section>
  );
}
