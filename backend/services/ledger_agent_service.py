"""Ledger agent chat — customer service threads for community fulfillment rows."""
from __future__ import annotations

import json
import os
import threading
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

_LOCK = threading.RLock()
_BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_THREADS_FILE = os.path.join(_BASE, "data", "ledger_agent_threads.json")
_GREETING_TEMPLATE = (
    "Hi {name}, MN2 community offer — we noticed your interest in MasterNoder coins. "
    "Reply here if you'd like a personalized pack via PayPal, USDT, or USDC."
)


def _iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _load_threads() -> Dict[str, Any]:
    if not os.path.isfile(_THREADS_FILE):
        return {"version": 1, "threads": {}, "updated_at": None}
    try:
        with open(_THREADS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict):
            data.setdefault("threads", {})
            return data
    except Exception:
        pass
    return {"version": 1, "threads": {}, "updated_at": None}


def _save_threads(doc: Dict[str, Any]) -> None:
    os.makedirs(os.path.dirname(_THREADS_FILE), exist_ok=True)
    doc["updated_at"] = _iso()
    tmp = _THREADS_FILE + ".tmp"
    with _LOCK:
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(doc, f, indent=2)
        os.replace(tmp, _THREADS_FILE)


def _display_name_for_row(row: Dict[str, Any]) -> str:
    return (
        row.get("display_name")
        or row.get("discord_username")
        or row.get("user_id")
        or row.get("youtube_id")
        or row.get("facebook_id")
        or "there"
    )


def get_thread(ledger_row_id: str) -> Dict[str, Any]:
    lid = (ledger_row_id or "").strip()
    if not lid:
        return {"success": False, "error": "ledger_row_id required"}
    doc = _load_threads()
    thread = (doc.get("threads") or {}).get(lid)
    if not thread:
        return {"success": True, "ledger_row_id": lid, "messages": [], "greeted": False}
    return {"success": True, "ledger_row_id": lid, **thread}


def post_chat_message(
    ledger_row_id: str,
    message: str,
    *,
    sender: str = "agent",
    sender_id: Optional[str] = None,
    camgirl_persona: Optional[str] = None,
) -> Dict[str, Any]:
    from backend.services.discord_fulfillment_ledger_service import get_row_by_id

    lid = (ledger_row_id or "").strip()
    text = (message or "").strip()
    if not lid or not text:
        return {"success": False, "error": "ledger_row_id and message required"}

    row = get_row_by_id(lid)
    doc = _load_threads()
    threads = doc.setdefault("threads", {})
    thread = threads.setdefault(
        lid,
        {
            "ledger_row_id": lid,
            "user_id": (row or {}).get("user_id"),
            "discord_id": (row or {}).get("discord_id"),
            "messages": [],
            "greeted": False,
            "created_at": _iso(),
        },
    )
    entry = {
        "id": f"msg_{uuid.uuid4().hex[:10]}",
        "sender": sender,
        "sender_id": sender_id,
        "camgirl_persona": camgirl_persona,
        "text": text[:2000],
        "ts": _iso(),
    }
    thread.setdefault("messages", []).append(entry)
    thread["updated_at"] = _iso()
    threads[lid] = thread
    _save_threads(doc)
    return {"success": True, "message": entry, "thread": thread}


def auto_greet(ledger_row_id: str, *, force: bool = False) -> Dict[str, Any]:
    from backend.services.discord_fulfillment_ledger_service import get_row_by_id

    lid = (ledger_row_id or "").strip()
    row = get_row_by_id(lid) or {}
    doc = _load_threads()
    threads = doc.get("threads") or {}
    thread = threads.get(lid) or {}
    if thread.get("greeted") and not force:
        return {"success": True, "skipped": True, "reason": "already_greeted"}

    name = _display_name_for_row(row)
    greeting = _GREETING_TEMPLATE.format(name=name)
    result = post_chat_message(lid, greeting, sender="agent", sender_id="ledger_auto_greet")
    if result.get("success"):
        threads = _load_threads().get("threads") or {}
        if lid in threads:
            threads[lid]["greeted"] = True
            doc = _load_threads()
            doc["threads"] = threads
            _save_threads(doc)
    return result


def list_threads(limit: int = 100) -> Dict[str, Any]:
    doc = _load_threads()
    items = []
    for lid, thread in (doc.get("threads") or {}).items():
        msgs = thread.get("messages") or []
        items.append(
            {
                "ledger_row_id": lid,
                "message_count": len(msgs),
                "greeted": thread.get("greeted"),
                "updated_at": thread.get("updated_at"),
                "last_message": msgs[-1] if msgs else None,
            }
        )
    items.sort(key=lambda x: x.get("updated_at") or "", reverse=True)
    return {"success": True, "threads": items[:limit], "total": len(items)}
