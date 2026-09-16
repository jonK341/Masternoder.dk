"""Peer trophy edition transfers with rate limits and ledger audit (plan 001 T-U2)."""
from __future__ import annotations

import json
import os
import threading
from datetime import datetime, timezone
from typing import Any, Dict, Optional

_LOCK = threading.RLock()
_BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_CONFIG_PATH = os.path.join(_BASE, "data", "trophy_transfer_config.json")
_DAILY_PATH = os.path.join(_BASE, "data", "trophy_transfer_daily.json")


def _iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _today_key() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _read_json(path: str, default: Any) -> Any:
    if not os.path.isfile(path):
        return default
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def _write_json(path: str, data: Any) -> bool:
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        tmp = path + ".tmp"
        with _LOCK:
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            os.replace(tmp, path)
        return True
    except Exception:
        return False


def get_transfer_config() -> Dict[str, Any]:
    doc = _read_json(
        _CONFIG_PATH,
        {"max_transfers_per_day": 10, "require_recipient_exists": False},
    )
    try:
        doc["max_transfers_per_day"] = max(1, int(doc.get("max_transfers_per_day") or 10))
    except (TypeError, ValueError):
        doc["max_transfers_per_day"] = 10
    return doc


def count_transfers_today(user_id: str) -> int:
    uid = (user_id or "").strip()
    if not uid:
        return 0
    doc = _read_json(_DAILY_PATH, {"days": {}})
    day = doc.get("days", {}).get(_today_key(), {})
    return int(day.get(uid) or 0)


def _increment_daily(user_id: str) -> None:
    uid = (user_id or "").strip()
    if not uid:
        return
    with _LOCK:
        doc = _read_json(_DAILY_PATH, {"days": {}})
        days = doc.setdefault("days", {})
        day = days.setdefault(_today_key(), {})
        day[uid] = int(day.get(uid) or 0) + 1
        doc["updated_at"] = _iso()
        _write_json(_DAILY_PATH, doc)


def transfer_trophy_edition(
    sender_id: str,
    recipient_id: str,
    item_id: str,
    edition_no: int,
    *,
    note: Optional[str] = None,
) -> Dict[str, Any]:
    """Validate and execute a peer trophy edition transfer."""
    sender = (sender_id or "").strip()
    recipient = (recipient_id or "").strip()
    iid = (item_id or "").strip()

    if not sender or sender in ("default_user", "guest"):
        return {"success": False, "error": "guest_blocked", "message": "Sign in to transfer trophies"}

    from backend.services.trophy_fulfillment_service import is_trophy_item, transfer_edition_peer

    if not is_trophy_item(iid):
        return {"success": False, "error": "not_a_trophy_item", "item_id": iid}

    cfg = get_transfer_config()
    if count_transfers_today(sender) >= cfg["max_transfers_per_day"]:
        return {
            "success": False,
            "error": "rate_limit_exceeded",
            "max_per_day": cfg["max_transfers_per_day"],
        }

    result = transfer_edition_peer(
        sender_id=sender,
        recipient_id=recipient,
        item_id=iid,
        edition_no=edition_no,
        note=note,
    )
    if not result.get("success"):
        return result

    _increment_daily(sender)

    try:
        from backend.services.mn2_ledger import append_entry

        append_entry(
            sender,
            "trophy_transfer",
            0.0,
            txid=f"transfer:{sender}:{recipient}:{iid}:{edition_no}",
            metadata={
                "item_id": iid,
                "edition_no": int(edition_no),
                "edition_key": result.get("edition_key"),
                "recipient_id": recipient,
                "note": (note or "").strip() or None,
            },
        )
    except Exception:
        pass

    return {
        **result,
        "transfers_today": count_transfers_today(sender),
        "max_transfers_per_day": cfg["max_transfers_per_day"],
    }
