"""
MN2 order payment (Phase 8): non-custodial pay at checkout.
Create a unique address per order; user sends MN2 on-chain; scanner matches and fulfils.
See docs/MASTERNODER2_CRYPTO_INTEGRATION_EXPANDED.md §8.5.
"""
import os
import json
import uuid
import threading
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional

_log = logging.getLogger(__name__)

_LOCK = threading.Lock()
_FILENAME = "mn2_order_payments.json"
_EXPIRY_HOURS = 1


def _data_dir() -> str:
    base = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    return os.path.join(base, "data")


def _path() -> str:
    return os.path.join(_data_dir(), _FILENAME)


def _load() -> List[Dict[str, Any]]:
    p = _path()
    with _LOCK:
        if os.path.exists(p):
            try:
                with open(p, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if isinstance(data, list):
                    return data
                if isinstance(data, dict) and "orders" in data:
                    return data["orders"]
            except Exception:
                pass
        return []


def _save(orders: List[Dict[str, Any]]) -> None:
    os.makedirs(_data_dir(), exist_ok=True)
    with _LOCK:
        with open(_path(), "w", encoding="utf-8") as f:
            json.dump({"orders": orders}, f, indent=2)


def create_order_payment(
    user_id: str,
    item_id: str,
    item_name: str,
    quantity: int,
    price_coins: int,
    price_mn2: float,
    address: str,
) -> Dict[str, Any]:
    """Register a new order payment (address already from RPC getnewaddress). Returns order record with payment_ref, expires_at."""
    payment_ref = str(uuid.uuid4())[:12]
    now = datetime.utcnow()
    expires_at = (now + timedelta(hours=_EXPIRY_HOURS)).isoformat() + "Z"
    order = {
        "payment_ref": payment_ref,
        "user_id": str(user_id),
        "address": address,
        "amount_mn2": round(price_mn2, 8),
        "item_id": item_id,
        "item_name": item_name,
        "quantity": quantity,
        "price_coins": price_coins,
        "created_at": now.isoformat() + "Z",
        "expires_at": expires_at,
        "status": "pending",
        "txid": None,
        "fulfilled_at": None,
    }
    orders = _load()
    orders.append(order)
    _save(orders)
    return order


def get_order(payment_ref: str) -> Optional[Dict[str, Any]]:
    """Return order by payment_ref or None."""
    ref = (payment_ref or "").strip()
    if not ref:
        return None
    for o in _load():
        if (o.get("payment_ref") or "").strip() == ref:
            return o
    return None


def get_address_to_order_map() -> Dict[str, Dict[str, Any]]:
    """Return map address -> order for pending, non-expired orders (for scanner)."""
    now = datetime.utcnow()
    out = {}
    for o in _load():
        if (o.get("status") or "").strip() != "pending":
            continue
        exp = o.get("expires_at") or ""
        if exp and exp < now.isoformat() + "Z":
            continue
        addr = (o.get("address") or "").strip()
        if addr:
            out[addr] = o
    return out


def confirm_and_fulfill(payment_ref: str, txid: str) -> Optional[Dict[str, Any]]:
    """
    Fulfill an on-chain MN2 order once the scanner has seen the payment.

    The order remains pending if purchase/inventory persistence fails, so the
    scanner can retry instead of stranding a paid user in "confirmed" limbo.
    """
    orders = _load()
    idx = None
    for i, o in enumerate(orders):
        if (o.get("payment_ref") or "").strip() == (payment_ref or "").strip():
            idx = i
            break
    if idx is None:
        return None
    order = orders[idx]
    if order.get("status") == "fulfilled":
        return order

    txid_val = (txid or "").strip()

    # Fulfill: record_purchase + add_to_inventory are mandatory. Ledger and
    # item effects are best-effort after the user owns what they paid for.
    if order.get("fulfilled_at"):
        return order
    try:
        from backend.services.shop_db_service import fulfill_shop_purchase
        from backend.services.mn2_ledger import append_entry
        from backend.routes.shop_routes import _get_shop_items, _apply_shop_item_effects
        user_id = order.get("user_id") or ""
        item_id = order.get("item_id") or ""
        item_name = order.get("item_name") or ""
        quantity = int(order.get("quantity") or 1)
        amount_mn2 = float(order.get("amount_mn2") or 0)
        price_coins = int(order.get("price_coins") or 0)

        purchase_id = fulfill_shop_purchase(
            user_id=user_id,
            item_id=item_id,
            item_name=item_name,
            quantity=quantity,
            price_type="mn2_onchain",
            price_paid_coins=0,
            price_paid_points={"mn2": amount_mn2},
            balance_before=None,
            balance_after=None,
        )
        try:
            append_entry(
                user_id=user_id,
                entry_type="shop_payment",
                amount=amount_mn2,
                txid=txid_val,
                address=order.get("address"),
                metadata={"item_id": item_id, "item_name": item_name, "quantity": quantity, "price_coins": price_coins, "onchain": True, "purchase_id": purchase_id},
            )
        except Exception as ledger_ex:
            _log.exception("mn2_order_payment ledger append failed ref=%s: %s", payment_ref, ledger_ex)
        try:
            items = _get_shop_items() or []
            item = next((x for x in items if (x.get("id") or "") == item_id), {})
            _apply_shop_item_effects(user_id, item_id, item, quantity)
        except Exception as effects_ex:
            _log.exception("mn2_order_payment effects failed ref=%s: %s", payment_ref, effects_ex)

        now_iso = datetime.utcnow().isoformat() + "Z"
        order["status"] = "fulfilled"
        order["txid"] = txid_val
        order["fulfilled_at"] = now_iso
        order.pop("fulfillment_error", None)
        orders[idx] = order
        _save(orders)
    except Exception as ex:
        _log.exception("mn2_order_payment fulfill failed ref=%s: %s", payment_ref, ex)
        order["status"] = "pending"
        order["txid"] = txid_val
        order["fulfillment_error"] = str(ex)
        orders[idx] = order
        _save(orders)
    return order


def mark_expired(payment_ref: str) -> bool:
    """Set status to expired if still pending. Returns True if updated."""
    orders = _load()
    for i, o in enumerate(orders):
        if (o.get("payment_ref") or "").strip() == (payment_ref or "").strip() and (o.get("status") or "") == "pending":
            orders[i] = {**o, "status": "expired"}
            _save(orders)
            return True
    return False
