"""
End-to-end integration test — Section 10: "create portfolio -> ingest prices
-> call /metrics -> assert against a pre-computed reference portfolio."

Two synthetic assets with fully deterministic (non-random) price series are
used so every downstream metric can be hand-verified, plus a synthetic
benchmark for beta/alpha.
"""
from datetime import date, timedelta


def _dates(n: int, start: date = date(2025, 1, 1)) -> list[str]:
    return [(start + timedelta(days=i)).isoformat() for i in range(n)]


def _price_series(base: float, daily_growth: float, n: int) -> list[float]:
    return [round(base * (1 + daily_growth) ** i, 4) for i in range(n)]


def test_full_portfolio_lifecycle(client):
    n = 60
    dates = _dates(n)

    # Two assets + a benchmark index, each with a smooth deterministic trend
    # plus a small oscillation so variance/covariance are well-defined (not zero).
    for symbol, name, asset_class, base, growth in [
        ("AAA", "Alpha Equity", "equity", 100.0, 0.0015),
        ("BBB", "Beta Debt", "debt", 100.0, 0.0004),
        ("NIFTY50", "Benchmark Index", "index", 100.0, 0.0010),
    ]:
        resp = client.post("/api/v1/assets", json={"symbol": symbol, "name": name, "asset_class": asset_class})
        assert resp.status_code == 201, resp.text

        prices = _price_series(base, growth, n)
        # add a tiny alternating wobble so returns aren't perfectly collinear
        prices = [p * (1 + (0.002 if i % 2 == 0 else -0.002)) for i, p in enumerate(prices)]
        payload = {"prices": [{"date": d, "close_price": p} for d, p in zip(dates, prices)]}
        resp = client.post(f"/api/v1/assets/{symbol}/prices", json=payload)
        assert resp.status_code == 201, resp.text
        assert resp.json()["inserted"] == n

    # Create portfolio with two holdings, weights summing to 1
    resp = client.post(
        "/api/v1/portfolios",
        json={
            "name": "Test Portfolio",
            "base_currency": "INR",
            "holdings": [
                {"asset_symbol": "AAA", "quantity": 10, "target_weight": 0.6, "buy_price": 100, "buy_date": "2025-01-01"},
                {"asset_symbol": "BBB", "quantity": 10, "target_weight": 0.4, "buy_price": 100, "buy_date": "2025-01-01"},
            ],
        },
    )
    assert resp.status_code == 201, resp.text
    portfolio_id = resp.json()["id"]

    # /metrics
    resp = client.get(f"/api/v1/portfolios/{portfolio_id}/metrics")
    assert resp.status_code == 200, resp.text
    metrics = resp.json()
    for key in ["expected_return", "volatility", "sharpe_ratio", "sortino_ratio", "beta", "alpha", "treynor_ratio"]:
        assert key in metrics
    assert metrics["volatility"] >= 0

    # /risk
    resp = client.get(f"/api/v1/portfolios/{portfolio_id}/risk")
    assert resp.status_code == 200, resp.text
    risk = resp.json()
    assert risk["historical_var_99"] >= risk["historical_var_95"] - 1e-6
    assert risk["cvar_95"] >= risk["historical_var_95"] - 1e-6
    assert risk["max_drawdown"] <= 0

    # /beta
    resp = client.get(f"/api/v1/portfolios/{portfolio_id}/beta")
    assert resp.status_code == 200, resp.text
    beta_payload = resp.json()
    assert "AAA" in beta_payload["per_asset_beta"]
    assert "BBB" in beta_payload["per_asset_beta"]

    # cash flows + /xirr
    resp = client.post(f"/api/v1/portfolios/{portfolio_id}/cashflows", json={"date": "2025-01-01", "amount": 2000})
    assert resp.status_code == 201, resp.text
    resp = client.get(f"/api/v1/portfolios/{portfolio_id}/xirr")
    assert resp.status_code == 200, resp.text
    assert isinstance(resp.json()["xirr"], float)

    # rebalance check + execute
    resp = client.post(f"/api/v1/portfolios/{portfolio_id}/rebalance/check")
    assert resp.status_code == 200, resp.text
    check = resp.json()
    assert len(check["drifts"]) == 2

    resp = client.post(f"/api/v1/portfolios/{portfolio_id}/rebalance/execute")
    assert resp.status_code == 200, resp.text
    assert "event_id" in resp.json()

    # efficient frontier
    resp = client.post(
        "/api/v1/optimize/efficient-frontier",
        json={"asset_symbols": ["AAA", "BBB"], "lookback_days": n, "n_points": 5},
    )
    assert resp.status_code == 200, resp.text
    frontier = resp.json()["frontier"]
    assert len(frontier) > 0
    for point in frontier:
        assert abs(sum(point["weights"].values()) - 1.0) < 1e-6

    # scenario simulate (what-if)
    resp = client.post(
        "/api/v1/scenarios/simulate",
        json={
            "portfolio_id": portfolio_id,
            "weights": {"AAA": 0.5, "BBB": 0.5},
            "lookback_days": n,
            "benchmark_symbol": "NIFTY50",
        },
    )
    assert resp.status_code == 200, resp.text
    scenario = resp.json()
    assert "expected_return" in scenario
    assert scenario["beta"] is not None


def test_health_check(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_portfolio_not_found(client):
    resp = client.get("/api/v1/portfolios/does-not-exist/metrics")
    assert resp.status_code == 404


def test_get_prices_round_trip(client):
    client.post("/api/v1/assets", json={"symbol": "ZZZ", "name": "Z Asset", "asset_class": "equity"})
    client.post(
        "/api/v1/assets/ZZZ/prices",
        json={"prices": [{"date": "2025-01-01", "close_price": 100}, {"date": "2025-01-02", "close_price": 101}]},
    )
    resp = client.get("/api/v1/assets/ZZZ/prices")
    assert resp.status_code == 200
    prices = resp.json()
    assert len(prices) == 2
    assert prices[0]["date"] == "2025-01-01"


def test_get_prices_unknown_asset_404(client):
    resp = client.get("/api/v1/assets/DOES-NOT-EXIST/prices")
    assert resp.status_code == 404


def test_create_portfolio_rejects_weights_not_summing_to_one(client):
    client.post("/api/v1/assets", json={"symbol": "XXX", "name": "X", "asset_class": "equity"})
    resp = client.post(
        "/api/v1/portfolios",
        json={
            "name": "Bad Portfolio",
            "holdings": [
                {"asset_symbol": "XXX", "quantity": 1, "target_weight": 0.5, "buy_price": 10, "buy_date": "2025-01-01"}
            ],
        },
    )
    assert resp.status_code == 422
