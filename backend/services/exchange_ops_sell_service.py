"""Sell plan with tax-aware ordering, dry-run, and smart pool pre-fill."""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from backend.services import crypto_exchange_service as ex
from backend.services.crypto_exchange_profit_agent_service import _pnl_from_trades, _read_trades
from backend.services.exchange_mn2_pool_service import pool_gaps, pool_user_id
from backend.services.exchange_ops_service import load_config


def _asset_usd(symbol: str, amount: float) -> float:
    sym = (symbol or "").strip().upper()
    if sym == "MN2":
        return float(amount or 0) * ex._mn2_usd()
    return float(amount or 0) * ex._price_usd(sym)


def _tax_priority_score(user_id: str, symbol: str) -> float:
    """Feature 16: lower score = sell first (prefer higher cost basis / lower gain)."""
    trades = _read_trades(limit=2000)
    pnl = _pnl_from_trades(user_id, trades)
    lots = pnl.get("lots") or {}
    lot = lots.get(symbol.upper()) or {}
    qty = float(lot.get("qty") or 0)
    cost = float(lot.get("cost") or 0)
    if qty <= 0 or cost <= 0:
        return 999.0
    avg_cost = cost / qty
    price = ex._price_usd(symbol)
    unrealized_gain_pct = ((price - avg_cost) / avg_cost * 100.0) if avg_cost > 0 else 0.0
    return max(0.0, unrealized_gain_pct)


def build_sell_plan(*, wallet_user_id: Optional[str] = None) -> Dict[str, Any]:
    cfg = load_config()
    sell_cfg = cfg.get("sell_plan") or {}
    uid = wallet_user_id or str(sell_cfg.get("wallet_user_id") or pool_user_id())
    excluded = {str(s).upper() for s in (sell_cfg.get("excluded_assets") or ["MN2", "USDT", "USDC"])}
    min_usd = float(sell_cfg.get("min_sell_usd") or 25.0)
    max_actions = int(sell_cfg.get("max_actions_per_run") or 8)
    targets = [str(q).upper() for q in (sell_cfg.get("target_quotes") or ["USDT", "USDC"])]

    wallet = ex.get_wallet(uid)
    assets = wallet.get("assets") or {}
    candidates: List[Dict[str, Any]] = []

    for sym, raw_amt in assets.items():
        sym_u = str(sym).upper()
        if sym_u in excluded:
            continue
        amt = float(raw_amt or 0)
        usd = _asset_usd(sym_u, amt)
        if usd < min_usd:
            continue
        tax_score = _tax_priority_score(uid, sym_u)
        candidates.append({
            "symbol": sym_u,
            "amount": round(amt, 12),
            "usd_value": round(usd, 2),
            "tax_priority_score": round(tax_score, 2),
            "target_quote": targets[0] if targets else "USDT",
            "side": "sell",
            "note": "tax_aware: lower score = sell first",
        })

    candidates.sort(key=lambda c: (c["tax_priority_score"], -c["usd_value"]))
    candidates = candidates[:max_actions]

    gaps = pool_gaps()
    gap_usd = sum(_asset_usd(s, a) for s, a in gaps.items())

    return {
        "success": True,
        "wallet_user_id": uid,
        "pool_gaps": gaps,
        "pool_gap_usd": round(gap_usd, 2),
        "actions": candidates,
        "tax_aware_order": True,
        "total_usd": round(sum(c["usd_value"] for c in candidates), 2),
    }


def execute_sell_plan(*, dry_run: bool = True, wallet_user_id: Optional[str] = None) -> Dict[str, Any]:
    """Feature 15: dry-run or execute tax-aware sell plan."""
    plan = build_sell_plan(wallet_user_id=wallet_user_id)
    if not plan.get("success"):
        return plan

    if dry_run:
        plan["dry_run"] = True
        plan["executed"] = []
        return plan

    uid = plan["wallet_user_id"]
    executed: List[Dict[str, Any]] = []
    for action in plan.get("actions") or []:
        sym = action["symbol"]
        amt = float(action["amount"])
        quote = action.get("target_quote") or "USDT"
        q = ex.quote_swap(uid, sym, "sell", amt, quote)
        if not q.get("success"):
            executed.append({"symbol": sym, "success": False, "error": q.get("error")})
            continue
        res = ex.execute_swap(uid, q.get("quote_id") or "", sym, "sell", amt, quote)
        executed.append({
            "symbol": sym,
            "success": bool(res.get("success")),
            "trade_id": res.get("trade_id"),
            "error": res.get("error"),
            "usd_value": action.get("usd_value"),
        })

    plan["dry_run"] = False
    plan["executed"] = executed
    return plan


def smart_prefill(
    from_asset: str,
    to_asset: str,
    amount: float,
    *,
    auto_execute: Optional[bool] = None,
) -> Dict[str, Any]:
    """Feature 3: queue internal sells when pool gap would block swoop."""
    cfg = load_config()
    prefill_cfg = cfg.get("prefill") or {}
    if not prefill_cfg.get("enabled", True):
        return {"success": True, "skipped": True, "reason": "prefill_disabled"}

    gaps = pool_gaps()
    min_gap_usd = float(prefill_cfg.get("min_gap_usd") or 50.0)
    gap_usd = sum(_asset_usd(s, a) for s, a in gaps.items())
    if gap_usd < min_gap_usd:
        return {"success": True, "skipped": True, "reason": "gap_below_threshold", "gap_usd": gap_usd}

    plan = build_sell_plan()
    actions = plan.get("actions") or []
    if not actions:
        return {"success": True, "skipped": True, "reason": "no_sell_candidates", "gap_usd": gap_usd}

    do_exec = auto_execute if auto_execute is not None else bool(prefill_cfg.get("auto_execute"))
    result = {
        "success": True,
        "gap_usd": gap_usd,
        "recommended_sells": actions[:3],
        "swoop": {"from": from_asset, "to": to_asset, "amount": amount},
    }

    if do_exec:
        exec_res = execute_sell_plan(dry_run=False)
        result["executed"] = exec_res.get("executed") or []
    else:
        result["dry_run_plan"] = plan

    return result
