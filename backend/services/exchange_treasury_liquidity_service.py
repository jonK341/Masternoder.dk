"""Treasury → liquidity pipeline: move platform MN2 into market-maker wallets + limit sells."""
from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from backend.services import crypto_exchange_service as ex
from backend.services.exchange_treasury_service import load_config, treasury_user_id

_LIQUIDITY_LEDGER = os.path.join(ex._DATA_DIR, "treasury_liquidity_ledger.jsonl")


def _iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _liquidity_cfg(cfg: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    cfg = cfg or load_config()
    liq = cfg.get("liquidity_pipeline")
    return liq if isinstance(liq, dict) else {}


def run_liquidity_tick() -> Dict[str, Any]:
    """Transfer a configured % of platform treasury MN2 to the liquidity bot and optionally list sells."""
    cfg = load_config()
    liq = _liquidity_cfg(cfg)
    if not liq.get("enabled", False):
        return {"success": True, "skipped": True, "reason": "disabled"}

    treasury_uid = treasury_user_id()
    target_agent = str(liq.get("liquidity_agent_id") or "exchange_agent_casino_liquidity")
    pct = float(liq.get("transfer_pct") or 0.05)
    min_mn2 = float(liq.get("min_transfer_mn2") or 100)
    sell_pct = float(liq.get("limit_sell_pct") or 0.5)
    quote = str(liq.get("sell_quote") or "COINS").upper()

    from backend.services.unified_points_database import unified_points_db
    bal = float((unified_points_db.get_all_points(treasury_uid).get("points") or {}).get("mn2_balance") or 0)
    transfer = round(bal * pct, 8)
    if transfer < min_mn2:
        return {"success": True, "skipped": True, "reason": "below_min", "treasury_mn2": bal}

    ref = f"treasury-liq:{_iso()[:19]}"
    try:
        ex._adjust_quote_balance(treasury_uid, "MN2", -transfer, "treasury_liquidity_pipeline",
                                 {"reference": ref, "target_agent": target_agent})
        ex._adjust_quote_balance(target_agent, "MN2", transfer, "treasury_liquidity_pipeline",
                                 {"reference": ref, "source": treasury_uid})
    except Exception as exc:
        return {"success": False, "error": str(exc)}

    order_result: Optional[Dict[str, Any]] = None
    sell_amt = round(transfer * sell_pct, 8)
    if sell_amt > 0:
        try:
            ex._adjust_quote_balance(target_agent, "MN2", -sell_amt, "treasury_liq_sell_lock", {"reference": ref})
            ex._adjust_balance(target_agent, "MN2", sell_amt)
            mn2_cfg = ex._read_json(os.path.join(ex._BASE, "data", "mn2_config.json"), {})
            cpm = float(mn2_cfg.get("coins_per_mn2") or 100)
            limit_price = round(cpm * 1.01, 4)
            order_result = ex.create_limit_order(target_agent, "MN2", "sell", sell_amt, limit_price, quote=quote)
        except Exception as exc:
            order_result = {"success": False, "error": str(exc)}

    row = {
        "ts": _iso(),
        "treasury_user_id": treasury_uid,
        "target_agent": target_agent,
        "transferred_mn2": transfer,
        "sell_mn2": sell_amt,
        "order": order_result,
    }
    ex._append_jsonl(_LIQUIDITY_LEDGER, row)
    ex._audit("treasury_liquidity_tick", user_id=treasury_uid, amount_mn2=transfer, target=target_agent)
    return {"success": True, **row}


def apply_fee_allocation() -> Dict[str, Any]:
    """Split fee_treasury MN2 per fee_allocation policy (informational ledger only)."""
    cfg = load_config()
    alloc = cfg.get("fee_allocation")
    if not isinstance(alloc, dict) or not alloc:
        return {"success": True, "skipped": True, "reason": "no_policy"}

    tre = ex._read_json(ex._TREASURY_PATH, {"total_fees_mn2": 0})
    total = float(tre.get("total_fees_mn2") or 0)
    if total <= 0:
        return {"success": True, "skipped": True, "reason": "empty_fee_treasury"}

    platform_pct = float(alloc.get("platform_treasury_pct") or 60)
    liq_pct = float(alloc.get("liquidity_pipeline_pct") or 25)
    reserve_pct = float(alloc.get("operating_reserve_pct") or 15)
    split = {
        "platform_treasury_mn2": round(total * platform_pct / 100, 8),
        "liquidity_pipeline_mn2": round(total * liq_pct / 100, 8),
        "operating_reserve_mn2": round(total * reserve_pct / 100, 8),
        "policy_pct": {"platform": platform_pct, "liquidity": liq_pct, "reserve": reserve_pct},
        "total_fees_mn2": round(total, 8),
    }
    return {"success": True, "allocation": split}
