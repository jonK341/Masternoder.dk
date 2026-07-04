"""Trader leveling, rewards and achievements for exchange / agent activity.

Per-user state in data/exchange_leveling/{user}.json:
  { xp, claimed_levels: [..], achievements: {id: ts}, stats: {...}, daily: {last_login} }

XP comes from exchange actions (crypto buys, agent purchases, agent profit, ticks, sweeps,
daily login). Levels grant MN2 + a cumulative fee discount. Achievements auto-unlock and pay
out when their stat threshold is crossed. Bots/agents also accrue "game time" and their own
levels (see ``agent_level_for_xp`` / ``agent_edge_bonus_bps``), used by the marketplace tick.
"""
from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from backend.services import crypto_exchange_service as ex

_CONFIG_PATH = os.path.join(ex._BASE, "data", "exchange_leveling_config.json")
_STATE_DIR = os.path.join(ex._DATA_DIR, "exchange_leveling")


def _iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def load_config() -> Dict[str, Any]:
    cfg = ex._read_json(_CONFIG_PATH, {})
    return cfg if isinstance(cfg, dict) else {}


def _state_path(user_id: str) -> str:
    safe = "".join(c if c.isalnum() or c in "-_" else "_" for c in str(user_id))
    return os.path.join(_STATE_DIR, f"{safe}.json")


def _load_state(user_id: str) -> Dict[str, Any]:
    data = ex._read_json(_state_path(user_id), {})
    if not isinstance(data, dict):
        data = {}
    data.setdefault("xp", 0.0)
    data.setdefault("claimed_levels", [])
    data.setdefault("achievements", {})
    data.setdefault("stats", {})
    data.setdefault("daily", {})
    st = data["stats"]
    for k in ("agents_owned", "premium_owned", "crypto_buys", "total_agent_profit_usd",
              "total_ticks", "total_game_time_sec", "sweeps"):
        st.setdefault(k, 0)
    return data


def _save_state(user_id: str, data: Dict[str, Any]) -> None:
    os.makedirs(_STATE_DIR, exist_ok=True)
    ex._write_json(_state_path(user_id), data)


# ----------------------------- level math -----------------------------

def _cost_for_level(level: int, base: float, growth: float) -> float:
    """XP cost to go from ``level`` to ``level+1``."""
    return base * (growth ** (level - 1))


def level_for_xp(xp: float, *, base: float = 100, growth: float = 1.22) -> Dict[str, Any]:
    xp = max(0.0, float(xp or 0))
    level = 1
    total = 0.0
    need = _cost_for_level(level, base, growth)
    while xp >= total + need:
        total += need
        level += 1
        need = _cost_for_level(level, base, growth)
    into = xp - total
    return {
        "level": level,
        "xp_into_level": round(into, 2),
        "xp_for_next": round(need, 2),
        "progress_pct": round(min(100.0, (into / need) * 100), 1) if need else 0.0,
    }


def agent_level_for_xp(xp: float, *, base: float = 60, growth: float = 1.2) -> int:
    return level_for_xp(xp, base=base, growth=growth)["level"]


def agent_edge_bonus_bps(agent_level: int, cfg: Optional[Dict[str, Any]] = None) -> float:
    al = (cfg or load_config()).get("agent_levels") or {}
    per = float(al.get("edge_bonus_bps_per_level") or 0.4)
    cap = float(al.get("max_edge_bonus_bps") or 8)
    return round(min(cap, max(0, int(agent_level) - 1) * per), 3)


def _rank_for_level(level: int, cfg: Dict[str, Any]) -> Dict[str, Any]:
    ranks = sorted((cfg.get("ranks") or []), key=lambda r: int(r.get("min_level") or 0))
    cur = {"name": "Trader", "icon": "📈", "min_level": 1}
    for r in ranks:
        if level >= int(r.get("min_level") or 0):
            cur = r
    return cur


def _credit_mn2(user_id: str, amount: float, source: str, meta: Optional[Dict[str, Any]] = None) -> bool:
    if amount <= 0 or not user_id or user_id == "default_user":
        return False
    try:
        ex._adjust_quote_balance(user_id, "MN2", float(amount), source, meta or {})
        return True
    except Exception:
        return False


# ----------------------------- achievements -----------------------------

def _evaluate_achievements(user_id: str, data: Dict[str, Any], cfg: Dict[str, Any]) -> List[Dict[str, Any]]:
    unlocked = data["achievements"]
    stats = dict(data["stats"])
    lc = cfg.get("level_base_cost") or 100
    lg = cfg.get("level_growth") or 1.22
    stats["level"] = level_for_xp(data.get("xp", 0), base=lc, growth=lg)["level"]
    newly: List[Dict[str, Any]] = []
    for ach in cfg.get("achievements") or []:
        aid = ach.get("id")
        if not aid or aid in unlocked:
            continue
        metric = ach.get("metric")
        threshold = float(ach.get("threshold") or 0)
        if float(stats.get(metric, 0) or 0) >= threshold:
            unlocked[aid] = _iso()
            reward_mn2 = float(ach.get("reward_mn2") or 0)
            reward_xp = float(ach.get("reward_xp") or 0)
            if reward_xp > 0:
                data["xp"] = round(float(data.get("xp") or 0) + reward_xp, 2)
            _credit_mn2(user_id, reward_mn2, "leveling_achievement", {"achievement": aid})
            ex._audit("leveling_achievement", user_id=user_id, achievement=aid,
                      reward_mn2=reward_mn2, reward_xp=reward_xp)
            newly.append({"id": aid, "name": ach.get("name"), "reward_mn2": reward_mn2, "reward_xp": reward_xp})
    return newly


# ----------------------------- award / record -----------------------------

def award_xp(user_id: str, amount: float, source: str, **meta) -> Dict[str, Any]:
    user_id = (user_id or "").strip()
    if not user_id:
        return {"success": False, "error": "user_id_required"}
    cfg = load_config()
    if not cfg.get("enabled", True):
        return {"success": False, "error": "leveling_disabled"}
    data = _load_state(user_id)
    lc = cfg.get("level_base_cost") or 100
    lg = cfg.get("level_growth") or 1.22
    before = level_for_xp(data.get("xp", 0), base=lc, growth=lg)["level"]
    data["xp"] = round(float(data.get("xp") or 0) + float(amount or 0), 2)
    after = level_for_xp(data["xp"], base=lc, growth=lg)["level"]
    newly = _evaluate_achievements(user_id, data, cfg)
    _save_state(user_id, data)
    return {"success": True, "xp": data["xp"], "level": after, "leveled_up": after > before,
            "gained": float(amount or 0), "new_achievements": newly}


def _bump_stats(user_id: str, cfg: Dict[str, Any], **deltas) -> Dict[str, Any]:
    data = _load_state(user_id)
    st = data["stats"]
    for k, v in deltas.items():
        if isinstance(v, bool):
            st[k] = 1 if v or st.get(k) else st.get(k, 0)
        else:
            st[k] = round(float(st.get(k) or 0) + float(v), 6)
    newly = _evaluate_achievements(user_id, data, cfg)
    _save_state(user_id, data)
    return {"stats": st, "new_achievements": newly}


def _merge(stat_res: Dict[str, Any], xp_res: Dict[str, Any]) -> Dict[str, Any]:
    seen = {}
    for a in (stat_res.get("new_achievements") or []) + (xp_res.get("new_achievements") or []):
        seen[a["id"]] = a
    out = dict(xp_res)
    out["new_achievements"] = list(seen.values())
    return out


def record_agent_purchase(user_id: str, *, premium: bool = False) -> Dict[str, Any]:
    cfg = load_config()
    xa = cfg.get("xp_actions") or {}
    xp = float(xa.get("agent_purchase") or 0) + (float(xa.get("premium_purchase_bonus") or 0) if premium else 0)
    stat_res = _bump_stats(user_id, cfg, agents_owned=1, premium_owned=bool(premium))
    return _merge(stat_res, award_xp(user_id, xp, "agent_purchase", premium=premium))


def record_agent_tick(user_id: str, profit_usd: float, *, tick_seconds: Optional[float] = None) -> Dict[str, Any]:
    cfg = load_config()
    xa = cfg.get("xp_actions") or {}
    al = cfg.get("agent_levels") or {}
    secs = float(tick_seconds if tick_seconds is not None else al.get("tick_seconds") or 3600)
    xp = float(xa.get("agent_tick") or 0) + max(0.0, float(profit_usd or 0)) * float(xa.get("agent_profit_per_usd") or 0)
    stat_res = _bump_stats(user_id, cfg, total_agent_profit_usd=max(0.0, float(profit_usd or 0)),
                           total_ticks=1, total_game_time_sec=secs)
    return _merge(stat_res, award_xp(user_id, xp, "agent_tick"))


def record_crypto_buy(user_id: str, usd: float = 0.0) -> Dict[str, Any]:
    cfg = load_config()
    xa = cfg.get("xp_actions") or {}
    stat_res = _bump_stats(user_id, cfg, crypto_buys=1)
    return _merge(stat_res, award_xp(user_id, float(xa.get("buy_crypto") or 0), "buy_crypto", usd=usd))


def record_sweep(user_id: str, amount_usd: float = 0.0) -> Dict[str, Any]:
    cfg = load_config()
    xa = cfg.get("xp_actions") or {}
    stat_res = _bump_stats(user_id, cfg, sweeps=1)
    return _merge(stat_res, award_xp(user_id, float(xa.get("sweep") or 0), "sweep", amount_usd=amount_usd))


def record_daily_login(user_id: str) -> Dict[str, Any]:
    cfg = load_config()
    data = _load_state(user_id)
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    if data["daily"].get("last_login") == today:
        return {"success": True, "already_claimed": True}
    data["daily"]["last_login"] = today
    _save_state(user_id, data)
    xa = cfg.get("xp_actions") or {}
    return award_xp(user_id, float(xa.get("daily_login") or 0), "daily_login")


# ----------------------------- claim / read -----------------------------

def claim_level_reward(user_id: str, level: int) -> Dict[str, Any]:
    user_id = (user_id or "").strip()
    if not user_id:
        return {"success": False, "error": "user_id_required"}
    level = int(level)
    cfg = load_config()
    lc = cfg.get("level_base_cost") or 100
    lg = cfg.get("level_growth") or 1.22
    data = _load_state(user_id)
    cur = level_for_xp(data.get("xp", 0), base=lc, growth=lg)["level"]
    if level < 1 or level > cur:
        return {"success": False, "error": "level_not_reached", "current_level": cur}
    if level in data["claimed_levels"]:
        return {"success": True, "already_claimed": True, "level": level}

    lr = cfg.get("level_reward") or {}
    mn2 = round(float(lr.get("mn2_per_level") or 0) * level, 6)
    credited = _credit_mn2(user_id, mn2, "leveling_level_reward", {"level": level})
    data["claimed_levels"].append(level)
    _save_state(user_id, data)
    ex._audit("leveling_level_claim", user_id=user_id, level=level, reward_mn2=mn2)
    return {"success": True, "level": level, "reward_mn2": mn2 if credited else 0.0}


def _fee_discount_bps(level: int, cfg: Dict[str, Any]) -> float:
    lr = cfg.get("level_reward") or {}
    per = float(lr.get("fee_discount_bps_per_level") or 0)
    cap = float(lr.get("max_fee_discount_bps") or 1e9)
    return round(min(cap, max(0, level - 1) * per), 2)


def user_progress(user_id: str) -> Dict[str, Any]:
    cfg = load_config()
    lc = cfg.get("level_base_cost") or 100
    lg = cfg.get("level_growth") or 1.22
    data = _load_state(user_id)
    lv = level_for_xp(data.get("xp", 0), base=lc, growth=lg)
    rank = _rank_for_level(lv["level"], cfg)
    claimable = [n for n in range(1, lv["level"] + 1) if n not in data["claimed_levels"]]
    ach_unlocked = data["achievements"]
    catalog = []
    stats = dict(data["stats"])
    stats["level"] = lv["level"]
    for ach in cfg.get("achievements") or []:
        aid = ach.get("id")
        cur = float(stats.get(ach.get("metric"), 0) or 0)
        thr = float(ach.get("threshold") or 0)
        catalog.append({
            "id": aid, "name": ach.get("name"), "desc": ach.get("desc"), "icon": ach.get("icon"),
            "unlocked": aid in ach_unlocked, "unlocked_at": ach_unlocked.get(aid),
            "progress": round(min(cur, thr), 2), "target": thr,
            "progress_pct": round(min(100.0, (cur / thr) * 100), 1) if thr else 0.0,
            "reward_mn2": ach.get("reward_mn2"),
        })
    return {
        "success": True,
        "user_id": user_id,
        "xp": round(float(data.get("xp") or 0), 2),
        "level": lv["level"],
        "xp_into_level": lv["xp_into_level"],
        "xp_for_next": lv["xp_for_next"],
        "progress_pct": lv["progress_pct"],
        "rank": {"name": rank.get("name"), "icon": rank.get("icon")},
        "fee_discount_bps": _fee_discount_bps(lv["level"], cfg),
        "claimable_levels": claimable,
        "stats": stats,
        "achievements_unlocked": len(ach_unlocked),
        "achievements_total": len(cfg.get("achievements") or []),
        "achievements": catalog,
    }
