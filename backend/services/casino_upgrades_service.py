"""Casino level-up upgrades — 250-item catalog, unlock progress, purchase."""
from __future__ import annotations

import json
import os
import threading
from typing import Any, Dict, List, Optional, Set

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_LOCK = threading.Lock()
_CATALOG_PATH = os.path.join(_ROOT, "data", "casino_upgrades.json")

_RTP_FORBIDDEN_KEYS = frozenset({
    "rtp_boost", "rtp_multiplier", "house_edge_delta", "win_rate_boost",
    "affects_rtp", "edge_perk", "payout_multiplier_boost",
})


def _log_dir() -> str:
    return os.environ.get("MASTERNODER_LOG_DIR") or os.path.join(_ROOT, "logs")


def _owned_path() -> str:
    os.makedirs(_log_dir(), exist_ok=True)
    return os.path.join(_log_dir(), "casino_upgrades_owned.json")


def _load_catalog() -> Dict[str, Any]:
    if not os.path.isfile(_CATALOG_PATH):
        return {"version": 0, "total": 0, "categories": [], "upgrades": []}
    try:
        with open(_CATALOG_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {"upgrades": []}
    except Exception:
        return {"version": 0, "total": 0, "categories": [], "upgrades": []}


def _load_owned() -> Dict[str, List[str]]:
    path = _owned_path()
    if not os.path.isfile(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _save_owned(data: Dict[str, List[str]]) -> None:
    try:
        with open(_owned_path(), "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except OSError:
        pass


def _find_upgrade(upgrade_id: str) -> Optional[Dict[str, Any]]:
    for row in _load_catalog().get("upgrades") or []:
        if isinstance(row, dict) and row.get("id") == upgrade_id:
            return row
    return None


def _player_level(user_id: str) -> int:
    try:
        from backend.services import casino_progression
        profile = casino_progression.get_profile(user_id)
        xp = profile.get("xp") or {}
        return int(xp.get("level") or 1)
    except Exception:
        return 1


def _player_xp(user_id: str) -> float:
    try:
        from backend.services import casino_progression
        profile = casino_progression.get_profile(user_id)
        xp = profile.get("xp") or {}
        return float(xp.get("xp") or 0)
    except Exception:
        return 0.0


def _owned_set(user_id: str) -> Set[str]:
    return set(_load_owned().get(user_id) or [])


def _upgrade_status(row: Dict[str, Any], user_id: str, owned: Set[str], level: int, xp: float) -> str:
    uid = row.get("id")
    if uid in owned:
        return "owned"
    prereq = row.get("prerequisite")
    if prereq and prereq not in owned:
        return "locked_prerequisite"
    if int(row.get("level_required") or 1) > level:
        return "locked_level"
    return "available"


def catalog_count() -> int:
    return len(_load_catalog().get("upgrades") or [])


def get_catalog(user_id: Optional[str] = None, category: Optional[str] = None) -> Dict[str, Any]:
    cat_data = _load_catalog()
    rows = [r for r in (cat_data.get("upgrades") or []) if isinstance(r, dict)]
    if category:
        category = category.strip().lower()
        rows = [r for r in rows if (r.get("category") or "").lower() == category]
    uid = (user_id or "").strip()
    owned: Set[str] = _owned_set(uid) if uid else set()
    level = _player_level(uid) if uid else 1
    xp = _player_xp(uid) if uid else 0.0
    items = []
    for row in rows:
        status = _upgrade_status(row, uid, owned, level, xp) if uid else "catalog"
        items.append({**row, "status": status, "owned": row.get("id") in owned})
    return {
        "success": True,
        "version": cat_data.get("version"),
        "total": len(cat_data.get("upgrades") or []),
        "categories": cat_data.get("categories") or [],
        "count": len(items),
        "upgrades": items,
    }


def get_progress(user_id: str) -> Dict[str, Any]:
    cat_data = _load_catalog()
    all_rows = [r for r in (cat_data.get("upgrades") or []) if isinstance(r, dict)]
    owned = _owned_set(user_id)
    level = _player_level(user_id)
    xp = _player_xp(user_id)
    by_cat: Dict[str, Dict[str, int]] = {}
    for row in all_rows:
        cid = row.get("category") or "other"
        by_cat.setdefault(cid, {"total": 0, "owned": 0})
        by_cat[cid]["total"] += 1
        if row.get("id") in owned:
            by_cat[cid]["owned"] += 1
    bonuses = _aggregate_bonuses(user_id, owned)
    return {
        "success": True,
        "user_id": user_id,
        "casino_level": level,
        "casino_xp": round(xp, 2),
        "unlocked": len(owned),
        "total": len(all_rows),
        "progress_pct": int(100 * len(owned) / len(all_rows)) if all_rows else 0,
        "by_category": by_cat,
        "owned_ids": sorted(owned),
        "active_bonuses": bonuses,
    }


def _aggregate_bonuses(user_id: str, owned: Set[str]) -> Dict[str, Any]:
    xp_boost = 0
    bonus_coins = 0
    mission_slots = 0
    vip_flair = 0
    visual_effects: List[str] = []
    for row in _load_catalog().get("upgrades") or []:
        if not isinstance(row, dict) or row.get("id") not in owned:
            continue
        xp_boost += int(row.get("xp_boost_pct") or 0)
        bonus_coins += int(row.get("bonus_coins_on_unlock") or 0)
        mission_slots += int(row.get("mission_tracker_slots") or 0)
        vip_flair = max(vip_flair, int(row.get("vip_flair_tier") or 0))
        ve = row.get("visual_effect") or row.get("effect")
        if ve:
            visual_effects.append(str(ve))
    return {
        "xp_boost_pct": min(50, xp_boost),
        "mission_tracker_slots": mission_slots,
        "vip_flair_tier": vip_flair,
        "visual_effects_count": len(visual_effects),
        "cosmetic_only": True,
    }


def _deduct_xp(user_id: str, amount: float) -> Optional[str]:
    try:
        from backend.services import casino_progression
        with casino_progression._LOCK:
            state = casino_progression._load_state()
            user = state.setdefault(user_id, casino_progression._default_user_state())
            current = float(user.get("xp") or 0)
            if current < amount:
                return "Insufficient casino XP"
            user["xp"] = round(current - amount, 2)
            casino_progression._save_state(state)
        return None
    except Exception as exc:
        return str(exc)


def purchase(user_id: str, upgrade_id: str, currency: str = "coins") -> Dict[str, Any]:
    row = _find_upgrade(upgrade_id)
    if not row:
        return {"success": False, "error": "Upgrade not found", "code": "NOT_FOUND"}

    owned = _owned_set(user_id)
    if upgrade_id in owned:
        return {"success": False, "error": "Already unlocked", "code": "ALREADY_OWNED"}

    level = _player_level(user_id)
    if level < int(row.get("level_required") or 1):
        return {
            "success": False,
            "error": f"Requires casino level {row.get('level_required')}",
            "code": "LEVEL_TOO_LOW",
            "level_required": row.get("level_required"),
            "casino_level": level,
        }

    prereq = row.get("prerequisite")
    if prereq and prereq not in owned:
        return {
            "success": False,
            "error": "Prerequisite upgrade required",
            "code": "PREREQUISITE",
            "prerequisite": prereq,
        }

    currency = (currency or "coins").strip().lower()
    if currency == "fiat":
        currency = "usd"

    price: Optional[float] = None
    if currency == "coins" and row.get("cost_coins") is not None:
        price = float(row["cost_coins"])
    elif currency == "mn2" and row.get("cost_mn2") is not None:
        price = float(row["cost_mn2"])
    elif currency == "xp" and row.get("cost_xp") is not None:
        price = float(row["cost_xp"])
    else:
        if row.get("cost_coins") is not None:
            currency = "coins"
            price = float(row["cost_coins"])
        elif row.get("cost_xp") is not None:
            currency = "xp"
            price = float(row["cost_xp"])
        elif row.get("cost_mn2") is not None:
            currency = "mn2"
            price = float(row["cost_mn2"])
        else:
            return {"success": False, "error": "No price configured", "code": "NO_PRICE"}

    if price is None or price <= 0:
        return {"success": False, "error": "Invalid price", "code": "INVALID_PRICE"}

    if currency == "xp":
        err = _deduct_xp(user_id, price)
        if err:
            return {"success": False, "error": err, "code": "INSUFFICIENT_XP"}
    else:
        try:
            from backend.services.casino_service import _apply_balance_delta, _normalize_currency, _validate_bet
            currency = _normalize_currency(currency)
            err = _validate_bet(user_id, price, currency)
            if err:
                return {"success": False, "error": err, "code": "INSUFFICIENT_FUNDS"}
            _apply_balance_delta(user_id, -price, currency, "casino_upgrade", {"upgrade_id": upgrade_id})
        except Exception as exc:
            return {"success": False, "error": str(exc), "code": "PAYMENT_FAILED"}

    with _LOCK:
        owned_data = _load_owned()
        user_list = list(owned_data.get(user_id) or [])
        user_list.append(upgrade_id)
        owned_data[user_id] = user_list
        _save_owned(owned_data)

    bonus_coins = int(row.get("bonus_coins_on_unlock") or 0)
    if bonus_coins > 0:
        try:
            from backend.services.casino_service import _apply_coin_delta
            _apply_coin_delta(user_id, bonus_coins, "casino_upgrade", {"upgrade_id": upgrade_id, "bonus": True})
        except Exception:
            pass

    try:
        from backend.services import casino_progression
        casino_progression.on_event(user_id, "upgrade_unlock", {"upgrade_id": upgrade_id})
    except Exception:
        pass

    return {
        "success": True,
        "upgrade": row,
        "currency": currency,
        "price": price,
        "bonus_coins_awarded": bonus_coins,
        "progress": get_progress(user_id),
    }


def audit_rtp_compliance() -> Dict[str, Any]:
    violations: List[Dict[str, Any]] = []
    for row in _load_catalog().get("upgrades") or []:
        if not isinstance(row, dict):
            continue
        issues: List[str] = []
        if not row.get("cosmetic_only", False):
            issues.append("cosmetic_only must be true")
        for key in row:
            if str(key).lower() in _RTP_FORBIDDEN_KEYS:
                issues.append(f"forbidden key: {key}")
        if issues:
            violations.append({"id": row.get("id"), "issues": issues})
    return {
        "success": True,
        "total": catalog_count(),
        "violations": violations,
        "compliant": len(violations) == 0,
    }
