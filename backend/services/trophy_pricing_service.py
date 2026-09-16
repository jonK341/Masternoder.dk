"""Trophy dynamic pricing (plan 001 P-U1)."""
from __future__ import annotations

import json
import math
import os
import threading
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

_LOCK = threading.RLock()
_BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_CONFIG_PATH = os.path.join(_BASE, "data", "trophy_pricing_config.json")


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


def _load_config() -> Dict[str, Any]:
    with _LOCK:
        if not os.path.isfile(_CONFIG_PATH):
            return {"defaults": {}, "items": {}}
        try:
            with open(_CONFIG_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
            return data if isinstance(data, dict) else {"defaults": {}, "items": {}}
        except Exception:
            return {"defaults": {}, "items": {}}


def _item_config(item_id: str, defaults: Dict[str, Any]) -> Dict[str, Any]:
    cfg = _load_config()
    items = cfg.get("items") if isinstance(cfg.get("items"), dict) else {}
    item_cfg = items.get(item_id) if isinstance(items.get(item_id), dict) else {}
    merged = dict(defaults or {})
    merged.update(item_cfg)
    return merged


def _parse_ts(value: Any) -> Optional[datetime]:
    if not value:
        return None
    try:
        raw = str(value).replace("Z", "+00:00")
        dt = datetime.fromisoformat(raw)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except Exception:
        return None


def _sales_7d(item_id: str) -> int:
    cutoff = datetime.now(timezone.utc) - timedelta(days=7)
    total = 0
    iid = (item_id or "").strip()
    if not iid:
        return 0

    try:
        from backend.services.shop_db_service import shop_tables_exist, _get_db
        from sqlalchemy import text

        if shop_tables_exist():
            db = _get_db()
            row = db.session.execute(
                text(
                    """
                    SELECT COALESCE(SUM(quantity), 0) AS qty
                    FROM shop_purchases
                    WHERE item_id = :item_id
                      AND purchase_status = 'completed'
                      AND created_at >= datetime('now', '-7 days')
                    """
                ),
                {"item_id": iid},
            ).fetchone()
            total += int(row.qty or 0) if row else 0
    except Exception:
        pass

    try:
        from backend.services.shop_db_service import _shop_file_root

        purchases_dir = os.path.join(_shop_file_root(), "purchases")
        if os.path.isdir(purchases_dir):
            for name in os.listdir(purchases_dir):
                if not name.endswith(".json"):
                    continue
                path = os.path.join(purchases_dir, name)
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        doc = json.load(f)
                except Exception:
                    continue
                rows = doc.get("purchases") if isinstance(doc, dict) else []
                if not isinstance(rows, list):
                    continue
                for row in rows:
                    if not isinstance(row, dict):
                        continue
                    if (row.get("item_id") or "") != iid:
                        continue
                    if (row.get("purchase_status") or "completed") != "completed":
                        continue
                    created = _parse_ts(row.get("created_at"))
                    if created and created >= cutoff:
                        total += int(row.get("quantity") or 0)
    except Exception:
        pass

    return total


def _auction_listing_count(item_id: str) -> int:
    iid = (item_id or "").strip()
    if not iid:
        return 0
    try:
        from backend.services.shop_auction_service import _load

        return sum(
            1
            for row in _load()
            if (row.get("status") or "") == "active" and (row.get("item_id") or "") == iid
        )
    except Exception:
        return 0


def _global_owner_count(item_id: str) -> int:
    iid = (item_id or "").strip()
    if not iid:
        return 0
    owners = set()
    try:
        from backend.services.shop_db_service import _shop_file_root

        root = os.path.join(_shop_file_root(), "trophy_editions")
        if not os.path.isdir(root):
            return 0
        for name in os.listdir(root):
            if not name.endswith(".json"):
                continue
            uid = name[:-5]
            path = os.path.join(root, name)
            try:
                with open(path, "r", encoding="utf-8") as f:
                    doc = json.load(f)
            except Exception:
                continue
            rows = doc.get("editions") if isinstance(doc, dict) else []
            if not isinstance(rows, list):
                continue
            for row in rows:
                if isinstance(row, dict) and (row.get("item_id") or "") == iid:
                    owners.add(uid)
                    break
    except Exception:
        pass
    return len(owners)


def get_effective_price(item_id: str) -> Dict[str, Any]:
    """Return server authoritative USD/coin price for a trophy SKU."""
    item = _catalog_item(item_id)
    if not item:
        return {"success": False, "error": "trophy_not_found", "item_id": item_id}

    base = _base_price_usd(item)
    if base is None or base <= 0:
        return {"success": False, "error": "price_not_configured", "item_id": item_id}

    cfg = _load_config()
    defaults = cfg.get("defaults") if isinstance(cfg.get("defaults"), dict) else {}
    item_cfg = _item_config(item_id, defaults)

    baseline_weekly = max(1, int(item_cfg.get("baseline_weekly") or defaults.get("baseline_weekly") or 5))
    max_boost = float(item_cfg.get("max_boost") if item_cfg.get("max_boost") is not None else defaults.get("max_boost") or 0.5)
    pop_cap = float(item_cfg.get("pop_cap") if item_cfg.get("pop_cap") is not None else defaults.get("pop_cap") or 0.3)
    pop_weight = float(item_cfg.get("pop_weight") if item_cfg.get("pop_weight") is not None else defaults.get("pop_weight") or 0.05)
    floor_mult = float(item_cfg.get("floor_multiplier") if item_cfg.get("floor_multiplier") is not None else defaults.get("floor_multiplier") or 1.0)
    ceiling_mult = float(item_cfg.get("ceiling_multiplier") if item_cfg.get("ceiling_multiplier") is not None else defaults.get("ceiling_multiplier") or 3.0)

    floor = float(item_cfg.get("floor_price_usd") or item.get("floor_price_usd") or round(base * floor_mult, 2))
    ceiling = float(item_cfg.get("ceiling_price_usd") or item.get("ceiling_price_usd") or round(base * ceiling_mult, 2))
    if ceiling < floor:
        ceiling = floor

    sales_7d = _sales_7d(item_id)
    auction_listings = _auction_listing_count(item_id)
    global_owners = _global_owner_count(item_id)

    demand_ratio = sales_7d / float(baseline_weekly)
    demand_multiplier = 1.0 + min(max_boost, demand_ratio)
    popularity_factor = 1.0 + min(pop_cap, math.log1p(global_owners) * pop_weight)

    raw_effective = base * demand_multiplier * popularity_factor
    effective = min(ceiling, max(floor, round(raw_effective, 2)))

    return {
        "success": True,
        "item_id": item_id,
        "name": item.get("name") or item_id,
        "base_price_usd": base,
        "effective_price_usd": effective,
        "effective_price_coins": int(round(effective * 100)),
        "price_factors": {
            "demand_multiplier": round(demand_multiplier, 4),
            "popularity_factor": round(popularity_factor, 4),
            "floor_price_usd": floor,
            "ceiling_price_usd": ceiling,
            "sales_7d": sales_7d,
            "auction_listings": auction_listings,
            "global_owners": global_owners,
            "baseline_weekly": baseline_weekly,
        },
        "computed_at": _iso(),
        "kind": "trophy",
        "on_chain_mint": False,
    }
