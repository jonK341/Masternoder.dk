"""
Custodial MN2 instant swap desk (off-chain spread book around Chainz oracle).
"""
from __future__ import annotations

import uuid
from typing import Any, Dict, Optional


def _oracle_usd() -> Optional[float]:
    try:
        from backend.services.mn2_chainz import chainz_ticker_usd
        p = chainz_ticker_usd()
        return float(p) if p and float(p) > 0 else None
    except Exception:
        return None


def _swap_enabled() -> bool:
    try:
        from backend.services.mn2_float_gate import assess
        from backend.services.mn2_proof_of_reserves_service import proof_of_reserves
        por = proof_of_reserves(force=False)
        fg = assess(0)
        return bool(por.get("fully_backed")) and fg.get("verdict") == "green"
    except Exception:
        return False


def quote(side: str, mn2_amount: float, spread_bps: int = 150) -> Dict[str, Any]:
    if not _swap_enabled():
        return {"success": False, "error": "Swap desk disabled until PoR and float gate are green", "code": "swap_disabled"}
    oracle = _oracle_usd()
    if oracle is None:
        return {"success": False, "error": "Oracle unavailable", "code": "no_oracle"}
    amt = float(mn2_amount or 0)
    if amt <= 0:
        return {"success": False, "error": "mn2_amount must be positive"}
    spread = max(0, int(spread_bps)) / 10000.0
    mid = oracle
    if (side or "").strip().lower() == "sell":
        px = mid * (1.0 - spread)
        usd = round(amt * px, 2)
    else:
        px = mid * (1.0 + spread)
        usd = round(amt * px, 2)
    qid = "sq_" + uuid.uuid4().hex[:16]
    return {
        "success": True,
        "quote_id": qid,
        "side": side,
        "mn2_amount": round(amt, 8),
        "oracle_usd_per_mn2": round(mid, 8),
        "price_usd_per_mn2": round(px, 8),
        "usd_total": usd,
        "spread_bps": spread_bps,
        "expires_in_sec": 120,
    }


def execute(user_id: str, quote_id: str, side: str, mn2_amount: float) -> Dict[str, Any]:
    if not _swap_enabled():
        return {"success": False, "error": "Swap desk disabled", "code": "swap_disabled"}
    uid = str(user_id or "").strip()
    if not uid:
        return {"success": False, "error": "user_id required"}
    q = quote(side, mn2_amount)
    if not q.get("success"):
        return q
    amt = float(mn2_amount)
    try:
        from backend.services.unified_points_database import unified_points_db
        from backend.services.mn2_ledger import append_entry
        if (side or "").lower() == "sell":
            bal = unified_points_db.get_all_points(uid)
            mn2 = float((bal.get("points") or {}).get("mn2_balance") or 0)
            if mn2 < amt:
                return {"success": False, "error": "Insufficient MN2"}
            unified_points_db.add_points(uid, "mn2_balance", -amt, source="mn2_swap_sell", metadata={"quote_id": quote_id})
            unified_points_db.add_points(uid, "casino_fiat_balance", q["usd_total"], source="mn2_swap_sell", metadata={"quote_id": quote_id})
            append_entry(uid, "swap_sell", amt, metadata={"quote_id": quote_id, "usd": q["usd_total"]})
        else:
            usd = q["usd_total"]
            bal = unified_points_db.get_all_points(uid)
            fiat = float((bal.get("points") or {}).get("casino_fiat_balance") or 0)
            if fiat < usd:
                return {"success": False, "error": "Insufficient USD balance"}
            unified_points_db.add_points(uid, "casino_fiat_balance", -usd, source="mn2_swap_buy", metadata={"quote_id": quote_id})
            unified_points_db.add_points(uid, "mn2_balance", amt, source="mn2_swap_buy", metadata={"quote_id": quote_id})
            append_entry(uid, "swap_buy", amt, metadata={"quote_id": quote_id, "usd": usd})
    except Exception as e:
        return {"success": False, "error": str(e)}
    return {"success": True, "quote_id": quote_id, **q}
