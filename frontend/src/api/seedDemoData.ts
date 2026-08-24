// Bootstraps a working demo: the SDD explicitly puts live market-data feeds
// out of scope (Section 1.3 — no broker execution / external price feed is
// specified), so price ingestion has to come from somewhere for the app to
// be usable. This generates deterministic synthetic daily price series
// (seeded PRNG geometric random walk) for a small asset universe + a
// benchmark index, then creates a starter portfolio against them.
import { api } from "./client";
import type { AssetClass, HoldingIn, PricePoint } from "./types";

function mulberry32(seed: number) {
  return function () {
    seed |= 0;
    seed = (seed + 0x6d2b79f5) | 0;
    let t = Math.imul(seed ^ (seed >>> 15), 1 | seed);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

function generatePriceSeries(
  seed: number,
  days: number,
  startPrice: number,
  annualDrift: number,
  annualVol: number
): PricePoint[] {
  const rand = mulberry32(seed);
  const dailyDrift = annualDrift / 252;
  const dailyVol = annualVol / Math.sqrt(252);
  const prices: PricePoint[] = [];
  let price = startPrice;
  const start = new Date();
  start.setDate(start.getDate() - days);

  for (let i = 0; i < days; i++) {
    // Box-Muller transform for a standard-normal shock from two uniforms.
    const u1 = Math.max(rand(), 1e-9);
    const u2 = rand();
    const z = Math.sqrt(-2 * Math.log(u1)) * Math.cos(2 * Math.PI * u2);
    const dailyReturn = dailyDrift + dailyVol * z;
    price = price * (1 + dailyReturn);

    const date = new Date(start);
    date.setDate(date.getDate() + i);
    prices.push({ date: date.toISOString().slice(0, 10), close_price: Math.round(price * 100) / 100 });
  }
  return prices;
}

const DEMO_ASSETS: Array<{
  symbol: string;
  name: string;
  asset_class: AssetClass;
  seed: number;
  startPrice: number;
  drift: number;
  vol: number;
  quantity: number;
  targetWeight: number;
}> = [
  { symbol: "NIFTYETF", name: "Nifty 50 Index Fund", asset_class: "equity", seed: 1, startPrice: 220, drift: 0.12, vol: 0.16, quantity: 200, targetWeight: 0.45 },
  { symbol: "GILTFUND", name: "Government Securities Fund", asset_class: "debt", seed: 2, startPrice: 42, drift: 0.07, vol: 0.05, quantity: 1500, targetWeight: 0.3 },
  { symbol: "GOLDETF", name: "Gold ETF", asset_class: "gold", seed: 3, startPrice: 55, drift: 0.09, vol: 0.14, quantity: 400, targetWeight: 0.15 },
  { symbol: "REITIDX", name: "REIT Index Fund", asset_class: "reit", seed: 4, startPrice: 95, drift: 0.10, vol: 0.18, quantity: 150, targetWeight: 0.10 },
];

const BENCHMARK_SYMBOL = "NIFTY50";

export async function seedDemoPortfolio(): Promise<string> {
  const days = 260;
  const existingAssets = await api.listAssets();
  const existingSymbols = new Set(existingAssets.map((a) => a.symbol));

  // Benchmark index for CAPM beta/alpha (FR-5).
  if (!existingSymbols.has(BENCHMARK_SYMBOL)) {
    await api.createAsset({ symbol: BENCHMARK_SYMBOL, name: "NIFTY 50 (Benchmark)", asset_class: "index" });
    await api.ingestPrices(BENCHMARK_SYMBOL, generatePriceSeries(99, days, 100, 0.11, 0.15));
  }

  const holdings: HoldingIn[] = [];
  let totalCostBasis = 0;
  for (const demo of DEMO_ASSETS) {
    if (!existingSymbols.has(demo.symbol)) {
      await api.createAsset({ symbol: demo.symbol, name: demo.name, asset_class: demo.asset_class });
      await api.ingestPrices(demo.symbol, generatePriceSeries(demo.seed, days, demo.startPrice, demo.drift, demo.vol));
    }
    const prices = await api.getPrices(demo.symbol);
    // buy_price/buy_date must agree: the price actually observed on the buy date
    // (the start of the generated series), not today's price.
    const buyDate = prices[0]?.date ?? new Date().toISOString().slice(0, 10);
    const buyPrice = prices[0]?.close_price ?? demo.startPrice;
    totalCostBasis += buyPrice * demo.quantity;
    holdings.push({
      asset_symbol: demo.symbol,
      quantity: demo.quantity,
      target_weight: demo.targetWeight,
      buy_price: buyPrice,
      buy_date: buyDate,
    });
  }

  const portfolio = await api.createPortfolio({
    name: "My Demo Portfolio",
    base_currency: "INR",
    holdings,
  });

  // A handful of SIP-style deposits so /xirr has cash flows to work with
  // (FR-8), sized to roughly match what the holdings actually cost — so the
  // resulting XIRR reflects real price drift instead of an arbitrary,
  // unrelated deposit total swamping the position size.
  const sipOffsetsDays = [180, 150, 120, 90, 60, 30];
  const perDeposit = Math.round(totalCostBasis / sipOffsetsDays.length);
  for (const daysAgo of sipOffsetsDays) {
    const d = new Date();
    d.setDate(d.getDate() - daysAgo);
    await api.addCashFlow(portfolio.id, { date: d.toISOString().slice(0, 10), amount: perDeposit });
  }

  return portfolio.id;
}

export { BENCHMARK_SYMBOL, DEMO_ASSETS };
