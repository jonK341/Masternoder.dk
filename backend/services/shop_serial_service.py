"""
Stable serial numbers, serial class codes, and serial keys for shop catalog rows.

Used for indexing, support lookup, and inventory cross-reference. Applied in
_get_shop_items() after media merge so every API item includes:

  serial_no          — 1-based canonical index (sorted by shop-N id, then string ids)
  serial_class       — short uppercase code (THM, BST, …)
  serial_class_label — human-readable class name
  serial_key         — MN2-{CLASS}-{NNNNNN}-{TAG4} (TAG4 = checksum)

Optional env SHOP_SERIAL_KEY_SALT tweaks checksums per deployment (default is stable).
"""
from __future__ import annotations

import hashlib
import os
import re
from typing import Any, Dict, List, Optional, Tuple

# category slug (lowercase) -> (serial_class_code, display label)
SERIAL_CLASS_BY_CATEGORY: Dict[str, Tuple[str, str]] = {
    "themes": ("THM", "Themes"),
    "boosts": ("BST", "Boosts"),
    "starmap25": ("SM5", "Star Map 25"),
    "cosmetic": ("COS", "Cosmetics"),
    "tech": ("TEC", "Tech"),
    "battle": ("BAT", "Battle"),
    "premium": ("PRE", "Premium"),
    "generation": ("GEN", "Generation"),
    "skill": ("SKL", "Skill"),
    "progression": ("PRG", "Progression"),
    "social": ("SOC", "Social"),
    "achievement": ("ACH", "Achievements"),
    "trophies": ("TRO", "Trophies"),
    "stories": ("STY", "Stories"),
    "currency": ("CUR", "Currency"),
    "upgrades": ("UPG", "Upgrades"),
    "unified_points": ("UPT", "Unified points"),
    "inventory": ("INV", "Inventory"),
}

DEFAULT_SERIAL_CLASS = ("OTH", "Other")


def serial_class_for_category(category: Optional[str]) -> Tuple[str, str]:
    key = (category or "other").strip().lower()
    return SERIAL_CLASS_BY_CATEGORY.get(key, DEFAULT_SERIAL_CLASS)


def _canonical_sort_key(item: Dict[str, Any]) -> Tuple[int, Any]:
    iid = (item.get("id") or "").strip()
    m = re.match(r"^shop-(\d+)$", iid, re.I)
    if m:
        return (0, int(m.group(1)))
    return (1, iid.lower())


def _checksum_tag(code: str, serial_no: int, item_id: str) -> str:
    salt = (os.environ.get("SHOP_SERIAL_KEY_SALT") or "mn2-shop-catalog-v1").strip()
    raw = f"{code}|{serial_no:06d}|{item_id}|{salt}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:4].upper()


def build_serial_key(serial_class_code: str, serial_no: int, item_id: str) -> str:
    code = (serial_class_code or "OTH").upper()[:8]
    tag = _checksum_tag(code, serial_no, item_id)
    return f"MN2-{code}-{serial_no:06d}-{tag}"


def enrich_shop_items_serial(items: Optional[List[Dict[str, Any]]]) -> List[Dict[str, Any]]:
    """
    Mutates each item dict: serial_no, serial_class, serial_class_label, serial_key.
    Preserves list order; serial_no follows canonical sort (not display order).
    """
    if not items:
        return items or []
    sorted_refs = sorted(items, key=_canonical_sort_key)
    rank: Dict[int, int] = {}
    for sn, it in enumerate(sorted_refs, start=1):
        rank[id(it)] = sn
    for it in items:
        cat = (it.get("category") or "other").strip().lower()
        code, label = serial_class_for_category(cat)
        sn = rank[id(it)]
        iid = it.get("id") or ""
        it["serial_no"] = sn
        it["serial_class"] = code
        it["serial_class_label"] = label
        it["serial_key"] = build_serial_key(code, sn, iid)
    return items


def serial_class_summary(items: Optional[List[Dict[str, Any]]]) -> List[Dict[str, Any]]:
    """Counts per serial_class for config / admin UI."""
    if not items:
        return []
    by_code: Dict[str, Dict[str, Any]] = {}
    for it in items:
        code = it.get("serial_class") or "OTH"
        label = it.get("serial_class_label") or "Other"
        if code not in by_code:
            by_code[code] = {"code": code, "label": label, "count": 0}
        by_code[code]["count"] += 1
    return sorted(by_code.values(), key=lambda x: (-x["count"], x["code"]))
