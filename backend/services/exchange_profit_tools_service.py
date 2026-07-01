"""Profit-generation tools: opportunity radar, compounding optimizer, what-if simulator."""
from __future__ import annotations

import random
from typing import Any, Dict, List, Optional

from backend.services import crypto_exchange_service as ex
from backend.services import external_exchange_connector_service as conn
from backend.services import exchange_prediction_service as predict
from backend.services import exchange_profit_calculator_service as calc


def opportunity_radar(symbols: Optional[List[str]] = None,
                      *, injected: Optional[Dict[str, Any]] = None, limit: int = 10) -> Dict[str, Any]:
    """Rank symbols right now by predicted net edge + arbitrage potential."""
    cfg = conn.load_connectors_config()
    symbols = [str(s).upper() for s in (symbols or cfg.get("supported_symbols") or [])]
    fetched = conn.fetch_prices(symbols, injected=injected)
    prices = fetched.get("prices") or {}

    rows: List[Dict[str, Any]] = []
    for sym in symbols:
        p = predict.predict_symbol(sym, prices)
        # Recommend cheapest-ask buy venue and richest-bid sell venue.
        best_buy = None
        best_sell = None
        for vid, syms in prices.items():
            t = syms.get(sym)
            if not t:
                continue
            if best_buy is None or t.get("ask", 0) and t["ask"] < best_buy[1]:
                best_buy = (vid, float(t.get("ask") or 0))
            if best_sell is None or t.get("bid", 0) > best_sell[1]:
                best_sell = (vid, float(t.get("bid") or 0))
        score = round(p["edge_uplift_bps"] + p["arb_edge_bps"], 2)
        rows.append({
            "symbol": sym,
            "direction": p["direction"],
            "confidence_pct": p["confidence_pct"],
            "expected_move_bps": p["expected_move_bps"],
            "arb_edge_bps": p["arb_edge_bps"],
            "edge_uplift_bps": p["edge_uplift_bps"],
            "score": score,
            "buy_venue": best_buy[0] if best_buy else None,
            "sell_venue": best_sell[0] if best_sell else None,
        })
    rows.sort(key=lambda r: r["score"], reverse=True)
    return {
        "success": True,
        "source": fetched.get("source"),
        "count": len(rows),
        "opportunities": rows[: max(1, int(limit or 10))],
        "disclaimer": predict._DISCLAIMER,
    }


def boost_scenarios(capital_usd: float, skill_ids: List[str], *, base_cycles: float = 24) -> Dict[str, Any]:
    """Show how much profit the bots can create at increasing boost levels."""
    try:
        from backend.services.exchange_premium_service import edge_bonus_and_cycles
        from backend.services.exchange_prediction_service import market_uplift_bps
        uplift = market_uplift_bps()
    except Exception:
        edge_bonus_and_cycles = None
        uplift = 0.0

    presets = [
        {"name": "Conservative", "risk": "low", "volatility": 0.20, "cycles_mult": 1.0, "premium": False},
        {"name": "Standard", "risk": "medium", "volatility": 0.35, "cycles_mult": 1.0, "premium": False},
        {"name": "Boosted (Premium)", "risk": "medium", "volatility": 0.45, "cycles_mult": 1.5, "premium": True},
        {"name": "Max Overdrive", "risk": "high", "volatility": 0.60, "cycles_mult": 2.0, "premium": True},
    ]
    rows = []
    for p in presets:
        bonus = 0.0
        cycles = base_cycles * p["cycles_mult"]
        if p["premium"] and edge_bonus_and_cycles:
            bonus, _ = edge_bonus_and_cycles(True, market_uplift_bps=uplift, base_cycles_per_day=base_cycles)
        proj = calc.cross_trade_projection(
            capital_usd, skill_ids, volatility=p["volatility"], cycles_per_day=cycles,
            risk_level=p["risk"], edge_bonus_bps=bonus,
        )
        rows.append({
            "name": p["name"], "premium": p["premium"], "risk": p["risk"],
            "cycles_per_day": round(cycles, 1), "edge_bps": proj["blended_edge_bps"],
            "daily_profit_usd": proj["daily_profit_usd"], "monthly_profit_usd": proj["monthly_profit_usd"],
            "monthly_roi_pct": proj["monthly_roi_pct"],
        })
    return {"success": True, "capital_usd": round(float(capital_usd or 0), 2),
            "skills": skill_ids, "scenarios": rows, "disclaimer": predict._DISCLAIMER}


def compounding_plan(capital_usd: float, daily_profit_usd: float, target_usd: float,
                     *, reinvest_pct: float = 100.0, max_days: int = 3650) -> Dict[str, Any]:
    capital = max(0.0, float(capital_usd or 0))
    target = float(target_usd or 0)
    if capital <= 0:
        return {"success": False, "error": "capital_required"}
    daily_rate = float(daily_profit_usd or 0) / capital
    reinvest = max(0.0, min(1.0, float(reinvest_pct or 0) / 100.0))

    cap = capital
    realized = 0.0
    days = 0
    days_to_target = None
    milestones: Dict[str, float] = {}
    checkpoints = {30: "d30", 90: "d90", 180: "d180", 365: "d365"}
    while days < int(max_days):
        days += 1
        profit = cap * daily_rate
        realized += profit
        cap += profit * reinvest
        if days in checkpoints:
            milestones[checkpoints[days]] = round(cap, 2)
        if days_to_target is None and target > 0 and cap >= target:
            days_to_target = days
            break
    return {
        "success": True,
        "start_capital_usd": round(capital, 2),
        "daily_rate_pct": round(daily_rate * 100.0, 4),
        "reinvest_pct": round(reinvest * 100.0, 2),
        "target_usd": round(target, 2),
        "days_to_target": days_to_target,
        "projected_capital_usd": round(cap, 2),
        "total_realized_profit_usd": round(realized, 2),
        "milestones": milestones,
    }


def simulate_strategy(capital_usd: float, edge_bps: float, *, cycles: int = 100,
                      volatility: float = 0.35, risk_level: str = "medium",
                      runs: int = 500, seed: int = 42) -> Dict[str, Any]:
    """Monte-Carlo-style distribution of total profit over N cycles (seeded, reproducible)."""
    position = calc.position_size_usd(capital_usd, edge_bps, risk_level)
    mean_per_cycle = position * max(0.0, float(edge_bps)) / 10000.0
    rng = random.Random(int(seed))
    cycles = max(1, int(cycles))
    totals: List[float] = []
    for _ in range(max(1, int(runs))):
        total = 0.0
        for _c in range(cycles):
            noise = 1.0 + rng.uniform(-float(volatility), float(volatility))
            total += mean_per_cycle * noise
        totals.append(total)
    totals.sort()
    n = len(totals)

    def pct(p: float) -> float:
        idx = min(n - 1, max(0, int(p * n)))
        return round(totals[idx], 4)

    profit_runs = sum(1 for t in totals if t > 0)
    return {
        "success": True,
        "capital_usd": round(float(capital_usd or 0), 2),
        "edge_bps": round(float(edge_bps or 0), 2),
        "position_usd": position,
        "cycles": cycles,
        "runs": n,
        "mean_total_usd": round(sum(totals) / n, 4),
        "p10_usd": pct(0.10),
        "p50_usd": pct(0.50),
        "p90_usd": pct(0.90),
        "prob_profit_pct": round(profit_runs / n * 100.0, 2),
        "disclaimer": predict._DISCLAIMER,
    }
