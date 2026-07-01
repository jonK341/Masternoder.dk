"""
Responsible gaming ladder — session loss limits scaled by XP tier.
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_SESSIONS = os.path.join(_ROOT, "logs", "casino_rg_sessions.json")


def _config() -> Dict[str, Any]:
    try:
        from backend.services.casino_service import _load_config
        rg = (_load_config().get("responsible_gaming") or {})
        return rg if isinstance(rg, dict) else {}
    except Exception:
        return {}


def _tier_for_user(user_id: str) -> Dict[str, Any]:
    tiers = _config().get("limits_by_xp") or []
    if not isinstance(tiers, list) or not tiers:
        return {}
    xp = 0.0
    try:
        from backend.services.unified_points_database import unified_points_db
        pts = unified_points_db.get_all_points(str(user_id))
        p = pts.get("points") if isinstance(pts.get("points"), dict) else {}
        systems = pts.get("systems") if isinstance(pts.get("systems"), dict) else {}
        xp = float(p.get("xp_total") or systems.get("xp_total") or 0)
    except Exception:
        pass
    chosen = {}
    for t in sorted(tiers, key=lambda x: int(x.get("min_xp") or 0), reverse=True):
        if xp >= float(t.get("min_xp") or 0):
            chosen = t
            break
    return chosen


def _load_sessions() -> Dict[str, Any]:
    if not os.path.isfile(_SESSIONS):
        return {}
    try:
        with open(_SESSIONS, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _save_sessions(data: Dict[str, Any]) -> None:
    os.makedirs(os.path.dirname(_SESSIONS), exist_ok=True)
    try:
        with open(_SESSIONS, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def _session_key(user_id: str, currency: str) -> str:
    return f"{user_id}:{currency}"


def check_before_bet(user_id: str, bet: float, currency: str) -> Optional[str]:
    cfg = _config()
    if not cfg.get("enabled", True):
        return None
    tier = _tier_for_user(user_id)
    if not tier:
        return None
    window_h = float(cfg.get("session_window_hours") or 24)
    cooldown_m = int(tier.get("cooldown_minutes") or 0)
    cap_key = {
        "coins": "max_loss_coins",
        "mn2": "max_loss_mn2",
        "usd": "max_loss_usd",
    }.get(currency, "max_loss_coins")
    cap = tier.get(cap_key)
    if cap is None:
        return None

    sessions = _load_sessions()
    rec = sessions.get(_session_key(user_id, currency)) or {}
    until = rec.get("cooldown_until")
    if until:
        try:
            end = datetime.fromisoformat(str(until).replace("Z", "+00:00"))
            if datetime.now(timezone.utc) < end:
                return f"Responsible gaming cooldown active — try again after {until}"
        except Exception:
            pass

    started = rec.get("started_at")
    loss = float(rec.get("session_loss") or 0)
    if started:
        try:
            start = datetime.fromisoformat(str(started).replace("Z", "+00:00"))
            if datetime.now(timezone.utc) - start > timedelta(hours=window_h):
                loss = 0.0
        except Exception:
            loss = 0.0
    if loss + float(bet or 0) > float(cap):
        return f"Session loss limit reached ({cap} {currency}) — take a break or earn more XP for higher limits"
    return None


def record_after_bet(user_id: str, net: float, currency: str) -> None:
    cfg = _config()
    if not cfg.get("enabled", True):
        return
    tier = _tier_for_user(user_id)
    if not tier:
        return
    window_h = float(cfg.get("session_window_hours") or 24)
    cooldown_m = int(tier.get("cooldown_minutes") or 60)
    cap_key = {
        "coins": "max_loss_coins",
        "mn2": "max_loss_mn2",
        "usd": "max_loss_usd",
    }.get(currency, "max_loss_coins")
    cap = tier.get(cap_key)
    if cap is None:
        return

    key = _session_key(user_id, currency)
    sessions = _load_sessions()
    rec = sessions.get(key) or {}
    now = datetime.now(timezone.utc)
    started = rec.get("started_at")
    loss = float(rec.get("session_loss") or 0)
    if started:
        try:
            start = datetime.fromisoformat(str(started).replace("Z", "+00:00"))
            if now - start > timedelta(hours=window_h):
                loss = 0.0
                rec = {"started_at": now.isoformat().replace("+00:00", "Z"), "session_loss": 0.0}
        except Exception:
            rec = {"started_at": now.isoformat().replace("+00:00", "Z"), "session_loss": 0.0}
    else:
        rec = {"started_at": now.isoformat().replace("+00:00", "Z"), "session_loss": 0.0}

    if float(net or 0) < 0:
        loss += abs(float(net))
    rec["session_loss"] = round(loss, 8)
    rec["updated_at"] = now.isoformat().replace("+00:00", "Z")
    if loss >= float(cap) and cooldown_m > 0:
        rec["cooldown_until"] = (now + timedelta(minutes=cooldown_m)).isoformat().replace("+00:00", "Z")
    sessions[key] = rec
    _save_sessions(sessions)


def status_for_user(user_id: str, currency: str = "coins") -> Dict[str, Any]:
    """Public RG session snapshot for UI nudges (no bet blocking side effects)."""
    cfg = _config()
    currency = (currency or "coins").lower()
    tier = _tier_for_user(user_id)
    cap_key = {
        "coins": "max_loss_coins",
        "mn2": "max_loss_mn2",
        "usd": "max_loss_usd",
    }.get(currency, "max_loss_coins")
    cap = tier.get(cap_key) if tier else None
    window_h = float(cfg.get("session_window_hours") or 24)

    sessions = _load_sessions()
    rec = sessions.get(_session_key(user_id, currency)) or {}
    now = datetime.now(timezone.utc)
    loss = float(rec.get("session_loss") or 0)
    started = rec.get("started_at")
    session_minutes = 0
    if started:
        try:
            start = datetime.fromisoformat(str(started).replace("Z", "+00:00"))
            elapsed = now - start
            if elapsed <= timedelta(hours=window_h):
                session_minutes = int(elapsed.total_seconds() // 60)
            else:
                loss = 0.0
        except Exception:
            pass

    cooldown_until = rec.get("cooldown_until")
    cooldown_active = False
    if cooldown_until:
        try:
            end = datetime.fromisoformat(str(cooldown_until).replace("Z", "+00:00"))
            cooldown_active = now < end
        except Exception:
            pass

    pct_used = round((loss / float(cap)) * 100, 1) if cap and float(cap) > 0 else 0.0
    nudge = None
    if cooldown_active:
        nudge = "Cooldown active — take a break before your next session."
    elif pct_used >= 90:
        nudge = "You're near your session loss limit — consider a break."
    elif session_minutes >= 120:
        nudge = "Long session detected — entertainment breaks help keep play fun."

    return {
        "success": True,
        "enabled": bool(cfg.get("enabled", True)),
        "currency": currency,
        "session_loss": round(loss, 8 if currency == "mn2" else 2),
        "session_loss_cap": cap,
        "session_loss_pct_used": pct_used,
        "session_minutes": session_minutes,
        "session_window_hours": window_h,
        "cooldown_active": cooldown_active,
        "cooldown_until": cooldown_until if cooldown_active else None,
        "tier_min_xp": tier.get("min_xp") if tier else 0,
        "nudge": nudge,
        "help_url": "/profile",
        "note": "Virtual entertainment only — shop cosmetics never change RTP.",
    }
