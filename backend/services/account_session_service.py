"""
Central account session/device registry.

This is intentionally file-backed so it works before a formal auth/session DB exists.
It tracks sanitized device entries and lets account UI revoke non-current devices.
"""
import hashlib
import json
import os
from datetime import datetime, timezone
from typing import Any, Dict, List


BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SESSIONS_PATH = os.path.join(BASE_DIR, "data", "account_sessions.json")


def _load() -> Dict[str, Any]:
    if not os.path.exists(SESSIONS_PATH):
        return {"users": {}}
    try:
        with open(SESSIONS_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {"users": {}}
    except Exception:
        return {"users": {}}


def _save(data: Dict[str, Any]) -> None:
    os.makedirs(os.path.dirname(SESSIONS_PATH), exist_ok=True)
    with open(SESSIONS_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def current_session_id(user_id: str, user_agent: str = "", remote_addr: str = "") -> str:
    ip_hash = hashlib.sha256((remote_addr or "").encode("utf-8")).hexdigest()[:10] if remote_addr else ""
    device_hash = hashlib.sha256(f"{user_id}|{user_agent}|{ip_hash}".encode("utf-8")).hexdigest()[:12]
    return f"device-{device_hash}"


def build_current_session(user_id: str, resolution_source: str, user_agent: str = "", remote_addr: str = "") -> Dict[str, Any]:
    ip_hash = hashlib.sha256((remote_addr or "").encode("utf-8")).hexdigest()[:10] if remote_addr else ""
    return {
        "id": current_session_id(user_id, user_agent, remote_addr),
        "current": True,
        "revoked": False,
        "resolution_source": resolution_source,
        "device": (user_agent or "")[:90],
        "ip_hash": ip_hash,
        "last_seen_at": datetime.now(timezone.utc).isoformat(),
    }


def record_current_session(user_id: str, resolution_source: str, user_agent: str = "", remote_addr: str = "") -> List[Dict[str, Any]]:
    data = _load()
    users = data.setdefault("users", {})
    sessions = users.get(user_id)
    if not isinstance(sessions, list):
        sessions = []

    current = build_current_session(user_id, resolution_source, user_agent, remote_addr)
    next_sessions: List[Dict[str, Any]] = []
    replaced = False
    for item in sessions:
        if not isinstance(item, dict):
            continue
        item = dict(item)
        item["current"] = False
        if item.get("id") == current["id"]:
            next_sessions.append({**item, **current})
            replaced = True
        else:
            next_sessions.append(item)
    if not replaced:
        next_sessions.insert(0, current)
    next_sessions = sorted(next_sessions, key=lambda s: s.get("last_seen_at", ""), reverse=True)[:20]
    users[user_id] = next_sessions
    _save(data)
    return next_sessions


def list_sessions(user_id: str) -> List[Dict[str, Any]]:
    data = _load()
    sessions = data.get("users", {}).get(user_id, [])
    return sessions if isinstance(sessions, list) else []


def revoke_session(user_id: str, session_id: str, current_id: str | None = None) -> Dict[str, Any]:
    if current_id and session_id == current_id:
        return {"success": False, "error": "cannot revoke current session from this device"}
    data = _load()
    users = data.setdefault("users", {})
    sessions = users.get(user_id)
    if not isinstance(sessions, list):
        return {"success": False, "error": "session not found"}
    changed = False
    for item in sessions:
        if not isinstance(item, dict) or item.get("id") != session_id:
            continue
        item["revoked"] = True
        item["current"] = False
        item["revoked_at"] = datetime.now(timezone.utc).isoformat()
        changed = True
    if not changed:
        return {"success": False, "error": "session not found"}
    users[user_id] = sessions
    _save(data)
    return {"success": True, "user_id": user_id, "sessions": sessions}


def is_session_revoked(user_id: str, user_agent: str = "", remote_addr: str = "") -> bool:
    sid = current_session_id(user_id, user_agent, remote_addr)
    for item in list_sessions(user_id):
        if isinstance(item, dict) and item.get("id") == sid:
            return bool(item.get("revoked"))
    return False
