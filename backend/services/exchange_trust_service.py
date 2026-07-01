"""Trust system for exchange users, marketplace agents, and platform bots.

Trust score (0–100) + tier (Unverified → Platinum) gates activations and boosts composite
intelligence (trust-adjusted IQ + edge bonus). Per-agent ``activation`` state:
  pending → active | paused | suspended

State: data/exchange_trust/{user}.json (controls) + fields on each owned agent.
Owner policy: data/exchange_trust_policy.json
"""
from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from backend.services import crypto_exchange_service as ex

_CONFIG_PATH = os.path.join(ex._BASE, "data", "exchange_trust_config.json")
_POLICY_PATH = os.path.join(ex._DATA_DIR, "exchange_trust_policy.json")
_STATE_DIR = os.path.join(ex._DATA_DIR, "exchange_trust")


def _iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def load_config() -> Dict[str, Any]:
    cfg = ex._read_json(_CONFIG_PATH, {})
    return cfg if isinstance(cfg, dict) else {}


def _policy() -> Dict[str, Any]:
    p = ex._read_json(_POLICY_PATH, None)
    if not isinstance(p, dict):
        p = {
            "min_user_trust_floor": 0,
            "require_manual_activation": True,
            "suspended_users": [],
            "updated_at": _iso(),
        }
        ex._write_json(_POLICY_PATH, p)
    return p


def _save_policy(p: Dict[str, Any]) -> None:
    p["updated_at"] = _iso()
    ex._write_json(_POLICY_PATH, p)


def _state_path(user_id: str) -> str:
    safe = "".join(c if c.isalnum() or c in "-_" else "_" for c in str(user_id))
    return os.path.join(_STATE_DIR, f"{safe}.json")


def _load_state(user_id: str) -> Dict[str, Any]:
    data = ex._read_json(_state_path(user_id), {})
    if not isinstance(data, dict):
        data = {}
    data.setdefault("activations_granted", {})
    data.setdefault("controls", {"global_auto_run": False, "trust_alerts": True})
    return data


def _save_state(user_id: str, data: Dict[str, Any]) -> None:
    os.makedirs(_STATE_DIR, exist_ok=True)
    ex._write_json(_state_path(user_id), data)


def _tier(score: float, cfg: Dict[str, Any]) -> Dict[str, Any]:
    tiers = sorted((cfg.get("tiers") or []), key=lambda t: int(t.get("min") or 0))
    cur = tiers[0] if tiers else {"name": "Unverified", "icon": "⚪"}
    for t in tiers:
        if score >= float(t.get("min") or 0):
            cur = t
    return {"name": cur.get("name"), "icon": cur.get("icon"), "color": cur.get("color"), "min": cur.get("min")}


def compute_user_trust(user_id: str) -> Dict[str, Any]:
    cfg = load_config()
    if not cfg.get("enabled", True):
        return {"score": 50.0, "tier": _tier(50, cfg), "factors": {}}
    uc = cfg.get("user_trust") or {}
    score = float(uc.get("base_score") or 0)
    factors: Dict[str, float] = {"base": score}
    try:
        from backend.services.exchange_leveling_service import user_progress
        prog = user_progress(user_id)
        lv = float(prog.get("level") or 1)
        ach = float(prog.get("achievements_unlocked") or 0)
        st = prog.get("stats") or {}
        score += lv * float(uc.get("level_weight") or 0)
        factors["level"] = lv * float(uc.get("level_weight") or 0)
        score += ach * float(uc.get("achievement_weight") or 0)
        factors["achievements"] = ach * float(uc.get("achievement_weight") or 0)
        score += float(st.get("total_agent_profit_usd") or 0) * float(uc.get("profit_usd_weight") or 0)
        factors["profit"] = float(st.get("total_agent_profit_usd") or 0) * float(uc.get("profit_usd_weight") or 0)
        score += float(st.get("agents_owned") or 0) * float(uc.get("agent_count_weight") or 0)
        factors["agents"] = float(st.get("agents_owned") or 0) * float(uc.get("agent_count_weight") or 0)
        score += float(st.get("crypto_buys") or 0) * float(uc.get("crypto_buy_weight") or 0)
        factors["crypto_buys"] = float(st.get("crypto_buys") or 0) * float(uc.get("crypto_buy_weight") or 0)
    except Exception:
        pass
    policy = _policy()
    if user_id in (policy.get("suspended_users") or []):
        score = min(score, float(policy.get("min_user_trust_floor") or 0))
    cap = float(uc.get("max_score") or 100)
    score = round(min(cap, max(0.0, score)), 1)
    return {"score": score, "tier": _tier(score, cfg), "factors": factors}


def compute_agent_trust(agent: Dict[str, Any]) -> Dict[str, Any]:
    cfg = load_config()
    ac = cfg.get("agent_trust") or {}
    score = float(ac.get("base_score") or 0)
    profit = float(agent.get("realized_profit_usd") or 0)
    ticks = float(agent.get("trade_count") or agent.get("ticks") or 0)
    hours = float(agent.get("game_time_sec") or 0) / 3600.0
    mastery = float(agent.get("mastery_pct") or 0)
    iq = float(agent.get("intelligence") or 100)
    score += profit * float(ac.get("profit_usd_weight") or 0)
    score += ticks * float(ac.get("tick_weight") or 0)
    score += hours * float(ac.get("game_hour_weight") or 0)
    score += mastery * float(ac.get("mastery_weight") or 0)
    score += iq * float(ac.get("iq_weight") or 0)
    if agent.get("activation") == "suspended":
        score = min(score, 10.0)
    cap = float(ac.get("max_score") or 100)
    score = round(min(cap, max(0.0, score)), 1)
    return {"score": score, "tier": _tier(score, cfg)}


def composite_intelligence(user_trust: float, agent: Dict[str, Any], cfg: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    cfg = cfg or load_config()
    ic = cfg.get("intelligence") or {}
    iq = float(agent.get("intelligence") or 100)
    at = compute_agent_trust(agent)
    tier_bonus = (ic.get("tier_bonus") or {}).get(at["tier"]["name"], 0)
    trust_iq = round(iq + user_trust * float(ic.get("trust_iq_multiplier") or 0.55) + float(tier_bonus), 1)
    edge = round(min(float(ic.get("max_trust_edge_bps") or 12),
                     at["score"] / 10.0 * float(ic.get("trust_edge_bps_per_10") or 0.6)), 3)
    return {"composite_iq": trust_iq, "trust_edge_bps": edge, "agent_trust": at["score"],
            "agent_tier": at["tier"], "base_iq": iq}


def _activation_catalog(cfg: Dict[str, Any]) -> List[Dict[str, Any]]:
    return [a for a in (cfg.get("activations") or []) if isinstance(a, dict) and a.get("id")]


def check_activation(user_id: str, activation_id: str, *, agent: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    cfg = load_config()
    act = next((a for a in _activation_catalog(cfg) if a["id"] == activation_id), None)
    if not act:
        return {"allowed": False, "error": "unknown_activation"}
    ut = compute_user_trust(user_id)
    policy = _policy()
    floor = float(policy.get("min_user_trust_floor") or 0)
    if user_id in (policy.get("suspended_users") or []):
        return {"allowed": False, "error": "user_suspended"}
    if ut["score"] < max(float(act.get("min_user_trust") or 0), floor):
        return {"allowed": False, "error": "insufficient_user_trust",
                "need": max(float(act.get("min_user_trust") or 0), floor), "have": ut["score"]}
    if agent and act.get("min_agent_trust"):
        at = compute_agent_trust(agent)
        if at["score"] < float(act["min_agent_trust"]):
            return {"allowed": False, "error": "insufficient_agent_trust",
                    "need": act["min_agent_trust"], "have": at["score"]}
    if agent:
        act = agent.get("activation") or "pending"
        if act == "pending":
            return {"allowed": False, "error": "agent_pending_activation"}
        if act in ("paused", "suspended"):
            return {"allowed": False, "error": f"agent_{act}"}
    return {"allowed": True, "activation_id": activation_id}


def user_trust_profile(user_id: str) -> Dict[str, Any]:
    user_id = (user_id or "").strip()
    cfg = load_config()
    ut = compute_user_trust(user_id)
    state = _load_state(user_id)
    catalog = []
    for act in _activation_catalog(cfg):
        chk = check_activation(user_id, act["id"])
        catalog.append({**act, "allowed": chk["allowed"], "reason": chk.get("error")})
    return {
        "success": True,
        "user_id": user_id,
        "trust_score": ut["score"],
        "tier": ut["tier"],
        "factors": ut["factors"],
        "controls": state.get("controls") or {},
        "activations": catalog,
        "policy": {"require_manual_activation": _policy().get("require_manual_activation", True)},
    }


def agent_trust_profile(user_id: str, agent: Dict[str, Any], user_trust: Optional[float] = None) -> Dict[str, Any]:
    ut = user_trust if user_trust is not None else compute_user_trust(user_id)["score"]
    at = compute_agent_trust(agent)
    ci = composite_intelligence(ut, agent)
    activation = agent.get("activation") or "pending"
    can_run = check_activation(user_id, "run_bots", agent=agent)["allowed"] and activation == "active"
    if agent.get("super"):
        can_run = can_run and check_activation(user_id, "super_agents", agent=agent)["allowed"]
    return {
        "agent_id": agent.get("agent_id"),
        "trust_score": at["score"],
        "tier": at["tier"],
        "activation": activation,
        "can_run": can_run,
        "composite_iq": ci["composite_iq"],
        "trust_edge_bps": ci["trust_edge_bps"],
    }


def set_user_controls(user_id: str, **controls) -> Dict[str, Any]:
    state = _load_state(user_id)
    c = state.setdefault("controls", {})
    for k in ("global_auto_run", "trust_alerts"):
        if k in controls:
            c[k] = bool(controls[k])
    _save_state(user_id, state)
    ex._audit("trust_controls_updated", user_id=user_id, **c)
    return {"success": True, "controls": c}


def set_agent_activation(user_id: str, agent_id: str, activation: str) -> Dict[str, Any]:
    """activation: pending | active | paused | suspended"""
    activation = (activation or "").strip().lower()
    if activation not in ("pending", "active", "paused", "suspended"):
        return {"success": False, "error": "invalid_activation"}
    from backend.services import agent_marketplace_service as mkt
    data = mkt._read_user_agents(user_id)
    agent = data.get("agents", {}).get(agent_id)
    if not agent:
        return {"success": False, "error": "agent_not_found"}
    if activation == "active":
        probe = {**agent, "activation": "active"}
        chk = check_activation(user_id, "run_bots", agent=probe)
        if not chk["allowed"]:
            return {"success": False, "error": chk.get("error"), "trust_gate": chk}
        if agent.get("super"):
            chk2 = check_activation(user_id, "super_agents", agent=probe)
            if not chk2["allowed"]:
                return {"success": False, "error": chk2.get("error"), "trust_gate": chk2}
    agent["activation"] = activation
    agent["activation_at"] = _iso()
    data["agents"][agent_id] = agent
    mkt._write_user_agents(user_id, data)
    ex._audit("trust_agent_activation", user_id=user_id, agent_id=agent_id, activation=activation)
    return {"success": True, "agent_id": agent_id, "activation": activation}


def owner_set_policy(**fields) -> Dict[str, Any]:
    p = _policy()
    if "min_user_trust_floor" in fields:
        p["min_user_trust_floor"] = float(fields["min_user_trust_floor"])
    if "require_manual_activation" in fields:
        p["require_manual_activation"] = bool(fields["require_manual_activation"])
    if "suspend_user" in fields and fields["suspend_user"]:
        su = p.setdefault("suspended_users", [])
        uid = str(fields["suspend_user"]).strip()
        if uid and uid not in su:
            su.append(uid)
    if "unsuspend_user" in fields and fields["unsuspend_user"]:
        uid = str(fields["unsuspend_user"]).strip()
        p["suspended_users"] = [u for u in (p.get("suspended_users") or []) if u != uid]
    _save_policy(p)
    ex._audit("trust_policy_updated", user_id="owner", **{k: v for k, v in fields.items() if v is not None})
    return {"success": True, "policy": p}


def trust_edge_for_agent(user_id: str, agent: Dict[str, Any]) -> float:
    ut = compute_user_trust(user_id)["score"]
    return composite_intelligence(ut, agent)["trust_edge_bps"]


def enrich_agent_on_purchase(agent: Dict[str, Any]) -> None:
    policy = _policy()
    agent.setdefault("activation", "pending" if policy.get("require_manual_activation", True) else "active")
    agent.setdefault("trust_score", 0.0)
    at = compute_agent_trust(agent)
    agent["trust_score"] = at["score"]


def refresh_agent_trust_fields(user_id: str, agent: Dict[str, Any]) -> Dict[str, Any]:
    prof = agent_trust_profile(user_id, agent)
    agent["trust_score"] = prof["trust_score"]
    agent["composite_iq"] = prof["composite_iq"]
    agent["trust_edge_bps"] = prof["trust_edge_bps"]
    return prof
