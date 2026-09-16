"""
Wallet micro-earn — click-to-earn small MN2 amounts with daily caps and cooldowns.

State: data/wallet_micro_earn_state.json
Config: data/wallet_micro_earn_config.json
"""
from __future__ import annotations

import json
import os
import threading
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

_LOCK = threading.RLock()

_BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_CONFIG_PATH = os.path.join(_BASE, "data", "wallet_micro_earn_config.json")
_STATE_PATH = os.path.join(_BASE, "data", "wallet_micro_earn_state.json")


def _iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _today() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _read_json(path: str) -> dict:
    if not os.path.isfile(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _write_json(path: str, data: dict) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    os.replace(tmp, path)


def get_config() -> Dict[str, Any]:
    cfg = _read_json(_CONFIG_PATH)
    if not cfg:
        cfg = {"enabled": False, "events": {}, "game_links": []}
    return cfg


def _load_state() -> dict:
    with _LOCK:
        return _read_json(_STATE_PATH)


def _save_state(data: dict) -> None:
    with _LOCK:
        _write_json(_STATE_PATH, data)


def _user_day_rec(state: dict, user_id: str, day: str) -> dict:
    users = state.setdefault("users", {})
    rec = users.setdefault(user_id, {})
    days = rec.setdefault("days", {})
    return days.setdefault(day, {"total_mn2": 0.0, "total_coins": 0.0, "events": {}})


def _event_rec(day_rec: dict, event_id: str) -> dict:
    events = day_rec.setdefault("events", {})
    return events.setdefault(event_id, {"clicks": 0, "earned_mn2": 0.0, "earned_coins": 0.0})


def _parse_ts(iso: Optional[str]) -> Optional[datetime]:
    if not iso:
        return None
    try:
        s = str(iso).replace("Z", "+00:00")
        return datetime.fromisoformat(s)
    except Exception:
        return None


def _cooldown_remaining(last_at: Optional[str], cooldown_sec: int) -> int:
    if cooldown_sec <= 0:
        return 0
    last = _parse_ts(last_at)
    if not last:
        return 0
    if last.tzinfo is None:
        last = last.replace(tzinfo=timezone.utc)
    elapsed = (datetime.now(timezone.utc) - last).total_seconds()
    return max(0, int(cooldown_sec - elapsed))


def _diminished_amount(base: float, clicks_before: int, factor: float, min_amt: float) -> float:
    if base <= 0:
        return 0.0
    amt = base * (factor ** max(0, clicks_before))
    return max(min_amt, round(amt, 8))


def _event_def(event_id: str, cfg: dict) -> Optional[dict]:
    events = cfg.get("events") if isinstance(cfg.get("events"), dict) else {}
    ev = events.get(event_id)
    return ev if isinstance(ev, dict) else None


def _build_event_status(
    event_id: str,
    ev: dict,
    day_rec: dict,
    cfg: dict,
    global_earned_mn2: float,
) -> dict:
    clicks = int(_event_rec(day_rec, event_id).get("clicks") or 0)
    earned_event = float(_event_rec(day_rec, event_id).get("earned_mn2") or 0)
    last_at = _event_rec(day_rec, event_id).get("last_click_at")
    cooldown_sec = int(ev.get("cooldown_seconds") or 0)
    max_clicks = int(ev.get("max_clicks_per_day") or 0)
    event_cap = float(ev.get("daily_cap_mn2") or 0)
    global_cap = float(cfg.get("global_daily_cap_mn2") or 0.05)
    cooldown_left = _cooldown_remaining(last_at, cooldown_sec)

    blocked_reason = None
    available = True
    if max_clicks > 0 and clicks >= max_clicks:
        available = False
        blocked_reason = "max_clicks"
    elif event_cap > 0 and earned_event >= event_cap - 1e-12:
        available = False
        blocked_reason = "event_cap"
    elif global_cap > 0 and global_earned_mn2 >= global_cap - 1e-12:
        available = False
        blocked_reason = "global_cap"
    elif cooldown_left > 0:
        available = False
        blocked_reason = "cooldown"

    next_amount = _diminished_amount(
        float(ev.get("base_amount") or 0),
        clicks,
        float(cfg.get("diminishing_factor") or 0.85),
        float(cfg.get("min_amount_mn2") or 0.0001),
    )

    return {
        "event_id": event_id,
        "unit_id": ev.get("unit_id"),
        "name": ev.get("name"),
        "description": ev.get("description"),
        "category": ev.get("category"),
        "unit": ev.get("unit", "mn2"),
        "base_amount": float(ev.get("base_amount") or 0),
        "next_amount_mn2": next_amount if available else 0.0,
        "clicks_today": clicks,
        "max_clicks_per_day": max_clicks,
        "earned_today_mn2": round(earned_event, 8),
        "daily_cap_mn2": event_cap,
        "cooldown_seconds": cooldown_sec,
        "cooldown_remaining_sec": cooldown_left,
        "available": available,
        "blocked_reason": blocked_reason,
    }


def get_status(user_id: str) -> Dict[str, Any]:
    """Today's earn progress, caps, and per-event availability."""
    cfg = get_config()
    user_id = (user_id or "").strip() or "default_user"
    guest = user_id in ("", "default_user", "guest")
    day = _today()
    state = _load_state()
    day_rec = _user_day_rec(state, user_id, day) if not guest else {"total_mn2": 0.0, "events": {}}
    earned_today = float(day_rec.get("total_mn2") or 0)
    global_cap = float(cfg.get("global_daily_cap_mn2") or 0.05)

    events_cfg = cfg.get("events") if isinstance(cfg.get("events"), dict) else {}
    events: List[dict] = []
    for event_id, ev in events_cfg.items():
        if isinstance(ev, dict):
            events.append(_build_event_status(event_id, ev, day_rec, cfg, earned_today))

    return {
        "success": True,
        "enabled": bool(cfg.get("enabled", True)),
        "user_id": user_id,
        "guest": guest,
        "day": day,
        "earned_today_mn2": round(earned_today, 8),
        "global_daily_cap_mn2": global_cap,
        "remaining_today_mn2": round(max(0.0, global_cap - earned_today), 8),
        "engagement_disclaimer": cfg.get("engagement_disclaimer"),
        "captcha_hook_enabled": bool(cfg.get("captcha_hook_enabled")),
        "events": events,
        "game_links": cfg.get("game_links") if isinstance(cfg.get("game_links"), list) else [],
        "message": "Sign in to earn micro MN2 via clicks." if guest else None,
    }


def record_click(user_id: str, event_id: str, captcha_token: Optional[str] = None) -> Dict[str, Any]:
    """Record a click event and credit micro MN2 when within caps."""
    from backend.services.mn2_earn_auth import require_earn_user

    ok, uid_or_err = require_earn_user(user_id)
    if not ok:
        return {"success": False, "error": uid_or_err}

    user_id = uid_or_err
    event_id = (event_id or "").strip()
    if not event_id:
        return {"success": False, "error": "event_id_required"}

    cfg = get_config()
    if not cfg.get("enabled", True):
        return {"success": False, "error": "micro_earn_disabled"}

    if cfg.get("captcha_hook_enabled"):
        # Hook for future captcha integration — token optional until wired
        if not captcha_token and cfg.get("captcha_hook_url"):
            return {
                "success": False,
                "error": "captcha_required",
                "captcha_hook_url": cfg.get("captcha_hook_url"),
            }

    ev = _event_def(event_id, cfg)
    if not ev:
        return {"success": False, "error": "unknown_event", "event_id": event_id}

    day = _today()
    state = _load_state()
    day_rec = _user_day_rec(state, user_id, day)
    global_earned = float(day_rec.get("total_mn2") or 0)
    global_cap = float(cfg.get("global_daily_cap_mn2") or 0.05)
    event_rec = _event_rec(day_rec, event_id)
    clicks = int(event_rec.get("clicks") or 0)
    earned_event = float(event_rec.get("earned_mn2") or 0)
    max_clicks = int(ev.get("max_clicks_per_day") or 0)
    event_cap = float(ev.get("daily_cap_mn2") or 0)
    cooldown_sec = int(ev.get("cooldown_seconds") or 0)
    cooldown_left = _cooldown_remaining(event_rec.get("last_click_at"), cooldown_sec)

    if max_clicks > 0 and clicks >= max_clicks:
        return {"success": False, "error": "max_clicks", "event_id": event_id}
    if event_cap > 0 and earned_event >= event_cap - 1e-12:
        return {"success": False, "error": "event_cap", "event_id": event_id}
    if global_cap > 0 and global_earned >= global_cap - 1e-12:
        return {
            "success": False,
            "error": "global_cap",
            "earned_today_mn2": round(global_earned, 8),
            "global_daily_cap_mn2": global_cap,
        }
    if cooldown_left > 0:
        return {
            "success": False,
            "error": "cooldown",
            "cooldown_remaining_sec": cooldown_left,
            "event_id": event_id,
        }

    base = float(ev.get("base_amount") or 0)
    amount = _diminished_amount(
        base,
        clicks,
        float(cfg.get("diminishing_factor") or 0.85),
        float(cfg.get("min_amount_mn2") or 0.0001),
    )
    if amount <= 0:
        return {"success": False, "error": "zero_reward", "event_id": event_id}

    room_event = max(0.0, event_cap - earned_event) if event_cap > 0 else amount
    room_global = max(0.0, global_cap - global_earned) if global_cap > 0 else amount
    amount = round(min(amount, room_event, room_global), 8)
    if amount <= 0:
        return {"success": False, "error": "cap_exhausted", "event_id": event_id}

    reference = f"wallet-earn:{event_id}:{user_id}:{day}:{clicks + 1}"
    from backend.services.game_mn2_rewards import credit_mn2

    credit = credit_mn2(
        user_id,
        amount,
        source="wallet_micro_earn",
        reference=reference,
        metadata={
            "event_id": event_id,
            "unit_id": ev.get("unit_id"),
            "day": day,
            "click_number": clicks + 1,
        },
    )
    if not credit.get("success"):
        return credit
    if credit.get("duplicate"):
        return {"success": True, "duplicate": True, "mn2_awarded": 0.0, "event_id": event_id}

    event_rec["clicks"] = clicks + 1
    event_rec["earned_mn2"] = round(earned_event + amount, 8)
    event_rec["last_click_at"] = _iso()
    day_rec["total_mn2"] = round(global_earned + amount, 8)
    day_rec["events"][event_id] = event_rec
    state["users"][user_id]["days"][day] = day_rec
    state["platform_total_mn2"] = round(float(state.get("platform_total_mn2") or 0) + amount, 8)
    state["platform_events"] = int(state.get("platform_events") or 0) + 1
    _save_state(state)

    return {
        "success": True,
        "event_id": event_id,
        "unit_id": ev.get("unit_id"),
        "mn2_awarded": amount,
        "earned_today_mn2": round(global_earned + amount, 8),
        "global_daily_cap_mn2": global_cap,
        "clicks_today": clicks + 1,
        "cooldown_seconds": cooldown_sec,
    }
