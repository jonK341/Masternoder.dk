"""Camgirls social layer — favorites, fan club, offline inbox, goals, leaderboard, private show."""
from __future__ import annotations

import json
import os
import random
import threading
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

_LOCK = threading.RLock()
_BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_FAVORITES_FILE = os.path.join(_BASE, "data", "camgirls_favorites.json")
_FANCLUB_FILE = os.path.join(_BASE, "data", "camgirls_fanclub.json")
_OFFLINE_FILE = os.path.join(_BASE, "data", "camgirls_offline_messages.jsonl")
_PRIVATE_FILE = os.path.join(_BASE, "data", "camgirls_private_sessions.json")
_TIPS_FILE = os.path.join(_BASE, "data", "camgirls_tips.jsonl")
_TIP_INDEX: Dict[str, Any] = {"mtime": 0.0, "totals": {}, "by_user": {}}


def _tip_index() -> tuple[Dict[str, float], Dict[str, Dict[str, float]]]:
    """One pass over tips jsonl — cached by file mtime."""
    if not os.path.isfile(_TIPS_FILE):
        return {}, {}
    try:
        mtime = os.path.getmtime(_TIPS_FILE)
    except OSError:
        return {}, {}
    if _TIP_INDEX.get("mtime") == mtime:
        return _TIP_INDEX["totals"], _TIP_INDEX["by_user"]
    totals: Dict[str, float] = {}
    by_user: Dict[str, Dict[str, float]] = {}
    try:
        with open(_TIPS_FILE, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    row = json.loads(line)
                except json.JSONDecodeError:
                    continue
                pid = (row.get("performer_id") or "").strip()
                if not pid:
                    continue
                amt = float(row.get("amount_mn2") or 0)
                totals[pid] = totals.get(pid, 0.0) + amt
                uid = (row.get("user_id") or "").strip()
                if uid:
                    by_user.setdefault(pid, {})[uid] = by_user.get(pid, {}).get(uid, 0.0) + amt
    except OSError:
        return {}, {}
    with _LOCK:
        _TIP_INDEX["mtime"] = mtime
        _TIP_INDEX["totals"] = totals
        _TIP_INDEX["by_user"] = by_user
    return totals, by_user


def _iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _read_json(path: str, default: Any) -> Any:
    if not os.path.isfile(path):
        return default
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if data is not None else default
    except Exception:
        return default


def _write_json(path: str, data: Any) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    os.replace(tmp, path)


def _append_jsonl(path: str, row: dict) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")


def _studio_extras(row: Dict[str, Any]) -> Dict[str, Any]:
    studio = row.get("studio") if isinstance(row.get("studio"), dict) else {}
    return {
        "fan_club_price_mn2": float(studio.get("fan_club_price_mn2") or row.get("fan_club_price_mn2") or 15),
        "private_show_mn2_per_min": float(studio.get("private_show_mn2_per_min") or row.get("private_show_mn2_per_min") or 8),
        "offline_message_price_mn2": float(studio.get("offline_message_price_mn2") or 3),
        "schedule": studio.get("schedule") or row.get("schedule") or "",
        "moods": list(studio.get("moods") or ["cozy", "party", "vip"]),
        "scenes": list(studio.get("scenes") or ["neon_club"]),
    }


def enrich_performer_public(
    pub: Dict[str, Any],
    row: Dict[str, Any],
    *,
    user_id: str,
    favs: Optional[set] = None,
    fanclub: Optional[Dict[str, Any]] = None,
    tip_totals: Optional[Dict[str, float]] = None,
    tip_by_user: Optional[Dict[str, Dict[str, float]]] = None,
) -> Dict[str, Any]:
    uid = (user_id or "").strip()
    pid = (pub.get("id") or "").strip()
    extras = _studio_extras(row)
    if favs is None:
        pub["favorite"] = is_favorite(uid, pid) if uid else False
    else:
        pub["favorite"] = pid in favs if uid else False
    if fanclub is None:
        pub["fan_club_member"] = is_fan_club_member(uid, pid) if uid else False
    else:
        rec = fanclub.get(pid) if isinstance(fanclub, dict) else None
        pub["fan_club_member"] = isinstance(rec, dict) and bool(rec.get("joined_at")) if uid else False
    pub["goal"] = get_goal_status(pid, row, tip_totals=tip_totals)
    pub["leaderboard"] = get_leaderboard(pid, limit=3, tip_by_user=tip_by_user).get("leaders") or []
    pub["next_show"] = extras.get("schedule") or ""
    pub["social"] = {
        "fan_club_price_mn2": extras["fan_club_price_mn2"],
        "private_show_mn2_per_min": extras["private_show_mn2_per_min"],
        "offline_message_price_mn2": extras["offline_message_price_mn2"],
        "moods": extras["moods"],
        "scenes": extras["scenes"],
    }
    return pub


def enrich_catalog_performers(
    performers: List[Dict[str, Any]],
    rows: List[Dict[str, Any]],
    *,
    user_id: str,
) -> None:
    """Batch enrich — single read of tips/favorites/fanclub per catalog request."""
    uid = (user_id or "").strip()
    fav_data = _read_json(_FAVORITES_FILE, {})
    favs = set(fav_data.get(uid) or []) if uid and isinstance(fav_data, dict) else set()
    fc_data = _read_json(_FANCLUB_FILE, {})
    fanclub = fc_data.get(uid) if uid and isinstance(fc_data, dict) else {}
    if not isinstance(fanclub, dict):
        fanclub = {}
    tip_totals, tip_by_user = _tip_index()
    row_by_id = {(r.get("id") or "").strip(): r for r in rows if isinstance(r, dict)}
    for pub in performers:
        pid = (pub.get("id") or "").strip()
        row = row_by_id.get(pid) or {}
        enrich_performer_public(
            pub,
            row,
            user_id=uid,
            favs=favs,
            fanclub=fanclub,
            tip_totals=tip_totals,
            tip_by_user=tip_by_user,
        )


def is_favorite(user_id: str, performer_id: str) -> bool:
    uid = (user_id or "").strip()
    pid = (performer_id or "").strip()
    data = _read_json(_FAVORITES_FILE, {})
    block = data.get(uid) if isinstance(data, dict) else []
    return pid in (block if isinstance(block, list) else [])


def toggle_favorite(user_id: str, performer_id: str) -> Dict[str, Any]:
    from backend.services.camgirls_service import get_performer

    uid = (user_id or "").strip()
    pid = (performer_id or "").strip()
    if not get_performer(pid):
        return {"success": False, "error": "performer_not_found"}
    with _LOCK:
        data = _read_json(_FAVORITES_FILE, {})
        if not isinstance(data, dict):
            data = {}
        favs = list(data.get(uid) or [])
        if pid in favs:
            favs.remove(pid)
            favored = False
        else:
            favs.append(pid)
            favored = True
        data[uid] = favs
        _write_json(_FAVORITES_FILE, data)
    return {"success": True, "performer_id": pid, "favorite": favored, "favorites": favs}


def list_favorites(user_id: str) -> Dict[str, Any]:
    uid = (user_id or "").strip()
    data = _read_json(_FAVORITES_FILE, {})
    favs = data.get(uid) if isinstance(data, dict) else []
    return {"success": True, "favorites": list(favs or []), "count": len(favs or [])}


def is_fan_club_member(user_id: str, performer_id: str) -> bool:
    uid = (user_id or "").strip()
    pid = (performer_id or "").strip()
    data = _read_json(_FANCLUB_FILE, {})
    block = data.get(uid) if isinstance(data, dict) else {}
    rec = block.get(pid) if isinstance(block, dict) else None
    return isinstance(rec, dict) and bool(rec.get("joined_at"))


def join_fan_club(user_id: str, performer_id: str) -> Dict[str, Any]:
    from backend.services.camgirls_service import _debit_mn2, _require_age, get_performer, user_has_unlock

    uid = (user_id or "").strip()
    gate = _require_age(uid)
    if gate:
        return gate
    row = get_performer(performer_id)
    if not row:
        return {"success": False, "error": "performer_not_found"}
    pid = (row.get("id") or "").strip()
    if not user_has_unlock(uid, pid):
        return {"success": False, "error": "unlock_required", "code": "unlock_required"}
    if is_fan_club_member(uid, pid):
        return {"success": True, "already_member": True, "performer_id": pid}
    price = _studio_extras(row)["fan_club_price_mn2"]
    debit = _debit_mn2(
        uid,
        price,
        source="camgirl_fan_club",
        metadata={"ledger_type": "camgirl_fan_club", "performer_id": pid},
    )
    if not debit.get("success"):
        return debit
    with _LOCK:
        data = _read_json(_FANCLUB_FILE, {})
        if not isinstance(data, dict):
            data = {}
        data.setdefault(uid, {})[pid] = {"joined_at": _iso(), "amount_mn2": price}
        _write_json(_FANCLUB_FILE, data)
    name = row.get("display_name") or pid
    return {
        "success": True,
        "performer_id": pid,
        "amount_mn2": price,
        "performer_reply": f"Welcome to {name}'s fan club — VIP perks unlocked!",
    }


def send_offline_message(user_id: str, performer_id: str, message: str) -> Dict[str, Any]:
    from backend.services.camgirls_service import _debit_mn2, _require_age, get_performer

    uid = (user_id or "").strip()
    msg = (message or "").strip()
    if not msg:
        return {"success": False, "error": "message_required"}
    if len(msg) > 2000:
        return {"success": False, "error": "message_too_long"}
    gate = _require_age(uid)
    if gate:
        return gate
    row = get_performer(performer_id)
    if not row:
        return {"success": False, "error": "performer_not_found"}
    pid = (row.get("id") or "").strip()
    extras = _studio_extras(row)
    price = 0.0 if is_fan_club_member(uid, pid) else extras["offline_message_price_mn2"]
    if price > 0:
        debit = _debit_mn2(
            uid,
            price,
            source="camgirl_offline",
            metadata={"ledger_type": "camgirl_offline", "performer_id": pid},
        )
        if not debit.get("success"):
            return debit
    row_out = {
        "ts": _iso(),
        "user_id": uid,
        "performer_id": pid,
        "message": msg,
        "amount_mn2": price,
        "fan_club_free": price == 0,
    }
    _append_jsonl(_OFFLINE_FILE, row_out)
    name = row.get("display_name") or pid
    return {
        "success": True,
        "performer_id": pid,
        "queued": True,
        "amount_mn2": price,
        "performer_reply": f"{name} got your offline note — I'll whisper back when I'm on.",
    }


def sum_tips_for_performer(performer_id: str, *, tip_totals: Optional[Dict[str, float]] = None) -> float:
    pid = (performer_id or "").strip()
    if tip_totals is not None:
        return round(float(tip_totals.get(pid) or 0), 8)
    totals, _ = _tip_index()
    return round(float(totals.get(pid) or 0), 8)


def get_goal_status(
    performer_id: str,
    row: Optional[Dict[str, Any]] = None,
    *,
    tip_totals: Optional[Dict[str, float]] = None,
) -> Dict[str, Any]:
    from backend.services.camgirls_service import get_performer

    pid = (performer_id or "").strip()
    if row is None:
        row = get_performer(pid) or {}
    try:
        from backend.services.camgirls_studio_service import _performer_studio
        st = _performer_studio(row)
        goal = float(st.get("goal_mn2") or 500)
        label = st.get("goal_label") or f"Goal: {int(goal)} MN2"
    except Exception:
        goal = 500.0
        label = "Goal"
    raised = sum_tips_for_performer(pid, tip_totals=tip_totals)
    pct = min(100, int((raised / goal) * 100)) if goal > 0 else 0
    return {
        "goal_mn2": goal,
        "raised_mn2": raised,
        "percent": pct,
        "label": label,
        "complete": raised >= goal,
    }


def get_leaderboard(
    performer_id: str,
    *,
    limit: int = 10,
    tip_by_user: Optional[Dict[str, Dict[str, float]]] = None,
) -> Dict[str, Any]:
    pid = (performer_id or "").strip()
    totals: Dict[str, float] = {}
    if tip_by_user is not None:
        totals = dict(tip_by_user.get(pid) or {})
    elif os.path.isfile(_TIPS_FILE):
        _, by_user = _tip_index()
        totals = dict(by_user.get(pid) or {})
    ranked = sorted(totals.items(), key=lambda x: x[1], reverse=True)[: max(1, min(limit, 25))]
    leaders = []
    for i, (uid, amt) in enumerate(ranked, start=1):
        leaders.append({
            "rank": i,
            "user_label": f"fan_{uid[-4:]}" if len(uid) > 4 else "fan",
            "amount_mn2": round(amt, 2),
        })
    return {"success": True, "performer_id": pid, "leaders": leaders, "count": len(leaders)}


def start_private_show(user_id: str, performer_id: str, minutes: int = 5) -> Dict[str, Any]:
    from backend.services.camgirls_service import _debit_mn2, _require_age, get_performer, user_has_unlock

    uid = (user_id or "").strip()
    gate = _require_age(uid)
    if gate:
        return gate
    row = get_performer(performer_id)
    if not row:
        return {"success": False, "error": "performer_not_found"}
    pid = (row.get("id") or "").strip()
    if not user_has_unlock(uid, pid):
        return {"success": False, "error": "unlock_required", "code": "unlock_required"}
    mins = max(1, min(int(minutes or 5), 60))
    rate = _studio_extras(row)["private_show_mn2_per_min"]
    total = round(rate * mins, 8)
    debit = _debit_mn2(
        uid,
        total,
        source="camgirl_private_show",
        metadata={"ledger_type": "camgirl_private_show", "performer_id": pid, "minutes": mins},
    )
    if not debit.get("success"):
        return debit
    session = {
        "user_id": uid,
        "performer_id": pid,
        "minutes": mins,
        "amount_mn2": total,
        "started_at": _iso(),
        "ends_at_epoch": int(datetime.now(timezone.utc).timestamp()) + mins * 60,
    }
    with _LOCK:
        data = _read_json(_PRIVATE_FILE, {"sessions": {}})
        if not isinstance(data, dict):
            data = {"sessions": {}}
        sessions = data.setdefault("sessions", {})
        sessions[f"{uid}:{pid}"] = session
        _write_json(_PRIVATE_FILE, data)
    name = row.get("display_name") or pid
    return {
        "success": True,
        "performer_id": pid,
        "minutes": mins,
        "amount_mn2": total,
        "ends_at_epoch": session["ends_at_epoch"],
        "performer_reply": f"{name} — private show live for {mins} min. VIP mode on.",
    }


def get_private_show_status(user_id: str, performer_id: str) -> Dict[str, Any]:
    uid = (user_id or "").strip()
    pid = (performer_id or "").strip()
    data = _read_json(_PRIVATE_FILE, {"sessions": {}})
    sessions = data.get("sessions") if isinstance(data.get("sessions"), dict) else {}
    session = sessions.get(f"{uid}:{pid}")
    if not isinstance(session, dict):
        return {"success": True, "active": False}
    now = int(datetime.now(timezone.utc).timestamp())
    active = now < int(session.get("ends_at_epoch") or 0)
    return {
        "success": True,
        "active": active,
        "minutes": session.get("minutes"),
        "ends_at_epoch": session.get("ends_at_epoch"),
        "seconds_left": max(0, int(session.get("ends_at_epoch") or 0) - now) if active else 0,
    }


def pick_mood_lingo(row: Dict[str, Any], mood_id: str) -> str:
    moods = {
        "cozy": "Cozy mode — soft lights, softer words.",
        "party": "Party mode — let's gooo, room's buzzing!",
        "vip": "VIP mode — velvet rope energy only.",
        "flirty_sfw": "Playful SFW flirt — wink without the edge.",
        "zen": "Zen mode — breathe with me.",
    }
    base = moods.get(mood_id) or moods["cozy"]
    studio = row.get("studio") if isinstance(row.get("studio"), dict) else {}
    catch = studio.get("catchphrases") or []
    if catch:
        return f"{random.choice(catch)} — {base}"
    return base
