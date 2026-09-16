"""
MN2 withdrawal address book (Top-10 #8).

Users label payout addresses. After one successful withdrawal ("clearance"), trusted
entries skip the new-address cooling-off on future sends.
"""
from __future__ import annotations

import json
import os
import threading
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

_LOCK = threading.Lock()
_BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_PATH = os.path.join(_BASE, "data", "mn2_address_book.json")


def _iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load() -> Dict[str, Any]:
    if not os.path.exists(_PATH):
        return {}
    try:
        with open(_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _save(data: Dict[str, Any]) -> None:
    os.makedirs(os.path.dirname(_PATH), exist_ok=True)
    tmp = _PATH + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    os.replace(tmp, _PATH)


def list_addresses(user_id: str) -> List[Dict[str, Any]]:
    uid = (user_id or "").strip()
    data = _load()
    book = data.get(uid) or {}
    out = []
    for addr, rec in book.items():
        if not isinstance(rec, dict):
            continue
        out.append({
            "address": addr,
            "label": rec.get("label") or "",
            "cleared": bool(rec.get("cleared")),
            "added_at": rec.get("added_at"),
            "cleared_at": rec.get("cleared_at"),
        })
    out.sort(key=lambda x: x.get("added_at") or "", reverse=True)
    return out


def add_address(user_id: str, address: str, label: str = "") -> Dict[str, Any]:
    uid = (user_id or "").strip()
    addr = (address or "").strip()
    if not uid or not addr:
        return {"success": False, "error": "user_id and address required"}
    with _LOCK:
        data = _load()
        book = data.setdefault(uid, {})
        if addr in book:
            book[addr]["label"] = (label or book[addr].get("label") or "").strip()
            _save(data)
            return {"success": True, "address": addr, "updated": True}
        book[addr] = {
            "label": (label or "").strip(),
            "cleared": False,
            "added_at": _iso(),
        }
        _save(data)
    return {"success": True, "address": addr, "cleared": False}


def remove_address(user_id: str, address: str) -> Dict[str, Any]:
    uid = (user_id or "").strip()
    addr = (address or "").strip()
    with _LOCK:
        data = _load()
        book = data.get(uid) or {}
        if addr not in book:
            return {"success": False, "error": "address not in book"}
        del book[addr]
        data[uid] = book
        _save(data)
    return {"success": True}


def is_cleared_trusted(user_id: str, address: str) -> bool:
    """True when address is in the user's book and has completed first clearance."""
    uid = (user_id or "").strip()
    addr = (address or "").strip()
    if not uid or not addr:
        return False
    book = (_load().get(uid) or {})
    rec = book.get(addr)
    return bool(isinstance(rec, dict) and rec.get("cleared"))


def mark_cleared(user_id: str, address: str) -> None:
    """Called after a successful withdrawal to trusted book entry."""
    uid = (user_id or "").strip()
    addr = (address or "").strip()
    if not uid or not addr:
        return
    with _LOCK:
        data = _load()
        book = data.get(uid) or {}
        if addr not in book:
            return
        book[addr]["cleared"] = True
        book[addr]["cleared_at"] = _iso()
        data[uid] = book
        _save(data)
