"""
Persistent battle social state (tournaments, clans) for single-node or shared filesystem.
Survives process restarts; for multi-instance without shared disk, use DB-backed storage later.
"""
from __future__ import annotations

import json
import os
import threading
from copy import deepcopy
from typing import Any, Dict, List, Optional, Tuple

_lock = threading.RLock()

_DEFAULT_TOURNAMENTS: List[Dict[str, Any]] = [
    {
        "id": "tour_alpha",
        "name": "Alpha Clash Cup",
        "status": "open",
        "type": "Single Elimination",
        "max_participants": 16,
        "entry_fee": 0,
        "prize_pool": {"1st": "500 pts", "2nd": "200 pts", "3rd": "100 pts"},
        "participants": [],
    },
    {
        "id": "tour_omega",
        "name": "Omega Skills League",
        "status": "open",
        "type": "Round Robin",
        "max_participants": 12,
        "entry_fee": 0,
        "prize_pool": {"1st": "400 pts", "2nd": "150 pts"},
        "participants": [],
    },
]

_DEFAULT_CLANS: List[Dict[str, Any]] = [
    {"id": "clan_vanguard", "name": "Vanguard Protocol", "focus": "offense", "members": []},
    {"id": "clan_aegis", "name": "Aegis Circuit", "focus": "defense", "members": []},
    {"id": "clan_nova", "name": "Nova Syndicate", "focus": "tactics", "members": []},
]


def _base_dir() -> str:
    return os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _state_path() -> str:
    return os.path.join(_base_dir(), "data", "battle_social_state.json")


def _ensure_defaults_structure(data: Dict[str, Any]) -> Dict[str, Any]:
    out = {"tournaments": [], "clans": []}
    if not isinstance(data, dict):
        return out
    tours = data.get("tournaments")
    clans = data.get("clans")
    out["tournaments"] = tours if isinstance(tours, list) else []
    out["clans"] = clans if isinstance(clans, list) else []
    return out


def _merge_with_seed(stored: Dict[str, Any]) -> Dict[str, Any]:
    """Ensure known tournament/clan ids exist; merge participant lists from stored state."""
    merged = {"tournaments": deepcopy(_DEFAULT_TOURNAMENTS), "clans": deepcopy(_DEFAULT_CLANS)}
    by_tid = {t["id"]: t for t in stored.get("tournaments", []) if isinstance(t, dict) and t.get("id")}
    for i, t in enumerate(merged["tournaments"]):
        tid = t["id"]
        if tid in by_tid:
            s = by_tid[tid]
            parts = s.get("participants")
            if isinstance(parts, list):
                merged["tournaments"][i]["participants"] = list(
                    dict.fromkeys(str(p) for p in parts if p)
                )
    by_cid = {c["id"]: c for c in stored.get("clans", []) if isinstance(c, dict) and c.get("id")}
    for i, c in enumerate(merged["clans"]):
        cid = c["id"]
        if cid in by_cid:
            m = by_cid[cid].get("members")
            if isinstance(m, list):
                merged["clans"][i]["members"] = list(dict.fromkeys(str(x) for x in m if x))
    return merged


def load_state() -> Dict[str, Any]:
    path = _state_path()
    with _lock:
        if not os.path.isfile(path):
            data = _merge_with_seed(_ensure_defaults_structure({}))
            _write_unlocked(data)
            return deepcopy(data)
        try:
            with open(path, "r", encoding="utf-8") as f:
                raw = json.load(f)
        except Exception:
            raw = {}
        return _merge_with_seed(_ensure_defaults_structure(raw))


def _write_unlocked(data: Dict[str, Any]) -> None:
    path = _state_path()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    os.replace(tmp, path)


def save_state(data: Dict[str, Any]) -> None:
    with _lock:
        _write_unlocked(data)


def get_tournaments_filtered(status: Optional[str] = None) -> List[Dict[str, Any]]:
    st = load_state()
    tours = st.get("tournaments", [])
    if not status:
        return deepcopy(tours)
    s = status.strip().lower()
    return [deepcopy(t) for t in tours if str(t.get("status", "")).lower() == s]


def join_tournament(tournament_id: str, user_id: str) -> Tuple[bool, Any, int]:
    """Returns (ok, detail_or_error, http_code). detail is participant count on success."""
    with _lock:
        data = load_state()
        tmap = {t["id"]: t for t in data.get("tournaments", [])}
        t = tmap.get(tournament_id)
        if not t:
            return False, "Tournament not found", 404
        uid = str(user_id).strip()
        parts = t.setdefault("participants", [])
        if not isinstance(parts, list):
            parts = []
            t["participants"] = parts
        if uid not in parts:
            max_p = int(t.get("max_participants") or 64)
            if len(parts) >= max_p:
                return False, "Tournament is full", 400
            parts.append(uid)
        save_state(data)
        return True, len(parts), 200


def join_clan(clan_id: str, agent_id: str) -> Tuple[bool, Any, int]:
    with _lock:
        data = load_state()
        cmap = {c["id"]: c for c in data.get("clans", [])}
        c = cmap.get(clan_id)
        if not c:
            return False, "Clan not found", 404
        aid = str(agent_id).strip()
        mem = c.setdefault("members", [])
        if not isinstance(mem, list):
            mem = []
            c["members"] = mem
        if aid not in mem:
            mem.append(aid)
        save_state(data)
        return True, len(mem), 200
