"""
Wallet upgrades catalog and per-user progress for /api/wallet/v2/upgrades.
Lazy-loaded — not included in summary.
"""
import json
import os
from typing import Any, Dict, List, Optional

_CATALOG_CACHE: Optional[Dict[str, Any]] = None


def _base() -> str:
    return os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _catalog_path() -> str:
    return os.path.join(_base(), "data", "wallet_upgrades_catalog.json")


def load_catalog() -> Dict[str, Any]:
    """Load upgrades catalog from JSON; cached in-process."""
    global _CATALOG_CACHE
    if _CATALOG_CACHE is not None:
        return _CATALOG_CACHE
    path = _catalog_path()
    if not os.path.isfile(path):
        _CATALOG_CACHE = {"version": 1, "total": 0, "categories": [], "upgrades": []}
        return _CATALOG_CACHE
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict):
            data = {"version": 1, "total": 0, "categories": [], "upgrades": []}
    except Exception:
        data = {"version": 1, "total": 0, "categories": [], "upgrades": []}
    _CATALOG_CACHE = data
    return data


def list_upgrades(category: Optional[str] = None) -> Dict[str, Any]:
    """Return full catalog or filtered by category."""
    doc = load_catalog()
    upgrades = doc.get("upgrades") or []
    if category:
        cat = category.strip().lower()
        upgrades = [u for u in upgrades if isinstance(u, dict) and (u.get("category") or "").lower() == cat]
    return {
        "success": True,
        "version": doc.get("version", 1),
        "total": len(upgrades),
        "categories": doc.get("categories") or [],
        "upgrades": upgrades,
    }


def _user_wallet_level(user_id: str) -> int:
    """Best-effort wallet level from engagement achievements."""
    if not (user_id or "").strip() or user_id in ("default_user", "guest"):
        return 1
    try:
        path = os.path.join(_base(), "logs", "user_engagement", user_id, "achievements.json")
        if not os.path.isfile(path):
            return 1
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict):
            return max(1, int(data.get("wallet_level") or data.get("level") or 1))
    except Exception:
        pass
    return 1


def _user_achievements(user_id: str) -> set:
    out: set = set()
    if not (user_id or "").strip():
        return out
    try:
        path = os.path.join(_base(), "logs", "user_engagement", user_id, "achievements.json")
        if not os.path.isfile(path):
            return out
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict):
            unlocked = data.get("unlocked") or data.get("achievements") or []
            if isinstance(unlocked, list):
                for a in unlocked:
                    if isinstance(a, str):
                        out.add(a)
                    elif isinstance(a, dict) and a.get("id"):
                        out.add(str(a["id"]))
    except Exception:
        pass
    return out


def _user_mn2_spent(user_id: str) -> float:
    """Approximate MN2 spent from shop ledger entries — best-effort."""
    if not (user_id or "").strip() or user_id in ("default_user", "guest"):
        return 0.0
    try:
        from backend.services.shop_db_service import get_purchases
        history = get_purchases(user_id, limit=500) or []
        total = 0.0
        for row in history:
            if not isinstance(row, dict):
                continue
            paid = row.get("paid_mn2") or row.get("mn2_amount") or row.get("amount_mn2")
            if paid is not None:
                try:
                    total += float(paid)
                except (TypeError, ValueError):
                    pass
        return total
    except Exception:
        return 0.0


def _is_unlocked(upgrade: Dict[str, Any], level: int, achievements: set, mn2_spent: float) -> bool:
    unlock = upgrade.get("unlock") if isinstance(upgrade.get("unlock"), dict) else {}
    utype = (unlock.get("type") or "default").lower()
    value = unlock.get("value")
    if utype == "default":
        return True
    if utype == "level":
        try:
            return level >= int(value or 1)
        except (TypeError, ValueError):
            return False
    if utype == "achievement":
        return str(value or "") in achievements
    if utype == "mn2_spent":
        try:
            return mn2_spent >= float(value or 0)
        except (TypeError, ValueError):
            return False
    return False


def get_progress(user_id: str) -> Dict[str, Any]:
    """Per-user unlock state for all catalog upgrades."""
    user_id = (user_id or "").strip() or "default_user"
    guest = user_id in ("", "default_user", "guest")
    doc = load_catalog()
    upgrades = doc.get("upgrades") or []
    level = _user_wallet_level(user_id)
    achievements = _user_achievements(user_id)
    mn2_spent = _user_mn2_spent(user_id)

    unlocked: List[str] = []
    locked: List[str] = []
    by_category: Dict[str, Dict[str, int]] = {}

    for u in upgrades:
        if not isinstance(u, dict):
            continue
        uid = u.get("id") or ""
        cat = (u.get("category") or "other").lower()
        if cat not in by_category:
            by_category[cat] = {"unlocked": 0, "total": 0}
        by_category[cat]["total"] += 1
        if _is_unlocked(u, level, achievements, mn2_spent):
            unlocked.append(uid)
            by_category[cat]["unlocked"] += 1
        else:
            locked.append(uid)

    return {
        "success": True,
        "user_id": user_id,
        "guest": guest,
        "wallet_level": level,
        "mn2_spent": round(mn2_spent, 8),
        "unlocked_count": len(unlocked),
        "locked_count": len(locked),
        "total": len(upgrades),
        "unlocked_ids": unlocked,
        "locked_ids": locked,
        "by_category": by_category,
    }


def build_masternode_map(limit: int = 48) -> Dict[str, Any]:
    """Lightweight masternode online grid — lazy endpoint, not on summary."""
    limit = max(1, min(int(limit or 48), 200))
    try:
        from backend.services.mn2_explorer_data import masternodes
        data = masternodes(limit=limit) or {}
    except Exception:
        data = {"total": 0, "enabled": 0, "list": []}
    nodes = []
    for mn in (data.get("list") or [])[:limit]:
        if not isinstance(mn, dict):
            continue
        status = str(mn.get("status") or "").upper()
        nodes.append({
            "rank": mn.get("rank"),
            "addr": mn.get("addr"),
            "status": status,
            "online": status == "ENABLED",
            "activetime": mn.get("activetime"),
            "lastpaid": mn.get("lastpaid"),
        })
    return {
        "success": True,
        "total": data.get("total") or len(nodes),
        "enabled": data.get("enabled") or sum(1 for n in nodes if n.get("online")),
        "nodes": nodes,
        "rpc_error": data.get("rpc_error"),
    }
