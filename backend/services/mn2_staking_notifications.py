"""
MN2 staking reward notifications + weekly digest (Top-10 #5).

Opt-in per user. Reward alerts throttle to at most one per 24h unless tier-up or
large-reward threshold. Weekly digest summarizes the last 7 days from reward rows.
"""
from __future__ import annotations

import json
import os
import threading
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional

_LOCK = threading.Lock()
_BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_PREFS_PATH = os.path.join(_BASE, "data", "mn2_staking_notify_prefs.json")
_STATE_PATH = os.path.join(_BASE, "logs", "mn2_staking_notify_state.json")
_REWARDS_FILE = os.path.join(_BASE, "logs", "mn2_staking_rewards.jsonl")

DEFAULT_PREFS = {
    "reward_alerts": False,
    "weekly_digest": False,
    "large_reward_mn2": 1.0,
}


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _load_json(path: str, default: Any) -> Any:
    if not os.path.exists(path):
        return default
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def _save_json(path: str, data: Any) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    os.replace(tmp, path)


def get_prefs(user_id: str) -> Dict[str, Any]:
    uid = (user_id or "").strip()
    all_prefs = _load_json(_PREFS_PATH, {})
    merged = dict(DEFAULT_PREFS)
    if uid and isinstance(all_prefs.get(uid), dict):
        merged.update(all_prefs[uid])
    return merged


def set_prefs(user_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
    uid = (user_id or "").strip()
    if not uid:
        return {"success": False, "error": "user_id required"}
    with _LOCK:
        all_prefs = _load_json(_PREFS_PATH, {})
        cur = dict(DEFAULT_PREFS)
        cur.update(all_prefs.get(uid) or {})
        for k in DEFAULT_PREFS:
            if k in updates:
                cur[k] = updates[k]
        all_prefs[uid] = cur
        _save_json(_PREFS_PATH, all_prefs)
    return {"success": True, "prefs": cur}


def _load_state() -> Dict[str, Any]:
    return _load_json(_STATE_PATH, {})


def _save_state(state: Dict[str, Any]) -> None:
    _save_json(_STATE_PATH, state)


def on_reward(
    user_id: str,
    reward: float,
    *,
    tier_id: str,
    prev_tier_id: str,
    staked: float,
    total_earned: float,
) -> None:
    """Fire an in-app notification when prefs allow (best-effort)."""
    uid = (user_id or "").strip()
    if not uid or reward <= 0:
        return
    prefs = get_prefs(uid)
    if not prefs.get("reward_alerts"):
        return

    tier_up = tier_id != prev_tier_id
    large = reward >= float(prefs.get("large_reward_mn2") or 1.0)
    now = _utcnow()

    with _LOCK:
        state = _load_state()
        user_state = state.setdefault(uid, {})
        last = user_state.get("last_reward_alert")
        if last and not tier_up and not large:
            try:
                last_dt = datetime.fromisoformat(str(last).replace("Z", "+00:00"))
                if (now - last_dt).total_seconds() < 86400:
                    return
            except Exception:
                pass

    if tier_up:
        title = f"Staking tier up: {tier_id}"
        message = (
            f"You reached the {tier_id} longevity tier with {staked:.4f} MN2 staked. "
            f"Total earned: {total_earned:.4f} MN2."
        )
    elif large:
        title = "Large staking reward"
        message = f"+{reward:.6f} MN2 this interval. Total earned: {total_earned:.4f} MN2."
    else:
        title = "Staking reward credited"
        message = f"+{reward:.6f} MN2 added to your balance. Staked: {staked:.4f} MN2."

    try:
        from backend.services.user_engagement import add_notification
        add_notification(uid, title, message, category="staking", metadata={
            "reward_mn2": round(reward, 8),
            "tier_id": tier_id,
            "tier_up": tier_up,
        })
    except Exception:
        return

    with _LOCK:
        state = _load_state()
        user_state = state.setdefault(uid, {})
        user_state["last_reward_alert"] = now.isoformat()
        _save_state(state)


def _week_rows(user_id: str) -> List[Dict[str, Any]]:
    uid = (user_id or "").strip()
    cutoff = _utcnow() - timedelta(days=7)
    rows: List[Dict[str, Any]] = []
    if not os.path.exists(_REWARDS_FILE):
        return rows
    try:
        with open(_REWARDS_FILE, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    row = json.loads(line)
                except Exception:
                    continue
                if (row.get("user_id") or "") != uid:
                    continue
                ts = str(row.get("accrued_at") or "").replace("Z", "+00:00")
                try:
                    if datetime.fromisoformat(ts) < cutoff:
                        continue
                except Exception:
                    continue
                rows.append(row)
    except Exception:
        pass
    return rows


def send_weekly_digest(user_id: str) -> Optional[Dict[str, Any]]:
    """Build and deliver one user's weekly digest if opted in."""
    uid = (user_id or "").strip()
    if not uid:
        return None
    prefs = get_prefs(uid)
    if not prefs.get("weekly_digest"):
        return None

    rows = _week_rows(uid)
    if not rows:
        return {"user_id": uid, "skipped": True, "reason": "no_rewards"}

    total = round(sum(float(r.get("reward_mn2") or 0) for r in rows), 8)
    intervals = len(rows)
    last_staked = float(rows[-1].get("staked") or 0) if rows else 0.0

    title = "Weekly staking digest"
    message = (
        f"Last 7 days: +{total:.6f} MN2 over {intervals} intervals. "
        f"Currently staked ≈ {last_staked:.4f} MN2. Rewards are variable — not guaranteed."
    )
    try:
        from backend.services.user_engagement import add_notification
        notif = add_notification(uid, title, message, category="staking_digest", metadata={
            "total_reward_mn2": total,
            "intervals": intervals,
            "period_days": 7,
        })
        return {"user_id": uid, "sent": True, "notification_id": notif.get("id"), "total_mn2": total}
    except Exception as exc:
        return {"user_id": uid, "sent": False, "error": str(exc)}


def run_weekly_digest(force: bool = False) -> Dict[str, Any]:
    """Ops/cron: send digest to every staker with weekly_digest enabled."""
    try:
        import backend.services.mn2_staking_service as staking
        stakes = staking._load_stakes()  # noqa: SLF001 — ops batch
    except Exception as exc:
        return {"success": False, "error": str(exc)}

    sent, skipped = 0, 0
    results: List[Dict[str, Any]] = []
    for uid, rec in (stakes or {}).items():
        if float((rec or {}).get("staked", 0) or 0) <= 0:
            continue
        r = send_weekly_digest(uid)
        if not r:
            continue
        if r.get("sent"):
            sent += 1
        else:
            skipped += 1
        results.append(r)

    return {"success": True, "sent": sent, "skipped": skipped, "users": len(results), "force": force}
