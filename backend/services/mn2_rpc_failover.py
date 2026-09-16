"""
MN2 RPC daemon failover / hot standby (Top-10 #9).

Single-active lock: at most one RPC endpoint is used for all wallet operations at a time.
When the primary daemon is unreachable for `fail_threshold` consecutive checks and a
configured standby responds, the app auto-promotes to standby (logged + ops alert).

Configure standby URL in data/mn2_rpc_failover.json or MN2_RPC_STANDBY_URL (.env).
Optional MN2_RPC_STANDBY_USER / MN2_RPC_STANDBY_PASSWORD (default: same as primary).
"""
from __future__ import annotations

import json
import os
import threading
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, Optional, Tuple

_LOCK = threading.Lock()
_BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_CONFIG_PATH = os.path.join(_BASE, "data", "mn2_rpc_failover.json")
_STATE_PATH = os.path.join(_BASE, "data", "mn2_rpc_failover_state.json")
_LOG_PATH = os.path.join(_BASE, "logs", "mn2_rpc_failover.jsonl")

DEFAULT_CONFIG: Dict[str, Any] = {
    "enabled": False,
    "fail_threshold": 3,
    "failback_stable_minutes": 30,
    "allow_auto_failback": False,
    "block_height_tolerance": 2,
}


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _iso() -> str:
    return _utcnow().isoformat()


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


def _log_event(event: str, payload: Dict[str, Any]) -> None:
    try:
        os.makedirs(os.path.dirname(_LOG_PATH), exist_ok=True)
        with open(_LOG_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps({"ts": _iso(), "event": event, **payload}) + "\n")
    except Exception:
        pass


def get_config() -> Dict[str, Any]:
    raw = _load_json(_CONFIG_PATH, {})
    cfg = dict(DEFAULT_CONFIG)
    if isinstance(raw, dict):
        cfg.update({k: raw[k] for k in DEFAULT_CONFIG if k in raw})
        cfg["standby"] = raw.get("standby") if isinstance(raw.get("standby"), dict) else {}
        cfg["primary"] = raw.get("primary") if isinstance(raw.get("primary"), dict) else {"label": "primary"}
    return cfg


def _primary_credentials() -> Tuple[str, str, str]:
    url = (os.environ.get("MN2_RPC_URL") or "").strip() or "http://127.0.0.1:9332"
    user = (os.environ.get("MN2_RPC_USER") or "").strip()
    password = (os.environ.get("MN2_RPC_PASSWORD") or "").strip()
    return url, user, password


def _standby_credentials(cfg: Dict[str, Any]) -> Optional[Tuple[str, str, str]]:
    standby = cfg.get("standby") or {}
    url = (os.environ.get("MN2_RPC_STANDBY_URL") or standby.get("url") or "").strip()
    if not url:
        return None
    user = (os.environ.get("MN2_RPC_STANDBY_USER") or os.environ.get("MN2_RPC_USER") or "").strip()
    password = (os.environ.get("MN2_RPC_STANDBY_PASSWORD") or os.environ.get("MN2_RPC_PASSWORD") or "").strip()
    return url, user, password


def _default_state() -> Dict[str, Any]:
    return {
        "active": "primary",
        "primary_fail_streak": 0,
        "standby_fail_streak": 0,
        "last_primary_check": None,
        "last_standby_check": None,
        "last_primary_ok_at": None,
        "last_standby_ok_at": None,
        "primary_block_height": None,
        "standby_block_height": None,
        "promoted_at": None,
        "promote_reason": None,
    }


def get_state() -> Dict[str, Any]:
    st = _load_json(_STATE_PATH, {})
    out = _default_state()
    if isinstance(st, dict):
        out.update(st)
    return out


def _save_state(state: Dict[str, Any]) -> None:
    _save_json(_STATE_PATH, state)


def _probe(url: str, user: str, password: str) -> Dict[str, Any]:
    from backend.services.mn2_rpc_client import probe_endpoint
    return probe_endpoint(url, user, password)


def is_failover_configured() -> bool:
    cfg = get_config()
    if not cfg.get("enabled"):
        return False
    return _standby_credentials(cfg) is not None


def resolve_active_endpoint() -> Optional[Dict[str, str]]:
    """Return {url, user, password, node} when failover is enabled; else None (use env default)."""
    if not is_failover_configured():
        return None
    cfg = get_config()
    state = get_state()
    if state.get("active") == "standby":
        url, user, password = _standby_credentials(cfg)  # type: ignore[misc]
        label = (cfg.get("standby") or {}).get("label") or "standby"
    else:
        url, user, password = _primary_credentials()
        label = (cfg.get("primary") or {}).get("label") or "primary"
    return {"url": url, "user": user, "password": password, "node": label}


def _alert(message: str, metadata: Dict[str, Any]) -> None:
    _log_event("alert", {"message": message, **metadata})
    admin = (os.environ.get("MN2_ALERT_USER_ID") or "").strip()
    if admin:
        try:
            from backend.services.user_engagement import add_notification
            add_notification(admin, "MN2 RPC failover", message, category="mn2_alert", metadata=metadata)
        except Exception:
            pass


def _switch_active(state: Dict[str, Any], target: str, reason: str) -> None:
    prev = state.get("active")
    if prev == target:
        return
    state["active"] = target
    state["promoted_at"] = _iso()
    state["promote_reason"] = reason
    if target == "standby":
        state["primary_fail_streak"] = 0
    else:
        state["standby_fail_streak"] = 0
    _log_event("switch", {"from": prev, "to": target, "reason": reason})
    _alert(
        f"MN2 RPC active node switched {prev} → {target}: {reason}",
        {"from": prev, "to": target, "reason": reason},
    )


def run_check(force: bool = False) -> Dict[str, Any]:
    """Probe primary + standby; auto-promote on sustained primary failure."""
    cfg = get_config()
    if not cfg.get("enabled"):
        return {"success": True, "enabled": False, "message": "failover disabled in config"}

    standby_creds = _standby_credentials(cfg)
    if not standby_creds:
        return {"success": True, "enabled": True, "configured": False, "message": "no standby URL"}

    with _LOCK:
        state = get_state()
        p_url, p_user, p_pass = _primary_credentials()
        s_url, s_user, s_pass = standby_creds

        p_probe = _probe(p_url, p_user, p_pass)
        s_probe = _probe(s_url, s_user, s_pass)
        now = _iso()

        state["last_primary_check"] = now
        state["last_standby_check"] = now

        if p_probe.get("status") == "healthy":
            state["primary_fail_streak"] = 0
            state["last_primary_ok_at"] = now
            state["primary_block_height"] = p_probe.get("block_height")
        else:
            state["primary_fail_streak"] = int(state.get("primary_fail_streak") or 0) + 1

        if s_probe.get("status") == "healthy":
            state["standby_fail_streak"] = 0
            state["last_standby_ok_at"] = now
            state["standby_block_height"] = s_probe.get("block_height")
        else:
            state["standby_fail_streak"] = int(state.get("standby_fail_streak") or 0) + 1

        threshold = int(cfg.get("fail_threshold") or 3)
        tol = int(cfg.get("block_height_tolerance") or 2)
        active = state.get("active") or "primary"

        # Auto-promote: primary down, standby up, standby not stale
        if active == "primary" and state["primary_fail_streak"] >= threshold and s_probe.get("status") == "healthy":
            p_h = p_probe.get("block_height")
            s_h = s_probe.get("block_height")
            stale = False
            if p_h is not None and s_h is not None:
                try:
                    stale = int(s_h) < int(p_h) - tol
                except (TypeError, ValueError):
                    stale = False
            if not stale:
                _switch_active(state, "standby", f"primary failed {state['primary_fail_streak']} checks")

        # Optional auto-failback when primary stable again
        if (
            active == "standby"
            and cfg.get("allow_auto_failback")
            and p_probe.get("status") == "healthy"
        ):
            stable_min = int(cfg.get("failback_stable_minutes") or 30)
            last_ok = state.get("last_primary_ok_at")
            if last_ok:
                try:
                    ok_at = datetime.fromisoformat(str(last_ok).replace("Z", "+00:00"))
                    if (_utcnow() - ok_at).total_seconds() >= stable_min * 60:
                        _switch_active(state, "primary", f"primary stable ≥{stable_min}m")
                except Exception:
                    pass

        _save_state(state)

    return {
        "success": True,
        "enabled": True,
        "configured": True,
        "active": state.get("active"),
        "primary": p_probe,
        "standby": s_probe,
        "primary_fail_streak": state.get("primary_fail_streak"),
        "standby_fail_streak": state.get("standby_fail_streak"),
        "promoted_at": state.get("promoted_at"),
        "promote_reason": state.get("promote_reason"),
    }


def force_promote_standby() -> Dict[str, Any]:
    cfg = get_config()
    creds = _standby_credentials(cfg)
    if not creds:
        return {"success": False, "error": "standby not configured"}
    probe = _probe(*creds)
    if probe.get("status") != "healthy":
        return {"success": False, "error": "standby unreachable", "probe": probe}
    with _LOCK:
        state = get_state()
        _switch_active(state, "standby", "manual ops promote")
        _save_state(state)
    return {"success": True, "active": "standby", "probe": probe}


def force_failback_primary() -> Dict[str, Any]:
    url, user, password = _primary_credentials()
    probe = _probe(url, user, password)
    if probe.get("status") != "healthy":
        return {"success": False, "error": "primary unreachable", "probe": probe}
    with _LOCK:
        state = get_state()
        _switch_active(state, "primary", "manual ops failback")
        _save_state(state)
    return {"success": True, "active": "primary", "probe": probe}


def status_summary() -> Dict[str, Any]:
    cfg = get_config()
    state = get_state()
    p_url, _, _ = _primary_credentials()
    s_creds = _standby_credentials(cfg)
    return {
        "enabled": bool(cfg.get("enabled")),
        "configured": s_creds is not None,
        "active": state.get("active") or "primary",
        "primary_url": p_url,
        "standby_url": s_creds[0] if s_creds else None,
        "primary_fail_streak": state.get("primary_fail_streak"),
        "standby_fail_streak": state.get("standby_fail_streak"),
        "promoted_at": state.get("promoted_at"),
        "promote_reason": state.get("promote_reason"),
        "primary_block_height": state.get("primary_block_height"),
        "standby_block_height": state.get("standby_block_height"),
    }
