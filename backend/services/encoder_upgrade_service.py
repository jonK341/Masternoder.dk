"""Persist per-user Super Encoder v2 upgrade unlock state."""
from __future__ import annotations

import json
import os
import threading
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set

_BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_PROGRESS_FILE = os.path.join(_BASE, "data", "encoder_v2_progress.json")
_LOCK = threading.Lock()


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _default_store() -> Dict[str, Any]:
    return {"version": 2, "users": {}}


def _load_store() -> Dict[str, Any]:
    if not os.path.isfile(_PROGRESS_FILE):
        return _default_store()
    try:
        with open(_PROGRESS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict):
            return _default_store()
        users = data.get("users")
        if not isinstance(users, dict):
            data["users"] = {}
        data.setdefault("version", 2)
        return data
    except Exception:
        return _default_store()


def _save_store(data: Dict[str, Any]) -> None:
    os.makedirs(os.path.dirname(_PROGRESS_FILE), exist_ok=True)
    with open(_PROGRESS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def _user_row(store: Dict[str, Any], user_id: str) -> Dict[str, Any]:
    users = store.setdefault("users", {})
    row = users.get(user_id)
    if not isinstance(row, dict):
        row = {"unlocked": [], "unlocked_at": {}, "updated_at": _now_iso()}
        users[user_id] = row
    if not isinstance(row.get("unlocked"), list):
        row["unlocked"] = []
    if not isinstance(row.get("unlocked_at"), dict):
        row["unlocked_at"] = {}
    return row


def get_unlocked_ids(user_id: str) -> Set[str]:
    with _LOCK:
        store = _load_store()
        row = _user_row(store, user_id)
        return {str(x) for x in row.get("unlocked") or [] if isinstance(x, str)}


def get_user_progress(user_id: str) -> Dict[str, Any]:
    with _LOCK:
        store = _load_store()
        row = _user_row(store, user_id)
        unlocked = [str(x) for x in row.get("unlocked") or [] if isinstance(x, str)]
        return {
            "user_id": user_id,
            "encoder_version": 2,
            "unlocked": unlocked,
            "unlocked_count": len(unlocked),
            "updated_at": row.get("updated_at"),
        }


def is_unlocked(user_id: str, upgrade_id: str) -> bool:
    return upgrade_id in get_unlocked_ids(user_id)


def unlock_upgrade(user_id: str, upgrade_id: str) -> Dict[str, Any]:
    uid = str(upgrade_id or "").strip()
    if not uid:
        return {"success": False, "error": "upgrade_id_required"}

    with _LOCK:
        store = _load_store()
        row = _user_row(store, user_id)
        unlocked: List[str] = [str(x) for x in row.get("unlocked") or [] if isinstance(x, str)]
        if uid in unlocked:
            return {
                "success": True,
                "duplicate": True,
                "upgrade_id": uid,
                "unlocked_count": len(unlocked),
            }
        unlocked.append(uid)
        row["unlocked"] = unlocked
        row.setdefault("unlocked_at", {})[uid] = _now_iso()
        row["updated_at"] = _now_iso()
        _save_store(store)
        return {
            "success": True,
            "upgrade_id": uid,
            "unlocked_count": len(unlocked),
        }


def bulk_unlock_free(user_id: str, upgrade_ids: List[str]) -> Dict[str, Any]:
    added = 0
    with _LOCK:
        store = _load_store()
        row = _user_row(store, user_id)
        unlocked: List[str] = [str(x) for x in row.get("unlocked") or [] if isinstance(x, str)]
        seen = set(unlocked)
        for uid in upgrade_ids:
            u = str(uid or "").strip()
            if not u or u in seen:
                continue
            unlocked.append(u)
            seen.add(u)
            row.setdefault("unlocked_at", {})[u] = _now_iso()
            added += 1
        row["unlocked"] = unlocked
        row["updated_at"] = _now_iso()
        _save_store(store)
    prog = get_user_progress(user_id)
    return {"success": True, "added": added, "progress": prog}
