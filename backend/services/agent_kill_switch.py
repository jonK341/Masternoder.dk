"""
Agent emergency halt matrix — global, per-agent, and per-verb kill switches.

State: data/agent_global_switches.json
"""
from __future__ import annotations

import json
import os
import threading
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

_LOCK = threading.Lock()
_BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_PATH = os.path.join(_BASE, "data", "agent_global_switches.json")

_MONEY_VERBS = frozenset({
    "stake", "unstake", "p2p_create_listing", "p2p_buy", "onramp_order",
    "execute_mn2_purchase", "run_agent", "run_all", "copy_trade",
})


def _iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _default() -> Dict[str, Any]:
    return {
        "global_halt": False,
        "halted_agents": [],
        "halted_verbs": [],
        "reason": "",
        "set_by": "",
        "updated_at": None,
    }


def _load() -> Dict[str, Any]:
    if not os.path.isfile(_PATH):
        return _default()
    try:
        with open(_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        out = _default()
        if isinstance(data, dict):
            out.update(data)
        return out
    except Exception:
        return _default()


def _save(data: Dict[str, Any]) -> None:
    os.makedirs(os.path.dirname(_PATH), exist_ok=True)
    tmp = _PATH + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    os.replace(tmp, _PATH)


def get_status() -> Dict[str, Any]:
    with _LOCK:
        s = _load()
    return {
        "success": True,
        "global_halt": bool(s.get("global_halt")),
        "halted_agents": list(s.get("halted_agents") or []),
        "halted_verbs": list(s.get("halted_verbs") or []),
        "reason": s.get("reason") or "",
        "updated_at": s.get("updated_at"),
    }


def set_switch(
    *,
    global_halt: Optional[bool] = None,
    halted_agents: Optional[List[str]] = None,
    halted_verbs: Optional[List[str]] = None,
    reason: str = "",
    set_by: str = "ops",
) -> Dict[str, Any]:
    with _LOCK:
        s = _load()
        if global_halt is not None:
            s["global_halt"] = bool(global_halt)
        if halted_agents is not None:
            s["halted_agents"] = [str(x).strip() for x in halted_agents if str(x).strip()]
        if halted_verbs is not None:
            s["halted_verbs"] = [str(x).strip().lower() for x in halted_verbs if str(x).strip()]
        s["reason"] = (reason or s.get("reason") or "").strip()
        s["set_by"] = set_by
        s["updated_at"] = _iso()
        _save(s)
    return get_status()


def check_action(verb: str, agent_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Return {allowed: True} or {allowed: False, code, error, ...}.
    """
    v = (verb or "").strip().lower()
    aid = (agent_id or "").strip()
    s = get_status()
    if s.get("global_halt"):
        return {
            "allowed": False,
            "code": "global_halt",
            "error": s.get("reason") or "Agent automation is globally halted.",
        }
    if aid and aid in (s.get("halted_agents") or []):
        return {
            "allowed": False,
            "code": "agent_halted",
            "error": f"Agent '{aid}' is halted.",
            "agent_id": aid,
        }
    halted_verbs = s.get("halted_verbs") or []
    if v in halted_verbs:
        return {
            "allowed": False,
            "code": "verb_halted",
            "error": f"Action '{v}' is halted.",
            "verb": v,
        }
    # run_all is blocked when any money verb is halted
    if v == "run_all" and any(hv in _MONEY_VERBS for hv in halted_verbs):
        return {
            "allowed": False,
            "code": "verb_halted",
            "error": "run_all blocked while money-moving verbs are halted.",
        }
    return {"allowed": True}
