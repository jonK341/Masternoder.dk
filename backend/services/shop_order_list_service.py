"""Shop-native order lists: catalog purchases + stall listings + hosting."""
from __future__ import annotations

import os
import re
from typing import Any, Dict, Iterable, List, Optional, Tuple

from backend.services.shop_order_pdf_service import build_orders_pdf, format_price_label
from backend.services.shop_taxonomy_service import enrich_rows, order_status_bucket

_MAX_LIST = 300
_PAYPAL_LOG = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "logs",
    "purchase_notifications.log",
)
_PURCHASE_LOG_RE = re.compile(
    r"\[(?P<ts>[^\]]+)\] PURCHASE \| amount=(?P<amount>[^\s]+) (?P<currency>\S+) \| "
    r"item=(?P<item_id>[^\s]+) \((?P<item_name>[^)]*)\) \| user=(?P<user_id>[^|]+) \| "
    r"order=(?P<order_id>[^|]+) \| coins_granted=(?P<coins>\d+) \| source=(?P<source>\S+)"
)

_PAYMENT_LABELS = {
    "paypal": "PayPal",
    "paypal_mn2_hosting": "PayPal",
    "coins": "Coins",
    "credits": "Coins",
    "mn2": "MN2 balance",
    "mn2_onchain": "MN2 on-chain",
    "unified_points": "Points",
    "points": "Points",
    "casino": "Casino",
    "exchange": "Exchange",
}


def _catalog_by_id() -> Dict[str, Dict[str, Any]]:
    try:
        from backend.services.shop_db_service import get_shop_items_from_db

        items = get_shop_items_from_db() or []
        return {str(i.get("id")): i for i in items if isinstance(i, dict) and i.get("id")}
    except Exception:
        return {}


def _enrich(rows: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
    try:
        return enrich_rows(list(rows or []), _catalog_by_id())
    except Exception:
        return list(rows or [])


def _cap(limit: int, default: int = 50) -> int:
    try:
        n = int(limit or default)
    except (TypeError, ValueError):
        n = default
    return max(1, min(n, _MAX_LIST))


def payment_method_label(row: Optional[Dict[str, Any]]) -> str:
    """Human label for the rail used (PayPal, coins, MN2, points, on-chain)."""
    row = row or {}
    raw = str(row.get("payment_method") or row.get("price_type") or "").strip().lower()
    if raw in _PAYMENT_LABELS:
        return _PAYMENT_LABELS[raw]
    if raw:
        return raw.replace("_", " ")
    source = str(row.get("source") or "")
    if source == "listing":
        return "Coins"
    if source == "masternode_hosting":
        return "PayPal"
    return "—"


def attach_payment_fields(row: Dict[str, Any]) -> Dict[str, Any]:
    """Fill payment_method + labels without inventing a missing rail."""
    pt = str(row.get("price_type") or "").strip().lower()
    method = str(row.get("payment_method") or "").strip().lower()
    if not method:
        if pt in ("paypal", "paypal_mn2_hosting"):
            method = "paypal"
        elif pt in ("coins", "credits"):
            method = "coins"
        elif pt in ("mn2", "mn2_onchain"):
            method = pt
        elif pt in ("unified_points", "points"):
            method = "points"
        elif str(row.get("source") or "") == "listing":
            method = "coins"
        elif str(row.get("source") or "") == "masternode_hosting":
            method = "paypal"
    if method:
        row["payment_method"] = method
    row["payment_method_label"] = payment_method_label(row)
    if not row.get("amount_label"):
        row["amount_label"] = format_price_label(row)
    return row


def _safe_purchases(user_id: str, limit: int) -> List[Dict[str, Any]]:
    try:
        from backend.services.shop_db_service import get_purchases

        return list(get_purchases(user_id, limit=limit) or [])
    except Exception:
        return []


def _safe_listings(user_id: str, limit: int) -> Dict[str, List[Dict[str, Any]]]:
    empty = {"selling": [], "bought": [], "sold": []}
    try:
        from backend.services.shop_auction_service import list_user_listings

        data = list_user_listings(user_id, limit=limit) or {}
        return {
            "selling": list(data.get("selling") or []),
            "bought": list(data.get("bought") or []),
            "sold": list(data.get("sold") or []),
        }
    except Exception:
        return empty


def _safe_hosting(user_id: str, limit: int) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    stats: Dict[str, Any] = {"paid_orders": 0, "pending_orders": 0, "by_payment_method": {}}
    try:
        from backend.services.mn2_masternode_hosting_service import hosting_stats, list_user_orders

        stats = hosting_stats() or stats
        rows = list(list_user_orders(user_id, limit=limit) or [])
        return rows, stats
    except Exception:
        return [], stats


def listing_to_order_row(listing: Dict[str, Any], role: str) -> Dict[str, Any]:
    """Normalize a stall/auction listing into the shared order-row shape."""
    row = dict(listing or {})
    status = str(row.get("status") or "").strip().lower()
    if role == "bought" and status in ("sold", "completed", ""):
        status = "bought"
    elif role == "sold":
        status = "sold"
    elif not status:
        status = "active"
    row["source"] = "listing"
    row["listing_role"] = role
    row["id"] = row.get("listing_id") or row.get("id")
    row["price_type"] = "coins"
    row["payment_method"] = "coins"
    if row.get("price_paid_coins") is None:
        row["price_paid_coins"] = row.get("price_coins") or 0
    row["purchase_status"] = status
    row["status"] = status
    row["created_at"] = row.get("sold_at") or row.get("cancelled_at") or row.get("created_at")
    row["status_bucket"] = order_status_bucket(status)
    return attach_payment_fields(row)


def flatten_stall_listings(buckets: Dict[str, List[Dict[str, Any]]]) -> List[Dict[str, Any]]:
    seen = set()
    out: List[Dict[str, Any]] = []
    order = (
        ("sold", buckets.get("sold") or []),
        ("bought", buckets.get("bought") or []),
        ("selling", buckets.get("selling") or []),
    )
    for role, rows in order:
        for listing in rows:
            lid = str((listing or {}).get("listing_id") or "")
            key = (lid, role)
            if not lid or key in seen:
                continue
            seen.add(key)
            out.append(listing_to_order_row(listing, role))
    return out


def hosting_order_to_row(order: Dict[str, Any]) -> Dict[str, Any]:
    """Sanitize a masternode hosting order into the shared order-row shape. No keys."""
    raw = dict(order or {})
    status = str(raw.get("status") or "").strip().lower()
    method = str(raw.get("payment_method") or "").strip().lower()
    slots = int(raw.get("slots") or 1)
    oid = str(raw.get("order_id") or raw.get("id") or "").strip()
    price_type = "paypal_mn2_hosting"
    if method in ("mn2", "mn2_onchain"):
        price_type = method
    elif method in ("coins", "credits"):
        price_type = "coins"
    elif method == "paypal" or not method:
        price_type = "paypal_mn2_hosting"
        if not method:
            method = "paypal"
    row: Dict[str, Any] = {
        "id": oid,
        "order_id": oid,
        "item_id": "mn2_masternode_hosting",
        "item_name": f"Masternode hosting × {slots}",
        "quantity": slots,
        "slots": slots,
        "usd_total": raw.get("usd_total"),
        "usd_per_slot": raw.get("usd_per_slot"),
        "coins_total": raw.get("coins_total"),
        "mn2_total": raw.get("mn2_total"),
        "price_type": price_type,
        "payment_method": method or "paypal",
        "price_paid_coins": int(raw.get("coins_total") or 0),
        "price_paid_points": {"usd": raw.get("usd_total"), "mn2": raw.get("mn2_total")},
        "purchase_status": status,
        "status": status,
        "source": "masternode_hosting",
        "created_at": raw.get("paid_at") or raw.get("created_at"),
        "paid_at": raw.get("paid_at"),
        "expires_at": raw.get("expires_at"),
        "host_ids": list(raw.get("host_ids") or []),
        "status_bucket": order_status_bucket(status),
        "subcategory": "hosting",
    }
    return attach_payment_fields(row)


def _paypal_log_rows(user_id: str, limit: int) -> List[Dict[str, Any]]:
    uid = str(user_id or "").strip()
    if not uid or not os.path.isfile(_PAYPAL_LOG):
        return []
    out: List[Dict[str, Any]] = []
    try:
        with open(_PAYPAL_LOG, "r", encoding="utf-8") as fh:
            lines = fh.readlines()[-2000:]
    except OSError:
        return []
    for line in reversed(lines):
        m = _PURCHASE_LOG_RE.search(line)
        if not m:
            continue
        if str(m.group("user_id") or "").strip() != uid:
            continue
        item_id = str(m.group("item_id") or "").strip()
        blob = f"{item_id} {m.group('item_name') or ''}".lower()
        if "masternode" in blob or item_id.startswith("mnq_"):
            continue
        try:
            usd = float(m.group("amount"))
        except (TypeError, ValueError):
            usd = 0.0
        coins = int(m.group("coins") or 0)
        source = str(m.group("source") or "paypal").strip().lower()
        method = "paypal" if source in ("paypal", "paypal_mn2_pack") else source
        order_id = str(m.group("order_id") or "").strip()
        row = {
            "id": f"paypal-log:{order_id or item_id}",
            "item_id": item_id,
            "item_name": str(m.group("item_name") or item_id).strip() or item_id,
            "quantity": 1,
            "price_type": "paypal" if method == "paypal" else method,
            "payment_method": method,
            "price_paid_coins": coins,
            "price_paid_points": {"usd": usd},
            "purchase_status": "completed",
            "created_at": str(m.group("ts") or "").replace(" UTC", "Z").replace(" ", "T"),
            "source": "purchase",
        }
        out.append(attach_payment_fields(row))
        if len(out) >= limit:
            break
    return out


def _exchange_shop_rows(user_id: str, limit: int) -> List[Dict[str, Any]]:
    uid = str(user_id or "").strip()
    if not uid:
        return []
    try:
        from backend.services.exchange_shop_service import _item_map, _load_state

        st = _load_state(uid)
        catalog = _item_map()
    except Exception:
        return []
    out: List[Dict[str, Any]] = []
    for idx, rec in enumerate(reversed(list(st.get("purchases") or []))):
        if not isinstance(rec, dict):
            continue
        iid = str(rec.get("item_id") or "").strip()
        if not iid:
            continue
        item = catalog.get(iid) or {}
        mn2 = rec.get("price_mn2") or rec.get("spent_mn2") or 0
        row = {
            "id": f"exchange:{iid}:{rec.get('ts') or idx}",
            "item_id": iid,
            "item_name": item.get("name") or iid,
            "quantity": 1,
            "price_type": "mn2",
            "payment_method": "mn2",
            "price_paid_points": {"mn2": mn2},
            "purchase_status": "completed",
            "created_at": rec.get("ts"),
            "source": "purchase",
            "category": "mn2_crypto",
        }
        out.append(attach_payment_fields(row))
        if len(out) >= limit:
            break
    return out


def _onchain_shop_rows(user_id: str, limit: int) -> List[Dict[str, Any]]:
    uid = str(user_id or "").strip()
    if not uid:
        return []
    try:
        from backend.services import mn2_order_payment_service as ops

        orders = ops._load() or []
    except Exception:
        return []
    out: List[Dict[str, Any]] = []
    for rec in reversed(list(orders)):
        if not isinstance(rec, dict):
            continue
        if str(rec.get("user_id") or "") != uid:
            continue
        product = str(rec.get("product") or "shop")
        if product == "mn2_masternode_hosting":
            continue
        status = str(rec.get("status") or rec.get("purchase_status") or "pending").lower()
        row = {
            "id": rec.get("payment_ref") or rec.get("id") or rec.get("item_id"),
            "item_id": rec.get("item_id"),
            "item_name": rec.get("item_name") or rec.get("item_id") or "On-chain order",
            "quantity": rec.get("quantity") or 1,
            "price_type": "mn2_onchain",
            "payment_method": "mn2_onchain",
            "price_paid_points": {"mn2": rec.get("amount_mn2") or rec.get("amount_received")},
            "purchase_status": "completed" if status in ("fulfilled", "confirmed", "paid") else status,
            "created_at": rec.get("fulfilled_at") or rec.get("created_at"),
            "source": "purchase",
        }
        out.append(attach_payment_fields(row))
        if len(out) >= limit:
            break
    return out


def _merge_purchase_rows(primary: List[Dict[str, Any]], extras: List[Dict[str, Any]], limit: int) -> List[Dict[str, Any]]:
    seen = set()
    out: List[Dict[str, Any]] = []

    def _key(row: Dict[str, Any]) -> Tuple[str, str, str]:
        return (
            str(row.get("id") or ""),
            str(row.get("item_id") or ""),
            str(row.get("created_at") or "")[:19],
        )

    for row in list(primary) + list(extras):
        if not isinstance(row, dict):
            continue
        key = _key(row)
        alt = (str(row.get("item_id") or ""), str(row.get("created_at") or "")[:19])
        if key in seen or (alt[0] and alt in {(k[1], k[2]) for k in seen}):
            continue
        seen.add(key)
        out.append(row)
        if len(out) >= limit:
            break
    return out


def collect_shop_purchases(user_id: str, limit: int = 50) -> List[Dict[str, Any]]:
    """Catalog purchases plus PayPal/exchange/on-chain rows. Never includes hosting."""
    cap = _cap(limit)
    uid = str(user_id or "").strip() or "default_user"
    primary = _safe_purchases(uid, cap)
    extras = _paypal_log_rows(uid, cap) + _exchange_shop_rows(uid, cap) + _onchain_shop_rows(uid, cap)
    merged = _merge_purchase_rows(primary, extras, cap)
    rows = _enrich(merged)
    for row in rows:
        row["source"] = row.get("source") or "purchase"
        attach_payment_fields(row)
    return rows


def collect_hosting_orders(user_id: str, limit: int = 50) -> Dict[str, Any]:
    cap = _cap(limit)
    uid = str(user_id or "").strip() or "default_user"
    raw, stats = _safe_hosting(uid, cap)
    rows = [hosting_order_to_row(o) for o in raw]
    return {
        "user_id": uid,
        "hosting": rows,
        "site": {
            "paid_orders": int(stats.get("paid_orders") or 0),
            "pending_orders": int(stats.get("pending_orders") or 0),
            "by_payment_method": stats.get("by_payment_method") or {},
        },
    }


def build_user_order_lists(user_id: str, limit: int = 50) -> Dict[str, Any]:
    """Purchases + stall + hosting for one profile. Never dumps hosting secrets."""
    cap = _cap(limit)
    uid = str(user_id or "").strip() or "default_user"
    purchases = collect_shop_purchases(uid, cap)
    listings = _enrich(flatten_stall_listings(_safe_listings(uid, cap)))
    hosting_payload = collect_hosting_orders(uid, cap)
    hosting = hosting_payload.get("hosting") or []
    return {
        "success": True,
        "user_id": uid,
        "purchases": purchases,
        "listings": listings,
        "hosting": hosting,
        "hosting_site": hosting_payload.get("site") or {},
        "counts": {
            "shop": len(purchases),
            "stall": len(listings),
            "hosting": len(hosting),
        },
    }


def _normalize_source(source: str) -> str:
    raw = str(source or "purchase").strip().lower()
    if raw in ("stall", "auction"):
        return "listing"
    if raw in ("hosting", "mn2_hosting", "masternode"):
        return "masternode_hosting"
    return raw


def resolve_checked_orders(user_id: str, items: Optional[Iterable[Dict[str, Any]]], limit: int = 100) -> List[Dict[str, Any]]:
    """Map checkbox selections onto this user's purchase/listing/hosting rows only."""
    payload = build_user_order_lists(user_id, limit=limit)
    index: Dict[tuple, Dict[str, Any]] = {}
    for row in payload["purchases"]:
        index[("purchase", str(row.get("id") or ""))] = row
    for row in payload["listings"]:
        index[("listing", str(row.get("listing_id") or row.get("id") or ""))] = row
    for row in payload.get("hosting") or []:
        oid = str(row.get("order_id") or row.get("id") or "")
        index[("masternode_hosting", oid)] = row
    out: List[Dict[str, Any]] = []
    seen = set()
    for raw in items or []:
        if not isinstance(raw, dict):
            continue
        source = _normalize_source(raw.get("source") or "purchase")
        oid = str(raw.get("id") or raw.get("listing_id") or raw.get("order_id") or "").strip()
        key = (source, oid)
        row = index.get(key)
        if not row or key in seen:
            continue
        seen.add(key)
        out.append(row)
    return out


def pdf_for_checked_orders(user_id: str, items: Optional[Iterable[Dict[str, Any]]]) -> bytes:
    rows = resolve_checked_orders(user_id, items)
    return build_orders_pdf(user_id=str(user_id or ""), rows=rows)
