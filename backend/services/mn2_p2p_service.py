"""
MN2 P2P marketplace, Model B (guarded).

Sellers escrow in-app MN2 and list it for sale priced in USD. Buyers pay via PayPal;
on a verified capture the escrowed MN2 transfers to the buyer under a clearance hold,
and the seller's USD payout is released ONLY after the buyer's chargeback window clears
(so a buyer chargeback is covered by clawing back the buyer's still-held MN2 and
returning the escrow to the seller).

Safety (mandatory, per docs/MN2_STAKING_PLAN.md sec.17):
- Seller escrow: MN2 leaves the seller's balance when listed (cannot double-spend).
- Sellers may only sell *cleared* MN2 (not coins still inside an on-ramp hold).
- Buyer hold: purchased MN2 is stakeable/spendable but not withdrawable until cleared.
- KYC/AML USD caps (shared tiering with the on-ramp).
- Webhook signature verified; idempotent on PayPal capture_id.
- Dispute -> clawback buyer MN2 + return escrow to seller; reserve/flag on shortfall.
- Disabled by default; enable only after on-ramp Model A is proven.

State (data/):
  mn2_p2p_listings.json   - {listing_id: listing}
  mn2_p2p_orders.json     - {order_id: order}
  mn2_p2p_payouts.json    - {seller_id: {balance_usd, pending_usd}}
  mn2_p2p_events.jsonl    - append-only audit log
"""
import os
import json
import uuid
import threading
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional

_LOCK = threading.RLock()

_LISTINGS_FILE = "mn2_p2p_listings.json"
_ORDERS_FILE = "mn2_p2p_orders.json"
_PAYOUTS_FILE = "mn2_p2p_payouts.json"
_EVENTS_FILE = "mn2_p2p_events.jsonl"

_OPEN_ORDER = ("pending_payment",)
_FUNDED_ORDER = ("held", "cleared")


# ----------------------------------------------------------------- io helpers

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


def _read(name: str) -> Dict[str, Any]:
    p = _path(name)
    if not os.path.exists(p):
        return {}
    try:
        with open(p, "r", encoding="utf-8") as f:
            d = json.load(f)
        return d if isinstance(d, dict) else {}
    except Exception:
        return {}


def _write(name: str, d: Dict[str, Any]) -> None:
    os.makedirs(_data_dir(), exist_ok=True)
    p = _path(name)
    tmp = p + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(d, f, indent=2)
    os.replace(tmp, p)


def _audit(kind: str, ref_id: str, status: str, extra: Optional[Dict[str, Any]] = None) -> None:
    row = {"kind": kind, "id": ref_id, "status": status, "at": _iso()}
    if extra:
        row.update(extra)
    try:
        os.makedirs(_data_dir(), exist_ok=True)
        with open(_path(_EVENTS_FILE), "a", encoding="utf-8") as f:
            f.write(json.dumps(row) + "\n")
    except Exception:
        pass


# ------------------------------------------------------------------- config

def get_config() -> Dict[str, Any]:
    try:
        from backend.services import mn2_staking_service as staking
        cfg = staking.get_config().get("p2p", {}) or {}
    except Exception:
        cfg = {}
    defaults = {
        "enabled": False, "model": "B", "platform_fee_percent": 2.5, "buyer_spread_percent": 1.0,
        "min_listing_mn2": 1.0, "max_listing_mn2": 5000.0, "max_open_listings_per_seller": 5,
        "requires_seller_verification": True, "seller_must_sell_cleared_only": True,
        "hold_hours": 72, "order_ttl_seconds": 900,
        "daily_usd_cap": 200.0, "daily_usd_cap_verified": 2000.0, "lifetime_usd_cap_unverified": 500.0,
    }
    merged = dict(defaults)
    merged.update({k: v for k, v in cfg.items() if v is not None})
    return merged


# ---------------------------------------------------- shared helpers (reuse on-ramp)

def _points():
    from backend.services.unified_points_database import unified_points_db
    return unified_points_db


def _balance(user_id: str) -> float:
    try:
        res = _points().get_all_points(str(user_id).strip())
        return float((res.get("points") or {}).get("mn2_balance", 0) or 0)
    except Exception:
        return 0.0


def _mn2_usd_price() -> Optional[float]:
    try:
        from backend.services import mn2_chainz
        return mn2_chainz.chainz_ticker_usd()
    except Exception:
        return None


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


def _onramp_held(user_id: str) -> float:
    try:
        from backend.services.mn2_onramp_service import held_amount
        return float(held_amount(user_id) or 0)
    except Exception:
        return 0.0


# ----------------------------------------------------------------- KYC / caps

def _usd_spent(buyer_id: str, since: Optional[datetime] = None) -> float:
    total = 0.0
    for o in _read(_ORDERS_FILE).values():
        if o.get("buyer_id") != buyer_id:
            continue
        if o.get("status") not in _FUNDED_ORDER + ("charged_back",):
            continue
        funded_at = _parse_iso(o.get("funded_at") or o.get("created_at"))
        if since and (not funded_at or funded_at < since):
            continue
        total += float(o.get("usd_amount", 0) or 0)
    return round(total, 2)


def _cap_check(buyer_id: str, usd: float) -> Optional[str]:
    cfg = get_config()
    verified = _is_verified(buyer_id)
    spent_24h = _usd_spent(buyer_id, _now() - timedelta(hours=24))
    daily_cap = float(cfg["daily_usd_cap_verified"] if verified else cfg["daily_usd_cap"])
    if spent_24h + usd > daily_cap:
        return (f"Daily purchase cap reached (${daily_cap:.0f}/24h"
                f"{'' if verified else ' - verify to raise it'}). Already ${spent_24h:.2f}.")
    if not verified and _usd_spent(buyer_id) + usd > float(cfg["lifetime_usd_cap_unverified"]):
        return f"Unverified lifetime cap reached (${cfg['lifetime_usd_cap_unverified']:.0f}). Verify to continue."
    return None


# --------------------------------------------------------------- seller: list

def create_listing(seller_id: str, mn2_amount: Any, price_usd_per_mn2: Any) -> Dict[str, Any]:
    cfg = get_config()
    sid = str(seller_id or "").strip()
    if not cfg.get("enabled"):
        return {"success": False, "error": "P2P market is currently disabled"}
    if not sid:
        return {"success": False, "error": "seller_id required"}
    try:
        amt = round(float(mn2_amount), 8)
        price = round(float(price_usd_per_mn2), 8)
    except (TypeError, ValueError):
        return {"success": False, "error": "mn2_amount and price_usd_per_mn2 must be numbers"}
    if amt < float(cfg["min_listing_mn2"]):
        return {"success": False, "error": f"Minimum listing is {cfg['min_listing_mn2']} MN2"}
    if amt > float(cfg["max_listing_mn2"]):
        return {"success": False, "error": f"Maximum listing is {cfg['max_listing_mn2']} MN2"}
    if price <= 0:
        return {"success": False, "error": "price_usd_per_mn2 must be positive"}
    if cfg.get("requires_seller_verification") and not _is_verified(sid):
        return {"success": False, "error": "Seller account verification required to list",
                "code": "verification_required"}

    with _LOCK:
        listings = _read(_LISTINGS_FILE)
        open_count = sum(1 for l in listings.values()
                         if l.get("seller_id") == sid and l.get("status") == "open")
        if open_count >= int(cfg["max_open_listings_per_seller"]):
            return {"success": False, "error": f"Max {cfg['max_open_listings_per_seller']} open listings per seller"}

        bal = _balance(sid)
        sellable = bal - (_onramp_held(sid) if cfg.get("seller_must_sell_cleared_only") else 0)
        if sellable < amt:
            return {"success": False,
                    "error": "Insufficient cleared MN2 to escrow (coins inside an on-ramp hold cannot be sold)"}

        # Escrow: MN2 leaves seller balance now
        _points().add_points(sid, "mn2_balance", -amt, source="mn2_p2p_escrow")
        _ledger(sid, "p2p_sell_escrow", amt, metadata={"price_usd_per_mn2": price})

        listing_id = "l_" + uuid.uuid4().hex[:16]
        listings[listing_id] = {
            "listing_id": listing_id, "seller_id": sid,
            "mn2_total": amt, "mn2_available": amt, "mn2_reserved": 0.0,
            "price_usd_per_mn2": price, "status": "open", "created_at": _iso(),
        }
        _write(_LISTINGS_FILE, listings)
    _audit("listing", listing_id, "open", {"seller_id": sid, "mn2": amt, "price": price})
    return {"success": True, **_public_listing(listings[listing_id])}


def cancel_listing(seller_id: str, listing_id: str) -> Dict[str, Any]:
    sid = str(seller_id or "").strip()
    with _LOCK:
        listings = _read(_LISTINGS_FILE)
        listing = listings.get(str(listing_id or "").strip())
        if not listing:
            return {"success": False, "error": "Listing not found"}
        if listing.get("seller_id") != sid:
            return {"success": False, "error": "Listing belongs to another seller"}
        if listing.get("status") not in ("open",):
            return {"success": False, "error": f"Listing not cancellable (status {listing.get('status')})"}
        if float(listing.get("mn2_reserved", 0) or 0) > 0:
            return {"success": False, "error": "Listing has a pending order; try again shortly"}
        refund = round(float(listing.get("mn2_available", 0) or 0), 8)
        if refund > 0:
            _points().add_points(sid, "mn2_balance", refund, source="mn2_p2p_escrow_return")
            _ledger(sid, "p2p_escrow_return", refund, metadata={"listing_id": listing_id})
        listing["mn2_available"] = 0.0
        listing["status"] = "cancelled"
        listing["updated_at"] = _iso()
        _write(_LISTINGS_FILE, listings)
    _audit("listing", listing_id, "cancelled", {"refunded_mn2": refund})
    return {"success": True, "listing_id": listing_id, "refunded_mn2": refund, "status": "cancelled"}


# --------------------------------------------------------------- buyer: order

def create_purchase(buyer_id: str, listing_id: str, mn2_amount: Any = None,
                    return_url: Optional[str] = None, cancel_url: Optional[str] = None) -> Dict[str, Any]:
    cfg = get_config()
    bid = str(buyer_id or "").strip()
    if not cfg.get("enabled"):
        return {"success": False, "error": "P2P market is currently disabled"}
    if not bid:
        return {"success": False, "error": "buyer_id required"}

    with _LOCK:
        listings = _read(_LISTINGS_FILE)
        listing = listings.get(str(listing_id or "").strip())
        if not listing or listing.get("status") != "open":
            return {"success": False, "error": "Listing not available"}
        if listing.get("seller_id") == bid:
            return {"success": False, "error": "Cannot buy your own listing"}
        available = round(float(listing.get("mn2_available", 0) or 0), 8)
        try:
            want = round(float(mn2_amount), 8) if mn2_amount is not None else available
        except (TypeError, ValueError):
            return {"success": False, "error": "mn2_amount must be a number"}
        if want <= 0:
            return {"success": False, "error": "mn2_amount must be positive"}
        if want > available:
            return {"success": False, "error": f"Only {available} MN2 available in this listing"}

        price = float(listing["price_usd_per_mn2"])
        spread = float(cfg["buyer_spread_percent"]) / 100.0
        usd_amount = round(want * price * (1.0 + spread), 2)
        if usd_amount < 1.0:
            return {"success": False, "error": "Order total must be at least $1.00"}
        cap_err = _cap_check(bid, usd_amount)
        if cap_err:
            return {"success": False, "error": cap_err, "code": "cap_exceeded"}

        fee = round(usd_amount * float(cfg["platform_fee_percent"]) / 100.0, 2)
        usd_seller = round(usd_amount - fee, 2)

        # Reserve the MN2 against the listing so it can't be double-sold
        listing["mn2_available"] = round(available - want, 8)
        listing["mn2_reserved"] = round(float(listing.get("mn2_reserved", 0) or 0) + want, 8)
        if listing["mn2_available"] <= 0 and listing["mn2_reserved"] <= 0:
            listing["status"] = "sold_out"

        order_id = "po_" + uuid.uuid4().hex[:16]
        order = {
            "order_id": order_id, "listing_id": listing_id, "buyer_id": bid,
            "seller_id": listing["seller_id"], "mn2_amount": want,
            "price_usd_per_mn2": price, "usd_amount": usd_amount,
            "platform_fee_usd": fee, "usd_seller": usd_seller,
            "status": "pending_payment", "paypal_order_id": None, "paypal_capture_id": None,
            "buyer_hold_until": None, "payout_release_at": None,
            "created_at": _iso(),
            "expires_at": _iso(_now() + timedelta(seconds=int(cfg["order_ttl_seconds"]))),
        }
        orders = _read(_ORDERS_FILE)
        orders[order_id] = order
        _write(_LISTINGS_FILE, listings)
        _write(_ORDERS_FILE, orders)

    try:
        from backend.services.paypal_service import create_order as pp_create
        result = pp_create(
            amount=usd_amount, currency="USD",
            item_name=f"MN2 P2P purchase ({want} MN2)",
            return_url=return_url, cancel_url=cancel_url,
            metadata={"item_id": "mn2_p2p", "p2p_order_id": order_id, "user_id": bid},
        )
    except Exception as exc:
        _release_reservation(order_id, reason="paypal_error")
        return {"success": False, "error": f"PayPal order failed: {exc}"}
    if not result.get("success"):
        _release_reservation(order_id, reason="paypal_failed")
        return {"success": False, "error": result.get("error", "PayPal order creation failed")}

    with _LOCK:
        orders = _read(_ORDERS_FILE)
        order = orders.get(order_id)
        order["paypal_order_id"] = result.get("order_id")
        order["updated_at"] = _iso()
        _write(_ORDERS_FILE, orders)
    _audit("order", order_id, "pending_payment", {"paypal_order_id": result.get("order_id"), "usd": usd_amount})
    return {"success": True, "order_id": order_id, "paypal_order_id": result.get("order_id"),
            "approve_url": result.get("approve_url"), "mn2_amount": want, "usd_amount": usd_amount}


def _release_reservation(order_id: str, reason: str) -> None:
    """Return a pending order's reserved MN2 to the listing's available pool. Caller may not hold lock."""
    with _LOCK:
        orders = _read(_ORDERS_FILE)
        order = orders.get(order_id)
        if not order or order.get("status") not in _OPEN_ORDER:
            return
        listings = _read(_LISTINGS_FILE)
        listing = listings.get(order.get("listing_id"))
        want = float(order.get("mn2_amount", 0) or 0)
        if listing:
            listing["mn2_reserved"] = round(max(0.0, float(listing.get("mn2_reserved", 0) or 0) - want), 8)
            listing["mn2_available"] = round(float(listing.get("mn2_available", 0) or 0) + want, 8)
            if listing.get("status") == "sold_out" and listing["mn2_available"] > 0:
                listing["status"] = "open"
            _write(_LISTINGS_FILE, listings)
        order["status"] = "expired"
        order["updated_at"] = _iso()
        _write(_ORDERS_FILE, orders)
    _audit("order", order_id, "expired", {"reason": reason})


# --------------------------------------------------------- credit / capture

def _settle_capture(orders: Dict[str, Any], listings: Dict[str, Any], order: Dict[str, Any],
                    capture_id: str, source: str) -> Dict[str, Any]:
    """Transfer escrow to buyer under hold; record seller payout pending. Caller holds _LOCK."""
    if order.get("status") in _FUNDED_ORDER:
        return {"success": True, "already": True, **_public_order(order)}
    if order.get("status") == "charged_back":
        return {"success": False, "error": "Order was charged back"}

    cfg = get_config()
    bid = order["buyer_id"]
    want = float(order["mn2_amount"])
    hold_until = _iso(_now() + timedelta(hours=float(cfg["hold_hours"])))

    # Convert listing reservation into a completed sale
    listing = listings.get(order.get("listing_id"))
    if listing:
        listing["mn2_reserved"] = round(max(0.0, float(listing.get("mn2_reserved", 0) or 0) - want), 8)
        if listing.get("mn2_available", 0) <= 0 and listing.get("mn2_reserved", 0) <= 0:
            listing["status"] = "sold_out"

    # Credit buyer (held / not withdrawable until cleared)
    _points().add_points(bid, "mn2_balance", want, source="mn2_p2p_buy",
                         metadata={"order_id": order["order_id"], "paypal_capture_id": capture_id})
    _ledger(bid, "p2p_buy", want, metadata={"order_id": order["order_id"], "usd_amount": order["usd_amount"]})

    # Seller payout is pending; released only after buyer hold clears (chargeback coverage)
    payouts = _read(_PAYOUTS_FILE)
    pr = payouts.get(order["seller_id"]) if isinstance(payouts.get(order["seller_id"]), dict) else {}
    pr["balance_usd"] = round(float(pr.get("balance_usd", 0) or 0), 2)
    pr["pending_usd"] = round(float(pr.get("pending_usd", 0) or 0) + float(order["usd_seller"]), 2)
    payouts[order["seller_id"]] = pr
    _write(_PAYOUTS_FILE, payouts)

    order["status"] = "held"
    order["paypal_capture_id"] = capture_id
    order["buyer_hold_until"] = hold_until
    order["payout_release_at"] = hold_until
    order["funded_at"] = _iso()
    order["credit_source"] = source
    order["updated_at"] = _iso()
    return {"success": True, **_public_order(order)}


def _capture_id_seen(orders: Dict[str, Any], capture_id: str) -> bool:
    return any(o.get("paypal_capture_id") == capture_id for o in orders.values())


def capture(order_id: str, buyer_id: str) -> Dict[str, Any]:
    bid = str(buyer_id or "").strip()
    with _LOCK:
        orders = _read(_ORDERS_FILE)
        order = orders.get(str(order_id or "").strip())
        if not order:
            return {"success": False, "error": "Order not found"}
        if order.get("buyer_id") != bid:
            return {"success": False, "error": "Order belongs to another buyer"}
        if order.get("status") in _FUNDED_ORDER:
            return {"success": True, "already": True, **_public_order(order)}
        if order.get("status") != "pending_payment":
            return {"success": False, "error": f"Order not capturable (status {order.get('status')})"}
        paypal_order_id = order.get("paypal_order_id")
    if not paypal_order_id:
        return {"success": False, "error": "Order has no PayPal order id"}

    try:
        from backend.services.paypal_service import capture_order as pp_capture
        result = pp_capture(paypal_order_id)
    except Exception as exc:
        return {"success": False, "error": f"PayPal capture failed: {exc}"}
    if not result.get("success"):
        return {"success": False, "error": result.get("error", "PayPal capture not completed")}

    capture_id = result.get("capture_id") or paypal_order_id
    with _LOCK:
        orders = _read(_ORDERS_FILE)
        listings = _read(_LISTINGS_FILE)
        order = orders.get(order_id)
        if _capture_id_seen(orders, capture_id) and order.get("paypal_capture_id") != capture_id:
            return {"success": False, "error": "Capture already processed"}
        out = _settle_capture(orders, listings, order, capture_id, source="capture")
        _write(_LISTINGS_FILE, listings)
        _write(_ORDERS_FILE, orders)
    _audit("order", order_id, "held", {"paypal_capture_id": capture_id, "source": "capture"})
    return out


# ------------------------------------------------------------------ webhook

def handle_webhook(event: Dict[str, Any], signature_ok: bool) -> Dict[str, Any]:
    if not signature_ok:
        return {"success": False, "error": "Webhook signature not verified"}
    event_type = str(event.get("event_type") or "").upper()
    resource = event.get("resource") or {}

    def _find(orders: Dict[str, Any]) -> Optional[Dict[str, Any]]:
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
        orders = _read(_ORDERS_FILE)
        order = _find(orders)
        if not order:
            return {"success": True, "ignored": True, "reason": "no matching p2p order"}
        listings = _read(_LISTINGS_FILE)

        if event_type == "PAYMENT.CAPTURE.COMPLETED":
            capture_id = resource.get("id") or order.get("paypal_order_id")
            if order.get("status") in _FUNDED_ORDER and order.get("paypal_capture_id") == capture_id:
                return {"success": True, "already": True}
            if _capture_id_seen(orders, capture_id) and order.get("paypal_capture_id") != capture_id:
                return {"success": True, "already": True}
            _settle_capture(orders, listings, order, capture_id, source="webhook")
            _write(_LISTINGS_FILE, listings)
            _write(_ORDERS_FILE, orders)
            _audit("order", order["order_id"], "held", {"paypal_capture_id": capture_id, "source": "webhook"})
            return {"success": True, "credited": True, "order_id": order["order_id"]}

        if event_type in ("PAYMENT.CAPTURE.DENIED", "PAYMENT.CAPTURE.REFUNDED",
                          "PAYMENT.CAPTURE.REVERSED", "CUSTOMER.DISPUTE.CREATED",
                          "CUSTOMER.DISPUTE.UPDATED"):
            res = _clawback(orders, listings, order, reason=event_type)
            _write(_LISTINGS_FILE, listings)
            _write(_ORDERS_FILE, orders)
            _audit("order", order["order_id"], "charged_back", {"reason": event_type, **res})
            return {"success": True, "clawback": res, "order_id": order["order_id"]}

    return {"success": True, "ignored": True, "event_type": event_type}


def _clawback(orders: Dict[str, Any], listings: Dict[str, Any], order: Dict[str, Any], reason: str) -> Dict[str, Any]:
    """Reverse a P2P sale: claw back buyer MN2, return escrow to seller, cancel payout. Caller holds _LOCK."""
    if order.get("status") == "charged_back":
        return {"already": True, "clawed_back_mn2": 0.0}
    bid = order["buyer_id"]
    sid = order["seller_id"]
    want = float(order.get("mn2_amount", 0) or 0)
    bal = _balance(bid)
    clawed = round(min(want, max(0.0, bal)), 8)
    if clawed > 0:
        _points().add_points(bid, "mn2_balance", -clawed, source="mn2_p2p_clawback",
                             metadata={"order_id": order["order_id"], "reason": reason})
        _ledger(bid, "p2p_clawback", clawed, metadata={"order_id": order["order_id"], "reason": reason})

    shortfall = round(want - clawed, 8)
    # Return the seller's escrowed MN2 (they keep their coins; the trade is unwound)
    _points().add_points(sid, "mn2_balance", want, source="mn2_p2p_escrow_return",
                         metadata={"order_id": order["order_id"], "reason": reason})
    _ledger(sid, "p2p_escrow_return", want, metadata={"order_id": order["order_id"], "reason": reason})

    # Cancel any pending seller payout for this order
    payouts = _read(_PAYOUTS_FILE)
    pr = payouts.get(sid) if isinstance(payouts.get(sid), dict) else {}
    pr["pending_usd"] = round(max(0.0, float(pr.get("pending_usd", 0) or 0) - float(order.get("usd_seller", 0) or 0)), 2)
    payouts[sid] = pr
    _write(_PAYOUTS_FILE, payouts)

    if shortfall > 0:
        _debit_reserve(shortfall, order["order_id"], reason)
        _flag(bid, order["order_id"], shortfall, reason)

    order["status"] = "charged_back"
    order["clawed_back_mn2"] = clawed
    order["shortfall_mn2"] = shortfall
    order["chargeback_reason"] = reason
    order["updated_at"] = _iso()
    return {"clawed_back_mn2": clawed, "shortfall_mn2": shortfall, "escrow_returned_to_seller": want}


def _debit_reserve(amount: float, order_id: str, reason: str) -> None:
    """Cover a clawback shortfall from the staking stabilization reserve when possible."""
    try:
        from backend.services import mn2_staking_service as staking
        reserve = staking._load_reserve()
        take = round(min(float(reserve.get("reserve_mn2", 0) or 0), amount), 8)
        if take > 0:
            reserve["reserve_mn2"] = round(float(reserve.get("reserve_mn2", 0) or 0) - take, 8)
            staking._save_reserve(reserve)
        _audit("reserve_debit", order_id, "debited", {"requested": amount, "taken": take, "reason": reason})
    except Exception:
        pass


def _flag(user_id: str, order_id: str, shortfall: float, reason: str) -> None:
    try:
        with open(_path("mn2_p2p_flags.jsonl"), "a", encoding="utf-8") as f:
            f.write(json.dumps({"user_id": user_id, "order_id": order_id,
                                "shortfall_mn2": shortfall, "reason": reason, "at": _iso()}) + "\n")
    except Exception:
        pass


# --------------------------------------------------------------- holds / clear

def buyer_held(user_id: str) -> float:
    """Sum of P2P-purchased MN2 still inside the buyer hold window (not withdrawable)."""
    uid = str(user_id or "").strip()
    now = _now()
    total = 0.0
    for o in _read(_ORDERS_FILE).values():
        if o.get("buyer_id") != uid or o.get("status") != "held":
            continue
        hu = _parse_iso(o.get("buyer_hold_until"))
        if hu and hu > now:
            total += float(o.get("mn2_amount", 0) or 0)
    return round(total, 8)


def clear_matured() -> Dict[str, Any]:
    """Ops: expire stale pending orders; clear matured held orders + release seller payouts."""
    now = _now()
    cleared = 0
    expired = 0
    released_usd = 0.0
    with _LOCK:
        orders = _read(_ORDERS_FILE)
        listings = _read(_LISTINGS_FILE)
        payouts = _read(_PAYOUTS_FILE)
        dirty_listings = False
        for o in list(orders.values()):
            if o.get("status") == "pending_payment":
                exp = _parse_iso(o.get("expires_at"))
                if exp and exp <= now:
                    want = float(o.get("mn2_amount", 0) or 0)
                    listing = listings.get(o.get("listing_id"))
                    if listing:
                        listing["mn2_reserved"] = round(max(0.0, float(listing.get("mn2_reserved", 0) or 0) - want), 8)
                        listing["mn2_available"] = round(float(listing.get("mn2_available", 0) or 0) + want, 8)
                        if listing.get("status") == "sold_out" and listing["mn2_available"] > 0:
                            listing["status"] = "open"
                        dirty_listings = True
                    o["status"] = "expired"
                    o["updated_at"] = _iso()
                    expired += 1
                    _audit("order", o["order_id"], "expired", {"reason": "ttl"})
            elif o.get("status") == "held":
                hu = _parse_iso(o.get("payout_release_at") or o.get("buyer_hold_until"))
                if hu and hu <= now:
                    o["status"] = "cleared"
                    o["cleared_at"] = _iso()
                    o["updated_at"] = _iso()
                    cleared += 1
                    sid = o["seller_id"]
                    pr = payouts.get(sid) if isinstance(payouts.get(sid), dict) else {}
                    amt = float(o.get("usd_seller", 0) or 0)
                    pr["pending_usd"] = round(max(0.0, float(pr.get("pending_usd", 0) or 0) - amt), 2)
                    pr["balance_usd"] = round(float(pr.get("balance_usd", 0) or 0) + amt, 2)
                    payouts[sid] = pr
                    released_usd += amt
                    _audit("order", o["order_id"], "cleared", {"seller_payout_usd": amt})
        if expired or cleared:
            _write(_ORDERS_FILE, orders)
        if dirty_listings:
            _write(_LISTINGS_FILE, listings)
        if released_usd:
            _write(_PAYOUTS_FILE, payouts)
    return {"success": True, "cleared": cleared, "expired": expired, "released_seller_usd": round(released_usd, 2)}


# -------------------------------------------------------------------- public

def _public_listing(l: Dict[str, Any]) -> Dict[str, Any]:
    import hashlib
    seller = l.get("seller_id") or ""
    return {
        "listing_id": l.get("listing_id"),
        "seller": "seller_" + hashlib.sha256(seller.encode("utf-8")).hexdigest()[:8],
        "mn2_total": l.get("mn2_total"),
        "mn2_available": l.get("mn2_available"),
        "price_usd_per_mn2": l.get("price_usd_per_mn2"),
        "status": l.get("status"),
        "created_at": l.get("created_at"),
    }


def _public_order(o: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "order_id": o.get("order_id"),
        "listing_id": o.get("listing_id"),
        "status": o.get("status"),
        "mn2_amount": o.get("mn2_amount"),
        "usd_amount": o.get("usd_amount"),
        "buyer_hold_until": o.get("buyer_hold_until"),
        "withdrawable": o.get("status") == "cleared",
        "created_at": o.get("created_at"),
    }


def list_listings(limit: int = 100) -> Dict[str, Any]:
    rows = [_public_listing(l) for l in _read(_LISTINGS_FILE).values() if l.get("status") == "open"]
    rows.sort(key=lambda r: float(r.get("price_usd_per_mn2") or 0))
    return {"success": True, "listings": rows[: max(1, min(int(limit or 100), 500))]}


def get_order(order_id: str, user_id: Optional[str] = None) -> Dict[str, Any]:
    o = _read(_ORDERS_FILE).get(str(order_id or "").strip())
    if not o:
        return {"success": False, "error": "Order not found"}
    if user_id and o.get("buyer_id") != str(user_id).strip() and o.get("seller_id") != str(user_id).strip():
        return {"success": False, "error": "Not your order"}
    return {"success": True, **_public_order(o)}


def get_user_overview(user_id: str) -> Dict[str, Any]:
    uid = str(user_id or "").strip()
    listings = [_public_listing(l) for l in _read(_LISTINGS_FILE).values() if l.get("seller_id") == uid]
    orders = [_public_order(o) for o in _read(_ORDERS_FILE).values() if o.get("buyer_id") == uid]
    payouts = _read(_PAYOUTS_FILE).get(uid) if isinstance(_read(_PAYOUTS_FILE).get(uid), dict) else {}
    listings.sort(key=lambda r: r.get("created_at") or "", reverse=True)
    orders.sort(key=lambda r: r.get("created_at") or "", reverse=True)
    return {
        "success": True,
        "my_listings": listings,
        "my_purchases": orders,
        "buyer_held_mn2": buyer_held(uid),
        "seller_payout_usd": round(float(payouts.get("balance_usd", 0) or 0), 2),
        "seller_payout_pending_usd": round(float(payouts.get("pending_usd", 0) or 0), 2),
    }


# --------------------------------------------------------------------- stats

def p2p_stats() -> Dict[str, Any]:
    orders = list(_read(_ORDERS_FILE).values())
    listings = list(_read(_LISTINGS_FILE).values())
    now = _now()
    day_ago = now - timedelta(hours=24)
    vol = 0.0
    mn2 = 0.0
    funded = 0
    charged = 0
    for o in orders:
        if o.get("status") in _FUNDED_ORDER:
            funded += 1
            fa = _parse_iso(o.get("funded_at"))
            if fa and fa >= day_ago:
                vol += float(o.get("usd_amount", 0) or 0)
                mn2 += float(o.get("mn2_amount", 0) or 0)
        elif o.get("status") == "charged_back":
            charged += 1
    denom = funded + charged
    return {
        "p2p_volume_usd_24h": round(vol, 2),
        "mn2_traded_24h": round(mn2, 8),
        "open_listings": sum(1 for l in listings if l.get("status") == "open"),
        "funded_orders": funded,
        "chargeback_rate": round(charged / denom, 4) if denom else 0.0,
    }
