"""Ops: unlock internal-exchange MN2 locked in open orders (ledger liquidity)."""
from __future__ import annotations

from typing import Any, Dict, List, Optional

LIQUIDITY_USER = "exchange_agent_casino_liquidity"


def _open_mn2_coin_sells(user_id: Optional[str] = None) -> List[Dict[str, Any]]:
    from backend.services.crypto_exchange_service import _read_orders

    uid = (user_id or LIQUIDITY_USER).strip()
    rows = _read_orders()
    return [
        o
        for o in rows
        if o.get("status") == "open"
        and str(o.get("user_id") or "") == uid
        and str(o.get("side") or "").lower() == "sell"
        and str(o.get("symbol") or "").upper() == "MN2"
        and str(o.get("quote") or "").upper() == "COINS"
    ]


def liquidity_lock_snapshot(user_id: Optional[str] = None) -> Dict[str, Any]:
    orders = _open_mn2_coin_sells(user_id)
    locked = round(sum(float(o.get("remaining") or 0) for o in orders), 8)
    from backend.services.crypto_exchange_service import get_wallet

    wallet = get_wallet(user_id or LIQUIDITY_USER)
    return {
        "success": True,
        "user_id": user_id or LIQUIDITY_USER,
        "open_orders": len(orders),
        "locked_mn2_in_orders": locked,
        "wallet_mn2_balance": wallet.get("mn2_balance"),
        "wallet_coins_balance": wallet.get("coins_balance"),
    }


def free_liquidity_from_open_sells(
    *,
    user_id: Optional[str] = None,
    dry_run: bool = False,
    limit: int = 0,
) -> Dict[str, Any]:
    """Cancel open MN2→COINS sells and return remaining size to the agent wallet (ledger)."""
    uid = (user_id or LIQUIDITY_USER).strip()
    before = liquidity_lock_snapshot(uid)
    orders = _open_mn2_coin_sells(uid)
    if limit > 0:
        orders = orders[: int(limit)]

    if dry_run:
        unlock = round(sum(float(o.get("remaining") or 0) for o in orders), 8)
        return {
            "success": True,
            "dry_run": True,
            "would_cancel": len(orders),
            "would_unlock_mn2": unlock,
            "before": before,
        }

    from datetime import datetime, timezone

    from backend.services.crypto_exchange_service import (
        _LOCK,
        _adjust_balance,
        _iso,
        _write_orders,
        _read_orders,
        get_wallet,
    )

    cancelled: List[Dict[str, Any]] = []
    unlocked = 0.0
    errors: List[str] = []

    with _LOCK:
        rows = _read_orders()
        open_ids = {o.get("order_id") for o in orders}
        for order in rows:
            if order.get("order_id") not in open_ids or order.get("status") != "open":
                continue
            rem = float(order.get("remaining") or 0)
            sym = str(order.get("symbol") or "MN2").upper()
            try:
                if rem > 0:
                    _adjust_balance(uid, sym, rem)
                    unlocked += rem
                order["status"] = "cancelled"
                order["cancelled_at"] = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
                order["cancel_reason"] = "collateral_liquidity_free_ops"
                cancelled.append(
                    {"order_id": order.get("order_id"), "unlocked_mn2": round(rem, 8)}
                )
            except Exception as exc:
                errors.append(f"{order.get('order_id')}: {exc}")
        _write_orders(rows)

    after_wallet = get_wallet(uid)
    return {
        "success": len(errors) == 0 and (cancelled or not orders),
        "dry_run": False,
        "cancelled_count": len(cancelled),
        "unlocked_mn2": round(unlocked, 8),
        "errors": errors,
        "before": before,
        "after": {
            "wallet_mn2_balance": after_wallet.get("mn2_balance"),
            "wallet_coins_balance": after_wallet.get("coins_balance"),
            **liquidity_lock_snapshot(uid),
        },
    }
