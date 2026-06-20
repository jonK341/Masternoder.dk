"""
Metered white-label Generator API keys (#3).

Keys map to org_label + user_id; usage lands in metering.jsonl like internal jobs.
"""
from __future__ import annotations

import hashlib
import json
import os
import secrets
import threading
from datetime import datetime, timezone
from typing import Any, Dict, Optional, Tuple

_LOCK = threading.Lock()
_BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_KEYS_PATH = os.path.join(_BASE, "data", "generator_api_keys.json")


def _load() -> Dict[str, Any]:
    if not os.path.isfile(_KEYS_PATH):
        return {"keys": []}
    try:
        with open(_KEYS_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {"keys": []}
    except Exception:
        return {"keys": []}


def _save(data: Dict[str, Any]) -> None:
    os.makedirs(os.path.dirname(_KEYS_PATH), exist_ok=True)
    with _LOCK:
        tmp = _KEYS_PATH + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        os.replace(tmp, _KEYS_PATH)


def _hash_key(raw: str) -> str:
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def create_api_key(
    *,
    org_label: str,
    user_id: str,
    label: Optional[str] = None,
) -> Dict[str, Any]:
    secret = os.environ.get("GENERATOR_API_KEY_SECRET") or "dev-change-me"
    raw = f"mn2gen_{secrets.token_urlsafe(24)}"
    h = _hash_key(f"{secret}:{raw}")
    row = {
        "id": secrets.token_hex(8),
        "key_hash": h,
        "org_label": (org_label or "").strip()[:256],
        "user_id": (user_id or "").strip(),
        "label": (label or org_label or "api")[:128],
        "created_at": datetime.now(timezone.utc).isoformat(),
        "active": True,
    }
    data = _load()
    keys = data.get("keys") if isinstance(data.get("keys"), list) else []
    keys.append(row)
    data["keys"] = keys[-500:]
    _save(data)
    return {"success": True, "api_key": raw, "key_id": row["id"], "org_label": row["org_label"], "note": "Store api_key now — shown once."}


def resolve_api_key(raw_key: str) -> Optional[Dict[str, Any]]:
    secret = os.environ.get("GENERATOR_API_KEY_SECRET") or "dev-change-me"
    h = _hash_key(f"{secret}:{(raw_key or '').strip()}")
    for row in _load().get("keys") or []:
        if not isinstance(row, dict) or not row.get("active"):
            continue
        if row.get("key_hash") == h:
            return row
    return None


def authenticate_request(headers: Dict[str, str]) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    raw = (headers.get("X-Generator-Api-Key") or headers.get("Authorization") or "").strip()
    if raw.lower().startswith("bearer "):
        raw = raw[7:].strip()
    if not raw:
        return None, None
    row = resolve_api_key(raw)
    if not row:
        return None, "invalid_api_key"
    return row, None


def list_keys_for_org(org_label: str) -> Dict[str, Any]:
    ol = (org_label or "").strip()
    out = []
    for row in _load().get("keys") or []:
        if isinstance(row, dict) and (row.get("org_label") or "") == ol:
            out.append({
                "id": row.get("id"),
                "label": row.get("label"),
                "user_id": row.get("user_id"),
                "created_at": row.get("created_at"),
                "active": row.get("active"),
            })
    return {"success": True, "org_label": ol, "keys": out}
