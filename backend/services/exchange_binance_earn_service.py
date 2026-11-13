"""Binance Flexible Earn unlock — redeem LD* / earn positions back to spot.

The profit daemon saw Binance free USDC near zero while balances sat in LDADA,
LDALGO, … Flexible Earn receipts. Spot market sells cannot raise quote from those
wrappers; redeem first, then the courier/hunter can sell the underlying.
"""
from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from backend.services import crypto_exchange_service as ex

_LEDGER_PATH = os.path.join(ex._DATA_DIR, "binance_earn_ledger.jsonl")


def _iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _cfg_float(key: str, default: float) -> float:
    raw = os.environ.get(key, "").strip()
    if not raw:
        return float(default)
    try:
        return float(raw)
    except ValueError:
        return float(default)


def earn_unlock_enabled() -> bool:
    raw = os.environ.get("BINANCE_EARN_UNLOCK", "1").strip().lower()
    return raw not in ("0", "false", "no", "off")


def _append(kind: str, **fields: Any) -> None:
    row = {"ts": _iso(), "kind": kind, "venue": "binance"}
    row.update(fields)
    try:
        ex._append_jsonl(_LEDGER_PATH, row)
    except Exception:
        pass


def _ld_underlying(asset: str) -> Optional[str]:
    """Map LDADA → ADA, LDALGO → ALGO, else None."""
    s = str(asset or "").upper()
    if s.startswith("LD") and len(s) > 2:
        return s[2:]
    return None


def list_ld_balances(bals: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
    from backend.services import exchange_venue_api_service as vapi
    from backend.services import external_exchange_connector_service as conn

    bals = bals if bals is not None else (vapi.parse_spot_balances("binance", dry_run=False, force_refresh=True) or {})
    rows: List[Dict[str, Any]] = []
    for asset, raw in (bals or {}).items():
        under = _ld_underlying(str(asset))
        if not under:
            continue
        try:
            qty = float(raw or 0)
        except (TypeError, ValueError):
            continue
        if qty <= 0:
            continue
        tick = conn.fetch_ticker("binance", under) or {}
        bid = float(tick.get("bid") or 0)
        rows.append({
            "ld_asset": str(asset).upper(),
            "asset": under,
            "qty": qty,
            "bid": bid,
            "usd": round(qty * bid, 4) if bid > 0 else 0.0,
        })
    rows.sort(key=lambda r: -float(r.get("usd") or 0))
    return rows


def _sapi(method: str, path: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Live earn calls use the withdraw sapi signer but skip the withdraw live gate."""
    from backend.services.exchange_binance_withdraw_service import _signed_sapi_request
    from backend.services import exchange_arbitrage_service as arb

    dry = not arb.live_enabled()
    return _signed_sapi_request(method, path, params or {}, dry_run=dry, skip_live_gate=True)


def list_flexible_positions() -> Dict[str, Any]:
    res = _sapi("GET", "/sapi/v1/simple-earn/flexible/position", {"current": 1, "size": 100})
    body = res.get("body") if isinstance(res.get("body"), (dict, list)) else res.get("body")
    rows: List[Dict[str, Any]] = []
    if isinstance(body, dict):
        rows = list(body.get("rows") or body.get("list") or [])
    elif isinstance(body, list):
        rows = body
    return {"success": bool(res.get("success")), "positions": rows, "raw": res}


def redeem_flexible(*, product_id: str, amount: float, asset: str = "") -> Dict[str, Any]:
    params: Dict[str, Any] = {
        "productId": str(product_id),
        "amount": f"{float(amount):.8f}".rstrip("0").rstrip(".") if float(amount) > 0 else "0",
    }
    res = _sapi("POST", "/sapi/v1/simple-earn/flexible/redeem", params)
    ok = bool(res.get("success"))
    _append(
        "redeem",
        product_id=product_id,
        asset=asset,
        amount=amount,
        success=ok,
        error=None if ok else (res.get("binance_msg") or res.get("error")),
        simulated=bool(res.get("simulated")),
    )
    return {
        "success": ok,
        "product_id": product_id,
        "asset": asset,
        "amount": amount,
        "response": res,
    }


def unlock_earn_to_spot(*, target_usd: float = 20.0, max_redeems: int = 3) -> Dict[str, Any]:
    """Redeem Flexible Earn / LD wrappers until ~target_usd of spot is freed."""
    if not earn_unlock_enabled():
        return {"success": False, "skipped": True, "reason": "earn_unlock_disabled"}

    target = max(3.0, float(target_usd or 0))
    ld_rows = list_ld_balances()
    pos = list_flexible_positions()
    positions = pos.get("positions") if pos.get("success") else []
    # Index positions by asset.
    by_asset: Dict[str, Dict[str, Any]] = {}
    for row in positions or []:
        if not isinstance(row, dict):
            continue
        asset = str(row.get("asset") or "").upper()
        pid = str(row.get("productId") or row.get("product_id") or "")
        try:
            total = float(row.get("totalAmount") or 0)
        except (TypeError, ValueError):
            total = 0.0
        if asset and pid and total > 0:
            by_asset[asset] = {"product_id": pid, "amount": total, "row": row}

    actions: List[Dict[str, Any]] = []
    freed_usd = 0.0

    # Prefer redeeming assets that appear as LD* in spot and have a productId.
    plan: List[Dict[str, Any]] = []
    for ld in ld_rows:
        asset = str(ld.get("asset") or "")
        info = by_asset.get(asset)
        if not info:
            # No position row — still record for diagnostics; cannot redeem without productId.
            plan.append({**ld, "product_id": None, "redeem_qty": float(ld.get("qty") or 0)})
            continue
        qty = min(float(ld.get("qty") or 0), float(info["amount"]))
        plan.append({**ld, "product_id": info["product_id"], "redeem_qty": qty})

    # Also redeem plain flexible positions not mirrored as LD* if still short of target.
    for asset, info in by_asset.items():
        if any(p.get("asset") == asset for p in plan):
            continue
        plan.append({
            "asset": asset,
            "ld_asset": f"LD{asset}",
            "qty": info["amount"],
            "usd": 0.0,
            "product_id": info["product_id"],
            "redeem_qty": float(info["amount"]),
            "bid": 0.0,
        })

    for row in plan:
        if freed_usd >= target or len(actions) >= max(1, int(max_redeems)):
            break
        pid = row.get("product_id")
        qty = float(row.get("redeem_qty") or 0)
        if not pid or qty <= 0:
            actions.append({"asset": row.get("asset"), "skipped": True, "reason": "missing_product_id"})
            continue
        # Cap redeem by USD target when we know a bid.
        bid = float(row.get("bid") or 0)
        if bid > 0:
            need_qty = (target - freed_usd) / bid
            qty = min(qty, need_qty * 1.05)
        if qty <= 0:
            continue
        res = redeem_flexible(product_id=str(pid), amount=qty, asset=str(row.get("asset") or ""))
        actions.append(res)
        if res.get("success"):
            if bid > 0:
                freed_usd += qty * bid
            else:
                freed_usd += _cfg_float("BINANCE_EARN_UNLOCK_ASSUME_USD", 5.0)

    from backend.services import exchange_venue_api_service as vapi

    vapi.invalidate_venue_balance_cache("binance")
    ok = any(bool(a.get("success")) for a in actions)
    out = {
        "success": ok,
        "target_usd": target,
        "freed_usd_est": round(freed_usd, 2),
        "ld_balances": ld_rows[:8],
        "position_count": len(positions or []),
        "actions": actions,
        "reason": "redeemed" if ok else ("no_product_id" if plan else "no_ld_inventory"),
    }
    _append("unlock", **{k: v for k, v in out.items() if k != "actions"}, action_n=len(actions))
    return out
