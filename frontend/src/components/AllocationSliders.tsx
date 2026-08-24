import { useMutation } from "@tanstack/react-query";
import { useRef, useState } from "react";
import { api } from "../api/client";
import type { Holding, ScenarioSimulateResponse } from "../api/types";
import { BENCHMARK_SYMBOL } from "../api/seedDemoData";

const DEBOUNCE_MS = 150; // Section 7.2: "Slider drags debounce 150ms then POST to /scenarios/simulate"

// Parent passes `key={holdingsFingerprint(holdings)}` (see PortfolioDashboard)
// so this component remounts — resetting slider state from the lazy
// useState initializer below — whenever saved holdings actually change,
// instead of syncing local state from a prop via an effect.
export function AllocationSliders({ portfolioId, holdings }: { portfolioId: string; holdings: Holding[] }) {
  const [weights, setWeights] = useState<Record<string, number>>(() =>
    Object.fromEntries(holdings.map((h) => [h.asset_symbol, h.target_weight]))
  );
  const debounceTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  const simulation = useMutation({
    mutationFn: (w: Record<string, number>) =>
      api.simulateScenario({ portfolio_id: portfolioId, weights: w, benchmark_symbol: BENCHMARK_SYMBOL }),
  });

  function normalizeAndSimulate(nextWeights: Record<string, number>) {
    if (debounceTimer.current) clearTimeout(debounceTimer.current);
    debounceTimer.current = setTimeout(() => {
      const total = Object.values(nextWeights).reduce((s, v) => s + v, 0);
      if (total <= 0) return;
      const normalized = Object.fromEntries(Object.entries(nextWeights).map(([k, v]) => [k, v / total]));
      simulation.mutate(normalized);
    }, DEBOUNCE_MS);
  }

  function handleSliderChange(symbol: string, value: number) {
    const next = { ...weights, [symbol]: value };
    setWeights(next);
    normalizeAndSimulate(next);
  }

  const totalRaw = Object.values(weights).reduce((s, v) => s + v, 0);
  const result: ScenarioSimulateResponse | undefined = simulation.data;

  return (
    <section className="panel">
      <h3>What-If Scenario Sliders</h3>
      <p className="stat-hint">Drag to explore hypothetical allocations — this does not save, only previews.</p>
      {holdings.map((h) => (
        <div className="slider-row" key={h.asset_symbol}>
          <label htmlFor={`slider-${h.asset_symbol}`}>{h.asset_symbol}</label>
          <input
            id={`slider-${h.asset_symbol}`}
            type="range"
            min={0}
            max={1}
            step={0.01}
            value={weights[h.asset_symbol] ?? 0}
            onChange={(e) => handleSliderChange(h.asset_symbol, Number(e.target.value))}
          />
          <span className="slider-value">{(((weights[h.asset_symbol] ?? 0) / (totalRaw || 1)) * 100).toFixed(0)}%</span>
        </div>
      ))}

      <div className="scenario-result">
        {simulation.isPending && <span className="stat-hint">Recomputing…</span>}
        {result && !simulation.isPending && (
          <div className="card-grid">
            <div className="stat-card">
              <div className="stat-label">Expected Return</div>
              <div className="stat-value">{(result.expected_return * 100).toFixed(2)}%</div>
            </div>
            <div className="stat-card">
              <div className="stat-label">Volatility</div>
              <div className="stat-value">{(result.volatility * 100).toFixed(2)}%</div>
            </div>
            <div className="stat-card">
              <div className="stat-label">Sharpe Ratio</div>
              <div className="stat-value">{result.sharpe_ratio.toFixed(2)}</div>
            </div>
            {result.beta !== null && (
              <div className="stat-card">
                <div className="stat-label">Beta</div>
                <div className="stat-value">{result.beta!.toFixed(2)}</div>
              </div>
            )}
          </div>
        )}
      </div>
    </section>
  );
}
