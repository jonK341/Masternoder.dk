"""
MN2 staking teams / pools (§20 #7).

Friends join a team via invite code. Team multiplier boosts rewards when ≥2 members
have min stake — based on pooled average longevity + member count, hard-capped.
"""
from __future__ import annotations

import json
import os
import re
import secrets
import threading
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

_LOCK = threading.Lock()
_BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_PATH = os.path.join(_BASE, "data", "mn2_staking_teams.json")

DEFAULT_TEAMS_CFG: Dict[str, Any] = {
    "enabled": True,
    "max_members": 8,
    "max_teams_per_user": 1,
    "min_member_staked_mn2": 0.1,
    "max_team_multiplier": 1.15,
    "per_member_bonus": 0.02,
    "longevity_pool_factor": 0.05,
    "longevity_pool_days_divisor": 90.0,
}


def _iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load() -> Dict[str, Any]:
    if not os.path.exists(_PATH):
        return {"teams": {}, "member_index": {}, "codes": {}}
    try:
        with open(_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict):
            return {"teams": {}, "member_index": {}, "codes": {}}
        data.setdefault("teams", {})
        data.setdefault("member_index", {})
        data.setdefault("codes", {})
        return data
    except Exception:
        return {"teams": {}, "member_index": {}, "codes": {}}


def _save(data: Dict[str, Any]) -> None:
    os.makedirs(os.path.dirname(_PATH), exist_ok=True)
    tmp = _PATH + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    os.replace(tmp, _PATH)


def _teams_cfg() -> Dict[str, Any]:
    try:
        import backend.services.mn2_staking_service as staking
        raw = (staking.get_config().get("teams") or {})
    except Exception:
        raw = {}
    cfg = dict(DEFAULT_TEAMS_CFG)
    if isinstance(raw, dict):
        cfg.update({k: raw[k] for k in DEFAULT_TEAMS_CFG if k in raw})
    return cfg


def _new_code(data: Dict[str, Any]) -> str:
    for _ in range(20):
        code = secrets.token_hex(3).upper()
        if code not in data.get("codes", {}):
            return code
    return secrets.token_hex(4).upper()


def _team_id() -> str:
    return "team_" + secrets.token_hex(6)


def _sanitize_name(name: str) -> str:
    n = re.sub(r"\s+", " ", (name or "").strip())[:32]
    return n or "Staking team"


def user_team_id(user_id: str) -> Optional[str]:
    uid = (user_id or "").strip()
    if not uid:
        return None
    return (_load().get("member_index") or {}).get(uid)


def team_multiplier(user_id: str) -> float:
    cfg = _teams_cfg()
    if not cfg.get("enabled"):
        return 1.0
    tid = user_team_id(user_id)
    if not tid:
        return 1.0
    team = (_load().get("teams") or {}).get(tid)
    if not isinstance(team, dict):
        return 1.0

    try:
        import backend.services.mn2_staking_service as staking
        stakes = staking._load_stakes()  # noqa: SLF001
        longevity_days = staking.longevity_days
    except Exception:
        return 1.0

    min_staked = float(cfg.get("min_member_staked_mn2") or 0.1)
    active_days: List[float] = []
    for mid in team.get("members") or []:
        rec = stakes.get(mid) if isinstance(stakes.get(mid), dict) else {}
        staked = float((rec or {}).get("staked", 0) or 0)
        if staked >= min_staked:
            active_days.append(longevity_days(rec or {}))

    if len(active_days) < 2:
        return 1.0

    avg_days = sum(active_days) / len(active_days)
    member_part = (len(active_days) - 1) * float(cfg.get("per_member_bonus") or 0.02)
    lon_part = (avg_days / float(cfg.get("longevity_pool_days_divisor") or 90.0)) * float(
        cfg.get("longevity_pool_factor") or 0.05
    )
    cap = float(cfg.get("max_team_multiplier") or 1.15) - 1.0
    bonus = min(member_part + lon_part, cap)
    return round(1.0 + max(0.0, bonus), 4)


def get_team_for_user(user_id: str) -> Dict[str, Any]:
    uid = (user_id or "").strip()
    cfg = _teams_cfg()
    tid = user_team_id(uid)
    if not tid:
        return {"success": True, "in_team": False, "enabled": bool(cfg.get("enabled"))}
    data = _load()
    team = (data.get("teams") or {}).get(tid)
    if not isinstance(team, dict):
        return {"success": True, "in_team": False, "enabled": bool(cfg.get("enabled"))}

    try:
        import backend.services.mn2_staking_service as staking
        stakes = staking._load_stakes()  # noqa: SLF001
    except Exception:
        stakes = {}

    members_out = []
    total_staked = 0.0
    pooled_days = 0.0
    active_count = 0
    min_staked = float(cfg.get("min_member_staked_mn2") or 0.1)
    for mid in team.get("members") or []:
        rec = stakes.get(mid) if isinstance(stakes.get(mid), dict) else {}
        staked = float((rec or {}).get("staked", 0) or 0)
        days = 0.0
        try:
            days = staking.longevity_days(rec or {})
        except Exception:
            pass
        total_staked += staked
        if staked >= min_staked:
            active_count += 1
            pooled_days += days
        members_out.append({
            "user_id": mid,
            "display_id": _anon(mid),
            "staked_mn2": round(staked, 8),
            "longevity_days": round(days, 2),
            "is_leader": mid == team.get("leader_id"),
            "counts_for_boost": staked >= min_staked,
        })

    avg_days = round(pooled_days / active_count, 2) if active_count else 0.0
    mult = team_multiplier(uid)
    return {
        "success": True,
        "in_team": True,
        "enabled": bool(cfg.get("enabled")),
        "team_id": tid,
        "name": team.get("name"),
        "invite_code": team.get("invite_code"),
        "leader_id": team.get("leader_id"),
        "is_leader": uid == team.get("leader_id"),
        "members": members_out,
        "member_count": len(members_out),
        "active_stakers": active_count,
        "total_staked_mn2": round(total_staked, 8),
        "pooled_avg_longevity_days": avg_days,
        "team_multiplier": mult,
        "max_team_multiplier": cfg.get("max_team_multiplier"),
    }


def _anon(user_id: str) -> str:
    import hashlib
    h = hashlib.sha256(str(user_id).encode("utf-8")).hexdigest()[:8]
    return f"user_{h}"


def create_team(user_id: str, name: str) -> Dict[str, Any]:
    cfg = _teams_cfg()
    if not cfg.get("enabled"):
        return {"success": False, "error": "Teams are disabled.", "code": "disabled"}
    uid = (user_id or "").strip()
    if not uid:
        return {"success": False, "error": "user_id required"}
    with _LOCK:
        data = _load()
        if (data.get("member_index") or {}).get(uid):
            return {"success": False, "error": "Already in a team. Leave first.", "code": "already_member"}
        tid = _team_id()
        code = _new_code(data)
        team = {
            "id": tid,
            "name": _sanitize_name(name),
            "leader_id": uid,
            "created_at": _iso(),
            "members": [uid],
            "invite_code": code,
        }
        data.setdefault("teams", {})[tid] = team
        data.setdefault("member_index", {})[uid] = tid
        data.setdefault("codes", {})[code] = tid
        _save(data)
    return {"success": True, "team": get_team_for_user(uid)}


def join_team(user_id: str, code: str) -> Dict[str, Any]:
    cfg = _teams_cfg()
    if not cfg.get("enabled"):
        return {"success": False, "error": "Teams are disabled.", "code": "disabled"}
    uid = (user_id or "").strip()
    invite = (code or "").strip().upper()
    if not uid or not invite:
        return {"success": False, "error": "invite code required"}
    max_members = int(cfg.get("max_members") or 8)
    with _LOCK:
        data = _load()
        if (data.get("member_index") or {}).get(uid):
            return {"success": False, "error": "Already in a team.", "code": "already_member"}
        tid = (data.get("codes") or {}).get(invite)
        if not tid:
            return {"success": False, "error": "Invalid invite code.", "code": "bad_code"}
        team = (data.get("teams") or {}).get(tid)
        if not isinstance(team, dict):
            return {"success": False, "error": "Team not found.", "code": "not_found"}
        members = list(team.get("members") or [])
        if uid in members:
            data.setdefault("member_index", {})[uid] = tid
            _save(data)
            return {"success": True, "team": get_team_for_user(uid)}
        if len(members) >= max_members:
            return {"success": False, "error": f"Team is full (max {max_members}).", "code": "full"}
        members.append(uid)
        team["members"] = members
        data["teams"][tid] = team
        data.setdefault("member_index", {})[uid] = tid
        _save(data)
    return {"success": True, "team": get_team_for_user(uid)}


def leave_team(user_id: str) -> Dict[str, Any]:
    uid = (user_id or "").strip()
    if not uid:
        return {"success": False, "error": "user_id required"}
    with _LOCK:
        data = _load()
        tid = (data.get("member_index") or {}).get(uid)
        if not tid:
            return {"success": False, "error": "Not in a team.", "code": "not_member"}
        team = (data.get("teams") or {}).get(tid)
        if not isinstance(team, dict):
            del data["member_index"][uid]
            _save(data)
            return {"success": True, "left": True}
        members = [m for m in (team.get("members") or []) if m != uid]
        code = team.get("invite_code")
        if not members:
            del data["teams"][tid]
            if code and code in data.get("codes", {}):
                del data["codes"][code]
        else:
            if team.get("leader_id") == uid:
                team["leader_id"] = members[0]
            team["members"] = members
            data["teams"][tid] = team
        del data["member_index"][uid]
        _save(data)
    return {"success": True, "left": True}


def team_leaderboard(limit: int = 20) -> Dict[str, Any]:
    cfg = _teams_cfg()
    data = _load()
    teams = data.get("teams") or {}
    try:
        import backend.services.mn2_staking_service as staking
        stakes = staking._load_stakes()  # noqa: SLF001
        longevity_days = staking.longevity_days
    except Exception:
        stakes = {}
        longevity_days = lambda r: 0.0  # noqa: E731

    min_staked = float(cfg.get("min_member_staked_mn2") or 0.1)
    rows: List[Dict[str, Any]] = []
    for tid, team in teams.items():
        if not isinstance(team, dict):
            continue
        total_staked = 0.0
        pooled_days = 0.0
        active = 0
        for mid in team.get("members") or []:
            rec = stakes.get(mid) if isinstance(stakes.get(mid), dict) else {}
            staked = float((rec or {}).get("staked", 0) or 0)
            total_staked += staked
            if staked >= min_staked:
                active += 1
                pooled_days += longevity_days(rec or {})
        if active < 2:
            continue
        avg_days = pooled_days / active
        member_part = (active - 1) * float(cfg.get("per_member_bonus") or 0.02)
        lon_part = (avg_days / float(cfg.get("longevity_pool_days_divisor") or 90.0)) * float(
            cfg.get("longevity_pool_factor") or 0.05
        )
        cap = float(cfg.get("max_team_multiplier") or 1.15) - 1.0
        mult = round(1.0 + min(member_part + lon_part, cap), 4)
        rows.append({
            "team_id": tid,
            "name": team.get("name"),
            "member_count": len(team.get("members") or []),
            "active_stakers": active,
            "total_staked_mn2": round(total_staked, 8),
            "pooled_avg_longevity_days": round(avg_days, 2),
            "team_multiplier": mult,
        })
    rows.sort(key=lambda r: (r["team_multiplier"], r["total_staked_mn2"]), reverse=True)
    lim = max(1, min(int(limit or 20), 100))
    return {
        "success": True,
        "leaderboard": rows[:lim],
        "note": "Teams need ≥2 active stakers (min stake each) to appear. Multiplier capped.",
    }
