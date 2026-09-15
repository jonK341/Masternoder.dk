"""Shop catalog + inventory taxonomy: parent groups and owned-item subcategories."""
from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional

CATALOG_PARENTS: List[Dict[str, Any]] = [
    {"id": "all", "label": "All", "categories": []},
    {
        "id": "play",
        "label": "Play",
        "categories": ["battle", "boosts", "starmap25", "trophies", "achievement", "skill"],
    },
    {"id": "look", "label": "Look", "categories": ["themes", "cosmetic", "stories"]},
    {
        "id": "build",
        "label": "Build",
        "categories": ["tech", "upgrades", "lab", "generation", "progression"],
    },
    {
        "id": "wallet",
        "label": "Wallet",
        "categories": ["currency", "buy_coins", "unified_points", "mn2_services", "mn2_crypto"],
    },
    {
        "id": "collect",
        "label": "Collect",
        "categories": ["top25", "exclusive", "premium", "bundles", "digital_goods"],
    },
    {"id": "ops", "label": "Ops & packs", "categories": ["inventory", "marketing", "social"]},
]

INVENTORY_SUBCATS: List[Dict[str, str]] = [
    {"id": "all", "label": "All"},
    {"id": "stacks", "label": "Super stacks"},
    {"id": "kits", "label": "Kits & tools"},
    {"id": "maps", "label": "Star maps"},
    {"id": "lab", "label": "Lab"},
    {"id": "media", "label": "Media"},
    {"id": "knowledge", "label": "Knowledge"},
    {"id": "boosts", "label": "Boosts"},
    {"id": "look", "label": "Cosmetics"},
    {"id": "battle", "label": "Battle"},
    {"id": "collect", "label": "Collectibles"},
    {"id": "wallet", "label": "Wallet"},
    {"id": "hosting", "label": "Hosting"},
    {"id": "other", "label": "Other"},
]

_PARENT_BY_CAT = {
    cat: p["id"]
    for p in CATALOG_PARENTS
    for cat in (p.get("categories") or [])
}


def parent_for_category(category: Optional[str]) -> str:
    cat = str(category or "other").strip().lower()
    return _PARENT_BY_CAT.get(cat, "ops" if cat in ("inventory", "other", "") else "other")


def subcategory_for(item_id: Optional[str], name: Optional[str], category: Optional[str] = None) -> str:
    cat = str(category or "").strip().lower()
    blob = f"{item_id or ''} {name or ''} {cat}".lower()

    if cat in ("themes", "cosmetic", "stories") or any(
        x in blob for x in ("theme", "cosmetic", "avatar", "skin", "banner")
    ):
        if cat not in ("boosts", "battle"):
            return "look"
    if cat in ("top25", "exclusive", "premium", "bundles", "digital_goods") or any(
        x in blob for x in ("legend", "top25", "bundle", "exclusive")
    ):
        if "booster" not in blob:
            return "collect"
    if "masternode" in blob or (cat == "mn2_services" and "host" in blob):
        return "hosting"
    if cat in ("currency", "buy_coins", "unified_points", "mn2_services", "mn2_crypto") or "mn2" in blob:
        if cat not in ("boosts", "battle"):
            return "wallet"
    if cat == "boosts" or "booster" in blob or "game time" in blob:
        return "boosts"
    if cat == "battle" or "battle" in blob:
        return "battle"
    if any(x in blob for x in ("star map", "starmap", "star-map")):
        return "maps"
    if "lab" in blob:
        return "lab"
    if any(x in blob for x in ("clip", "video", "3d monitor", "flyer")):
        return "media"
    if any(
        x in blob
        for x in ("rulebook", "knowledge", "psych", "theory", "framing", "influence")
    ):
        return "knowledge"
    if any(x in blob for x in ("super stack", "super-stack", " pack t", "engine pack", " ops pack", "vault stack")):
        return "stacks"
    if any(x in blob for x in ("kit", "verification", "dna", "magnet", "tracker", "geo", "aggregator")):
        return "kits"
    if cat == "inventory":
        return "stacks" if "pack" in blob else "kits"
    return "other"


PENDING_STATUSES = frozenset(
    {
        "pending",
        "pending_payment",
        "quoted",
        "unpaid",
        "awaiting",
        "processing",
        "active",
        "listed",
        "reserved",
    }
)
COMPLETED_STATUSES = frozenset(
    {"completed", "captured", "paid", "fulfilled", "sold", "bought"}
)
REFUNDED_STATUSES = frozenset({"refunded"})
CANCELLED_STATUSES = frozenset({"cancelled", "canceled", "expired", "failed"})


def order_status_bucket(status: Optional[str]) -> str:
    """Map a raw purchase_status onto list filter buckets."""
    raw = str(status or "completed").strip().lower()
    if raw in PENDING_STATUSES:
        return "pending"
    if raw in REFUNDED_STATUSES:
        return "refunded"
    if raw in CANCELLED_STATUSES:
        return "cancelled"
    return "completed"


def classify_item(
    *,
    item_id: Optional[str] = None,
    name: Optional[str] = None,
    category: Optional[str] = None,
) -> Dict[str, str]:
    cat = str(category or "other").strip().lower() or "other"
    return {
        "category": cat,
        "parent": parent_for_category(cat),
        "subcategory": subcategory_for(item_id, name, cat),
    }


def enrich_rows(rows: Iterable[Dict[str, Any]], catalog_by_id: Optional[Dict[str, Dict[str, Any]]] = None) -> List[Dict[str, Any]]:
    catalog = catalog_by_id or {}
    out: List[Dict[str, Any]] = []
    for row in rows or []:
        if not isinstance(row, dict):
            continue
        item = dict(row)
        iid = item.get("item_id") or item.get("id")
        cat_item = catalog.get(str(iid)) if iid else None
        if isinstance(cat_item, dict):
            item.setdefault("item_name", cat_item.get("name"))
            item.setdefault("icon", cat_item.get("icon"))
            item.setdefault("rarity", cat_item.get("rarity"))
            if not item.get("category"):
                item["category"] = cat_item.get("category")
        classified = classify_item(
            item_id=str(iid or ""),
            name=str(item.get("item_name") or item.get("name") or ""),
            category=item.get("category"),
        )
        item.update(classified)
        item["status_bucket"] = order_status_bucket(item.get("purchase_status") or item.get("status"))
        out.append(item)
    return out


def taxonomy_payload() -> Dict[str, Any]:
    return {
        "parents": CATALOG_PARENTS,
        "inventory_subcategories": INVENTORY_SUBCATS,
    }
