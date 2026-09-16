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
    {"id": "other", "label": "Other"},
]

SPECIAL_GROUPS: Dict[str, List[Dict[str, str]]] = {
    "coin_packs": [
        {"id": "all", "label": "All packs"},
        {"id": "starter", "label": "Starter"},
        {"id": "value", "label": "Best value"},
        {"id": "whale", "label": "Whale"},
    ],
    "mn2_services": [
        {"id": "all", "label": "All services"},
        {"id": "hosting", "label": "Hosting"},
        {"id": "wallet", "label": "Wallet & on-ramp"},
        {"id": "staking", "label": "Staking"},
        {"id": "market", "label": "Markets"},
        {"id": "reports", "label": "Reports"},
    ],
    "boosters": [
        {"id": "all", "label": "All"},
        {"id": "resources", "label": "Battle resources"},
        {"id": "boosts", "label": "XP & boosts"},
        {"id": "gametime", "label": "Game time"},
        {"id": "battle", "label": "Battle power"},
    ],
    "mystery_boxes": [
        {"id": "all", "label": "All boxes"},
        {"id": "common", "label": "Bronze"},
        {"id": "rare", "label": "Silver"},
        {"id": "legendary", "label": "Gold"},
    ],
}

TX_SUBCATS: List[Dict[str, str]] = [
    {"id": "all", "label": "All"},
    {"id": "deposit", "label": "Deposits"},
    {"id": "withdraw", "label": "Withdrawals"},
    {"id": "spend", "label": "Shop spend"},
    {"id": "reward", "label": "Rewards"},
    {"id": "other", "label": "Other"},
]

CASINO_PARENTS: List[Dict[str, Any]] = [
    {"id": "all", "label": "All", "categories": []},
    {"id": "look", "label": "Look", "categories": ["avatar", "table_skin", "card_back", "slot_theme", "display", "banner"]},
    {"id": "play", "label": "Play", "categories": ["booster", "token", "emote", "celebration"]},
    {"id": "vip", "label": "VIP", "categories": ["vip_flair"]},
]

EXCHANGE_PARENTS: List[Dict[str, Any]] = [
    {"id": "all", "label": "All", "categories": []},
    {"id": "play", "label": "Play", "categories": ["skill", "boost", "reward"]},
    {"id": "rent", "label": "Rent", "categories": ["rental", "rental_voucher"]},
    {"id": "ops", "label": "Ops", "categories": ["trust", "fee", "tool"]},
]

PROFILE_HUB_PARENTS: List[Dict[str, Any]] = [
    {"id": "all", "label": "All", "routes": []},
    {"id": "you", "label": "You", "routes": ["overview", "avatar", "account", "settings"]},
    {"id": "play", "label": "Play", "routes": ["skills", "trophies", "points", "battle", "progress"]},
    {"id": "market", "label": "Shop & wallet", "routes": ["shop", "wallet"]},
    {"id": "ops", "label": "Ops", "routes": ["security", "agents", "activity", "lab", "leaderboard"]},
]

MARKETPLACE_TIERS: List[Dict[str, str]] = [
    {"id": "all", "label": "All bots"},
    {"id": "starter", "label": "Starter"},
    {"id": "pro", "label": "Pro"},
    {"id": "elite", "label": "Elite & Quant"},
]

RENTAL_GROUPS: List[Dict[str, str]] = [
    {"id": "all", "label": "All rentals"},
    {"id": "bots", "label": "Timed bots"},
    {"id": "daemons", "label": "Daemons"},
]

P2P_PRICE_GROUPS: List[Dict[str, str]] = [
    {"id": "all", "label": "All listings"},
    {"id": "budget", "label": "Budget"},
    {"id": "mid", "label": "Mid"},
    {"id": "premium", "label": "Premium"},
]

DIGITAL_DOWNLOAD_SUBCATS: List[Dict[str, str]] = [
    {"id": "all", "label": "All downloads"},
    {"id": "themes", "label": "Themes"},
    {"id": "prompts", "label": "Prompt packs"},
    {"id": "other", "label": "Other"},
]

NAV_GROUPS: List[Dict[str, Any]] = [
    {"id": "all", "label": "All", "ids": []},
    {
        "id": "play",
        "label": "Play",
        "ids": ["game", "battle", "trophies", "quests", "casino", "battlegrounds", "starmap25"],
    },
    {"id": "create", "label": "Create", "ids": ["generator", "podcast", "gallery", "lab", "library"]},
    {
        "id": "market",
        "label": "Market",
        "ids": ["shop", "exchange", "market", "wallets", "explorer", "staking_leaderboard", "staking_teams"],
    },
    {"id": "people", "label": "People", "ids": ["profile", "agents", "social", "chat", "customers", "camgirls"]},
    {
        "id": "ops",
        "label": "Ops",
        "ids": ["agent_support", "debugger", "aggregator", "agents_control", "hosting", "profit", "news"],
    },
]

_PARENT_BY_CAT = {
    cat: p["id"]
    for p in CATALOG_PARENTS
    for cat in (p.get("categories") or [])
}

_CASINO_PARENT_BY_CAT = {
    cat: p["id"]
    for p in CASINO_PARENTS
    for cat in (p.get("categories") or [])
}

_EXCHANGE_PARENT_BY_CAT = {
    cat: p["id"]
    for p in EXCHANGE_PARENTS
    for cat in (p.get("categories") or [])
}

_PROFILE_PARENT_BY_ROUTE = {
    route: p["id"]
    for p in PROFILE_HUB_PARENTS
    for route in (p.get("routes") or [])
}

_NAV_GROUP_BY_ID = {
    lid: p["id"]
    for p in NAV_GROUPS
    for lid in (p.get("ids") or [])
}


def parent_for_category(category: Optional[str]) -> str:
    cat = str(category or "other").strip().lower()
    return _PARENT_BY_CAT.get(cat, "ops" if cat in ("inventory", "other", "") else "other")


def casino_parent_for(category: Optional[str]) -> str:
    cat = str(category or "other").strip().lower()
    return _CASINO_PARENT_BY_CAT.get(cat, "other")


def exchange_parent_for(category: Optional[str]) -> str:
    cat = str(category or "other").strip().lower()
    return _EXCHANGE_PARENT_BY_CAT.get(cat, "other")


def profile_hub_parent_for(route: Optional[str]) -> str:
    key = str(route or "").strip().lower()
    return _PROFILE_PARENT_BY_ROUTE.get(key, "other")


def nav_group_for(link_id: Optional[str]) -> str:
    key = str(link_id or "").strip().lower()
    if key in ("home",):
        return "all"
    return _NAV_GROUP_BY_ID.get(key, "ops")


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
    if any(x in blob for x in ("kit", "verification", "dna", "magnet", "tracker", "geo", "aggregator", "navigator")):
        return "kits"
    if cat == "inventory":
        return "stacks" if "pack" in blob else "kits"
    return "other"


def special_subcategory_for(table: str, row: Optional[Dict[str, Any]] = None) -> str:
    """Classify rows in shop special tables (coin packs, MN2 services, boosters, boxes)."""
    item = row or {}
    kind = str(table or "").strip().lower()
    blob = " ".join(
        str(item.get(k) or "")
        for k in ("id", "name", "description", "service_id", "category", "rarity", "kind")
    ).lower()

    if kind == "coin_packs":
        coins = float(item.get("coins_granted") or 0)
        price = float(item.get("price_usd") or 0)
        featured = bool(item.get("featured") or str(item.get("tag") or "").lower() == "featured")
        if coins >= 1500 or price >= 9.0:
            return "whale"
        if featured or (coins >= 400 and coins < 1500) or (price >= 3.0 and price < 9.0):
            return "value"
        return "starter"

    if kind == "mn2_services":
        if any(x in blob for x in ("hosting", "masternode")):
            return "hosting"
        if "stak" in blob:
            return "staking"
        if any(x in blob for x in ("p2p", "trader", "market")):
            return "market"
        if any(x in blob for x in ("onramp", "on-ramp", "wallet")):
            return "wallet"
        if any(x in blob for x in ("reserve", "proof", "report")):
            return "reports"
        return "wallet"

    if kind == "boosters":
        if item.get("kind") == "resource" or "resource" in blob:
            return "resources"
        if any(x in blob for x in ("game time", "gametime", "weekend pass")):
            return "gametime"
        if "battle" in blob:
            return "battle"
        return "boosts"

    if kind == "mystery_boxes":
        rarity = str(item.get("rarity") or "").strip().lower()
        if rarity in ("common", "rare", "legendary"):
            return rarity
        if "bronze" in blob or "common" in blob:
            return "common"
        if "silver" in blob or "rare" in blob:
            return "rare"
        if any(x in blob for x in ("gold", "legend", "whale")):
            return "legendary"
        return "common"

    return "other"


def tx_subcategory_for(tx_type: Optional[str]) -> str:
    blob = str(tx_type or "").strip().lower()
    if any(x in blob for x in ("deposit", "credit_in", "onramp")):
        return "deposit"
    if any(x in blob for x in ("withdraw", "payout")):
        return "withdraw"
    if any(x in blob for x in ("spend", "purchase", "shop", "buy")):
        return "spend"
    if any(x in blob for x in ("reward", "stake", "interest", "earn", "airdrop")):
        return "reward"
    return "other"


def marketplace_tier_for(row: Optional[Dict[str, Any]] = None) -> str:
    item = row or {}
    tier = str(item.get("tier") or "").strip().lower()
    price = float(item.get("price_mn2") or 0)
    if "starter" in tier or (0 < price < 500):
        return "starter"
    if "pro" in tier or (500 <= price < 1200):
        return "pro"
    if any(x in tier for x in ("elite", "quant")) or price >= 1200:
        return "elite"
    return "starter"


def rental_group_for(row: Optional[Dict[str, Any]] = None) -> str:
    item = row or {}
    return "daemons" if item.get("daemon") else "bots"


def p2p_price_group_for(row: Optional[Dict[str, Any]] = None) -> str:
    item = row or {}
    price = float(item.get("price_usd_per_mn2") or 0)
    if price <= 0:
        return "other"
    if price < 0.1:
        return "budget"
    if price < 0.5:
        return "mid"
    return "premium"


def digital_download_subcat_for(row: Optional[Dict[str, Any]] = None) -> str:
    item = row or {}
    blob = " ".join(
        str(item.get(k) or "") for k in ("id", "name", "category", "kind")
    ).lower()
    if any(x in blob for x in ("theme", "skin", "wallpaper")):
        return "themes"
    if any(x in blob for x in ("prompt", "pack", "template")):
        return "prompts"
    return "other"


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
        out.append(item)
    return out


def taxonomy_payload() -> Dict[str, Any]:
    return {
        "parents": CATALOG_PARENTS,
        "inventory_subcategories": INVENTORY_SUBCATS,
        "special_groups": SPECIAL_GROUPS,
        "tx_subcategories": TX_SUBCATS,
        "casino_parents": CASINO_PARENTS,
        "exchange_parents": EXCHANGE_PARENTS,
        "profile_hub_parents": PROFILE_HUB_PARENTS,
        "nav_groups": NAV_GROUPS,
        "marketplace_tiers": MARKETPLACE_TIERS,
        "rental_groups": RENTAL_GROUPS,
        "p2p_price_groups": P2P_PRICE_GROUPS,
        "digital_download_subcats": DIGITAL_DOWNLOAD_SUBCATS,
    }
