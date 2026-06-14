"""
MN2 staking agent personas + autonomous loop (plan sec.19.3).

A persona binds an `agent_id` to a real `user_id` plus a policy (caps, target stake,
allowed actions, auto-compound, rig heartbeat). `run_agent` executes ONE policy step
over the existing atomic staking tools — it adds no new money logic, it just drives
stake/unstake/heartbeat/auto-compound toward the policy within the same guardrails a
user has. Every step is audited and tags the stake record so the monitor can flag and
count agent-managed stake (`agent_staked_mn2`, `agent_actions_24h`).

State files (same data dir as mn2_staking_service):
  agent_staking_agents.json          - persona definitions
  mn2_staking_agent_activity.jsonl   - append-only audit of every step
"""
import os
import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import backend.services.mn2_staking_service as staking

_AGENTS_FILE = "agent_staking_agents.json"
_ACTIVITY_FILE = staking._AGENT_ACTIVITY_FILE  # shared name the monitor reads

_DEFAULT_POLICY = {
    "enabled": True,
    "target_staked": 0.0,          # desired staked amount; rebalance moves toward this
    "max_staked": 0.0,             # hard cap; 0 = no agent cap (still bound by per-user max)
    "keep_balance_min": 0.0,       # never stake below this free balance
    "auto_compound": True,         # restake matured rewards
    "heartbeat": True,             # keep the rig signal alive
    "auto_accept_terms": False,    # if False, agent is blocked until consent recorded
    "allowed_actions": ["accept_terms", "heartbeat", "set_auto_compound", "stake", "unstake"],
    "rebalance_step_max": 0.0,     # max MN2 moved in a single step; 0 = unlimited
}


def _iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _agents_path() -> str:
    return os.path.join(staking._data_dir(), _AGENTS_FILE)


def _load_agents() -> Dict[str, Any]:
    p = _agents_path()
    if not os.path.exists(p):
        return {}
    try:
        with open(p, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _save_agents(d: Dict[str, Any]) -> None:
    p = _agents_path()
    os.makedirs(os.path.dirname(p), exist_ok=True)
    tmp = p + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(d, f, indent=2)
    os.replace(tmp, p)


def _policy(agent: Dict[str, Any]) -> Dict[str, Any]:
    pol = dict(_DEFAULT_POLICY)
    pol.update(agent.get("policy") or {})
    return pol


def _audit(agent_id: str, user_id: str, actions: List[Dict[str, Any]]) -> None:
    p = os.path.join(staking._data_dir(), _ACTIVITY_FILE)
    try:
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "a", encoding="utf-8") as f:
            f.write(json.dumps({"ts": _iso(), "agent_id": agent_id, "user_id": user_id,
                                "actions": actions}) + "\n")
    except Exception:
        pass


def _tag_managed(user_id: str, agent_id: str) -> None:
    """Mark the user's stake record as agent-managed so the monitor can flag/count it."""
    try:
        stakes = staking._load_stakes()
        rec = stakes.get(user_id)
        if isinstance(rec, dict):
            rec["managed_by_agent"] = agent_id
            stakes[user_id] = rec
            staking._save_stakes(stakes)
    except Exception:
        pass


def list_agents() -> Dict[str, Any]:
    agents = _load_agents()
    out = []
    for aid, a in agents.items():
        pol = _policy(a)
        out.append({
            "agent_id": aid,
            "user_id": a.get("user_id"),
            "enabled": bool(pol.get("enabled", True)),
            "target_staked": pol.get("target_staked"),
            "max_staked": pol.get("max_staked"),
            "auto_compound": pol.get("auto_compound"),
            "heartbeat": pol.get("heartbeat"),
            "allowed_actions": pol.get("allowed_actions"),
        })
    return {"success": True, "agents": out, "count": len(out),
            "automation_enabled": bool(staking.get_config().get("agent", {}).get("automation_enabled", True))}


def upsert_agent(agent_id: str, user_id: str, policy: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    agent_id = str(agent_id or "").strip()
    user_id = str(user_id or "").strip()
    if not agent_id or not user_id:
        return {"success": False, "error": "agent_id and user_id required"}
    agents = _load_agents()
    rec = agents.get(agent_id) or {}
    rec["user_id"] = user_id
    pol = dict(rec.get("policy") or {})
    if isinstance(policy, dict):
        pol.update(policy)
    rec["policy"] = pol
    rec["updated_at"] = _iso()
    agents[agent_id] = rec
    _save_agents(agents)
    return {"success": True, "agent_id": agent_id, "user_id": user_id, "policy": _policy(rec)}


def run_agent(agent_id: str, dry_run: bool = False) -> Dict[str, Any]:
    """Execute one policy step for a persona. Returns the actions taken (or planned, if dry_run)."""
    agent_id = str(agent_id or "").strip()
    try:
        from backend.services.agent_kill_switch import check_action
        halt = check_action("run_agent", agent_id=agent_id)
        if not halt.get("allowed"):
            return {"success": False, **halt}
    except ImportError:
        pass
    if not bool(staking.get_config().get("agent", {}).get("automation_enabled", True)):
        return {"success": False, "error": "agent automation disabled by ops kill switch", "code": "automation_disabled"}
    agents = _load_agents()
    agent = agents.get(agent_id)
    if not agent:
        return {"success": False, "error": f"unknown agent '{agent_id}'", "code": "unknown_agent"}
    user_id = str(agent.get("user_id") or "").strip()
    pol = _policy(agent)
    if not pol.get("enabled", True):
        return {"success": False, "error": "agent disabled", "code": "disabled", "agent_id": agent_id}

    allowed = set(pol.get("allowed_actions") or [])
    actions: List[Dict[str, Any]] = []

    def _do(name: str, fn, amount: Optional[float] = None):
        if name not in allowed:
            actions.append({"action": name, "skipped": "not_allowed"})
            return None
        if dry_run:
            actions.append({"action": name, "planned": True, "amount": amount})
            return None
        res = fn()
        act: Dict[str, Any] = {"action": name, "result": res}
        if amount is not None:
            act["amount"] = amount
        actions.append(act)
        return res

    # 1. Consent gate (sec.19.4) — required before any stake.
    if not staking.has_accepted_terms(user_id):
        if pol.get("auto_accept_terms") and "accept_terms" in allowed:
            _do("accept_terms", lambda: staking.accept_terms(user_id))
        else:
            _audit(agent_id, user_id, [{"action": "blocked", "reason": "consent_required"}])
            return {"success": False, "error": "consent_required", "code": "consent_required",
                    "agent_id": agent_id, "user_id": user_id}

    # 2. Keep the rig heartbeat alive.
    if pol.get("heartbeat"):
        _do("heartbeat", lambda: staking.submit_work_proof(user_id))

    # 3. Align auto-compound flag.
    cur = staking.get_stake(user_id)
    if bool(cur.get("auto_compound")) != bool(pol.get("auto_compound")):
        _do("set_auto_compound", lambda: staking.set_auto_compound(user_id, bool(pol.get("auto_compound"))))

    # 4. Rebalance toward target within caps.
    bal = float(cur.get("mn2_balance", 0) or 0)
    staked = float(cur.get("staked", 0) or 0)
    target = float(pol.get("target_staked") or 0)
    max_staked = float(pol.get("max_staked") or 0)
    keep_min = float(pol.get("keep_balance_min") or 0)
    step_max = float(pol.get("rebalance_step_max") or 0)

    if max_staked > 0 and staked > max_staked + 1e-9:
        amt = round(staked - max_staked, 8)
        if step_max > 0:
            amt = min(amt, step_max)
        _do("unstake", lambda a=amt: staking.unstake(user_id, a), amount=amt)
    elif target > 0 and staked < target - 1e-9:
        want = target - staked
        free = max(0.0, bal - keep_min)
        amt = round(min(want, free), 8)
        if max_staked > 0:
            amt = min(amt, round(max(0.0, max_staked - staked), 8))
        if step_max > 0:
            amt = min(amt, step_max)
        amt = round(amt, 8)
        if amt > 0:
            r = _do("stake", lambda a=amt: staking.stake(user_id, a), amount=amt)
            if r and r.get("success") and not dry_run:
                _tag_managed(user_id, agent_id)
        else:
            actions.append({"action": "stake", "skipped": "insufficient_free_balance",
                            "free_balance": round(free, 8)})

    if not dry_run:
        agent["last_run_at"] = _iso()
        agents[agent_id] = agent
        _save_agents(agents)
        _audit(agent_id, user_id, actions)
        try:
            from backend.services.mn2_copy_trading import mirror_agent_run
            mirror_agent_run(agent_id, user_id, actions)
        except ImportError:
            pass

    after = staking.get_stake(user_id)
    return {"success": True, "agent_id": agent_id, "user_id": user_id, "dry_run": dry_run,
            "actions": actions,
            "state": {"staked": after.get("staked"), "mn2_balance": after.get("mn2_balance"),
                      "auto_compound": after.get("auto_compound"), "terms_accepted": after.get("terms_accepted")}}


def run_all(dry_run: bool = False) -> Dict[str, Any]:
    try:
        from backend.services.agent_kill_switch import check_action
        halt = check_action("run_all")
        if not halt.get("allowed"):
            return {"success": False, **halt}
    except ImportError:
        pass
    agents = _load_agents()
    results = []
    for aid, a in agents.items():
        if not _policy(a).get("enabled", True):
            continue
        results.append(run_agent(aid, dry_run=dry_run))
    return {"success": True, "ran": len(results), "results": results}


def stake_for_agent(agent_id: str, user_id: str, amount: float) -> Dict[str, Any]:
    """Stake MN2 from the user's wallet and mark the position as agent-managed."""
    from backend.services import mn2_staking_service as staking

    agent_id = str(agent_id or "").strip()
    user_id = str(user_id or "").strip()
    if not agent_id or not user_id:
        return {"success": False, "error": "agent_id and user_id required"}
    res = staking.stake(user_id, amount)
    if not res.get("success"):
        return res
    upsert_agent(agent_id, user_id, policy={"enabled": True})
    _tag_managed(user_id, agent_id)
    return {
        "success": True,
        "agent_id": agent_id,
        "user_id": user_id,
        "amount": amount,
        "stake": res,
    }


def disable_agent(agent_id: str, user_id: str) -> Dict[str, Any]:
    """Disable a staking persona without unstaking (stops autonomous rebalance)."""
    agent_id = str(agent_id or "").strip()
    user_id = str(user_id or "").strip()
    if not agent_id or not user_id:
        return {"success": False, "error": "agent_id and user_id required"}
    agents = _load_agents()
    agent = agents.get(agent_id)
    if not agent or str(agent.get("user_id") or "") != user_id:
        return {"success": False, "error": "agent persona not found for user"}
    pol = dict(agent.get("policy") or {})
    pol["enabled"] = False
    agent["policy"] = pol
    agent["updated_at"] = _iso()
    agents[agent_id] = agent
    _save_agents(agents)
    return {"success": True, "agent_id": agent_id, "enabled": False}


def unstake_for_agent(agent_id: str, user_id: str, amount: Optional[float] = None) -> Dict[str, Any]:
    """Unstake MN2 from agent-managed position back to liquid wallet."""
    from backend.services import mn2_staking_service as staking

    agent_id = str(agent_id or "").strip()
    user_id = str(user_id or "").strip()
    if not agent_id or not user_id:
        return {"success": False, "error": "agent_id and user_id required"}
    agents = _load_agents()
    agent = agents.get(agent_id)
    if not agent or str(agent.get("user_id") or "") != user_id:
        return {"success": False, "error": "agent persona not found for user"}
    cur = staking.get_stake(user_id)
    staked = float(cur.get("staked") or 0)
    if staked <= 0:
        return {"success": False, "error": "nothing staked", "staked": staked}
    amt = float(amount) if amount is not None else staked
    if amt <= 0 or amt > staked + 1e-9:
        return {"success": False, "error": f"invalid unstake amount (staked {staked})", "staked": staked}
    res = staking.unstake(user_id, amt)
    if not res.get("success"):
        return res
    # Any unstake disables autonomous agent policy until re-enabled (partial or full).
    pol = dict(agent.get("policy") or {})
    pol["enabled"] = False
    agent["policy"] = pol
    agent["updated_at"] = _iso()
    agents[agent_id] = agent
    _save_agents(agents)
    after = staking.get_stake(user_id)
    if float(after.get("staked") or 0) <= 1e-9:
        try:
            stakes = staking._load_stakes()
            rec = stakes.get(user_id)
            if isinstance(rec, dict) and rec.get("managed_by_agent") == agent_id:
                rec.pop("managed_by_agent", None)
                stakes[user_id] = rec
                staking._save_stakes(stakes)
        except Exception:
            pass
    return {
        "success": True,
        "agent_id": agent_id,
        "user_id": user_id,
        "amount": amt,
        "unstake": res,
    }
