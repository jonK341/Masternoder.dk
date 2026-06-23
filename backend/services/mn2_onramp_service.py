"""
PayPal -> MN2 on-ramp, Model A (custodial).

User pays USD via PayPal; on a verified capture the site treasury credits in-app
MN2 at a time-boxed quoted rate. Purchased MN2 is stakeable/spendable in-app but
NOT withdrawable until a hold/clearance window passes (defeats buy-then-chargeback-
then-withdraw). Chargebacks/disputes trigger clawback of un-withdrawn MN2.

State (data/):
  mn2_onramp_orders.json   - {order_id: order} mutable state (current status)
  mn2_onramp_orders.jsonl  - append-only audit log of every state transition

See docs/MN2_STAKING_PLAN.md sec.17 (Model A). Core rule: never mix reversible
fiat with irreversible crypto in one unclear SKU - holds + KYC + idempotent capture
+ clawback are mandatory.
"""
import os
import json
import uuid
import threading
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional

_LOCK = threading.RLock()

_ORDERS_FILE = "mn2_onramp_orders.json"
_EVENTS_FILE = "mn2_onramp_orders.jsonl"

_OPEN_STATUSES = ("quoted", "pending_payment")
_FUNDED_STATUSES = ("held", "cleared")  # money taken & MN2 credited


# ------------------------------------------------------------------ io utils

def _base_dir() -> str:
    return os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _data_dir() -> str:
    return os.path.join(_base_dir(), "data")


def _path(name: str) -> str:
    return os.path.join(_data_dir(), name)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(dt: Optional[datetime] = None) -> str:
    return (dt or _now()).isoformat().replace("+00:00", "Z")


def _parse_iso(s: Optional[str]) -> Optional[datetime]:
    if not s:
        return None
    try:
        return datetime.fromisoformat(str(s).replace("Z", "+00:00"))
    except Exception:
        return None


def _load_orders() -> Dict[str, Any]:
    p = _path(_ORDERS_FILE)
    if not os.path.exists(p):
        return {}
    try:
        with open(p, "r", encoding="utf-8") as f:
            d = json.load(f)
        return d if isinstance(d, dict) else {}
    except Exception:
        return {}


def _save_orders(d: Dict[str, Any]) -> None:
    os.makedirs(_data_dir(), exist_ok=True)
    p = _path(_ORDERS_FILE)
    tmp = p + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(d, f, indent=2)
    os.replace(tmp, p)


def _audit(order_id: str, status: str, extra: Optional[Dict[str, Any]] = None) -> None:
    os.makedirs(_data_dir(), exist_ok=True)
    row = {"order_id": order_id, "status": status, "at": _iso()}
    if extra:
        row.update(extra)
    try:
        with open(_path(_EVENTS_FILE), "a", encoding="utf-8") as f:
            f.write(json.dumps(row) + "\n")
    except Exception:
        pass


# ------------------------------------------------------------------- config

def get_config() -> Dict[str, Any]:
    try:
        from backend.services import mn2_staking_service as staking
        cfg = staking.get_config().get("onramp", {}) or {}
    except Exception:
        cfg = {}
    defaults = {
        "enabled": True,
        "model": "A",
        "spread_percent": 3.0,
        "quote_ttl_seconds": 60,
        "hold_hours": 72,
        "daily_usd_cap": 200.0,
        "daily_usd_cap_verified": 2000.0,
        "lifetime_usd_cap_unverified": 500.0,
        "min_usd": 1.0,
        "max_usd_per_order": 1000.0,
    }
    merged = dict(defaults)
    merged.update({k: v for k, v in cfg.items() if v is not None})
    return merged


# ------------------------------------------------------------------ pricing

def _mn2_usd_price() -> Optional[float]:
    try:
        from backend.services import mn2_chainz
        return mn2_chainz.chainz_ticker_usd()
    except Exception:
        return None


def _points():
    from backend.services.unified_points_database import unified_points_db
    return unified_points_db


def _is_verified(user_id: str) -> bool:
    try:
        from backend.services.mn2_verification import is_verified
        return bool(is_verified(user_id))
    except Exception:
        return False


def _ledger(user_id: str, entry_type: str, amount: float, metadata: Optional[Dict[str, Any]] = None) -> None:
    try:
        from backend.services.mn2_ledger import append_entry
        append_entry(user_id=user_id, entry_type=entry_type, amount=float(amount), metadata=metadata or {})
    except Exception:
        pass


# --------------------------------------------------------------- KYC / caps

def _usd_spent(user_id: str, since: Optional[datetime] = None) -> float:
    """Sum USD of funded orders for the user (optionally within a window)."""
    total = 0.0
    for o in _load_orders().values():
        if (o.get("user_id") or "") != user_id:
            continue
        if o.get("status") not in _FUNDED_STATUSES + ("charged_back",):
            continue
        funded_at = _parse_iso(o.get("funded_at") or o.get("created_at"))
        if since and (not funded_at or funded_at < since):
            continue
        total += float(o.get("usd_amount", 0) or 0)
    return round(total, 2)


def _cap_check(user_id: str, usd: float) -> Optional[str]:
    """Return an error string if the purchase would breach a cap, else None."""
    cfg = get_config()
    verified = _is_verified(user_id)
    day_ago = _now() - timedelta(hours=24)
    spent_24h = _usd_spent(user_id, day_ago)
    daily_cap = float(cfg["daily_usd_cap_verified"] if verified else cfg["daily_usd_cap"])
    if spent_24h + usd > daily_cap:
        return (f"Daily purchase cap reached (${daily_cap:.0f}/24h"
                f"{'' if verified else ' - verify your account to raise it'}). "
                f"Already ${spent_24h:.2f}.")
    if not verified:
        lifetime_cap = float(cfg["lifetime_usd_cap_unverified"])
        if _usd_spent(user_id) + usd > lifetime_cap:
            return (f"Unverified lifetime purchase cap reached (${lifetime_cap:.0f}). "
                    f"Verify your account to continue.")
    return None


# ----------------------------------------------------------------- quoting

def get_quote(usd: Any, user_id: str) -> Dict[str, Any]:
    cfg = get_config()
    uid = str(user_id or "").strip()
    if not cfg.get("enabled"):
        return {"success": False, "error": "On-ramp is currently disabled"}
    if not uid:
        return {"success": False, "error": "user_id required"}
    try:
        usd_amt = round(float(usd), 2)
    except (TypeError, ValueError):
        return {"success": False, "error": "usd must be a number"}
    if usd_amt < float(cfg["min_usd"]):
        return {"success": False, "error": f"Minimum purchase is ${cfg['min_usd']:.2f}"}
    if usd_amt > float(cfg["max_usd_per_order"]):
        return {"success": False, "error": f"Maximum per order is ${cfg['max_usd_per_order']:.2f}"}

    cap_err = _cap_check(uid, usd_amt)
    if cap_err:
        return {"success": False, "error": cap_err, "code": "cap_exceeded"}

    price = _mn2_usd_price()
    if not price or price <= 0:
        return {"success": False, "error": "MN2 price unavailable right now; try again shortly"}

    spread = float(cfg["spread_percent"]) / 100.0
    mn2_per_usd = (1.0 / price) * (1.0 - spread)
    mn2_amount = round(usd_amt * mn2_per_usd, 8)
    quote_id = "q_" + uuid.uuid4().hex[:16]
    expires_at = _iso(_now() + timedelta(seconds=int(cfg["quote_ttl_seconds"])))

    with _LOCK:
        orders = _load_orders()
        orders[quote_id] = {
            "order_id": quote_id,
            "user_id": uid,
            "usd_amount": usd_amt,
            "mn2_price_usd": round(price, 8),
            "spread_percent": float(cfg["spread_percent"]),
            "quoted_rate_mn2_per_usd": round(mn2_per_usd, 8),
            "mn2_amount": mn2_amount,
            "status": "quoted",
            "paypal_order_id": None,
            "paypal_capture_id": None,
            "hold_until": None,
            "created_at": _iso(),
            "expires_at": expires_at,
        }
        _save_orders(orders)
    _audit(quote_id, "quoted", {"usd": usd_amt, "mn2": mn2_amount})

    return {
        "success": True,
        "quote_id": quote_id,
        "usd_amount": usd_amt,
        "mn2_amount": mn2_amount,
        "mn2_price_usd": round(price, 8),
        "spread_percent": float(cfg["spread_percent"]),
        "rate_mn2_per_usd": round(mn2_per_usd, 8),
        "expires_at": expires_at,
        "hold_hours": float(cfg["hold_hours"]),
        "verified": _is_verified(uid),
        "disclaimer": "Purchased MN2 is held in-app and not withdrawable until the clearance window passes. "
                      "Rate is locked only until the quote expires. Not financial advice.",
    }


# --------------------------------------------------------------- create order

def create_order(quote_id: str, user_id: str,
                 return_url: Optional[str] = None, cancel_url: Optional[str] = None) -> Dict[str, Any]:
    uid = str(user_id or "").strip()
    with _LOCK:
        orders = _load_orders()
        order = orders.get(str(quote_id or "").strip())
        if not order:
            return {"success": False, "error": "Quote not found"}
        if order.get("user_id") != uid:
            return {"success": False, "error": "Quote belongs to another user"}
        if order.get("status") != "quoted":
            return {"success": False, "error": f"Quote is not open (status {order.get('status')})"}
        if _parse_iso(order.get("expires_at")) and _parse_iso(order["expires_at"]) < _now():
            order["status"] = "expired"
            _save_orders(orders)
            _audit(order["order_id"], "expired")
            return {"success": False, "error": "Quote expired; request a new quote", "code": "quote_expired"}

        # Re-check caps at order time (price/cap may have moved since quote)
        cap_err = _cap_check(uid, float(order["usd_amount"]))
        if cap_err:
            return {"success": False, "error": cap_err, "code": "cap_exceeded"}

    try:
        from backend.services.paypal_service import create_order as pp_create
        result = pp_create(
            amount=float(order["usd_amount"]),
            currency="USD",
            item_name=f"MN2 on-ramp ({order['mn2_amount']} MN2)",
            return_url=return_url,
            cancel_url=cancel_url,
            metadata={"item_id": "mn2_onramp", "onramp_quote_id": order["order_id"], "user_id": uid},
        )
    except Exception as exc:
        return {"success": False, "error": f"PayPal order failed: {exc}"}

    if not result.get("success"):
        return {"success": False, "error": result.get("error", "PayPal order creation failed")}

    with _LOCK:
        orders = _load_orders()
        order = orders.get(quote_id)
        order["status"] = "pending_payment"
        order["paypal_order_id"] = result.get("order_id")
        order["updated_at"] = _iso()
        _save_orders(orders)
    _audit(quote_id, "pending_payment", {"paypal_order_id": result.get("order_id")})

    return {
        "success": True,
        "order_id": quote_id,
        "paypal_order_id": result.get("order_id"),
        "approve_url": result.get("approve_url"),
        "usd_amount": order["usd_amount"],
        "mn2_amount": order["mn2_amount"],
    }


# --------------------------------------------------------------- credit/capture

def _credit_order(order: Dict[str, Any], capture_id: str, source: str) -> Dict[str, Any]:
    """Idempotently credit MN2 for a funded order and start the hold window. Caller holds _LOCK."""
    if order.get("status") in _FUNDED_STATUSES:
        return {"success": True, "already": True, **_public(order)}
    if order.get("status") == "charged_back":
        return {"success": False, "error": "Order was charged back"}

    cfg = get_config()
    uid = order["user_id"]
    mn2_amount = float(order["mn2_amount"])
    hold_until = _iso(_now() + timedelta(hours=float(cfg["hold_hours"])))

    _points().add_points(uid, "mn2_balance", mn2_amount, source="mn2_onramp",
                         metadata={"order_id": order["order_id"], "paypal_capture_id": capture_id})
    _ledger(uid, "onramp_purchase", mn2_amount,
            metadata={"order_id": order["order_id"], "paypal_capture_id": capture_id,
                      "usd_amount": order["usd_amount"]})

    order["status"] = "held"
    order["paypal_capture_id"] = capture_id
    order["hold_until"] = hold_until
    order["funded_at"] = _iso()
    order["credit_source"] = source
    order["updated_at"] = _iso()
    return {"success": True, **_public(order)}


def _capture_id_seen(orders: Dict[str, Any], capture_id: str) -> bool:
    return any(o.get("paypal_capture_id") == capture_id for o in orders.values())


def capture(order_id: str, user_id: str) -> Dict[str, Any]:
    """Client-confirm capture path. Verifies with PayPal, idempotent on capture_id."""
    uid = str(user_id or "").strip()
    with _LOCK:
        orders = _load_orders()
        order = orders.get(str(order_id or "").strip())
        if not order:
            return {"success": False, "error": "Order not found"}
        if order.get("user_id") != uid:
            return {"success": False, "error": "Order belongs to another user"}
        if order.get("status") in _FUNDED_STATUSES:
            return {"success": True, "already": True, **_public(order)}
        if order.get("status") == "charged_back":
            return {"success": False, "error": "Order was charged back"}
        paypal_order_id = order.get("paypal_order_id")
    if not paypal_order_id:
        return {"success": False, "error": "Order has no PayPal order id; create the order first"}

    try:
        from backend.services.paypal_service import capture_order as pp_capture
        result = pp_capture(paypal_order_id)
    except Exception as exc:
        return {"success": False, "error": f"PayPal capture failed: {exc}"}
    if not result.get("success"):
        return {"success": False, "error": result.get("error", "PayPal capture not completed")}

    capture_id = result.get("capture_id") or paypal_order_id
    with _LOCK:
        orders = _load_orders()
        order = orders.get(order_id)
        if _capture_id_seen(orders, capture_id) and order.get("paypal_capture_id") != capture_id:
            return {"success": False, "error": "Capture already processed"}
        out = _credit_order(order, capture_id, source="capture")
        _save_orders(orders)
    _audit(order_id, "held", {"paypal_capture_id": capture_id, "source": "capture"})
    return out


# ------------------------------------------------------------------ webhook

def handle_webhook(event: Dict[str, Any], signature_ok: bool) -> Dict[str, Any]:
    """
    Handle PayPal webhook events. Credits only on verified capture-completed; triggers
    clawback on denial/refund/reversal/dispute. Idempotent on capture id.
    """
    if not signature_ok:
        return {"success": False, "error": "Webhook signature not verified"}

    event_type = str(event.get("event_type") or "").upper()
    resource = event.get("resource") or {}

    # Find our order via custom_id / supplementary data / capture id
    def _find_order(orders: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        custom = (resource.get("custom_id")
                  or (resource.get("supplementary_data", {}) or {}).get("related_ids", {}).get("order_id"))
        pp_order = (resource.get("supplementary_data", {}) or {}).get("related_ids", {}).get("order_id")
        cap_id = resource.get("id")
        for o in orders.values():
            if custom and o.get("order_id") == custom:
                return o
            if pp_order and o.get("paypal_order_id") == pp_order:
                return o
            if cap_id and o.get("paypal_capture_id") == cap_id:
                return o
        return None

    with _LOCK:
        orders = _load_orders()
        order = _find_order(orders)
        if not order:
            return {"success": True, "ignored": True, "reason": "no matching on-ramp order"}

        if event_type in ("PAYMENT.CAPTURE.COMPLETED",):
            capture_id = resource.get("id") or order.get("paypal_order_id")
            if order.get("status") in _FUNDED_STATUSES and order.get("paypal_capture_id") == capture_id:
                return {"success": True, "already": True}
            if _capture_id_seen(orders, capture_id) and order.get("paypal_capture_id") != capture_id:
                return {"success": True, "already": True}
            _credit_order(order, capture_id, source="webhook")
            _save_orders(orders)
            _audit(order["order_id"], "held", {"paypal_capture_id": capture_id, "source": "webhook"})
            return {"success": True, "credited": True, "order_id": order["order_id"]}

        if event_type in ("PAYMENT.CAPTURE.DENIED", "PAYMENT.CAPTURE.REFUNDED",
                          "PAYMENT.CAPTURE.REVERSED", "CUSTOMER.DISPUTE.CREATED",
                          "CUSTOMER.DISPUTE.UPDATED"):
            res = _clawback(order, reason=event_type)
            _save_orders(orders)
            _audit(order["order_id"], "charged_back", {"reason": event_type, **res})
            return {"success": True, "clawback": res, "order_id": order["order_id"]}

    return {"success": True, "ignored": True, "event_type": event_type}


def _clawback(order: Dict[str, Any], reason: str) -> Dict[str, Any]:
    """Reverse an on-ramp credit. Deducts up to mn2_amount of un-withdrawn MN2. Caller holds _LOCK."""
    if order.get("status") == "charged_back":
        return {"already": True, "clawed_back_mn2": 0.0}
    uid = order["user_id"]
    mn2_amount = float(order.get("mn2_amount", 0) or 0)
    try:
        res = _points().get_all_points(uid)
        bal = float((res.get("points") or {}).get("mn2_balance", 0) or 0)
    except Exception:
        bal = 0.0
    clawed = round(min(mn2_amount, max(0.0, bal)), 8)
    if clawed > 0:
        _points().add_points(uid, "mn2_balance", -clawed, source="mn2_onramp_clawback",
                             metadata={"order_id": order["order_id"], "reason": reason})
        _ledger(uid, "onramp_clawback", clawed,
                metadata={"order_id": order["order_id"], "reason": reason})
    order["status"] = "charged_back"
    order["clawed_back_mn2"] = clawed
    order["shortfall_mn2"] = round(mn2_amount - clawed, 8)
    order["chargeback_reason"] = reason
    order["updated_at"] = _iso()
    # Flag account for review when we couldn't fully claw back
    if mn2_amount - clawed > 0:
        _flag_account(uid, order["order_id"], round(mn2_amount - clawed, 8), reason)
    return {"clawed_back_mn2": clawed, "shortfall_mn2": round(mn2_amount - clawed, 8)}


def _flag_account(user_id: str, order_id: str, shortfall: float, reason: str) -> None:
    try:
        path = _path("mn2_onramp_flags.jsonl")
        with open(path, "a", encoding="utf-8") as f:
            f.write(json.dumps({"user_id": user_id, "order_id": order_id,
                                "shortfall_mn2": shortfall, "reason": reason, "at": _iso()}) + "\n")
    except Exception:
        pass


# ------------------------------------------------------------------- holds

def held_amount(user_id: str) -> float:
    """Sum of on-ramp MN2 still inside the hold window (not yet withdrawable)."""
    uid = str(user_id or "").strip()
    now = _now()
    total = 0.0
    for o in _load_orders().values():
        if o.get("user_id") != uid or o.get("status") != "held":
            continue
        hold_until = _parse_iso(o.get("hold_until"))
        if hold_until and hold_until > now:
            total += float(o.get("mn2_amount", 0) or 0)
    return round(total, 8)


def clear_matured() -> Dict[str, Any]:
    """Ops: move held orders whose hold window has passed to 'cleared' (withdrawable)."""
    now = _now()
    cleared = 0
    with _LOCK:
        orders = _load_orders()
        for o in orders.values():
            if o.get("status") != "held":
                continue
            hold_until = _parse_iso(o.get("hold_until"))
            if hold_until and hold_until <= now:
                o["status"] = "cleared"
                o["cleared_at"] = _iso()
                o["updated_at"] = _iso()
                cleared += 1
                _audit(o["order_id"], "cleared")
        if cleared:
            _save_orders(orders)
    return {"success": True, "cleared": cleared}


# -------------------------------------------------------------------- status

def _public(order: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "order_id": order.get("order_id"),
        "status": order.get("status"),
        "usd_amount": order.get("usd_amount"),
        "mn2_amount": order.get("mn2_amount"),
        "rate_mn2_per_usd": order.get("quoted_rate_mn2_per_usd"),
        "hold_until": order.get("hold_until"),
        "created_at": order.get("created_at"),
        "withdrawable": order.get("status") == "cleared",
    }


def get_status(order_id: str, user_id: Optional[str] = None) -> Dict[str, Any]:
    order = _load_orders().get(str(order_id or "").strip())
    if not order:
        return {"success": False, "error": "Order not found"}
    if user_id and order.get("user_id") != str(user_id).strip():
        return {"success": False, "error": "Order belongs to another user"}
    return {"success": True, **_public(order)}


def get_user_orders(user_id: str, limit: int = 50) -> Dict[str, Any]:
    uid = str(user_id or "").strip()
    rows = [_public(o) for o in _load_orders().values() if o.get("user_id") == uid]
    rows.sort(key=lambda r: r.get("created_at") or "", reverse=True)
    return {"success": True, "orders": rows[: max(1, min(int(limit or 50), 500))],
            "held_mn2": held_amount(uid)}


# --------------------------------------------------------------------- stats

def onramp_stats() -> Dict[str, Any]:
    orders = list(_load_orders().values())
    now = _now()
    day_ago = now - timedelta(hours=24)
    vol_24h = 0.0
    mn2_24h = 0.0
    rates: List[float] = []
    open_orders = 0
    funded = 0
    charged_back = 0
    for o in orders:
        status = o.get("status")
        if status in _OPEN_STATUSES:
            open_orders += 1
        if status in _FUNDED_STATUSES:
            funded += 1
            funded_at = _parse_iso(o.get("funded_at"))
            if funded_at and funded_at >= day_ago:
                vol_24h += float(o.get("usd_amount", 0) or 0)
                mn2_24h += float(o.get("mn2_amount", 0) or 0)
                r = o.get("quoted_rate_mn2_per_usd")
                if r:
                    rates.append(float(r))
        if status == "charged_back":
            charged_back += 1
    denom = funded + charged_back
    return {
        "onramp_volume_usd_24h": round(vol_24h, 2),
        "mn2_sold_24h": round(mn2_24h, 8),
        "avg_onramp_rate_mn2_per_usd": round(sum(rates) / len(rates), 8) if rates else None,
        "open_orders": open_orders,
        "funded_orders": funded,
        "chargeback_rate": round(charged_back / denom, 4) if denom else 0.0,
    }
