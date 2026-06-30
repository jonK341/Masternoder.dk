"""Profit intelligence agent for the MasterNoder exchange."""
from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from backend.services import crypto_exchange_service as ex


def _read_trades(limit: int = 1000) -> List[Dict[str, Any]]:
    if not ex.os.path.isfile(ex._TRADES_PATH):
        return []
    rows: List[Dict[str, Any]] = []
    with open(ex._TRADES_PATH, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                row = json.loads(line)
            except Exception:
                continue
            if isinstance(row, dict):
                rows.append(row)
    return rows[-max(1, int(limit or 1000)):]


def _as_float(value: Any) -> float:
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0


def _fee_usd(row: Dict[str, Any]) -> float:
    if row.get("fee_usd") is not None:
        return _as_float(row.get("fee_usd"))
    fee = _as_float(row.get("fee"))
    quote = str(row.get("quote") or "MN2").upper()
    if quote == "MN2":
        return fee * ex._mn2_usd()
    if quote == "COINS":
        mn2_cfg = ex._read_json(ex.os.path.join(ex._BASE, "data", "mn2_config.json"), {})
        coins_per_mn2 = max(_as_float(mn2_cfg.get("coins_per_mn2")) or 100.0, 1.0)
        return (fee / coins_per_mn2) * ex._mn2_usd()
    return 0.0


def _user_trade_side(row: Dict[str, Any], user_id: str) -> Optional[str]:
    if row.get("buyer") == user_id:
        return "buy"
    if row.get("seller") == user_id:
        return "sell"
    if row.get("user_id") == user_id:
        side = str(row.get("side") or "").lower()
        if side in ("buy", "sell"):
            return side
    return None


def _trade_usd_value(row: Dict[str, Any]) -> float:
    if row.get("usd_value") is not None:
        return _as_float(row.get("usd_value"))
    symbol = str(row.get("symbol") or "").upper()
    return _as_float(row.get("amount")) * ex._price_usd(symbol)


def _pnl_from_trades(user_id: str, trades: List[Dict[str, Any]]) -> Dict[str, Any]:
    lots: Dict[str, Dict[str, float]] = {}
    realized = 0.0
    fees = 0.0
    volume = 0.0
    wins = 0
    sells = 0
    by_asset: Dict[str, Dict[str, float]] = {}
    user_rows = []

    for row in trades:
        side = _user_trade_side(row, user_id)
        if not side:
            continue
        symbol = str(row.get("symbol") or "").upper()
        if not symbol:
            continue
        qty = _as_float(row.get("amount"))
        usd = _trade_usd_value(row)
        fee = _fee_usd(row)
        if qty <= 0 or usd <= 0:
            continue
        fees += fee
        volume += usd
        user_rows.append(row)
        asset = by_asset.setdefault(symbol, {"bought_usd": 0.0, "sold_usd": 0.0, "realized_pnl_usd": 0.0, "fees_usd": 0.0})
        asset["fees_usd"] += fee
        lot = lots.setdefault(symbol, {"qty": 0.0, "cost": 0.0})

        if side == "buy":
            lot["qty"] += qty
            lot["cost"] += usd + fee
            asset["bought_usd"] += usd
        else:
            sells += 1
            avg_cost = (lot["cost"] / lot["qty"]) if lot["qty"] > 0 else 0.0
            cost_out = min(qty, lot["qty"]) * avg_cost
            proceeds = max(0.0, usd - fee)
            pnl = proceeds - cost_out
            realized += pnl
            asset["sold_usd"] += usd
            asset["realized_pnl_usd"] += pnl
            if pnl > 0:
                wins += 1
            if lot["qty"] > 0:
                reduction = min(1.0, qty / lot["qty"])
                lot["qty"] = max(0.0, lot["qty"] - qty)
                lot["cost"] = max(0.0, lot["cost"] * (1.0 - reduction))

    remaining_basis = sum(v["cost"] for v in lots.values())
    return {
        "lots": lots,
        "realized_pnl_usd": round(realized, 4),
        "remaining_cost_basis_usd": round(remaining_basis, 4),
        "fees_paid_usd": round(fees, 4),
        "trade_volume_usd": round(volume, 4),
        "trade_count": len(user_rows),
        "sell_win_rate_pct": round((wins / sells) * 100.0, 2) if sells else None,
        "by_asset": {k: {kk: round(vv, 4) for kk, vv in val.items()} for k, val in by_asset.items()},
        "recent_trades": user_rows[-10:][::-1],
    }


def _agent_performance(trades: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    agent_ids = []
    try:
        from backend.services.crypto_exchange_agent_service import list_agents
        agent_ids = [a.get("id") for a in (list_agents().get("agents") or []) if a.get("id")]
    except Exception:
        agent_ids = []
    rows = []
    for aid in agent_ids:
        pnl = _pnl_from_trades(aid, trades)
        wallet = ex.get_wallet(aid)
        portfolio = ex._portfolio_value_usd(wallet.get("assets") or {})
        unrealized = portfolio - _as_float(pnl.get("remaining_cost_basis_usd"))
        rows.append({
            "agent_id": aid,
            "portfolio_value_usd": round(portfolio, 4),
            "realized_pnl_usd": pnl["realized_pnl_usd"],
            "unrealized_pnl_usd": round(unrealized, 4),
            "fees_paid_usd": pnl["fees_paid_usd"],
            "trade_count": pnl["trade_count"],
        })
    return sorted(rows, key=lambda r: r["realized_pnl_usd"] + r["unrealized_pnl_usd"], reverse=True)


def _insights(user_report: Dict[str, Any], pnl: Dict[str, Any], unrealized: float, portfolio_value: float) -> List[Dict[str, str]]:
    insights: List[Dict[str, str]] = []
    total_pnl = _as_float(pnl.get("realized_pnl_usd")) + unrealized
    if total_pnl > 0:
        insights.append({"level": "positive", "text": f"Estimated total P/L is positive at ${total_pnl:.2f}."})
    elif portfolio_value > 0:
        insights.append({"level": "watch", "text": f"Estimated total P/L is ${total_pnl:.2f}; watch fees and entry price."})
    else:
        insights.append({"level": "info", "text": "No portfolio value yet. Start with a PayPal buy or MN2 swap."})

    fees = _as_float(pnl.get("fees_paid_usd"))
    volume = _as_float(pnl.get("trade_volume_usd"))
    if volume > 0 and (fees / volume) > 0.01:
        insights.append({"level": "fee", "text": "Fees are above 1% of volume; use limit orders or higher volume tier rebates."})

    next_tier = user_report.get("next_tier")
    if isinstance(next_tier, dict):
        gap = max(0.0, _as_float(next_tier.get("min_volume_usd")) - _as_float(user_report.get("volume_usd_30d")))
        insights.append({"level": "target", "text": f"${gap:.2f} more 30d volume unlocks {next_tier.get('label')} rebates."})

    return insights[:5]


def build_profit_report(user_id: str) -> Dict[str, Any]:
    uid = str(user_id or "").strip()
    if not uid:
        return {"success": False, "error": "user_id required"}
    trades = _read_trades()
    wallet = ex.get_wallet(uid)
    assets = wallet.get("assets") or {}
    progress = ex.get_user_progress_report(uid)
    pnl = _pnl_from_trades(uid, trades)
    portfolio_value = ex._portfolio_value_usd(assets)
    unrealized = round(portfolio_value - _as_float(pnl.get("remaining_cost_basis_usd")), 4)
    realized = _as_float(pnl.get("realized_pnl_usd"))
    total = round(realized + unrealized, 4)
    basis = _as_float(pnl.get("remaining_cost_basis_usd"))
    roi = round((total / basis) * 100.0, 2) if basis > 0 else None
    daily_projection = total / 30.0 if pnl.get("trade_count") else 0.0
    monthly_projection = daily_projection * 30.0

    return {
        "success": True,
        "agent": {
            "id": "exchange_profit_oracle",
            "name": "Exchange Profit Oracle",
            "version": "1.0",
            "capabilities": [
                "realized_pnl",
                "unrealized_pnl",
                "fee_drag",
                "tier_gap",
                "agent_performance",
                "projection",
            ],
        },
        "user_id": uid,
        "portfolio_value_usd": portfolio_value,
        "realized_pnl_usd": realized,
        "unrealized_pnl_usd": unrealized,
        "estimated_total_pnl_usd": total,
        "roi_pct": roi,
        "fees_paid_usd": pnl["fees_paid_usd"],
        "trade_volume_usd": pnl["trade_volume_usd"],
        "trade_count": pnl["trade_count"],
        "sell_win_rate_pct": pnl["sell_win_rate_pct"],
        "monthly_projection_usd": round(monthly_projection, 4),
        "by_asset": pnl["by_asset"],
        "insights": _insights(progress, pnl, unrealized, portfolio_value),
        "agent_performance": _agent_performance(trades),
        "recent_trades": pnl["recent_trades"],
        "generated_at": ex._iso(),
    }
