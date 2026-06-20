"""
Copy-trading mirror — followers scale leader agent staking actions.
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone, timedelta
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
    leader_reward: float,
    *,
    interval_id: str = "",
) -> Dict[str, Any]:
    """Credit followers a scaled share of a trader agent's staking reward."""
    reward = float(leader_reward or 0)
    if reward <= 0:
        return {"success": True, "mirrored": 0, "results": []}

    data = _load()
    followers = data.get("followers") or {}
    mirrored: List[Dict[str, Any]] = []
    import backend.services.mn2_staking_service as staking

    for uid, cfg in followers.items():
        if not isinstance(cfg, dict) or not cfg.get("enabled"):
            continue
        if cfg.get("leader_agent_id") != leader_agent_id:
            continue
        scale = float(cfg.get("scale") or 0.25)
        cap = float(cfg.get("max_mn2_per_step") or 0)
        bonus = round(reward * scale, 8)
        if cap > 0:
            bonus = min(bonus, cap)
        if bonus <= 0:
            continue
        try:
            from backend.services.agent_kill_switch import check_action
            halt = check_action("copy_trade", agent_id=leader_agent_id)
            if not halt.get("allowed"):
                mirrored.append({"follower": uid, "skipped": halt.get("reason")})
                continue
        except ImportError:
            pass
        if not staking.has_accepted_terms(uid):
            mirrored.append({"follower": uid, "skipped": "terms_not_accepted"})
            continue
        staking._points().add_points(
            uid,
            "mn2_balance",
            bonus,
            source="copy_trading_reward",
            metadata={
                "interval_id": interval_id,
                "leader_agent_id": leader_agent_id,
                "leader_reward": reward,
                "scale": scale,
            },
        )
        stakes = staking._load_stakes()
        rec = staking._get_record(stakes, uid)
        rec["total_earned"] = round(float(rec.get("total_earned", 0) or 0) + bonus, 8)
        rec["last_accrued_iso"] = _iso()
        stakes[uid] = rec
        staking._save_stakes(stakes)
        staking._ledger_append(
            uid,
            "copy_trading_reward",
            bonus,
            metadata={"leader_agent_id": leader_agent_id, "interval_id": interval_id},
        )
        row = {"follower": uid, "leader_agent_id": leader_agent_id, "reward_mn2": bonus, "scale": scale}
        mirrored.append(row)
        _append({"ts": _iso(), "event": "leader_reward_mirror", **row})
    return {"success": True, "mirrored": len(mirrored), "results": mirrored}


def get_follower(follower_user_id: str) -> Dict[str, Any]:
    uid = str(follower_user_id or "").strip()
    data = _load()
    cfg = (data.get("followers") or {}).get(uid)
    if not isinstance(cfg, dict):
        return {"success": True, "following": False}
    return {"success": True, "following": bool(cfg.get("enabled", True)), "follower": cfg}


def unfollow(follower_user_id: str) -> Dict[str, Any]:
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


def get_premium_status(user_id: str) -> Dict[str, Any]:
    uid = (user_id or "").strip()
    data = _load()
    pu = data.get("premium_users") if isinstance(data.get("premium_users"), dict) else {}
    row = pu.get(uid) or {}
    exp = row.get("expires_at")
    active = False
    if exp:
        try:
            active = datetime.fromisoformat(str(exp).replace("Z", "+00:00")) > datetime.now(timezone.utc)
        except Exception:
            active = False
    return {"active": active, "expires_at": exp if active else None, "source": row.get("source")}


def activate_premium(user_id: str, *, days: int = 30, source: str = "shop") -> Dict[str, Any]:
    uid = (user_id or "").strip()
    if not uid:
        return {"success": False, "error": "user_id required"}
    data = _load()
    premium = data.setdefault("premium_users", {})
    now = datetime.now(timezone.utc)
    current = premium.get(uid) or {}
    start = now
    if current.get("expires_at"):
        try:
            prev = datetime.fromisoformat(str(current["expires_at"]).replace("Z", "+00:00"))
            if prev > now:
                start = prev
        except Exception:
            pass
    expires = (start + timedelta(days=max(1, int(days or 30)))).isoformat().replace("+00:00", "Z")
    premium[uid] = {"expires_at": expires, "source": source, "updated_at": _iso()}
    _save(data)
    return {"success": True, "premium_until": expires, "active": True}
