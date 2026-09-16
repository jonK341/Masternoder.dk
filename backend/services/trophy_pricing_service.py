"""Trophy dynamic pricing (plan 001 P-U1 stub — multiplier 1.0 until signals ship)."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Optional


def _iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _catalog_item(item_id: str) -> Optional[Dict[str, Any]]:
    iid = (item_id or "").strip()
    if not iid:
        return None
    try:
        from backend.routes.shop_routes import _get_shop_items, _is_trophy_catalog_item

        for item in _get_shop_items() or []:
            if (item.get("id") or "") == iid and _is_trophy_catalog_item(item):
                return item
    except Exception:
        pass
    return None


def _base_price_usd(item: Dict[str, Any]) -> Optional[float]:
    if item.get("base_price_usd") is not None:
        return float(item["base_price_usd"])
    if item.get("price_usd") is not None:
        return float(item["price_usd"])
    price = item.get("price")
    if isinstance(price, (int, float)) and float(price) > 0:
        return max(0.99, round(float(price) / 100, 2))
    return None


def get_effective_price(item_id: str) -> Dict[str, Any]:
    """Return server authoritative USD price for a trophy SKU."""
    item = _catalog_item(item_id)
    if not item:
        return {"success": False, "error": "trophy_not_found", "item_id": item_id}

    base = _base_price_usd(item)
    if base is None or base <= 0:
        return {"success": False, "error": "price_not_configured", "item_id": item_id}

    floor = float(item.get("floor_price_usd") or base)
    ceiling = float(item.get("ceiling_price_usd") or max(base * 3, base))
    demand_multiplier = 1.0
    popularity_factor = 1.0
    effective = min(ceiling, max(floor, round(base * demand_multiplier * popularity_factor, 2)))

    return {
        "success": True,
        "item_id": item_id,
        "name": item.get("name") or item_id,
        "base_price_usd": base,
        "effective_price_usd": effective,
        "effective_price_coins": int(round(effective * 100)),
        "price_factors": {
            "demand_multiplier": demand_multiplier,
            "popularity_factor": popularity_factor,
            "floor_price_usd": floor,
            "ceiling_price_usd": ceiling,
        },
        "computed_at": _iso(),
        "kind": "trophy",
        "on_chain_mint": False,
    }
