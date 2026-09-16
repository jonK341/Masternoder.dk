"""Tier C5 — compendium free pages 1–3, premium unlock SKUs, access checks."""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Set

FREE_PAGE_MAX = 3

SKU_FULL = "compendium-premium-full"
SKU_VOLUME = "compendium-chapters-4-12"

TIER_FULL = "full"
TIER_VOLUME = "volume_2"

RULEBOOK_PAGE_MAP = {
    1: 12,
    4: 13,
    5: 14,
    6: 15,
    7: 16,
    8: 17,
    9: 18,
    10: 19,
    11: 20,
    12: 21,
    13: 22,
    14: 23,
    15: 24,
    16: 25,
}


def page_number_for_path(path: str) -> Optional[int]:
    p = (path or "").lower()
    if "hunters-rulebook" in p:
        return 11
    if "rulebook-v3-2" in p:
        return None
    import re

    m = re.search(r"rulebook-v(\d+)", p)
    if m:
        return RULEBOOK_PAGE_MAP.get(int(m.group(1)))
    m = re.search(r"page-(\d+)", p)
    if m:
        return int(m.group(1))
    if p.rstrip("/").endswith("/compendium") or "compendium/index" in p:
        return 24
    return None


def _load_compendium_data(user_id: str) -> dict:
    from backend.services.user_engagement import _load

    data = _load(user_id, "compendium_pages.json")
    data.setdefault("pages_read", [])
    data.setdefault("premium_tiers", [])
    return data


def _save_compendium_data(user_id: str, data: dict) -> None:
    from backend.services.user_engagement import _save

    _save(user_id, "compendium_pages.json", data)


def _tier_unlocks_page(tier: str, page_number: int) -> bool:
    if page_number <= FREE_PAGE_MAX:
        return True
    if tier == TIER_FULL:
        return 4 <= page_number <= 25
    if tier == TIER_VOLUME:
        return 4 <= page_number <= 12
    return False


def user_tiers(user_id: str) -> Set[str]:
    data = _load_compendium_data(user_id)
    tiers = data.get("premium_tiers") or []
    if isinstance(tiers, str):
        tiers = [tiers]
    return {str(t).strip() for t in tiers if str(t).strip()}


def grant_compendium_tier(user_id: str, tier: str) -> Dict[str, Any]:
    uid = (user_id or "").strip()
    tier = (tier or TIER_FULL).strip()
    if tier not in (TIER_FULL, TIER_VOLUME):
        tier = TIER_FULL
    data = _load_compendium_data(uid)
    tiers = set(user_tiers(uid))
    tiers.add(tier)
    if TIER_FULL in tiers:
        tiers.add(TIER_VOLUME)
    data["premium_tiers"] = sorted(tiers)
    _save_compendium_data(uid, data)
    return {"success": True, "user_id": uid, "premium_tiers": data["premium_tiers"]}


def can_access_page(user_id: str, page_number: int) -> bool:
    try:
        page_number = int(page_number)
    except (TypeError, ValueError):
        return False
    if page_number <= FREE_PAGE_MAX:
        return True
    tiers = user_tiers(user_id)
    return any(_tier_unlocks_page(t, page_number) for t in tiers)


def get_access_status(user_id: str) -> Dict[str, Any]:
    tiers = sorted(user_tiers(user_id))
    has_full = TIER_FULL in tiers
    has_volume = TIER_VOLUME in tiers or has_full
    unlocked: List[int] = list(range(1, FREE_PAGE_MAX + 1))
    if has_volume:
        unlocked.extend(range(4, 13))
    if has_full:
        unlocked.extend(range(13, 26))
    unlocked = sorted(set(unlocked))
    locked = [n for n in range(1, 26) if n not in set(unlocked)]
    return {
        "success": True,
        "free_pages_max": FREE_PAGE_MAX,
        "premium_tiers": tiers,
        "has_full_premium": has_full,
        "has_volume_premium": has_volume,
        "unlocked_pages": unlocked,
        "locked_pages": locked,
        "shop_skus": {
            "full": SKU_FULL,
            "volume": SKU_VOLUME,
        },
        "shop_href": "/shop?category=digital_goods",
    }


def tier_for_sku(item_id: str) -> Optional[str]:
    iid = (item_id or "").strip()
    if iid == SKU_FULL:
        return TIER_FULL
    if iid == SKU_VOLUME:
        return TIER_VOLUME
    return None
