"""
PayPal checkout for MN2 masternode hosting slots.

Flow: quote → PayPal order → capture (client or webhook) → auto-provision host on-chain.

State: data/mn2_masternode_orders.json (+ append-only .jsonl audit).
"""
from __future__ import annotations

import json
import os
import threading
import uuid
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional

_LOCK = threading.RLock()
_ORDERS_FILE = "mn2_masternode_orders.json"
_EVENTS_FILE = "mn2_masternode_orders.jsonl"
_PAID_STATUS = ("paid",)


def _base() -> str:
    return os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _data_path(name: str) -> str:
    return os.path.join(_base(), "data", name)


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


def _read_json(path: str) -> dict:
    if not os.path.isfile(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            d = json.load(f)
        return d if isinstance(d, dict) else {}
    except Exception:
        return {}


def _write_json(path: str, data: dict) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    os.replace(tmp, path)


def _audit(order_id: str, event: str, meta: Optional[dict] = None) -> None:
    try:
        rec = {"ts": _iso(), "order_id": order_id, "event": event, "meta": meta or {}}
        with open(_data_path(_EVENTS_FILE), "a", encoding="utf-8") as f:
            f.write(json.dumps(rec) + "\n")
    except Exception:
        pass


def get_paypal_config() -> Dict[str, Any]:
    from backend.services.mn2_masternode_service import get_config
    cfg = get_config()
    pp = cfg.get("paypal") if isinstance(cfg.get("paypal"), dict) else {}
    shop = cfg.get("shop_payments") if isinstance(cfg.get("shop_payments"), dict) else {}
    rails = shop.get("payment_rails")
    if not isinstance(rails, list):
        rails = ["paypal", "mn2", "credits", "mn2_onchain"]
    return {
        "enabled": bool(cfg.get("enabled", True) and pp.get("enabled", True)),
        "price_usd_per_slot": float(pp.get("price_usd_per_slot") or 4.99),
        "currency": (pp.get("currency") or "USD").upper(),
        "billing_label": pp.get("billing_label") or "MN2 Masternode Hosting",
        "quote_ttl_seconds": int(pp.get("quote_ttl_seconds") or 900),
        "max_slots_per_order": int(pp.get("max_slots_per_order") or 5),
        "return_path": pp.get("return_path") or "/explorer?tab=masternodes",
        "collateral_mn2": float(cfg.get("collateral_mn2") or 10000),
        "max_hosted_nodes": int(cfg.get("max_hosted_nodes") or 50),
        "auto_provision": bool(cfg.get("auto_provision", True)),
        "shop_payments": {
            "enabled": bool(shop.get("enabled", True)),
            "payment_rails": rails,
            "price_coins_per_slot": shop.get("price_coins_per_slot"),
        },
    }


def _coins_per_mn2() -> float:
    try:
        with open(_data_path("mn2_config.json"), "r", encoding="utf-8") as f:
            return float(json.load(f).get("coins_per_mn2") or 100)
    except Exception:
        return 100.0


def _mn2_usd_price() -> Optional[float]:
    try:
        from backend.services.mn2_chainz import mn2_usd_price_median
        bundle = mn2_usd_price_median()
        if bundle and bundle.get("price"):
            return float(bundle["price"])
    except Exception:
        pass
    try:
        with open(_data_path("mn2_config.json"), "r", encoding="utf-8") as f:
            px = json.load(f).get("mn2_usd_price")
            if px is not None:
                return float(px)
    except Exception:
        pass
    return None


def pricing_for_slots(slots: int) -> Dict[str, Any]:
    """USD, coins, and MN2 totals for hosting checkout."""
    pp = get_paypal_config()
    try:
        slots = max(1, int(slots or 1))
    except (TypeError, ValueError):
        slots = 1
    usd_per_slot = float(pp["price_usd_per_slot"])
    usd_total = round(usd_per_slot * slots, 2)
    shop = pp.get("shop_payments") if isinstance(pp.get("shop_payments"), dict) else {}
    fixed_coins = shop.get("price_coins_per_slot")
    cpm = _coins_per_mn2()
    if fixed_coins is not None:
        coins_per_slot = int(fixed_coins)
    else:
        mn2_usd = _mn2_usd_price()
        if mn2_usd and mn2_usd > 0 and cpm > 0:
            mn2_per_slot = usd_per_slot / mn2_usd
            coins_per_slot = max(1, int(round(mn2_per_slot * cpm)))
        else:
            coins_per_slot = max(1, int(round(usd_per_slot * 100)))
    coins_total = coins_per_slot * slots
    mn2_total = round(coins_total / cpm, 8) if cpm > 0 else 0.0
    return {
        "slots": slots,
        "usd_per_slot": usd_per_slot,
        "usd_total": usd_total,
        "coins_per_slot": coins_per_slot,
        "coins_total": coins_total,
        "mn2_per_slot": round(mn2_total / slots, 8) if slots else mn2_total,
        "mn2_total": mn2_total,
        "coins_per_mn2": cpm,
        "mn2_usd_price": _mn2_usd_price(),
        "payment_rails": shop.get("payment_rails") or ["paypal", "mn2", "credits", "mn2_onchain"],
    }


def _load_orders() -> Dict[str, Any]:
    with _LOCK:
        return _read_json(_data_path(_ORDERS_FILE))


def _save_orders(data: Dict[str, Any]) -> None:
    with _LOCK:
        _write_json(_data_path(_ORDERS_FILE), data)


def get_quote(slots: int, user_id: str) -> Dict[str, Any]:
    uid = str(user_id or "").strip()
    if not uid:
        return {"success": False, "error": "Could not identify your account for checkout", "code": "auth_required"}

    pp = get_paypal_config()
    if not pp.get("enabled"):
        return {"success": False, "error": "Masternode hosting checkout is disabled"}

    try:
        slots = int(slots or 1)
    except (TypeError, ValueError):
        return {"success": False, "error": "slots must be a number"}
    if slots < 1:
        return {"success": False, "error": "At least 1 slot required"}
    if slots > int(pp["max_slots_per_order"]):
        return {"success": False, "error": f"Maximum {pp['max_slots_per_order']} slots per order"}

    from backend.services import mn2_masternode_service as mn
    st = mn.get_service_status()
    avail = int(st.get("slots_available") or 0)
    if avail < slots:
        return {
            "success": False,
            "error": f"Only {avail} slot(s) available (max {pp['max_hosted_nodes']})",
            "slots_available": avail,
        }

    price = float(pp["price_usd_per_slot"])
    usd_total = round(price * slots, 2)
    shop_prices = pricing_for_slots(slots)
    quote_id = "mnq_" + uuid.uuid4().hex[:16]
    expires_at = _iso(_now() + timedelta(seconds=int(pp["quote_ttl_seconds"])))

    with _LOCK:
        orders = _load_orders()
        orders[quote_id] = {
            "order_id": quote_id,
            "user_id": uid,
            "slots": slots,
            "usd_per_slot": price,
            "usd_total": usd_total,
            "coins_per_slot": shop_prices["coins_per_slot"],
            "coins_total": shop_prices["coins_total"],
            "mn2_total": shop_prices["mn2_total"],
            "currency": pp["currency"],
            "status": "quoted",
            "payment_method": None,
            "payment_ref": None,
            "paypal_order_id": None,
            "paypal_capture_id": None,
            "onchain_payment_ref": None,
            "host_ids": [],
            "created_at": _iso(),
            "expires_at": expires_at,
        }
        _save_orders(orders)
    _audit(quote_id, "quoted", {"slots": slots, "usd_total": usd_total, "coins_total": shop_prices["coins_total"]})

    return {
        "success": True,
        "quote_id": quote_id,
        "slots": slots,
        "usd_per_slot": price,
        "usd_total": usd_total,
        "coins_per_slot": shop_prices["coins_per_slot"],
        "coins_total": shop_prices["coins_total"],
        "mn2_total": shop_prices["mn2_total"],
        "mn2_per_slot": shop_prices["mn2_per_slot"],
        "coins_per_mn2": shop_prices["coins_per_mn2"],
        "payment_rails": shop_prices["payment_rails"],
        "currency": pp["currency"],
        "collateral_mn2_per_slot": pp["collateral_mn2"],
        "expires_at": expires_at,
        "disclaimer": "Checkout reserves a slot and provisions your masternode automatically.",
    }


def create_order(quote_id: str, user_id: str,
                 return_url: Optional[str] = None, cancel_url: Optional[str] = None) -> Dict[str, Any]:
    uid = str(user_id or "").strip()
    qid = str(quote_id or "").strip()
    with _LOCK:
        orders = _load_orders()
        order = orders.get(qid)
        if not order:
            return {"success": False, "error": "Quote not found"}
        if order.get("user_id") != uid:
            return {"success": False, "error": "Quote belongs to another user"}
        if order.get("status") != "quoted":
            return {"success": False, "error": f"Quote not open (status {order.get('status')})"}
        if _parse_iso(order.get("expires_at")) and _parse_iso(order["expires_at"]) < _now():
            order["status"] = "expired"
            _save_orders(orders)
            return {"success": False, "error": "Quote expired", "code": "quote_expired"}

    pp = get_paypal_config()
    base = (os.environ.get("BASE_URL") or "https://masternoder.dk").rstrip("/")
    return_url = return_url or f"{base}{pp['return_path']}&mn_quote={qid}&paypal=success"
    cancel_url = cancel_url or f"{base}{pp['return_path']}&paypal=cancel"

    slots = int(order.get("slots") or 1)
    item = f"{pp['billing_label']} × {slots} slot(s)"
    try:
        from backend.services.paypal_service import create_order as pp_create
        result = pp_create(
            amount=float(order["usd_total"]),
            currency=str(order.get("currency") or "USD"),
            item_name=item,
            return_url=return_url,
            cancel_url=cancel_url,
            metadata={"item_id": qid, "product": "mn2_masternode_hosting", "user_id": uid},
        )
    except Exception as exc:
        return {"success": False, "error": f"PayPal order failed: {exc}"}

    if not result.get("success"):
        return {"success": False, "error": result.get("error", "PayPal order creation failed")}

    with _LOCK:
        orders = _load_orders()
        order = orders.get(qid)
        order["status"] = "pending_payment"
        order["paypal_order_id"] = result.get("order_id")
        order["updated_at"] = _iso()
        _save_orders(orders)
    _audit(qid, "pending_payment", {"paypal_order_id": result.get("order_id")})

    return {
        "success": True,
        "order_id": qid,
        "paypal_order_id": result.get("order_id"),
        "approve_url": result.get("approve_url"),
        "usd_total": order["usd_total"],
        "slots": slots,
    }


def _register_and_provision(order: Dict[str, Any]) -> Dict[str, Any]:
    from backend.services import mn2_masternode_service as mn
    slots = int(order.get("slots") or 1)
    uid = order.get("user_id") or ""
    oid = order.get("order_id") or ""
    host_ids: List[str] = []
    provisions: List[Dict[str, Any]] = []
    for i in range(slots):
        hid = f"user-{uid[:8]}-{uuid.uuid4().hex[:6]}"
        label = f"Hosted MN · {oid[:12]}"
        res = mn.register_host({
            "id": hid,
            "label": label,
            "status": "provisioning",
            "owner_user_id": uid,
            "notes": f"PayPal {oid}",
        })
        if res.get("success"):
            host_ids.append(hid)
            prov = mn.provision_host(hid, order_id=oid)
            provisions.append(prov)
    live = sum(1 for p in provisions if p.get("status") == "active")
    msg = (
        f"Payment received — {live or len(host_ids)} slot(s) provisioning automatically."
        if host_ids
        else "Payment received but slot registration failed — contact support."
    )
    return {"host_ids": host_ids, "provisions": provisions, "message": msg}


def _payment_ref_seen(orders: Dict[str, Any], payment_ref: str) -> bool:
    pref = str(payment_ref or "")
    return any(
        isinstance(o, dict) and (o.get("payment_ref") == pref or o.get("paypal_capture_id") == pref)
        for o in orders.values()
    )


def _mark_paid(order: Dict[str, Any], payment_ref: str, source: str, payment_method: str) -> Dict[str, Any]:
    if order.get("status") == "paid" and order.get("host_ids"):
        return {
            "success": True,
            "already_paid": True,
            "host_ids": order.get("host_ids") or [],
            "slots": order.get("slots"),
            "message": "Already paid — your slot(s) are on the fleet list.",
        }

    fulfilled = _register_and_provision(order)
    order["status"] = "paid"
    order["payment_method"] = payment_method
    order["payment_ref"] = payment_ref
    if payment_method == "paypal":
        order["paypal_capture_id"] = payment_ref
    order["host_ids"] = fulfilled.get("host_ids") or []
    order["paid_at"] = _iso()
    order["updated_at"] = _iso()
    order["fulfillment_source"] = source
    _audit(order["order_id"], "paid", {
        "payment_ref": payment_ref,
        "payment_method": payment_method,
        "host_ids": order["host_ids"],
        "source": source,
    })
    return {
        "success": True,
        "order_id": order.get("order_id"),
        "slots": order.get("slots"),
        "host_ids": order["host_ids"],
        "provisions": fulfilled.get("provisions"),
        "message": fulfilled.get("message"),
        "payment_method": payment_method,
    }


def _apply_capture(order: Dict[str, Any], capture_id: str, source: str) -> Dict[str, Any]:
    return _mark_paid(order, capture_id, source, "paypal")


def _quote_open(order: Optional[Dict[str, Any]], uid: str, *, allow_statuses: Optional[tuple] = None) -> Optional[Dict[str, Any]]:
    if not order:
        return {"success": False, "error": "Quote not found"}
    if order.get("user_id") != uid:
        return {"success": False, "error": "Quote belongs to another user"}
    if order.get("status") == "paid":
        return {
            "success": True,
            "already_paid": True,
            "host_ids": order.get("host_ids") or [],
            "slots": order.get("slots"),
            "message": "Already paid — your slot(s) are on the fleet list.",
        }
    allowed = allow_statuses or ("quoted",)
    if order.get("status") not in allowed:
        return {"success": False, "error": f"Quote not open (status {order.get('status')})"}
    if _parse_iso(order.get("expires_at")) and _parse_iso(order["expires_at"]) < _now():
        order["status"] = "expired"
        return {"success": False, "error": "Quote expired", "code": "quote_expired"}
    return None


def purchase_with_coins(quote_id: str, user_id: str) -> Dict[str, Any]:
    uid = str(user_id or "").strip()
    qid = str(quote_id or "").strip()
    with _LOCK:
        orders = _load_orders()
        order = orders.get(qid)
        err = _quote_open(order, uid)
        if err:
            if err.get("already_paid"):
                return err
            if err.get("code") == "quote_expired":
                _save_orders(orders)
            return err

    coins_total = int(order.get("coins_total") or 0)
    if coins_total <= 0:
        shop_prices = pricing_for_slots(int(order.get("slots") or 1))
        coins_total = int(shop_prices["coins_total"])
        order["coins_total"] = coins_total
        order["coins_per_slot"] = shop_prices["coins_per_slot"]
        order["mn2_total"] = shop_prices["mn2_total"]

    from backend.services.unified_points_database import unified_points_db
    points_result = unified_points_db.get_all_points(uid)
    if not points_result.get("success"):
        return {"success": False, "error": "Failed to retrieve user balance"}
    user_points = points_result.get("points", {})
    user_coins = int(user_points.get("coins", 0) or 0)
    if user_coins < coins_total:
        return {
            "success": False,
            "error": f"Insufficient coins. Need {coins_total}, have {user_coins}",
            "coins_required": coins_total,
            "coins_balance": user_coins,
        }

    deduct = unified_points_db.add_points(
        user_id=uid,
        point_type="coins",
        amount=-coins_total,
        source="mn2_masternode_hosting",
        metadata={"quote_id": qid, "slots": order.get("slots"), "payment_method": "credits"},
    )
    if not deduct.get("success", True):
        return {"success": False, "error": "Failed to deduct coins"}

    with _LOCK:
        orders = _load_orders()
        order = orders.get(qid)
        err = _quote_open(order, uid)
        if err:
            unified_points_db.add_points(
                user_id=uid, point_type="coins", amount=coins_total,
                source="mn2_masternode_hosting_refund",
                metadata={"quote_id": qid, "reason": "quote_no_longer_open"},
            )
            return err if not err.get("already_paid") else err
        out = _mark_paid(order, f"coins:{qid}", "pay_coins", "credits")
        _save_orders(orders)

    try:
        from backend.services.shop_monetization_service import accrue_purchase_loyalty
        accrue_purchase_loyalty(uid, coins_total)
    except Exception:
        pass
    out["coins_paid"] = coins_total
    return out


def purchase_with_mn2_balance(quote_id: str, user_id: str) -> Dict[str, Any]:
    uid = str(user_id or "").strip()
    qid = str(quote_id or "").strip()
    with _LOCK:
        orders = _load_orders()
        order = orders.get(qid)
        err = _quote_open(order, uid)
        if err:
            if err.get("already_paid"):
                return err
            if err.get("code") == "quote_expired":
                _save_orders(orders)
            return err

    mn2_total = float(order.get("mn2_total") or 0)
    if mn2_total <= 0:
        shop_prices = pricing_for_slots(int(order.get("slots") or 1))
        mn2_total = float(shop_prices["mn2_total"])
        order["mn2_total"] = mn2_total
        order["coins_total"] = shop_prices["coins_total"]

    from backend.services.unified_points_database import unified_points_db
    from backend.services.mn2_ledger import append_entry

    points_result = unified_points_db.get_all_points(uid)
    if not points_result.get("success"):
        return {"success": False, "error": "Failed to retrieve user balance"}
    user_points = points_result.get("points", {})
    mn2_balance = float(user_points.get("mn2_balance", 0) or 0)
    if mn2_balance == 0 and isinstance(user_points.get("systems"), dict):
        mn2_balance = float(user_points["systems"].get("mn2_balance", 0) or 0)
    if mn2_balance < mn2_total:
        return {
            "success": False,
            "error": f"Insufficient MN2. Need {mn2_total:.8f}, have {mn2_balance:.8f}",
            "mn2_required": mn2_total,
            "mn2_balance": mn2_balance,
        }

    debit = unified_points_db.add_points(
        user_id=uid,
        point_type="mn2_balance",
        amount=-mn2_total,
        source="mn2_masternode_hosting",
        metadata={"quote_id": qid, "slots": order.get("slots"), "payment_method": "mn2"},
    )
    if not debit.get("success", True):
        return {"success": False, "error": "Failed to debit MN2 balance"}

    with _LOCK:
        orders = _load_orders()
        order = orders.get(qid)
        err = _quote_open(order, uid)
        if err:
            unified_points_db.add_points(
                user_id=uid, point_type="mn2_balance", amount=mn2_total,
                source="mn2_masternode_hosting_refund",
                metadata={"quote_id": qid, "reason": "quote_no_longer_open"},
            )
            return err if not err.get("already_paid") else err
        out = _mark_paid(order, f"mn2:{qid}", "pay_mn2", "mn2")
        _save_orders(orders)

    try:
        append_entry(
            user_id=uid,
            entry_type="masternode_hosting_payment",
            amount=mn2_total,
            txid=None,
            address=None,
            metadata={"quote_id": qid, "slots": order.get("slots"), "payment_method": "mn2"},
        )
    except Exception:
        pass
    try:
        from backend.services.shop_monetization_service import accrue_purchase_loyalty
        accrue_purchase_loyalty(uid, int(order.get("coins_total") or 0))
    except Exception:
        pass
    out["mn2_paid"] = mn2_total
    return out


def create_onchain_payment(quote_id: str, user_id: str) -> Dict[str, Any]:
    uid = str(user_id or "").strip()
    qid = str(quote_id or "").strip()
    with _LOCK:
        orders = _load_orders()
        order = orders.get(qid)
        err = _quote_open(order, uid)
        if err:
            if err.get("already_paid"):
                return err
            if err.get("code") == "quote_expired":
                _save_orders(orders)
            return err

    mn2_total = float(order.get("mn2_total") or 0)
    coins_total = int(order.get("coins_total") or 0)
    slots = int(order.get("slots") or 1)
    if mn2_total <= 0:
        shop_prices = pricing_for_slots(slots)
        mn2_total = float(shop_prices["mn2_total"])
        coins_total = int(shop_prices["coins_total"])

    try:
        from backend.services.mn2_rpc_client import getnewaddress
        r = getnewaddress()
        if r.get("error"):
            return {"success": False, "error": r.get("error", "Could not get address")}
        address = (r.get("result") or "").strip()
        if not address:
            return {"success": False, "error": "RPC did not return address"}
    except Exception as exc:
        return {"success": False, "error": str(exc)}

    from backend.services.mn2_order_payment_service import create_order_payment
    pp = get_paypal_config()
    payment = create_order_payment(
        user_id=uid,
        item_id=qid,
        item_name=f"{pp.get('billing_label')} × {slots} slot(s)",
        quantity=slots,
        price_coins=coins_total,
        price_mn2=mn2_total,
        address=address,
        product="mn2_masternode_hosting",
        hosting_quote_id=qid,
    )

    with _LOCK:
        orders = _load_orders()
        order = orders.get(qid)
        if order and order.get("status") in ("quoted", "pending_onchain"):
            order["status"] = "pending_onchain"
            order["onchain_payment_ref"] = payment.get("payment_ref")
            order["updated_at"] = _iso()
            _save_orders(orders)
    _audit(qid, "pending_onchain", {"payment_ref": payment.get("payment_ref")})

    try:
        from backend.routes.mn2_routes import explorer_address_url
        explorer_url = explorer_address_url(address)
    except Exception:
        explorer_url = ""

    return {
        "success": True,
        "quote_id": qid,
        "payment_ref": payment.get("payment_ref"),
        "address": address,
        "amount_mn2": payment.get("amount_mn2"),
        "expires_at": payment.get("expires_at"),
        "slots": slots,
        "explorer_address_url": explorer_url,
    }


def fulfill_onchain_payment(quote_id: str, user_id: str, txid: str, amount_mn2: Optional[float] = None) -> Dict[str, Any]:
    """Called by deposit scanner when on-chain hosting payment confirms."""
    uid = str(user_id or "").strip()
    qid = str(quote_id or "").strip()
    with _LOCK:
        orders = _load_orders()
        order = orders.get(qid)
        if not order:
            return {"success": False, "error": "Hosting quote not found"}
        if order.get("user_id") != uid:
            return {"success": False, "error": "Quote belongs to another user"}
        if order.get("status") == "paid":
            return {"success": True, "already_paid": True, "host_ids": order.get("host_ids") or []}
        pref = f"onchain:{(txid or '').strip()}"
        if _payment_ref_seen(orders, pref) and order.get("payment_ref") != pref:
            return {"success": True, "already_paid": True, "host_ids": order.get("host_ids") or []}
        out = _mark_paid(order, pref, "mn2_onchain", "mn2_onchain")
        if amount_mn2 is not None:
            order["mn2_paid_onchain"] = float(amount_mn2)
        _save_orders(orders)
    return out


def capture(order_id: str, user_id: str) -> Dict[str, Any]:
    uid = str(user_id or "").strip()
    oid = str(order_id or "").strip()
    with _LOCK:
        orders = _load_orders()
        order = orders.get(oid)
        if not order:
            return {"success": False, "error": "Order not found"}
        if order.get("user_id") != uid:
            return {"success": False, "error": "Order belongs to another user"}
        if order.get("status") == "paid":
            return {
                "success": True,
                "already_paid": True,
                "host_ids": order.get("host_ids") or [],
                "slots": order.get("slots"),
                "message": "Already paid — your slot(s) are on the fleet list.",
            }

    paypal_order_id = order.get("paypal_order_id")
    if not paypal_order_id:
        return {"success": False, "error": "No PayPal order linked"}

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
        order = orders.get(oid)
        if _payment_ref_seen(orders, capture_id) and order.get("paypal_capture_id") != capture_id:
            return {"success": True, "already_paid": True, "host_ids": order.get("host_ids") or []}
        out = _apply_capture(order, capture_id, source="capture")
        _save_orders(orders)
    return out


def handle_webhook(event: Dict[str, Any], signature_ok: bool) -> Dict[str, Any]:
    """Server-side PayPal fulfillment — no browser return required."""
    if not signature_ok:
        return {"success": False, "error": "Webhook signature not verified"}

    event_type = str(event.get("event_type") or "").upper()
    resource = event.get("resource") or {}

    def _find_order(orders: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        custom = resource.get("custom_id")
        pp_order = (resource.get("supplementary_data", {}) or {}).get("related_ids", {}).get("order_id")
        cap_id = resource.get("id")
        for o in orders.values():
            if not isinstance(o, dict):
                continue
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
            return {"success": True, "ignored": True, "reason": "no matching masternode order"}

        if event_type == "PAYMENT.CAPTURE.COMPLETED":
            capture_id = resource.get("id") or order.get("paypal_order_id")
            if order.get("status") == "paid" and order.get("paypal_capture_id") == capture_id:
                return {"success": True, "already_paid": True}
            if _payment_ref_seen(orders, capture_id) and order.get("paypal_capture_id") != capture_id:
                return {"success": True, "already_paid": True}
            out = _apply_capture(order, capture_id, source="webhook")
            _save_orders(orders)
            return out

        if event_type == "CHECKOUT.ORDER.APPROVED":
            pp_oid = resource.get("id") or order.get("paypal_order_id")
            if not pp_oid:
                return {"success": True, "ignored": True}
            try:
                from backend.services.paypal_service import capture_order as pp_capture
                result = pp_capture(pp_oid)
            except Exception as exc:
                return {"success": False, "error": str(exc)}
            if not result.get("success"):
                return {"success": False, "error": result.get("error", "capture failed")}
            capture_id = result.get("capture_id") or pp_oid
            if order.get("status") == "paid":
                return {"success": True, "already_paid": True}
            out = _apply_capture(order, capture_id, source="webhook_approved")
            _save_orders(orders)
            return out

    return {"success": True, "ignored": True, "event_type": event_type}


def get_order(order_id: str, user_id: str) -> Dict[str, Any]:
    uid = str(user_id or "").strip()
    order = _load_orders().get(str(order_id or "").strip())
    if not order:
        return {"success": False, "error": "Order not found"}
    if order.get("user_id") != uid:
        return {"success": False, "error": "Forbidden"}
    return {"success": True, "order": {
        k: order.get(k) for k in (
            "order_id", "status", "slots", "usd_total", "usd_per_slot",
            "host_ids", "created_at", "paid_at", "expires_at",
        )
    }}


def list_user_orders(user_id: str, limit: int = 20) -> List[Dict[str, Any]]:
    """Paid/pending masternode hosting orders for shop purchase history."""
    uid = str(user_id or "").strip()
    if not uid:
        return []
    rows: List[Dict[str, Any]] = []
    for order in _load_orders().values():
        if not isinstance(order, dict) or order.get("user_id") != uid:
            continue
        status = str(order.get("status") or "")
        if status not in ("quoted", "pending_payment", "paid", "expired"):
            continue
        rows.append({
            "order_id": order.get("order_id"),
            "status": status,
            "slots": int(order.get("slots") or 1),
            "usd_total": float(order.get("usd_total") or 0),
            "usd_per_slot": float(order.get("usd_per_slot") or 0),
            "coins_total": int(order.get("coins_total") or 0),
            "mn2_total": float(order.get("mn2_total") or 0),
            "payment_method": order.get("payment_method"),
            "host_ids": order.get("host_ids") or [],
            "created_at": order.get("created_at"),
            "paid_at": order.get("paid_at"),
            "expires_at": order.get("expires_at"),
        })
    rows.sort(key=lambda r: str(r.get("paid_at") or r.get("created_at") or ""), reverse=True)
    return rows[: max(1, int(limit or 20))]


def hosting_stats() -> Dict[str, Any]:
    orders = _load_orders()
    paid = sum(1 for o in orders.values() if isinstance(o, dict) and o.get("status") == "paid")
    pending = sum(1 for o in orders.values() if isinstance(o, dict) and o.get("status") == "pending_payment")
    return {"paid_orders": paid, "pending_orders": pending, "paypal": get_paypal_config()}
