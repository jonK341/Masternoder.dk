"""
Aggregator MN2 generation — credit MN2 for monitor/intel engagement (Phase 8 mint path).

Awards are capped per user per UTC day. State in data/aggregator_mn2_awards.json.
"""
from __future__ import annotations

import json
import os
import threading
from datetime import datetime, timezone
from typing import Any, Dict, Optional

_LOCK = threading.RLock()

_BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_AWARDS_FILE = os.path.join(_BASE, "data", "aggregator_mn2_awards.json")
_MN2_CFG = os.path.join(_BASE, "data", "mn2_config.json")

_DEFAULTS = {
    "enabled": True,
    "daily_cap_mn2": 0.25,
    "action_rewards_mn2": {
        "monitor_move": 0.00005,
        "monitor_battle_complete": 0.002,
        "battle_overlay_enter": 0.0003,
        "link_encode": 0.0005,
        "link_decode": 0.0003,
        "intel_loaded": 0.0002,
        "progress_refresh": 0.0001,
        "explorer_chat": 0.0004,
        "interaction": 0.00005,
    },
    "default_reward_mn2": 0.00005,
}


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
    cfg = dict(_DEFAULTS)
    root = _read_json(_MN2_CFG)
    agg = root.get("aggregator") if isinstance(root.get("aggregator"), dict) else {}
    cfg.update(agg)
    cfg["coins_per_mn2"] = float(root.get("coins_per_mn2") or 100)
    return cfg


def _load_awards() -> dict:
    with _LOCK:
        return _read_json(_AWARDS_FILE)


def _save_awards(data: dict) -> None:
    with _LOCK:
        _write_json(_AWARDS_FILE, data)


def _normalize_action(action: str) -> str:
    return (action or "interaction").strip().lower().replace(" ", "_").replace("-", "_")


def _reward_for_action(action: str, cfg: Dict[str, Any]) -> float:
    rewards = cfg.get("action_rewards_mn2") or {}
    if not isinstance(rewards, dict):
        rewards = {}
    key = _normalize_action(action)
    if key in rewards:
        return float(rewards[key] or 0)
    return float(cfg.get("default_reward_mn2") or 0)


def _user_day_total(data: dict, user_id: str, day: str) -> float:
    users = data.get("users") if isinstance(data.get("users"), dict) else {}
    rec = users.get(user_id) if isinstance(users.get(user_id), dict) else {}
    days = rec.get("days") if isinstance(rec.get("days"), dict) else {}
    return float(days.get(day) or 0)


def _credit(user_id: str, amount: float, meta: dict) -> bool:
    if amount <= 0:
        return False
    from backend.services.unified_points_database import unified_points_db
    from backend.services.mn2_ledger import append_entry

    result = unified_points_db.add_points(
        user_id, "mn2_balance", amount, source="aggregator_mn2_earn", metadata=meta,
    )
    if not result.get("success", True):
        return False
    try:
        append_entry(user_id=user_id, entry_type="aggregator_mn2_earn", amount=amount, metadata=meta)
    except Exception:
        pass
    return True


def award_for_action(user_id: str, action: str, meta: Optional[dict] = None) -> Dict[str, Any]:
    """Credit MN2 for an aggregator engagement action (daily-capped)."""
    user_id = str(user_id or "").strip()
    if not user_id:
        return {"success": False, "error": "user_id required", "mn2_awarded": 0.0}

    cfg = get_config()
    if not cfg.get("enabled", True):
        return {"success": True, "skipped": "disabled", "mn2_awarded": 0.0}

    base = _reward_for_action(action, cfg)
    if base <= 0:
        return {"success": True, "skipped": "zero_reward", "mn2_awarded": 0.0}

    day = _today()
    data = _load_awards()
    cap = float(cfg.get("daily_cap_mn2") or 0.25)
    earned_today = _user_day_total(data, user_id, day)
    if earned_today >= cap - 1e-12:
        return {
            "success": True,
            "skipped": "daily_cap",
            "mn2_awarded": 0.0,
            "daily_cap_mn2": cap,
            "earned_today_mn2": round(earned_today, 8),
        }

    amount = round(min(base, cap - earned_today), 8)
    if amount <= 0:
        return {"success": True, "skipped": "cap_exhausted", "mn2_awarded": 0.0}

    full_meta = {"action": _normalize_action(action), "day": day}
    if meta:
        full_meta.update(meta)

    if not _credit(user_id, amount, full_meta):
        return {"success": False, "error": "MN2 credit failed", "mn2_awarded": 0.0}

    users = data.setdefault("users", {})
    rec = users.setdefault(user_id, {"days": {}, "total_mn2": 0.0, "events": 0})
    days = rec.setdefault("days", {})
    days[day] = round(float(days.get(day) or 0) + amount, 8)
    rec["total_mn2"] = round(float(rec.get("total_mn2") or 0) + amount, 8)
    rec["events"] = int(rec.get("events") or 0) + 1
    rec["last_action"] = _normalize_action(action)
    rec["last_at"] = _iso()
    users[user_id] = rec
    data["platform_total_mn2"] = round(float(data.get("platform_total_mn2") or 0) + amount, 8)
    data["platform_events"] = int(data.get("platform_events") or 0) + 1
    _save_awards(data)

    return {
        "success": True,
        "mn2_awarded": amount,
        "action": _normalize_action(action),
        "earned_today_mn2": round(earned_today + amount, 8),
        "daily_cap_mn2": cap,
    }


def get_user_stats(user_id: str) -> Dict[str, Any]:
    """Stats for aggregator HUD — today's earn + lifetime from aggregator play."""
    user_id = str(user_id or "").strip()
    cfg = get_config()
    data = _load_awards()
    day = _today()
    earned_today = _user_day_total(data, user_id, day) if user_id else 0.0
    users = data.get("users") if isinstance(data.get("users"), dict) else {}
    rec = users.get(user_id) if user_id and isinstance(users.get(user_id), dict) else {}
    return {
        "success": True,
        "enabled": bool(cfg.get("enabled", True)),
        "user_id": user_id or None,
        "earned_today_mn2": round(earned_today, 8),
        "lifetime_mn2": round(float(rec.get("total_mn2") or 0), 8),
        "events": int(rec.get("events") or 0),
        "last_action": rec.get("last_action"),
        "daily_cap_mn2": float(cfg.get("daily_cap_mn2") or 0.25),
        "platform_total_mn2": round(float(data.get("platform_total_mn2") or 0), 8),
        "platform_events": int(data.get("platform_events") or 0),
    }


def get_public_stats() -> Dict[str, Any]:
    """Platform-wide aggregator MN2 generation stats (no PII)."""
    cfg = get_config()
    data = _load_awards()
    return {
        "success": True,
        "enabled": bool(cfg.get("enabled", True)),
        "platform_total_mn2": round(float(data.get("platform_total_mn2") or 0), 8),
        "platform_events": int(data.get("platform_events") or 0),
        "daily_cap_mn2": float(cfg.get("daily_cap_mn2") or 0.25),
        "action_rewards_mn2": cfg.get("action_rewards_mn2"),
    }


def process_external_bet(user_id: str, amount: float, meta: Optional[dict] = None) -> Dict[str, Any]:
    """Debit MN2 for an external aggregator/casino bet callback."""
    user_id = str(user_id or "").strip()
    try:
        amount = round(float(amount), 8)
    except (TypeError, ValueError):
        return {"success": False, "error": "amount required"}
    if amount <= 0:
        return {"success": False, "error": "amount must be positive"}
    if not user_id:
        return {"success": False, "error": "user_id required"}

    from backend.services.unified_points_database import unified_points_db
    from backend.services.mn2_ledger import append_entry

    points = unified_points_db.get_all_points(user_id).get("points", {}) or {}
    bal = float(points.get("mn2_balance", 0) or 0)
    if bal < amount:
        return {"success": False, "error": "Insufficient MN2 balance", "mn2_balance": bal}

    meta = dict(meta or {})
    meta["source"] = "aggregator_callback_bet"
    result = unified_points_db.add_points(
        user_id, "mn2_balance", -amount, source="aggregator_callback_bet", metadata=meta,
    )
    if not result.get("success", True):
        return {"success": False, "error": "Debit failed"}
    try:
        append_entry(user_id=user_id, entry_type="aggregator_callback_bet", amount=amount, metadata=meta)
    except Exception:
        pass
    new_bal = unified_points_db.get_all_points(user_id).get("points", {}) or {}
    return {
        "success": True,
        "amount": amount,
        "mn2_balance": float(new_bal.get("mn2_balance", 0) or 0),
    }


def process_external_win(user_id: str, amount: float, meta: Optional[dict] = None) -> Dict[str, Any]:
    """Credit MN2 for an external aggregator/casino win callback (daily-capped)."""
    user_id = str(user_id or "").strip()
    try:
        amount = round(float(amount), 8)
    except (TypeError, ValueError):
        return {"success": False, "error": "amount required"}
    if amount <= 0:
        return {"success": False, "error": "amount must be positive"}
    if not user_id:
        return {"success": False, "error": "user_id required"}

    cfg = get_config()
    if not cfg.get("enabled", True):
        return {"success": False, "error": "Aggregator MN2 disabled"}

    meta = dict(meta or {})
    meta["source"] = "aggregator_callback_win"
    data = _load_awards()
    day = _today()
    cap = float(cfg.get("daily_cap_mn2") or 0.25)
    earned_today = _user_day_total(data, user_id, day)
    room = max(0.0, cap - earned_today)
    credit = round(min(amount, room), 8)
    if credit <= 0:
        return {
            "success": False,
            "error": "Daily MN2 earn cap reached",
            "earned_today_mn2": earned_today,
            "daily_cap_mn2": cap,
        }

    if not _credit(user_id, credit, meta):
        return {"success": False, "error": "Credit failed"}

    users = data.setdefault("users", {})
    rec = users.setdefault(user_id, {"days": {}, "total_mn2": 0, "events": 0})
    days = rec.setdefault("days", {})
    days[day] = round(float(days.get(day) or 0) + credit, 8)
    rec["total_mn2"] = round(float(rec.get("total_mn2") or 0) + credit, 8)
    rec["events"] = int(rec.get("events") or 0) + 1
    rec["last_action"] = "callback_win"
    data["platform_total_mn2"] = round(float(data.get("platform_total_mn2") or 0) + credit, 8)
    data["platform_events"] = int(data.get("platform_events") or 0) + 1
    _save_awards(data)

    return {
        "success": True,
        "mn2_awarded": credit,
        "requested": amount,
        "earned_today_mn2": round(earned_today + credit, 8),
        "daily_cap_mn2": cap,
    }
