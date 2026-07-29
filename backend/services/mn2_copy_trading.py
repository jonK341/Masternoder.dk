"""
Copy-trading mirror — followers scale leader agent staking actions.
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

_BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_FOLLOWS = os.path.join(_BASE, "data", "mn2_copy_trading.json")
_LOG = os.path.join(_BASE, "logs", "mn2_copy_trading.jsonl")


def _iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _load() -> Dict[str, Any]:
    if not os.path.isfile(_FOLLOWS):
        return {"followers": {}}
    try:
        with open(_FOLLOWS, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {"followers": {}}
    except Exception:
        return {"followers": {}}


def _save(data: Dict[str, Any]) -> None:
    os.makedirs(os.path.dirname(_FOLLOWS), exist_ok=True)
    tmp = _FOLLOWS + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    os.replace(tmp, _FOLLOWS)


def _append(row: Dict[str, Any]) -> None:
    os.makedirs(os.path.dirname(_LOG), exist_ok=True)
    try:
        with open(_LOG, "a", encoding="utf-8") as f:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
    except Exception:
        pass


def list_followers(leader_agent_id: Optional[str] = None) -> Dict[str, Any]:
    data = _load()
    followers = data.get("followers") or {}
    if leader_agent_id:
        out = {k: v for k, v in followers.items() if (v or {}).get("leader_agent_id") == leader_agent_id}
        return {"success": True, "followers": out, "count": len(out)}
    return {"success": True, "followers": followers, "count": len(followers)}


def upsert_follower(
    follower_user_id: str,
    leader_agent_id: str,
    *,
    scale: float = 0.25,
    max_mn2_per_step: float = 1.0,
    enabled: bool = True,
) -> Dict[str, Any]:
    uid = str(follower_user_id or "").strip()
    lid = str(leader_agent_id or "").strip()
    if not uid or not lid:
        return {"success": False, "error": "follower_user_id and leader_agent_id required"}
    data = _load()
    followers = data.setdefault("followers", {})
    followers[uid] = {
        "follower_user_id": uid,
        "leader_agent_id": lid,
        "scale": max(0.01, min(float(scale or 0.25), 1.0)),
        "max_mn2_per_step": max(0.0, float(max_mn2_per_step or 0)),
        "enabled": bool(enabled),
        "updated_at": _iso(),
    }
    _save(data)
    return {"success": True, "follower": followers[uid]}


def get_follower(follower_user_id: str) -> Dict[str, Any]:
    """Return follow state for a user (test + API helper)."""
    uid = str(follower_user_id or "").strip()
    if not uid:
        return {"success": False, "error": "follower_user_id required"}
    data = _load()
    followers = data.get("followers") or {}
    cfg = followers.get(uid)
    if not isinstance(cfg, dict):
        return {"success": True, "following": False, "follower_user_id": uid}
    return {
        "success": True,
        "following": bool(cfg.get("enabled")),
        "follower": cfg,
        "follower_user_id": uid,
    }


def unfollow(follower_user_id: str) -> Dict[str, Any]:
    """Alias for remove_follower (API naming)."""
    return remove_follower(follower_user_id)


def remove_follower(follower_user_id: str) -> Dict[str, Any]:
    """Disable copy-trading for a follower."""
    uid = str(follower_user_id or "").strip()
    if not uid:
        return {"success": False, "error": "follower_user_id required"}
    data = _load()
    followers = data.get("followers") or {}
    if uid not in followers:
        return {"success": True, "removed": False}
    del followers[uid]
    data["followers"] = followers
    _save(data)
    return {"success": True, "removed": True}


def mirror_agent_run(leader_agent_id: str, leader_user_id: str, actions: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Mirror stake/unstake steps from a leader agent run onto followers."""
    data = _load()
    followers = data.get("followers") or {}
    mirrored: List[Dict[str, Any]] = []
    stake_actions = [a for a in actions if a.get("action") in ("stake", "unstake") and not a.get("skipped")]
    if not stake_actions:
        return {"success": True, "mirrored": 0, "results": []}

    import backend.services.mn2_staking_service as staking

    for uid, cfg in followers.items():
        if not isinstance(cfg, dict) or not cfg.get("enabled"):
            continue
        if cfg.get("leader_agent_id") != leader_agent_id:
            continue
        scale = float(cfg.get("scale") or 0.25)
        cap = float(cfg.get("max_mn2_per_step") or 0)
        for act in stake_actions:
            amt = float(act.get("amount") or 0)
            if amt <= 0:
                res = act.get("result") or {}
                amt = float(res.get("amount") or 0)
            if amt <= 0:
                continue
            scaled = round(amt * scale, 8)
            if cap > 0:
                scaled = min(scaled, cap)
            if scaled <= 0:
                continue
            try:
                from backend.services.agent_kill_switch import check_action
                halt = check_action("copy_trade", agent_id=leader_agent_id)
                if not halt.get("allowed"):
                    mirrored.append({"follower": uid, "skipped": halt.get("reason")})
                    continue
            except ImportError:
                pass
            if act.get("action") == "stake":
                out = staking.stake(uid, scaled)
            else:
                out = staking.unstake(uid, scaled)
            row = {"follower": uid, "action": act.get("action"), "amount": scaled, "result": out}
            mirrored.append(row)
            _append({"ts": _iso(), "leader_agent_id": leader_agent_id, **row})
    return {"success": True, "mirrored": len(mirrored), "results": mirrored}


def mirror_leader_reward(
    leader_agent_id: str,
    reward_mn2: float,
    *,
    interval_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Credit scaled staking rewards to copy-trading followers of a trader agent."""
    lid = str(leader_agent_id or "").strip()
    reward = float(reward_mn2 or 0)
    if not lid or reward <= 0:
        return {"success": True, "mirrored": 0, "results": []}

    import backend.services.mn2_staking_service as staking

    data = _load()
    followers = data.get("followers") or {}
    mirrored: List[Dict[str, Any]] = []

    for uid, cfg in followers.items():
        if not isinstance(cfg, dict) or not cfg.get("enabled"):
            continue
        if cfg.get("leader_agent_id") != lid:
            continue
        scale = float(cfg.get("scale") or 0.25)
        cap = float(cfg.get("max_mn2_per_step") or 0)
        share = round(reward * scale, 8)
        if cap > 0:
            share = min(share, cap)
        if share <= 0:
            continue
        staking.accept_terms(uid)
        staking._points().add_points(
            uid, "mn2_balance", share,
            source="copy_trade_reward",
            metadata={"leader_agent_id": lid, "interval_id": interval_id},
        )
        stakes = staking._load_stakes()
        rec = staking._get_record(stakes, uid)
        rec["total_earned"] = round(float(rec.get("total_earned", 0) or 0) + share, 8)
        stakes[uid] = rec
        staking._save_stakes(stakes)
        row = {"follower": uid, "share_mn2": share, "leader_agent_id": lid}
        mirrored.append(row)
        _append({"ts": _iso(), "type": "mirror_leader_reward", **row, "interval_id": interval_id})

    return {"success": True, "mirrored": len(mirrored), "results": mirrored}
