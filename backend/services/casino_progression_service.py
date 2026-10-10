"""
Casino v10 — XP levels, daily walk, trophies, achievement history, crypto level rewards.
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

_BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_CONFIG_PATH = os.path.join(_BASE, "data", "casino_progression_v10.json")
_STATE_PATH = os.path.join(_BASE, "logs", "casino_progression", "users.json")


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _load_config() -> Dict[str, Any]:
    if not os.path.isfile(_CONFIG_PATH):
        return {}
    try:
        with open(_CONFIG_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _load_state() -> Dict[str, Any]:
    if not os.path.isfile(_STATE_PATH):
        return {"users": {}}
    try:
        with open(_STATE_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {"users": {}}
    except Exception:
        return {"users": {}}


def _save_state(data: Dict[str, Any]) -> None:
    os.makedirs(os.path.dirname(_STATE_PATH), exist_ok=True)
    tmp = _STATE_PATH + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    os.replace(tmp, _STATE_PATH)


def _user_row(user_id: str) -> Dict[str, Any]:
    uid = (user_id or "").strip()
    data = _load_state()
    users = data.setdefault("users", {})
    row = users.setdefault(uid, {})
    row.setdefault("xp", 0)
    row.setdefault("level", 1)
    row.setdefault("claimed_levels", [])
    row.setdefault("trophies_earned", [])
    row.setdefault("achievement_history", [])
    row.setdefault("walk_today", {})
    row.setdefault("assigned_agent", None)
    row.setdefault("metrics", {})
    row.setdefault("walk_agent_days", 0)
    _save_state(data)
    return row


def _levels_cfg() -> List[Dict[str, Any]]:
    cfg = _load_config()
    levels = cfg.get("levels") or []
    return [dict(x) for x in levels if isinstance(x, dict)]


def _level_for_xp(xp: int) -> int:
    levels = _levels_cfg()
    current = 1
    for row in levels:
        try:
            req = int(row.get("xp_required") or 0)
            lvl = int(row.get("level") or 1)
        except (TypeError, ValueError):
            continue
        if xp >= req:
            current = max(current, lvl)
    return current


def _fx_tier_for_level(level: int) -> Dict[str, Any]:
    cfg = _load_config()
    tiers = cfg.get("experience_tiers") or []
    tier = 1
    for row in tiers:
        if isinstance(row, dict):
            try:
                t = int(row.get("tier") or 0)
            except (TypeError, ValueError):
                continue
            if level >= t:
                tier = max(tier, t)
    for row in tiers:
        if isinstance(row, dict) and int(row.get("tier") or 0) == tier:
            return dict(row)
    return {"tier": 1, "label": "Rookie", "fx": "minimal", "sound_pack": "soft"}


def _append_history(user_id: str, entry: Dict[str, Any]) -> None:
    uid = (user_id or "").strip()
    if not uid:
        return
    data = _load_state()
    users = data.setdefault("users", {})
    row = users.setdefault(uid, {})
    hist = row.setdefault("achievement_history", [])
    if not isinstance(hist, list):
        hist = []
        row["achievement_history"] = hist
    entry = dict(entry)
    entry.setdefault("at", _utcnow().isoformat())
    hist.append(entry)
    if len(hist) > 200:
        row["achievement_history"] = hist[-200:]
    _save_state(data)


def add_casino_xp(user_id: str, amount: int, *, source: str = "bet") -> None:
    """Called from casino bet finalization hooks."""
    try:
        amt = int(amount)
    except (TypeError, ValueError):
        return
    if amt <= 0:
        return
    uid = (user_id or "").strip()
    if not uid or uid == "default_user":
        return
    data = _load_state()
    users = data.setdefault("users", {})
    row = users.setdefault(uid, {})
    old_level = int(row.get("level") or 1)
    row["xp"] = int(row.get("xp") or 0) + amt
    new_level = _level_for_xp(int(row["xp"]))
    row["level"] = new_level
    _save_state(data)
    if new_level > old_level:
        _append_history(uid, {"type": "level_up", "level": new_level, "source": source})


def get_progression_public() -> Dict[str, Any]:
    cfg = _load_config()
    out = {
        "success": True,
        "version": cfg.get("version"),
        "levels": _levels_cfg(),
        "experience_tiers": cfg.get("experience_tiers") or [],
        "game_media": cfg.get("game_media") or {},
        "daily_walk": cfg.get("daily_walk") or [],
        "agent_casino_roles": cfg.get("agent_casino_roles") or [],
        "trophies": cfg.get("trophies") or [],
    }
    try:
        from backend.services.casino_earnings_service import _load_json as load_earn
        import os as _os

        feats = load_earn(_os.path.join(_BASE, "data", "casino_features_v12.json"))
        if feats.get("features"):
            out["earn_features"] = feats.get("features")
    except Exception:
        pass
    return out


def get_user_progression(user_id: str) -> Dict[str, Any]:
    cfg = _load_config()
    uid = (user_id or "").strip()
    if not uid:
        return {"success": False, "error": "user_id required"}
    row = _user_row(uid)
    xp = int(row.get("xp") or 0)
    level = int(row.get("level") or _level_for_xp(xp))
    levels = _levels_cfg()
    next_level = None
    for lv in levels:
        try:
            if int(lv.get("level") or 0) > level:
                next_level = lv
                break
        except (TypeError, ValueError):
            continue
    return {
        "success": True,
        "user_id": uid,
        "xp": xp,
        "level": level,
        "fx_tier": _fx_tier_for_level(level),
        "next_level": next_level,
        "claimed_levels": list(row.get("claimed_levels") or []),
        "trophies_earned": list(row.get("trophies_earned") or []),
        "assigned_agent": row.get("assigned_agent"),
        "achievement_history": list(row.get("achievement_history") or [])[-30:],
        "walk": _walk_status(uid, row, cfg),
        "trophies": _trophy_progress(uid, row, cfg),
    }


def _walk_status(uid: str, row: Dict[str, Any], cfg: Dict[str, Any]) -> Dict[str, Any]:
    today = _utcnow().strftime("%Y-%m-%d")
    walk = row.get("walk_today") if isinstance(row.get("walk_today"), dict) else {}
    if walk.get("date") != today:
        walk = {"date": today, "completed": [], "current_index": 0}
        row["walk_today"] = walk
        data = _load_state()
        data.setdefault("users", {})[uid] = row
        _save_state(data)
    steps = cfg.get("daily_walk") or []
    completed = set(walk.get("completed") or [])
    out_steps = []
    for i, step in enumerate(steps):
        if not isinstance(step, dict):
            continue
        sid = step.get("id")
        out_steps.append({
            **step,
            "index": i,
            "completed": sid in completed,
            "active": i == int(walk.get("current_index") or 0) and sid not in completed,
        })
    return {
        "date": today,
        "steps": out_steps,
        "completed_count": len(completed),
        "total": len(out_steps),
    }


def _trophy_progress(uid: str, row: Dict[str, Any], cfg: Dict[str, Any]) -> List[Dict[str, Any]]:
    earned = set(row.get("trophies_earned") or [])
    metrics = row.get("metrics") if isinstance(row.get("metrics"), dict) else {}
    out = []
    for tr in cfg.get("trophies") or []:
        if not isinstance(tr, dict):
            continue
        tid = tr.get("id")
        try:
            target = int(tr.get("target") or 1)
        except (TypeError, ValueError):
            target = 1
        metric = tr.get("metric") or ""
        if metric == "casino_level":
            progress = int(row.get("level") or 1)
        elif metric in ("shop_items_owned", "hunt_claimed", "play_app_chests"):
            try:
                from backend.services.casino_earnings_service import _user_row as earn_row

                er = earn_row(uid)
                if metric == "shop_items_owned":
                    progress = len(er.get("owned_items") or [])
                elif metric == "hunt_claimed":
                    progress = len(er.get("hunt_claimed") or [])
                else:
                    progress = int(er.get("play_app_chests") or 0)
            except Exception:
                progress = 0
        elif metric == "social_friends":
            try:
                from backend.services.casino_earnings_service import _friend_count

                progress = _friend_count(uid)
            except Exception:
                progress = 0
        else:
            try:
                progress = int(metrics.get(metric) or 0)
            except (TypeError, ValueError):
                progress = 0
        out.append({
            **tr,
            "earned": tid in earned,
            "progress": progress,
            "target": target,
        })
    return out


def complete_walk_step(user_id: str, step_id: str) -> Dict[str, Any]:
    uid = (user_id or "").strip()
    sid = (step_id or "").strip()
    cfg = _load_config()
    steps = cfg.get("daily_walk") or []
    step = next((s for s in steps if isinstance(s, dict) and s.get("id") == sid), None)
    if not step:
        return {"success": False, "error": "unknown_step"}
    row = _user_row(uid)
    walk = row.get("walk_today") if isinstance(row.get("walk_today"), dict) else {}
    today = _utcnow().strftime("%Y-%m-%d")
    if walk.get("date") != today:
        walk = {"date": today, "completed": [], "current_index": 0}
    completed = list(walk.get("completed") or [])
    if sid in completed:
        return {"success": True, "already_completed": True}
    if step.get("assign_agent") and not row.get("assigned_agent"):
        return {"success": False, "error": "assign_agent_first", "code": "AGENT_REQUIRED"}
    completed.append(sid)
    walk["completed"] = completed
    walk["current_index"] = min(len(completed), max(0, len(steps) - 1))
    row["walk_today"] = walk
    if row.get("assigned_agent"):
        row["walk_agent_days"] = int(row.get("walk_agent_days") or 0) + 1
    reward_coins = int(step.get("reward_coins") or 0)
    reward_mn2 = float(step.get("reward_mn2") or 0)
    data = _load_state()
    data.setdefault("users", {})[uid] = row
    _save_state(data)
    _grant_rewards(uid, reward_coins, reward_mn2, source="casino_walk", metadata={"step_id": sid})
    add_casino_xp(uid, int(_load_config().get("xp_per_quest") or 40), source="walk")
    _append_history(uid, {"type": "walk_step", "step_id": sid, "reward_coins": reward_coins})
    _check_trophies(uid)
    try:
        from backend.services.casino_social_hub_service import push_casino_activity

        push_casino_activity(uid, "casino_walk", f"Completed daily walk step: {step.get('title') or sid}", {"step_id": sid})
    except Exception:
        pass
    return {
        "success": True,
        "step_id": sid,
        "reward_coins": reward_coins,
        "reward_mn2": reward_mn2 or None,
        "walk": _walk_status(uid, row, cfg),
    }


def assign_walk_agent(user_id: str, agent_id: str) -> Dict[str, Any]:
    uid = (user_id or "").strip()
    aid = (agent_id or "").strip()
    cfg = _load_config()
    pool = {a.get("id") for a in (cfg.get("agent_casino_roles") or []) if isinstance(a, dict)}
    if aid not in pool:
        return {"success": False, "error": "unknown_agent"}
    row = _user_row(uid)
    row["assigned_agent"] = aid
    data = _load_state()
    data.setdefault("users", {})[uid] = row
    _save_state(data)
    role = next((a for a in cfg.get("agent_casino_roles") or [] if a.get("id") == aid), {})
    _append_history(uid, {"type": "agent_assigned", "agent_id": aid})
    return {"success": True, "assigned_agent": aid, "role": role}


def claim_level_reward(user_id: str, level: int) -> Dict[str, Any]:
    uid = (user_id or "").strip()
    try:
        lvl = int(level)
    except (TypeError, ValueError):
        return {"success": False, "error": "invalid_level"}
    row = _user_row(uid)
    current = int(row.get("level") or 1)
    if lvl > current:
        return {"success": False, "error": "level_not_reached"}
    claimed = list(row.get("claimed_levels") or [])
    if lvl in claimed:
        return {"success": True, "already_claimed": True}
    level_row = next((x for x in _levels_cfg() if int(x.get("level") or 0) == lvl), None)
    if not level_row:
        return {"success": False, "error": "unknown_level"}
    coins = int(level_row.get("reward_coins") or 0)
    mn2 = float(level_row.get("reward_mn2") or 0)
    claimed.append(lvl)
    row["claimed_levels"] = claimed
    data = _load_state()
    data.setdefault("users", {})[uid] = row
    _save_state(data)
    _grant_rewards(uid, coins, mn2, source="casino_level", metadata={"level": lvl})
    _append_history(uid, {"type": "level_reward", "level": lvl, "coins": coins, "mn2": mn2})
    _check_trophies(uid)
    return {"success": True, "level": lvl, "reward_coins": coins, "reward_mn2": mn2 or None}


def _grant_rewards(user_id: str, coins: int, mn2: float, *, source: str, metadata: Optional[dict] = None) -> None:
    try:
        from backend.services.unified_points_database import unified_points_db

        if coins > 0:
            unified_points_db.add_points(user_id, "coins", float(coins), source=source, metadata=metadata)
        if mn2 > 0:
            unified_points_db.add_points(user_id, "mn2_balance", mn2, source=source, metadata=metadata)
    except Exception:
        pass


def _check_trophies(user_id: str) -> None:
    uid = (user_id or "").strip()
    cfg = _load_config()
    data = _load_state()
    users = data.get("users") or {}
    row = users.get(uid) if isinstance(users.get(uid), dict) else None
    if not row:
        return
    earned = set(row.get("trophies_earned") or [])
    metrics = row.get("metrics") if isinstance(row.get("metrics"), dict) else {}
    for tr in cfg.get("trophies") or []:
        if not isinstance(tr, dict):
            continue
        tid = tr.get("id")
        if not tid or tid in earned:
            continue
        metric = tr.get("metric") or ""
        try:
            target = int(tr.get("target") or 1)
        except (TypeError, ValueError):
            target = 1
        if metric == "casino_level":
            progress = int(row.get("level") or 1)
        elif metric in ("shop_items_owned", "hunt_claimed", "play_app_chests"):
            try:
                from backend.services.casino_earnings_service import _user_row as earn_row

                er = earn_row(uid)
                if metric == "shop_items_owned":
                    progress = len(er.get("owned_items") or [])
                elif metric == "hunt_claimed":
                    progress = len(er.get("hunt_claimed") or [])
                else:
                    progress = int(er.get("play_app_chests") or 0)
            except Exception:
                progress = 0
        elif metric == "social_friends":
            try:
                from backend.services.casino_earnings_service import _friend_count

                progress = _friend_count(uid)
            except Exception:
                progress = 0
        else:
            try:
                progress = int(metrics.get(metric) or 0)
            except (TypeError, ValueError):
                progress = 0
        if progress < target:
            continue
        earned.add(tid)
        row["trophies_earned"] = list(earned)
        coins = int(tr.get("reward_coins") or 0)
        mn2 = float(tr.get("reward_mn2") or 0)
        _grant_rewards(uid, coins, mn2, source="casino_trophy", metadata={"trophy_id": tid})
        _append_history(uid, {"type": "trophy", "trophy_id": tid, "name": tr.get("name")})
        try:
            from backend.services.casino_social_hub_service import push_casino_activity

            push_casino_activity(uid, "casino_trophy", f"Earned trophy: {tr.get('name') or tid}", {"trophy_id": tid})
        except Exception:
            pass
    users[uid] = row
    data["users"] = users
    _save_state(data)


def record_casino_metric(user_id: str, metric: str, amount: int = 1) -> None:
    """Increment progression metrics (wins, big_wins, etc.) from casino_service hooks."""
    uid = (user_id or "").strip()
    key = (metric or "").strip()
    if not uid or not key:
        return
    try:
        delta = int(amount)
    except (TypeError, ValueError):
        delta = 1
    row = _user_row(uid)
    metrics = row.setdefault("metrics", {})
    metrics[key] = int(metrics.get(key) or 0) + delta
    data = _load_state()
    data.setdefault("users", {})[uid] = row
    _save_state(data)
    _check_trophies(uid)
