"""Shop-native order lists: catalog purchases + stall/auction listings."""
from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional

from backend.services.shop_order_pdf_service import build_orders_pdf, format_price_label
from backend.services.shop_taxonomy_service import enrich_rows, order_status_bucket


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
    if row.get("price_paid_coins") is None:
        row["price_paid_coins"] = row.get("price_coins") or 0
    row["purchase_status"] = status
    row["status"] = status
    row["created_at"] = row.get("sold_at") or row.get("cancelled_at") or row.get("created_at")
    row["amount_label"] = format_price_label(row)
    row["status_bucket"] = order_status_bucket(status)
    return row


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


def build_user_order_lists(user_id: str, limit: int = 50) -> Dict[str, Any]:
    """Purchases + stall listings for one profile. Never dumps hosting secrets."""
    cap = max(1, min(int(limit or 50), 100))
    uid = str(user_id or "").strip() or "default_user"
    purchases = _enrich(_safe_purchases(uid, cap))
    for row in purchases:
        row["source"] = "purchase"
        row["amount_label"] = format_price_label(row)
    listings = _enrich(flatten_stall_listings(_safe_listings(uid, cap)))
    return {
        "success": True,
        "user_id": uid,
        "purchases": purchases,
        "listings": listings,
        "counts": {"shop": len(purchases), "stall": len(listings)},
    }


def resolve_checked_orders(user_id: str, items: Optional[Iterable[Dict[str, Any]]], limit: int = 100) -> List[Dict[str, Any]]:
    """Map checkbox selections onto this user's purchase/listing rows only."""
    payload = build_user_order_lists(user_id, limit=limit)
    index: Dict[tuple, Dict[str, Any]] = {}
    for row in payload["purchases"]:
        index[("purchase", str(row.get("id") or ""))] = row
    for row in payload["listings"]:
        index[("listing", str(row.get("listing_id") or row.get("id") or ""))] = row
    out: List[Dict[str, Any]] = []
    seen = set()
    for raw in items or []:
        if not isinstance(raw, dict):
            continue
        source = str(raw.get("source") or "purchase").strip().lower()
        if source in ("stall", "auction"):
            source = "listing"
        oid = str(raw.get("id") or raw.get("listing_id") or "").strip()
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
