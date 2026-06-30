"""Easy agent rental + skill add-ons for exchange bots.

Rent a bot for N days (cheaper than buying), bolt on extra skills from the addon catalog,
and earn completion rewards if the rental runs the full term. Rented agents live in the
same user_agents store with ``rented: true`` and ``expires_at``.
"""
from __future__ import annotations

import os
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from backend.services import crypto_exchange_service as ex
from backend.services import agent_marketplace_service as mkt

_CONFIG_PATH = os.path.join(ex._BASE, "data", "exchange_rental_config.json")
_RENTALS_PATH = os.path.join(ex._DATA_DIR, "rental_history.jsonl")


def _iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def load_config() -> Dict[str, Any]:
    cfg = ex._read_json(_CONFIG_PATH, {})
    return cfg if isinstance(cfg, dict) else {}


def _rental_map(cfg: Optional[Dict[str, Any]] = None) -> Dict[str, Dict[str, Any]]:
    cfg = cfg or load_config()
    return {r["id"]: r for r in (cfg.get("rentals") or []) if isinstance(r, dict) and r.get("id")}


def _addon_map(cfg: Optional[Dict[str, Any]] = None) -> Dict[str, Dict[str, Any]]:
    cfg = cfg or load_config()
    return {a["id"]: a for a in (cfg.get("skill_addons") or []) if isinstance(a, dict) and a.get("id")}


def effective_skills(agent: Dict[str, Any]) -> List[str]:
    """Base skills + rental add-ons + shop extra skills (deduped, order preserved)."""
    seen = set()
    out: List[str] = []
    for sid in list(agent.get("skills") or []) + list(agent.get("rental_skills") or []) + list(agent.get("extra_skills") or []):
        if sid and sid not in seen:
            seen.add(sid)
            out.append(sid)
    return out


def _is_expired(agent: Dict[str, Any]) -> bool:
    exp = agent.get("expires_at")
    if not exp:
        return False
    try:
        dt = datetime.fromisoformat(str(exp).replace("Z", "+00:00"))
        return dt <= datetime.now(timezone.utc)
    except Exception:
        return False


def rental_catalog() -> Dict[str, Any]:
    cfg = load_config()
    from backend.services import exchange_bot_skills_service as sk
    smap = sk._skill_map()
    vol = 0.35
    addons = []
    for a in cfg.get("skill_addons") or []:
        sid = a.get("skill_id")
        detail = smap.get(sid) or {}
        addons.append({
            **a,
            "skill_name": detail.get("name", sid),
            "skill_details": sk.skill_details([sid], volatility=vol),
        })
    rentals = []
    for r in cfg.get("rentals") or []:
        if not isinstance(r, dict):
            continue
        rentals.append(sk.enrich_agent_offer(r, volatility=vol))
    return {
        "success": True,
        "enabled": bool(cfg.get("enabled", True)),
        "currency": cfg.get("currency", "MN2"),
        "rentals": rentals,
        "skill_addons": addons,
    }


def list_user_rentals(user_id: str) -> Dict[str, Any]:
    data = mkt._read_user_agents(user_id)
    now = datetime.now(timezone.utc)
    rows = []
    for a in data.get("agents", {}).values():
        if not a.get("rented"):
            continue
        exp = a.get("expires_at")
        expired = _is_expired(a)
        days_left = 0
        if exp and not expired:
            try:
                dt = datetime.fromisoformat(str(exp).replace("Z", "+00:00"))
                days_left = max(0, (dt - now).days)
            except Exception:
                pass
        from backend.services import exchange_bot_skills_service as sk
        eff = effective_skills(a)
        skill_meta = sk.enrich_agent_offer({"skills": eff, "skill_set": a.get("skill_set")}, volatility=0.35)
        rows.append({
            **a,
            "expired": expired,
            "days_left": days_left,
            "effective_skills": eff,
            "skill_details": skill_meta.get("skill_details") or [],
            "skill_set": skill_meta.get("skill_set"),
            "blended_edge_bps": skill_meta.get("blended_edge_bps"),
        })
    return {"success": True, "user_id": user_id, "count": len(rows),
            "rentals": sorted(rows, key=lambda r: r.get("expires_at") or "", reverse=True)}


def rent_agent(user_id: str, rental_id: str, *, prepaid: bool = False, auto_renew: bool = False) -> Dict[str, Any]:
    user_id = (user_id or "").strip()
    cfg = load_config()
    if not cfg.get("enabled", True):
        return {"success": False, "error": "rentals_disabled"}
    tmpl = _rental_map(cfg).get((rental_id or "").strip())
    if not tmpl:
        return {"success": False, "error": "unknown_rental"}
    price = float(tmpl.get("price_mn2") or 0)
    if not prepaid and price > 0 and ex._get_quote_balance(user_id, "MN2") < price:
        return {"success": False, "error": "insufficient_mn2", "needed_mn2": price}

    days = int(tmpl.get("days") or 7)
    expires = (datetime.now(timezone.utc) + timedelta(days=days)).isoformat().replace("+00:00", "Z")
    agent_id = f"rent_{uuid.uuid4().hex[:12]}"

    if not prepaid and price > 0:
        ex._adjust_quote_balance(user_id, "MN2", -price, "exchange_rental",
                                 {"rental_id": tmpl["id"], "agent_id": agent_id})

    agent = {
        "agent_id": agent_id,
        "rental_id": tmpl["id"],
        "template_id": tmpl.get("template_id"),
        "name": tmpl.get("name") or tmpl["id"],
        "tier": "Rental",
        "owner": user_id,
        "rented": True,
        "rental_days": days,
        "expires_at": expires,
        "skills": list(tmpl.get("skills") or []),
        "skill_set": tmpl.get("skill_set"),
        "rental_skills": [],
        "extra_skills": [],
        "farm_venues": list(tmpl.get("default_venues") or []),
        "farm_symbols": list(tmpl.get("default_symbols") or []),
        "farm_strategy": str(tmpl.get("farm_strategy") or "cross_exchange_farm"),
        "is_daemon": bool(tmpl.get("daemon")),
        "capital_usd": float(tmpl.get("capital_usd") or 500),
        "risk": "low",
        "cycles_per_day": float(tmpl.get("cycles_per_day") or 24),
        "premium": bool(tmpl.get("premium")),
        "super": False,
        "realized_profit_usd": 0.0,
        "trade_count": 0,
        "game_time_sec": 0,
        "ticks": 0,
        "agent_xp": 0.0,
        "agent_level": 1,
        "skill_proficiency": {},
        "intelligence": 100.0,
        "learning_bonus_bps": 0.0,
        "mastery_pct": 0.0,
        "enabled": True,
        "activation": "active",
        "completion_reward_mn2": float(tmpl.get("completion_reward_mn2") or 0),
        "completion_reward_xp": float(tmpl.get("completion_reward_xp") or 0),
        "reward_claimed": False,
        "auto_renew": bool(auto_renew),
        "auto_renew_count": 0,
        "created_at": _iso(),
        "last_action": None,
    }
    try:
        from backend.services import exchange_trust_service as trust_svc
        trust_svc.enrich_agent_on_purchase(agent)
        agent["activation"] = "active"
    except Exception:
        pass

    data = mkt._read_user_agents(user_id)
    data["agents"][agent_id] = agent
    mkt._write_user_agents(user_id, data)
    try:
        mkt._sync_exchange_skills_to_profile(user_id, agent)
    except Exception:
        pass
    ex._append_jsonl(_RENTALS_PATH, {"ts": _iso(), "user_id": user_id, "agent_id": agent_id,
                                       "rental_id": tmpl["id"], "price_mn2": price, "days": days})
    ex._audit("exchange_rental_start", user_id=user_id, agent_id=agent_id, rental_id=tmpl["id"], amount_usd=price * 0.05)
    try:
        from backend.services.exchange_casino_quest_service import record_bridge_action, emit_bridge_market_event
        from backend.services.exchange_casino_leaderboard_service import record_rental_start

        record_bridge_action(user_id, "exchange_rent")
        record_rental_start(user_id)
        if bool(tmpl.get("premium")) or float(tmpl.get("price_mn2") or 0) >= 80:
            emit_bridge_market_event("exchange_rental_start", user_id, {
                "rental_id": tmpl["id"], "name": tmpl.get("name"), "days": days,
                "price_mn2": price, "agent_id": agent_id, "premium": bool(tmpl.get("premium")),
            })
    except Exception:
        pass
    try:
        from backend.services import exchange_leveling_service as lvl
        lvl.award_xp(user_id, 20, "rental_start", rental_id=tmpl["id"])
    except Exception:
        pass
    return {"success": True, "agent": agent, "spent_mn2": price, "expires_at": expires}


def add_skill_addon(user_id: str, agent_id: str, addon_id: str, *, prepaid: bool = False) -> Dict[str, Any]:
    cfg = load_config()
    addon = _addon_map(cfg).get((addon_id or "").strip())
    if not addon:
        return {"success": False, "error": "unknown_addon"}
    data = mkt._read_user_agents(user_id)
    agent = data.get("agents", {}).get(agent_id)
    if not agent:
        return {"success": False, "error": "agent_not_found"}
    if _is_expired(agent):
        return {"success": False, "error": "rental_expired"}

    price = float(addon.get("price_mn2") or 0)
    if not prepaid and price > 0 and ex._get_quote_balance(user_id, "MN2") < price:
        return {"success": False, "error": "insufficient_mn2"}

    skill_id = addon.get("skill_id")
    rental_skills = list(agent.get("rental_skills") or [])
    if skill_id in effective_skills(agent):
        return {"success": False, "error": "skill_already_attached"}

    if not prepaid and price > 0:
        ex._adjust_quote_balance(user_id, "MN2", -price, "exchange_skill_addon",
                                 {"addon_id": addon_id, "agent_id": agent_id, "skill_id": skill_id})

    days = int(addon.get("days") or 7)
    rental_skills.append(skill_id)
    agent["rental_skills"] = rental_skills
    agent.setdefault("addon_expires", {})[skill_id] = (
        datetime.now(timezone.utc) + timedelta(days=days)).isoformat().replace("+00:00", "Z")
    data["agents"][agent_id] = agent
    mkt._write_user_agents(user_id, data)
    ex._audit("exchange_skill_addon", user_id=user_id, agent_id=agent_id, skill_id=skill_id, addon_id=addon_id)
    try:
        from backend.services.exchange_casino_quest_service import record_bridge_action

        record_bridge_action(user_id, "exchange_skill_addon")
    except Exception:
        pass
    return {"success": True, "agent_id": agent_id, "skill_id": skill_id, "effective_skills": effective_skills(agent),
            "spent_mn2": price}


def extend_rental(user_id: str, agent_id: str, days: int) -> Dict[str, Any]:
    data = mkt._read_user_agents(user_id)
    agent = data.get("agents", {}).get(agent_id)
    if not agent or not agent.get("rented"):
        return {"success": False, "error": "not_a_rental"}
    exp = agent.get("expires_at")
    base = datetime.now(timezone.utc)
    if exp:
        try:
            dt = datetime.fromisoformat(str(exp).replace("Z", "+00:00"))
            if dt > base:
                base = dt
        except Exception:
            pass
    agent["expires_at"] = (base + timedelta(days=int(days or 0))).isoformat().replace("+00:00", "Z")
    data["agents"][agent_id] = agent
    mkt._write_user_agents(user_id, data)
    return {"success": True, "agent_id": agent_id, "expires_at": agent["expires_at"]}


def claim_rental_reward(user_id: str, agent_id: str) -> Dict[str, Any]:
    data = mkt._read_user_agents(user_id)
    agent = data.get("agents", {}).get(agent_id)
    if not agent or not agent.get("rented"):
        return {"success": False, "error": "not_a_rental"}
    if agent.get("reward_claimed"):
        return {"success": True, "already_claimed": True}
    if not _is_expired(agent):
        return {"success": False, "error": "rental_still_active"}
    mn2 = float(agent.get("completion_reward_mn2") or 0)
    xp = float(agent.get("completion_reward_xp") or 0)
    if mn2 > 0:
        ex._adjust_quote_balance(user_id, "MN2", mn2, "rental_completion_reward", {"agent_id": agent_id})
    if xp > 0:
        try:
            from backend.services import exchange_leveling_service as lvl
            lvl.award_xp(user_id, xp, "rental_completion")
        except Exception:
            pass
    agent["reward_claimed"] = True
    data["agents"][agent_id] = agent
    mkt._write_user_agents(user_id, data)
    ex._audit("exchange_rental_reward", user_id=user_id, agent_id=agent_id, reward_mn2=mn2)
    casino_coins = 0
    try:
        from backend.services.exchange_user_controller_service import grant_casino_bridge_bonus

        casino_coins = grant_casino_bridge_bonus(user_id, "rental_completion", agent_id=agent_id)
    except Exception:
        pass
    try:
        from backend.services.exchange_casino_quest_service import record_bridge_action

        record_bridge_action(user_id, "exchange_rental_complete")
    except Exception:
        pass
    return {"success": True, "reward_mn2": mn2, "reward_xp": xp, "casino_coins_bonus": casino_coins}


def rental_gate(agent: Dict[str, Any]) -> Optional[str]:
    """Return error code if rental blocks tick, else None."""
    if not agent.get("rented"):
        return None
    if _is_expired(agent):
        return "rental_expired"
    return None


def _auto_renew_cfg(cfg: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    cfg = cfg or load_config()
    ar = cfg.get("auto_renew") or {}
    return ar if isinstance(ar, dict) else {}


def _renewal_price(agent: Dict[str, Any], cfg: Optional[Dict[str, Any]] = None) -> float:
    tmpl = _rental_map(cfg).get(agent.get("rental_id") or "", {})
    base = float(tmpl.get("price_mn2") or 0)
    disc = float(_auto_renew_cfg(cfg).get("discount_pct") or 0)
    return max(0.0, base * (1.0 - disc / 100.0))


def _hours_until_expiry(agent: Dict[str, Any]) -> Optional[float]:
    exp = agent.get("expires_at")
    if not exp:
        return None
    try:
        dt = datetime.fromisoformat(str(exp).replace("Z", "+00:00"))
        return (dt - datetime.now(timezone.utc)).total_seconds() / 3600.0
    except Exception:
        return None


def set_auto_renew(user_id: str, agent_id: str, enabled: bool) -> Dict[str, Any]:
    data = mkt._read_user_agents(user_id)
    agent = data.get("agents", {}).get(agent_id)
    if not agent or not agent.get("rented"):
        return {"success": False, "error": "not_a_rental"}
    if _is_expired(agent) and enabled:
        return {"success": False, "error": "rental_expired"}
    agent["auto_renew"] = bool(enabled)
    data["agents"][agent_id] = agent
    mkt._write_user_agents(user_id, data)
    ex._audit("exchange_rental_auto_renew", user_id=user_id, agent_id=agent_id, enabled=bool(enabled))
    return {"success": True, "agent_id": agent_id, "auto_renew": bool(enabled)}


def try_auto_renew(user_id: str, agent_id: str) -> Dict[str, Any]:
    """Charge discounted MN2 and extend a rental when within renew window or grace."""
    cfg = load_config()
    ar = _auto_renew_cfg(cfg)
    if not ar.get("enabled", True):
        return {"success": False, "error": "auto_renew_disabled"}

    data = mkt._read_user_agents(user_id)
    agent = data.get("agents", {}).get(agent_id)
    if not agent or not agent.get("rented") or not agent.get("auto_renew"):
        return {"success": False, "error": "not_eligible"}

    attempts = int(agent.get("auto_renew_count") or 0)
    max_attempts = int(ar.get("max_attempts") or 12)
    if attempts >= max_attempts:
        agent["auto_renew"] = False
        data["agents"][agent_id] = agent
        mkt._write_user_agents(user_id, data)
        return {"success": False, "error": "max_auto_renew_reached"}

    hours_left = _hours_until_expiry(agent)
    if hours_left is None:
        return {"success": False, "error": "no_expiry"}
    renew_window = float(ar.get("renew_window_hours") or 24)
    grace = float(ar.get("grace_hours") or 6)
    if hours_left > renew_window:
        return {"success": False, "error": "not_due_yet"}
    if hours_left < -grace:
        agent["auto_renew"] = False
        data["agents"][agent_id] = agent
        mkt._write_user_agents(user_id, data)
        return {"success": False, "error": "grace_elapsed"}

    price = _renewal_price(agent, cfg)
    if price > 0 and ex._get_quote_balance(user_id, "MN2") < price:
        agent["auto_renew"] = False
        data["agents"][agent_id] = agent
        mkt._write_user_agents(user_id, data)
        return {"success": False, "error": "insufficient_mn2", "needed_mn2": price}

    tmpl = _rental_map(cfg).get(agent.get("rental_id") or "", {})
    days = int(agent.get("rental_days") or tmpl.get("days") or 7)
    if price > 0:
        ex._adjust_quote_balance(user_id, "MN2", -price, "exchange_rental_auto_renew",
                                 {"agent_id": agent_id, "rental_id": agent.get("rental_id")})

    base = datetime.now(timezone.utc)
    exp = agent.get("expires_at")
    if exp:
        try:
            dt = datetime.fromisoformat(str(exp).replace("Z", "+00:00"))
            if dt > base:
                base = dt
        except Exception:
            pass
    agent["expires_at"] = (base + timedelta(days=days)).isoformat().replace("+00:00", "Z")
    agent["auto_renew_count"] = attempts + 1
    agent["reward_claimed"] = False
    agent["last_auto_renew_at"] = _iso()
    data["agents"][agent_id] = agent
    mkt._write_user_agents(user_id, data)
    ex._audit("exchange_rental_auto_renew_charge", user_id=user_id, agent_id=agent_id,
              rental_id=agent.get("rental_id"), amount_usd=price * 0.05)
    return {"success": True, "agent_id": agent_id, "spent_mn2": price, "expires_at": agent["expires_at"],
            "days_extended": days}


def process_auto_renewals(user_id: Optional[str] = None) -> Dict[str, Any]:
    """Scan rentals and renew those with auto_renew enabled (daemon hook)."""
    renewed: List[Dict[str, Any]] = []
    failed: List[Dict[str, Any]] = []

    def _scan(uid: str) -> None:
        data = mkt._read_user_agents(uid)
        for aid, agent in (data.get("agents") or {}).items():
            if not agent.get("rented") or not agent.get("auto_renew"):
                continue
            res = try_auto_renew(uid, aid)
            if res.get("success"):
                renewed.append({"user_id": uid, **res})
            elif res.get("error") not in ("not_due_yet", "not_eligible", "auto_renew_disabled"):
                failed.append({"user_id": uid, "agent_id": aid, "error": res.get("error")})

    if user_id:
        _scan(user_id.strip())
    else:
        udir = mkt._USER_AGENTS_DIR
        if os.path.isdir(udir):
            for name in os.listdir(udir):
                if name.endswith(".json"):
                    _scan(name[:-5])

    return {"success": True, "renewed": len(renewed), "failed": len(failed),
            "renewed_agents": renewed, "failures": failed}
