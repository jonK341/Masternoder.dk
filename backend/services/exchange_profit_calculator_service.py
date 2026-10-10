"""Advanced cross-trading profit math: margins, position sizing, projections."""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from backend.services import exchange_bot_skills_service as skills

_RISK_FACTOR = {"low": 0.5, "medium": 0.8, "high": 1.15}


def net_margin_bps(
    buy_ask: float,
    sell_bid: float,
    *,
    buy_fee_bps: float = 10,
    sell_fee_bps: float = 10,
    transfer_bps: float = 20,
    slippage_bps: float = 5,
) -> Dict[str, Any]:
    buy_ask = float(buy_ask or 0)
    sell_bid = float(sell_bid or 0)
    if buy_ask <= 0:
        return {"gross_bps": 0.0, "fee_bps": 0.0, "net_bps": 0.0, "profitable": False}
    gross = (sell_bid - buy_ask) / buy_ask * 10000.0
    fee = float(buy_fee_bps) + float(sell_fee_bps) + float(transfer_bps) + float(slippage_bps)
    net = gross - fee
    return {
        "gross_bps": round(gross, 2),
        "fee_bps": round(fee, 2),
        "net_bps": round(net, 2),
        "profitable": net > 0,
    }


def position_size_usd(capital_usd: float, edge_bps: float, risk_level: str = "medium") -> float:
    """Scale exposure by edge and risk appetite, capped at the available capital."""
    capital_usd = max(0.0, float(capital_usd or 0))
    edge_bps = max(0.0, float(edge_bps or 0))
    rf = _RISK_FACTOR.get((risk_level or "medium").lower(), 0.8)
    # Fraction grows with edge but saturates; 50 bps edge ~ full risk fraction.
    fraction = min(1.0, edge_bps / 50.0) * rf
    return round(capital_usd * fraction, 2)


def opportunity_profit(capital_usd: float, net_bps: float, *, risk_level: str = "medium") -> Dict[str, Any]:
    pos = position_size_usd(capital_usd, net_bps, risk_level)
    profit = pos * max(0.0, float(net_bps)) / 10000.0
    return {
        "position_usd": pos,
        "net_bps": round(float(net_bps), 2),
        "profit_per_cycle_usd": round(profit, 4),
    }


def cross_trade_projection(
    capital_usd: float,
    skill_ids: List[str],
    *,
    volatility: float = 0.35,
    cycles_per_day: float = 24,
    risk_level: str = "medium",
    edge_bonus_bps: float = 0.0,
) -> Dict[str, Any]:
    blended = skills.blended_edge_bps(skill_ids, volatility)
    base_edge = blended["blended_edge_bps"]
    edge = round(base_edge + max(0.0, float(edge_bonus_bps or 0)), 2)
    per_cycle = opportunity_profit(capital_usd, edge, risk_level=risk_level)
    daily = per_cycle["profit_per_cycle_usd"] * float(cycles_per_day or 0)
    capital = max(1.0, float(capital_usd or 0))
    return {
        "success": True,
        "capital_usd": round(float(capital_usd or 0), 2),
        "skills": skill_ids,
        "volatility": float(volatility),
        "risk_level": risk_level,
        "base_edge_bps": base_edge,
        "edge_bonus_bps": round(max(0.0, float(edge_bonus_bps or 0)), 2),
        "blended_edge_bps": edge,
        "edge_breakdown": blended["breakdown"],
        "position_usd": per_cycle["position_usd"],
        "profit_per_cycle_usd": per_cycle["profit_per_cycle_usd"],
        "cycles_per_day": float(cycles_per_day or 0),
        "daily_profit_usd": round(daily, 4),
        "weekly_profit_usd": round(daily * 7, 4),
        "monthly_profit_usd": round(daily * 30, 4),
        "annual_profit_usd": round(daily * 365, 4),
        "daily_roi_pct": round(daily / capital * 100.0, 4),
        "monthly_roi_pct": round(daily * 30 / capital * 100.0, 4),
    }


def bot_roi(realized_usd: float, capital_usd: float, age_days: float) -> Dict[str, Any]:
    realized = float(realized_usd or 0)
    capital = max(1.0, float(capital_usd or 0))
    age = max(0.0001, float(age_days or 0))
    per_day = realized / age
    return {
        "realized_usd": round(realized, 4),
        "roi_pct": round(realized / capital * 100.0, 4),
        "avg_profit_per_day_usd": round(per_day, 4),
        "projected_monthly_usd": round(per_day * 30, 4),
    }


def portfolio_projection(bots: List[Dict[str, Any]], *, horizon_days: int = 30) -> Dict[str, Any]:
    """Compound the per-day projection of a set of bots over a horizon."""
    daily = 0.0
    capital = 0.0
    for b in bots or []:
        daily += float(b.get("daily_profit_usd") or 0)
        capital += float(b.get("capital_usd") or 0)
    return {
        "bot_count": len(bots or []),
        "total_capital_usd": round(capital, 2),
        "combined_daily_profit_usd": round(daily, 4),
        "horizon_days": horizon_days,
        "horizon_profit_usd": round(daily * horizon_days, 4),
        "horizon_roi_pct": round(daily * horizon_days / max(1.0, capital) * 100.0, 4),
    }
