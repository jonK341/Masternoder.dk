"""
Wallet upgrades catalog and per-user progress for /api/wallet/v2/upgrades.
Lazy-loaded — not included in summary.
"""
import json
import os
import threading
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set, Tuple

_CATALOG_CACHE: Optional[Dict[str, Any]] = None
_LOCK = threading.RLock()
_GUEST_IDS = frozenset({"", "default_user", "guest"})


def _base() -> str:
    return os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _catalog_path() -> str:
    return os.path.join(_base(), "data", "wallet_upgrades_catalog.json")


def _progress_dir() -> str:
    return os.path.join(_base(), "data", "wallet_upgrades_progress")


def _progress_path(user_id: str) -> str:
    safe = "".join(c if c.isalnum() or c in "-_" else "_" for c in (user_id or "default_user"))
    return os.path.join(_progress_dir(), f"{safe}.json")


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


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


def _upgrade_index() -> Dict[str, Dict[str, Any]]:
    doc = load_catalog()
    out: Dict[str, Dict[str, Any]] = {}
    for u in doc.get("upgrades") or []:
        if isinstance(u, dict) and u.get("id"):
            out[str(u["id"])] = u
    return out


def get_upgrade_by_id(upgrade_id: str) -> Optional[Dict[str, Any]]:
    return _upgrade_index().get((upgrade_id or "").strip())


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


def _read_json(path: str) -> dict:
    if not os.path.isfile(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _write_json(path: str, data: dict) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
        f.write("\n")
    os.replace(tmp, path)


def load_user_progress(user_id: str) -> Dict[str, Any]:
    """Load persisted unlock state for a user."""
    user_id = (user_id or "").strip() or "default_user"
    path = _progress_path(user_id)
    with _LOCK:
        doc = _read_json(path)
    unlocked = doc.get("unlocked_ids") or []
    if not isinstance(unlocked, list):
        unlocked = []
    unlocked_at = doc.get("unlocked_at") if isinstance(doc.get("unlocked_at"), dict) else {}
    return {
        "user_id": user_id,
        "unlocked_ids": [str(x) for x in unlocked if x],
        "unlocked_at": {str(k): v for k, v in unlocked_at.items()},
        "version": int(doc.get("version") or 1),
    }


def _save_user_progress(user_id: str, unlocked_ids: List[str], unlocked_at: Dict[str, str]) -> None:
    path = _progress_path(user_id)
    doc = {
        "version": 1,
        "user_id": user_id,
        "unlocked_ids": unlocked_ids,
        "unlocked_at": unlocked_at,
        "updated_at": _iso_now(),
    }
    with _LOCK:
        _write_json(path, doc)


def _user_wallet_level(user_id: str) -> int:
    """Best-effort wallet level from engagement achievements."""
    if not (user_id or "").strip() or user_id in _GUEST_IDS:
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


def _user_achievements(user_id: str) -> Set[str]:
    out: Set[str] = set()
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
    if not (user_id or "").strip() or user_id in _GUEST_IDS:
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


def _user_trophy_count(user_id: str) -> int:
    if not (user_id or "").strip() or user_id in _GUEST_IDS:
        return 0
    try:
        from backend.services.wallet_v2_service import _trophy_counts

        counts = _trophy_counts(user_id)
        return int(counts.get("total") or 0)
    except Exception:
        return 0


def _user_clicks_today(user_id: str) -> int:
    if not (user_id or "").strip() or user_id in _GUEST_IDS:
        return 0
    try:
        from backend.services.wallet_micro_earn_service import get_status

        status = get_status(user_id) or {}
        total = 0
        for ev in status.get("events") or []:
            if isinstance(ev, dict):
                total += int(ev.get("clicks_today") or 0)
        return total
    except Exception:
        return 0


def _build_user_context(user_id: str, unlocked_ids: Optional[List[str]] = None) -> Dict[str, Any]:
    unlocked = unlocked_ids or []
    return {
        "level": _user_wallet_level(user_id),
        "achievements": _user_achievements(user_id),
        "mn2_spent": _user_mn2_spent(user_id),
        "trophy_count": _user_trophy_count(user_id),
        "clicks_today": _user_clicks_today(user_id),
        "upgrade_count": len(unlocked),
    }


def _normalize_unlock_type(utype: str) -> str:
    t = (utype or "default").lower()
    if t in ("default", "always"):
        return "always"
    return t


def _check_unlock_condition(
    unlock: Dict[str, Any],
    ctx: Dict[str, Any],
) -> Tuple[bool, Optional[str]]:
    """Return (met, progress_hint)."""
    utype = _normalize_unlock_type(unlock.get("type") or "default")
    value = unlock.get("value")

    if utype == "always":
        return True, None

    if utype == "level":
        try:
            need = int(value or 1)
        except (TypeError, ValueError):
            need = 1
        have = int(ctx.get("level") or 1)
        if have >= need:
            return True, None
        return False, f"Level {have}/{need}"

    if utype == "achievement":
        ach = str(value or "")
        if ach in (ctx.get("achievements") or set()):
            return True, None
        return False, f"Achievement {ach} required"

    if utype == "mn2_spent":
        try:
            need = float(value or 0)
        except (TypeError, ValueError):
            need = 0.0
        have = float(ctx.get("mn2_spent") or 0)
        if have >= need:
            return True, None
        return False, f"Spent {have:.0f}/{need:.0f} MN2"

    if utype == "trophy_count":
        try:
            need = int(value or 0)
        except (TypeError, ValueError):
            need = 0
        have = int(ctx.get("trophy_count") or 0)
        if have >= need:
            return True, None
        return False, f"Trophies {have}/{need}"

    if utype == "clicks_today":
        try:
            need = int(value or 0)
        except (TypeError, ValueError):
            need = 0
        have = int(ctx.get("clicks_today") or 0)
        if have >= need:
            return True, None
        return False, f"Clicks today {have}/{need}"

    if utype == "upgrade_count":
        try:
            need = int(value or 0)
        except (TypeError, ValueError):
            need = 0
        have = int(ctx.get("upgrade_count") or 0)
        if have >= need:
            return True, None
        return False, f"Unlocks {have}/{need}"

    return False, "Unknown unlock condition"


def effects_for_upgrade(upgrade: Dict[str, Any]) -> Dict[str, Any]:
    """Phase-1 metadata flags derived from category and tier."""
    category = (upgrade.get("category") or "").lower()
    tier = (upgrade.get("tier") or "common").lower()
    mult = {"common": 1, "rare": 2, "epic": 3}.get(tier, 1)
    effects: Dict[str, Any] = {"upgrade_id": upgrade.get("id"), "tier": tier, "category": category}

    if category == "speed":
        effects["summary_cache_ttl_bonus"] = 15 * mult
    elif category == "network_visibility":
        effects["network_kpi_refresh_bonus"] = 5 * mult
    elif category == "trophies":
        effects["trophy_preview_bonus"] = mult
    elif category == "send_receive":
        effects["send_preview_cache_bonus"] = 10 * mult
    elif category == "monitors":
        effects["monitor_refresh_bonus"] = 5 * mult
    elif category == "fun":
        if tier in ("rare", "epic"):
            effects["fun_mode_unlock"] = True
    elif category == "desktop":
        effects["desktop_tray_poll_bonus"] = mult
    elif category == "discord":
        effects["discord_notify_bonus"] = mult
    elif category == "security":
        effects["security_checklist_bonus"] = mult

    if tier == "epic":
        effects["earn_cap_bonus_pct"] = 2 * mult

    return effects


def merge_effects_summary(unlocked_upgrades: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Aggregate effect flags from unlocked upgrades."""
    summary: Dict[str, Any] = {
        "summary_cache_ttl_bonus": 0,
        "network_kpi_refresh_bonus": 0,
        "trophy_preview_bonus": 0,
        "send_preview_cache_bonus": 0,
        "monitor_refresh_bonus": 0,
        "desktop_tray_poll_bonus": 0,
        "discord_notify_bonus": 0,
        "security_checklist_bonus": 0,
        "earn_cap_bonus_pct": 0,
        "fun_mode_unlock": False,
        "unlocked_effect_count": len(unlocked_upgrades),
    }
    for upgrade in unlocked_upgrades:
        fx = effects_for_upgrade(upgrade)
        for key, val in fx.items():
            if key in ("upgrade_id", "tier", "category"):
                continue
            if key == "fun_mode_unlock":
                if val:
                    summary[key] = True
            elif isinstance(val, (int, float)) and isinstance(summary.get(key), (int, float)):
                summary[key] = summary[key] + val
    return summary


def get_user_effects_summary(user_id: str) -> Dict[str, Any]:
    """Effects from persisted unlocks — for summary/earn integration."""
    progress = load_user_progress(user_id)
    index = _upgrade_index()
    unlocked_upgrades = [index[uid] for uid in progress["unlocked_ids"] if uid in index]
    return merge_effects_summary(unlocked_upgrades)


def get_progress(user_id: str) -> Dict[str, Any]:
    """Per-user unlock state: persisted unlocks, available-to-unlock, effects summary."""
    user_id = (user_id or "").strip() or "default_user"
    guest = user_id in _GUEST_IDS
    doc = load_catalog()
    upgrades = doc.get("upgrades") or []
    persisted = load_user_progress(user_id)
    unlocked_set = set(persisted["unlocked_ids"])
    ctx = _build_user_context(user_id, persisted["unlocked_ids"])

    unlocked: List[str] = []
    available: List[str] = []
    locked: List[str] = []
    hints: Dict[str, str] = {}
    by_category: Dict[str, Dict[str, int]] = {}

    for u in upgrades:
        if not isinstance(u, dict):
            continue
        uid = u.get("id") or ""
        cat = (u.get("category") or "other").lower()
        if cat not in by_category:
            by_category[cat] = {"unlocked": 0, "available": 0, "locked": 0, "total": 0}
        by_category[cat]["total"] += 1

        if uid in unlocked_set:
            unlocked.append(uid)
            by_category[cat]["unlocked"] += 1
            continue

        unlock = u.get("unlock") if isinstance(u.get("unlock"), dict) else {}
        met, hint = _check_unlock_condition(unlock, ctx)
        if met:
            available.append(uid)
            by_category[cat]["available"] += 1
        else:
            locked.append(uid)
            by_category[cat]["locked"] += 1
            if hint:
                hints[uid] = hint

    index = _upgrade_index()
    unlocked_upgrades = [index[uid] for uid in unlocked if uid in index]

    return {
        "success": True,
        "user_id": user_id,
        "guest": guest,
        "wallet_level": ctx["level"],
        "mn2_spent": round(float(ctx["mn2_spent"]), 8),
        "trophy_count": ctx["trophy_count"],
        "clicks_today": ctx["clicks_today"],
        "upgrade_count": len(unlocked),
        "unlocked_count": len(unlocked),
        "available_count": len(available),
        "locked_count": len(locked),
        "total": len(upgrades),
        "unlocked_ids": unlocked,
        "available_ids": available,
        "locked_ids": locked,
        "progress_hints": hints,
        "by_category": by_category,
        "effects_summary": merge_effects_summary(unlocked_upgrades),
        "unlocked_effects": [
            {"id": u.get("id"), "effects": effects_for_upgrade(u)} for u in unlocked_upgrades
        ],
    }


def unlock_upgrade(user_id: str, upgrade_id: str) -> Dict[str, Any]:
    """Unlock one upgrade when conditions are met; persist to user progress file."""
    user_id = (user_id or "").strip() or "default_user"
    upgrade_id = (upgrade_id or "").strip()

    if user_id in _GUEST_IDS:
        return {"success": False, "error": "guest_cannot_unlock", "message": "Sign in to unlock upgrades."}

    if not upgrade_id:
        return {"success": False, "error": "missing_upgrade_id", "message": "Upgrade id is required."}

    upgrade = get_upgrade_by_id(upgrade_id)
    if not upgrade:
        return {"success": False, "error": "unknown_upgrade", "message": f"Unknown upgrade: {upgrade_id}"}

    progress = load_user_progress(user_id)
    if upgrade_id in progress["unlocked_ids"]:
        return {
            "success": False,
            "error": "already_unlocked",
            "message": f"{upgrade_id} is already unlocked.",
            "upgrade_id": upgrade_id,
        }

    ctx = _build_user_context(user_id, progress["unlocked_ids"])
    unlock = upgrade.get("unlock") if isinstance(upgrade.get("unlock"), dict) else {}
    met, hint = _check_unlock_condition(unlock, ctx)
    if not met:
        return {
            "success": False,
            "error": "conditions_not_met",
            "message": unlock.get("label") or hint or "Unlock conditions not met.",
            "upgrade_id": upgrade_id,
            "progress_hint": hint,
        }

    unlocked_ids = list(progress["unlocked_ids"])
    unlocked_ids.append(upgrade_id)
    unlocked_at = dict(progress["unlocked_at"])
    unlocked_at[upgrade_id] = _iso_now()
    _save_user_progress(user_id, unlocked_ids, unlocked_at)

    effects = effects_for_upgrade(upgrade)
    return {
        "success": True,
        "upgrade_id": upgrade_id,
        "name": upgrade.get("name"),
        "effects": effects,
        "unlocked_at": unlocked_at[upgrade_id],
        "progress": get_progress(user_id),
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
