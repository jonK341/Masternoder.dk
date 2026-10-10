"""Camgirls social — favorites, fan club, goals, private show, offline."""
from __future__ import annotations

import json
import os
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_FAVORITES_FILE = os.path.join(_ROOT, "data", "camgirls_favorites.json")
_FANCLUB_FILE = os.path.join(_ROOT, "data", "camgirls_fanclub.json")
_OFFLINE_FILE = os.path.join(_ROOT, "data", "camgirls_offline.jsonl")
_PRIVATE_FILE = os.path.join(_ROOT, "data", "camgirls_private.json")
_TIPS_FILE = os.path.join(_ROOT, "data", "camgirls_tips.jsonl")

_MOOD_LINGO = {
    "cozy": "Dim lights, slow chat — perfect cozy mode.",
    "party": "Energy up — tips and gifts light the room.",
    "flirty": "Playful banter unlocked — keep it fun.",
    "vip": "VIP tone — you have the spotlight.",
}


def _iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _read_json(path: str, default: Any) -> Any:
    if not os.path.isfile(path):
        return default
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def _write_json(path: str, data: Any) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def _append_jsonl(path: str, row: dict) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(row) + "\n")


def _catalog_pricing() -> Dict[str, Any]:
    from backend.services.camgirls_studio_service import studio_catalog

    cat = studio_catalog()
    if not cat.get("success"):
        return {}
    return cat


def fan_club_price_mn2() -> float:
    cat = _catalog_pricing()
    fc = cat.get("fan_club") if isinstance(cat.get("fan_club"), dict) else {}
    return float(fc.get("price_mn2") or 25)


def private_show_price_mn2(minutes: int) -> float:
    cat = _catalog_pricing()
    ps = cat.get("private_show") if isinstance(cat.get("private_show"), dict) else {}
    per_min = float(ps.get("mn2_per_minute") or 5)
    max_m = int(ps.get("max_minutes") or 60)
    mins = max(1, min(int(minutes or 5), max_m))
    return per_min * mins


def is_favorite(user_id: str, performer_id: str) -> bool:
    data = _read_json(_FAVORITES_FILE, {})
    return performer_id in (data.get(user_id) or [])


def list_favorites(user_id: str) -> Dict[str, Any]:
    data = _read_json(_FAVORITES_FILE, {})
    return {"success": True, "favorites": list(data.get(user_id) or [])}


def toggle_favorite(user_id: str, performer_id: str) -> Dict[str, Any]:
    data = _read_json(_FAVORITES_FILE, {})
    favs = set(data.get(user_id) or [])
    if performer_id in favs:
        favs.remove(performer_id)
        on = False
    else:
        favs.add(performer_id)
        on = True
    data[user_id] = sorted(favs)
    _write_json(_FAVORITES_FILE, data)
    return {"success": True, "favorite": on}


def is_fan_club_member(user_id: str, performer_id: str) -> bool:
    data = _read_json(_FANCLUB_FILE, {})
    return user_id in (data.get(performer_id) or [])


def _add_fan_club_member(user_id: str, performer_id: str) -> Dict[str, Any]:
    data = _read_json(_FANCLUB_FILE, {})
    members = set(data.get(performer_id) or [])
    if user_id in members:
        return {"success": True, "already_member": True}
    members.add(user_id)
    data[performer_id] = sorted(members)
    _write_json(_FANCLUB_FILE, data)
    return {"success": True}


def grant_fan_club(user_id: str, performer_id: str) -> Dict[str, Any]:
    """Fan club after external payment (no MN2 debit)."""
    from backend.services.camgirls_service import _is_age_verified, _is_unlocked

    if not _is_age_verified(user_id):
        return {"success": False, "code": "age_verification_required"}
    if not _is_unlocked(user_id, performer_id):
        return {"success": False, "code": "unlock_required"}
    out = _add_fan_club_member(user_id, performer_id)
    out["action"] = "fan_club"
    out["performer_id"] = performer_id
    return out


def join_fan_club(user_id: str, performer_id: str) -> Dict[str, Any]:
    from backend.services.camgirls_service import _debit_mn2, _is_unlocked, _is_age_verified

    if not _is_age_verified(user_id):
        return {"success": False, "code": "age_verification_required"}
    if not _is_unlocked(user_id, performer_id):
        return {"success": False, "code": "unlock_required"}
    if is_fan_club_member(user_id, performer_id):
        return {"success": True, "already_member": True}
    price = fan_club_price_mn2()
    debit = _debit_mn2(user_id, price, "camgirls_fan_club", {"performer_id": performer_id})
    if debit.get("error"):
        return debit
    out = _add_fan_club_member(user_id, performer_id)
    out["amount_mn2"] = price
    return out


def grant_private_show(user_id: str, performer_id: str, minutes: int) -> Dict[str, Any]:
    return _activate_private_show(user_id, performer_id, minutes, payment_method="paypal")


def start_private_show(user_id: str, performer_id: str, minutes: int) -> Dict[str, Any]:
    from backend.services.camgirls_service import _debit_mn2, _is_unlocked, _is_age_verified

    if not _is_age_verified(user_id):
        return {"success": False, "code": "age_verification_required"}
    if not _is_unlocked(user_id, performer_id):
        return {"success": False, "code": "unlock_required"}
    price = private_show_price_mn2(minutes)
    debit = _debit_mn2(user_id, price, "camgirls_private_show", {"performer_id": performer_id, "minutes": minutes})
    if debit.get("error"):
        return debit
    return _activate_private_show(user_id, performer_id, minutes, amount_mn2=price, payment_method="mn2")


def _activate_private_show(
    user_id: str,
    performer_id: str,
    minutes: int,
    *,
    amount_mn2: float = 0,
    payment_method: str = "mn2",
) -> Dict[str, Any]:
    cat = _catalog_pricing()
    ps = cat.get("private_show") if isinstance(cat.get("private_show"), dict) else {}
    max_m = int(ps.get("max_minutes") or 60)
    mins = max(1, min(int(minutes or 5), max_m))
    if amount_mn2 <= 0:
        amount_mn2 = private_show_price_mn2(mins)
    ends = datetime.now(timezone.utc) + timedelta(minutes=mins)
    data = _read_json(_PRIVATE_FILE, {})
    key = f"{user_id}:{performer_id}"
    data[key] = {
        "user_id": user_id,
        "performer_id": performer_id,
        "minutes": mins,
        "started_at": _iso(),
        "ends_at": ends.isoformat().replace("+00:00", "Z"),
        "amount_mn2": amount_mn2,
        "payment_method": payment_method,
    }
    _write_json(_PRIVATE_FILE, data)
    return {
        "success": True,
        "action": "private_show",
        "performer_id": performer_id,
        "minutes": mins,
        "ends_at": data[key]["ends_at"],
        "amount_mn2": amount_mn2,
    }


def get_private_show_status(user_id: str, performer_id: str) -> Dict[str, Any]:
    data = _read_json(_PRIVATE_FILE, {})
    key = f"{user_id}:{performer_id}"
    row = data.get(key)
    if not isinstance(row, dict):
        return {"success": True, "active": False}
    ends_raw = row.get("ends_at") or ""
    active = False
    try:
        ends = datetime.fromisoformat(ends_raw.replace("Z", "+00:00"))
        active = ends > datetime.now(timezone.utc)
    except Exception:
        active = False
    if not active:
        return {"success": True, "active": False}
    return {"success": True, "active": True, **row}


def send_offline_message(user_id: str, performer_id: str, message: str) -> Dict[str, Any]:
    from backend.services.camgirls_service import _debit_mn2, _is_age_verified

    if not _is_age_verified(user_id):
        return {"success": False, "code": "age_verification_required"}
    text = (message or "").strip()
    if not text:
        return {"success": False, "error": "message_required"}
    cat = _catalog_pricing()
    off = cat.get("offline_message") if isinstance(cat.get("offline_message"), dict) else {}
    price = float(off.get("price_mn2") or 3)
    debit = _debit_mn2(user_id, price, "camgirls_offline", {"performer_id": performer_id})
    if debit.get("error"):
        return debit
    _append_jsonl(_OFFLINE_FILE, {
        "user_id": user_id,
        "performer_id": performer_id,
        "message": text[:2000],
        "amount_mn2": price,
        "created_at": _iso(),
    })
    return {"success": True, "amount_mn2": price}


def get_leaderboard(performer_id: str, limit: int = 10) -> Dict[str, Any]:
    totals: Dict[str, float] = {}
    if os.path.isfile(_TIPS_FILE):
        with open(_TIPS_FILE, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    row = json.loads(line)
                except Exception:
                    continue
                if row.get("performer_id") != performer_id:
                    continue
                uid = str(row.get("user_id") or "anonymous")
                totals[uid] = totals.get(uid, 0.0) + float(row.get("amount_mn2") or 0)
    ranked = sorted(totals.items(), key=lambda x: x[1], reverse=True)[: max(1, limit)]
    rows: List[Dict[str, Any]] = [{"user_id": u, "amount_mn2": a} for u, a in ranked]
    return {"success": True, "leaderboard": rows}


def pick_mood_lingo(performer_row: Dict[str, Any], mood_id: str) -> str:
    mood = (mood_id or "cozy").strip().lower()
    base = _MOOD_LINGO.get(mood) or _MOOD_LINGO["cozy"]
    name = performer_row.get("display_name") or performer_row.get("id") or "Host"
    return f"{name}: {base}"


def get_goal_status(performer_id: str) -> Dict[str, Any]:
    from backend.services.camgirls_service import _get_performer

    p = _get_performer(performer_id) or {}
    goal = float(p.get("goal_mn2") or 100)
    raised = 0.0
    if os.path.isfile(_TIPS_FILE):
        with open(_TIPS_FILE, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    row = json.loads(line)
                except Exception:
                    continue
                if row.get("performer_id") == performer_id:
                    raised += float(row.get("amount_mn2") or 0)
    percent = min(100, int((raised / goal) * 100)) if goal > 0 else 0
    return {"success": True, "raised_mn2": raised, "goal_mn2": goal, "percent": percent}
