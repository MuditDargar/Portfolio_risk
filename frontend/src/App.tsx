import { useState } from "react";
import { GetStarted } from "./components/GetStarted";
import { PortfolioDashboard } from "./components/PortfolioDashboard";

const STORAGE_KEY = "portfolio_risk_dashboard.portfolio_id";

function App() {
  const [portfolioId, setPortfolioId] = useState<string | null>(() => localStorage.getItem(STORAGE_KEY));

  function handleCreated(id: string) {
    localStorage.setItem(STORAGE_KEY, id);
    setPortfolioId(id);
  }

  function handleReset() {
    localStorage.removeItem(STORAGE_KEY);
    setPortfolioId(null);
  }

  return portfolioId ? (
    <PortfolioDashboard portfolioId={portfolioId} onReset={handleReset} />
  ) : (
    <GetStarted onCreated={handleCreated} />
  );
}

export default App;
