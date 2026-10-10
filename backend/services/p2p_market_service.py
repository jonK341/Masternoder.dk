"""Internal MN2 ↔ coins order book (orchestrator Plan 1 Phase 3)."""
from __future__ import annotations

import json
import os
import threading
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

_LOCK = threading.RLock()
_BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_ORDERS = os.path.join(_BASE, "data", "p2p_market_orders.json")
_TRADES = os.path.join(_BASE, "data", "p2p_market_trades.jsonl")


def _iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _read_orders() -> List[dict]:
    if not os.path.isfile(_ORDERS):
        return []
    try:
        with open(_ORDERS, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, list) else []
    except Exception:
        return []


def _write_orders(rows: List[dict]) -> None:
    os.makedirs(os.path.dirname(_ORDERS), exist_ok=True)
    tmp = _ORDERS + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(rows, f, indent=2)
    os.replace(tmp, _ORDERS)


def _append_trade(row: dict) -> None:
    os.makedirs(os.path.dirname(_TRADES), exist_ok=True)
    with open(_TRADES, "a", encoding="utf-8") as f:
        f.write(json.dumps(row, default=str) + "\n")


def _emit(event: str, **kwargs) -> None:
    try:
        from backend.services.activity_events_service import emit
        emit(event, **kwargs)
    except Exception:
        pass


def _award_activity_points(user_id: str, points: float = 5.0) -> None:
    try:
        from backend.services.unified_points_database import unified_points_db
        unified_points_db.add_points(
            user_id, "activity_points", float(points),
            source="p2p_market", metadata={"reference": f"market-ap:{user_id}"},
        )
    except Exception:
        pass


def _safe_price(row: dict) -> float:
    try:
        return float(row.get("price_coins_per_mn2") or 0)
    except (TypeError, ValueError):
        return 0.0


def list_orders(side: Optional[str] = None, limit: int = 50) -> Dict[str, Any]:
    rows = [o for o in _read_orders() if o.get("status") == "open"]
    if side:
        rows = [o for o in rows if o.get("side") == side]
    rows.sort(key=_safe_price, reverse=(side == "sell"))
    return {"success": True, "orders": rows[:limit]}


def list_recent_trades(limit: int = 20) -> Dict[str, Any]:
    """Return most recent trades from the jsonl log (newest first)."""
    limit = max(1, min(int(limit or 20), 200))
    if not os.path.isfile(_TRADES):
        return {"success": True, "trades": []}
    rows: List[dict] = []
    try:
        with open(_TRADES, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    row = json.loads(line)
                    if isinstance(row, dict):
                        rows.append(row)
                except Exception:
                    continue
    except Exception:
        return {"success": True, "trades": []}
    return {"success": True, "trades": rows[-limit:][::-1]}


def create_order(user_id: str, side: str, mn2_amount: float, price_coins_per_mn2: float) -> Dict[str, Any]:
    from backend.services.mn2_earn_auth import require_earn_user
    ok, uid_or_err = require_earn_user(user_id)
    if not ok:
        return {"success": False, "error": uid_or_err}
    side = (side or "").strip().lower()
    if side not in ("buy", "sell"):
        return {"success": False, "error": "side must be buy or sell"}
    amt = float(mn2_amount or 0)
    price = float(price_coins_per_mn2 or 0)
    if amt <= 0 or price <= 0:
        return {"success": False, "error": "invalid amount or price"}

    with _LOCK:
        if side == "sell":
            from backend.services.unified_points_database import unified_points_db
            bal = unified_points_db.get_all_points(uid_or_err).get("points") or {}
            mn2 = float(bal.get("mn2_balance") or 0)
            if mn2 < amt:
                return {"success": False, "error": "insufficient_mn2"}
            ref = f"market-lock:{uuid.uuid4().hex[:12]}"
            unified_points_db.add_points(
                uid_or_err, "mn2_balance", -amt, source="p2p_market_lock",
                metadata={"reference": ref},
            )
        order = {
            "order_id": uuid.uuid4().hex[:16],
            "user_id": uid_or_err,
            "side": side,
            "mn2_amount": amt,
            "remaining_mn2": amt,
            "price_coins_per_mn2": price,
            "status": "open",
            "created_at": _iso(),
        }
        rows = _read_orders()
        rows.append(order)
        _write_orders(rows)

    _emit("p2p_market_order", channel="market", user_id=uid_or_err, payload=order)
    _award_activity_points(uid_or_err)
    return {"success": True, "order": order}


def fill_order(buyer_id: str, order_id: str, mn2_amount: Optional[float] = None) -> Dict[str, Any]:
    from backend.services.mn2_earn_auth import require_earn_user
    ok, buyer = require_earn_user(buyer_id)
    if not ok:
        return {"success": False, "error": buyer}

    with _LOCK:
        rows = _read_orders()
        order = next((o for o in rows if o.get("order_id") == order_id and o.get("status") == "open"), None)
        if not order or order.get("side") != "sell":
            return {"success": False, "error": "order_not_found"}
        fill = float(mn2_amount or order.get("remaining_mn2") or 0)
        fill = min(fill, float(order.get("remaining_mn2") or 0))
        if fill <= 0:
            return {"success": False, "error": "invalid_fill"}
        coins = round(fill * float(order.get("price_coins_per_mn2") or 0), 4)
        seller = order.get("user_id")
        ref = f"market-fill:{order_id}:{uuid.uuid4().hex[:8]}"

        from backend.services.unified_points_database import unified_points_db
        from backend.services.mn2_ledger import append_entry

        buyer_bal = unified_points_db.get_all_points(buyer).get("points") or {}
        if float(buyer_bal.get("coins") or 0) < coins:
            return {"success": False, "error": "insufficient_coins"}

        meta = {"reference": ref, "order_id": order_id}
        unified_points_db.add_points(buyer, "coins", -coins, source="p2p_market_buy", metadata=meta)
        unified_points_db.add_points(buyer, "mn2_balance", fill, source="p2p_market_buy", metadata=meta)
        unified_points_db.add_points(seller, "coins", coins, source="p2p_market_sell", metadata=meta)

        append_entry(buyer, "p2p_market_buy", fill, metadata=meta)
        append_entry(seller, "p2p_market_sell", fill, metadata=meta)

        order["remaining_mn2"] = round(float(order["remaining_mn2"]) - fill, 8)
        if order["remaining_mn2"] <= 0:
            order["status"] = "filled"
        trade = {"ts": _iso(), "order_id": order_id, "buyer": buyer, "seller": seller, "mn2": fill, "coins": coins, "ref": ref}
        _append_trade(trade)
        _write_orders(rows)

    _emit("p2p_market_fill", channel="market", payload=trade)
    _award_activity_points(buyer, 10.0)
    _award_activity_points(seller, 10.0)
    return {"success": True, "trade": trade, "order": order}


def cancel_order(user_id: str, order_id: str) -> Dict[str, Any]:
    from backend.services.mn2_earn_auth import require_earn_user
    ok, uid_or_err = require_earn_user(user_id)
    if not ok:
        return {"success": False, "error": uid_or_err}

    with _LOCK:
        rows = _read_orders()
        order = next((o for o in rows if o.get("order_id") == order_id and o.get("status") == "open"), None)
        if not order:
            return {"success": False, "error": "order_not_found"}
        if order.get("user_id") != uid_or_err:
            return {"success": False, "error": "not_order_owner"}

        remaining = float(order.get("remaining_mn2") or 0)
        if order.get("side") == "sell" and remaining > 0:
            ref = f"market-unlock:{order_id}"
            from backend.services.unified_points_database import unified_points_db
            unified_points_db.add_points(
                uid_or_err, "mn2_balance", remaining, source="p2p_market_unlock",
                metadata={"reference": ref, "order_id": order_id},
            )
        order["status"] = "cancelled"
        order["cancelled_at"] = _iso()
        _write_orders(rows)

    _emit("p2p_market_cancel", channel="market", user_id=uid_or_err, payload={"order_id": order_id})
    return {"success": True, "order": order}
