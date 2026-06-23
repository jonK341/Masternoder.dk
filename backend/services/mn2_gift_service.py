"""
Internal MN2 gift / transfer between users (Top-10 #6).

In-app only — no on-chain move. Sender must have withdrawable balance; caps apply.
"""
from __future__ import annotations

import json
import os
import threading
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, Optional

_LOCK = threading.Lock()
_BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_DAILY_PATH = os.path.join(_BASE, "logs", "mn2_gift_daily.json")


def _load_config() -> Dict[str, Any]:
    path = os.path.join(_BASE, "data", "mn2_config.json")
    try:
        with open(path, "r", encoding="utf-8") as f:
            cfg = json.load(f)
        return (cfg.get("gift") or {}) if isinstance(cfg, dict) else {}
    except Exception:
        return {}


def _resolve_recipient(to: str) -> Optional[str]:
    target = (to or "").strip()
    if not target:
        return None
    if target.startswith("user_"):
        return target
    try:
        from backend.services.mn2_wallet_service import get_address_to_user_map
        return (get_address_to_user_map().get(target) or "").strip() or None
    except Exception:
        return None


def _daily_sent(user_id: str) -> float:
    data = {}
    if os.path.exists(_DAILY_PATH):
        try:
            with open(_DAILY_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            data = {}
    day = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    return float(((data.get(day) or {}).get(user_id) or 0))


def _record_daily(user_id: str, amount: float) -> None:
    day = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    with _LOCK:
        data = {}
        if os.path.exists(_DAILY_PATH):
            try:
                with open(_DAILY_PATH, "r", encoding="utf-8") as f:
                    data = json.load(f)
            except Exception:
                data = {}
        bucket = data.setdefault(day, {})
        bucket[user_id] = round(float(bucket.get(user_id) or 0) + amount, 8)
        # prune entries older than 3 days
        cutoff = (datetime.now(timezone.utc) - timedelta(days=3)).strftime("%Y-%m-%d")
        data = {k: v for k, v in data.items() if k >= cutoff}
        os.makedirs(os.path.dirname(_DAILY_PATH), exist_ok=True)
        with open(_DAILY_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)


def transfer(from_user: str, to: str, amount: float, note: str = "") -> Dict[str, Any]:
    cfg = _load_config()
    if not cfg.get("enabled", True):
        return {"success": False, "error": "Internal transfers are disabled.", "code": "disabled"}

    sender = (from_user or "").strip()
    recipient = _resolve_recipient(to)
    if not sender:
        return {"success": False, "error": "sender required"}
    if not recipient:
        return {"success": False, "error": "Recipient not found (use user_id or deposit address).", "code": "recipient_not_found"}
    if recipient == sender:
        return {"success": False, "error": "Cannot send to yourself.", "code": "self_transfer"}

    try:
        amt = round(float(amount), 8)
    except (TypeError, ValueError):
        return {"success": False, "error": "Invalid amount"}
    if amt <= 0:
        return {"success": False, "error": "amount_must_be_positive"}

    max_tx = float(cfg.get("max_per_transfer_mn2") or 1000)
    max_day = float(cfg.get("max_per_day_mn2") or 5000)
    min_after = float(cfg.get("min_balance_after_mn2") or 0)

    if amt > max_tx:
        return {"success": False, "error": f"Max per transfer is {max_tx} MN2.", "code": "cap_exceeded"}
    if _daily_sent(sender) + amt > max_day:
        return {"success": False, "error": f"Daily transfer cap is {max_day} MN2.", "code": "daily_cap"}

    try:
        from backend.services.mn2_hold_registry import assert_withdrawable
        gate = assert_withdrawable(sender, amt)
        if not gate.get("allowed"):
            return {
                "success": False,
                "error": gate.get("error") or "Amount is not transferable (hold/clearance).",
                "code": gate.get("code", "hold_blocked"),
            }
    except ImportError:
        pass

    from backend.services.unified_points_database import unified_points_db
    from backend.services.mn2_ledger import append_entry

    bal = unified_points_db.get_all_points(sender)
    pts = (bal.get("points") or {}) if isinstance(bal, dict) else {}
    liquid = float(pts.get("mn2_balance") or 0)
    if liquid < amt:
        return {"success": False, "error": "Insufficient balance", "code": "insufficient"}
    if liquid - amt < min_after:
        return {"success": False, "error": f"Must keep at least {min_after} MN2 after transfer.", "code": "min_balance"}

    meta = {"to_user": recipient, "from_user": sender, "note": (note or "")[:200]}
    dr = unified_points_db.add_points(sender, "mn2_balance", -amt, source="mn2_gift_sent", metadata=meta)
    if not dr.get("success"):
        return {"success": False, "error": dr.get("error", "debit failed")}
    cr = unified_points_db.add_points(recipient, "mn2_balance", amt, source="mn2_gift_received", metadata=meta)
    if not cr.get("success"):
        unified_points_db.add_points(sender, "mn2_balance", amt, source="mn2_gift_rollback", metadata=meta)
        return {"success": False, "error": cr.get("error", "credit failed")}

    append_entry(sender, "gift_sent", amt, metadata={"to_user": recipient, **meta})
    append_entry(recipient, "gift_received", amt, metadata={"from_user": sender, **meta})
    _record_daily(sender, amt)

    return {
        "success": True,
        "amount_mn2": amt,
        "from_user": sender,
        "to_user": recipient,
        "note": meta["note"] or None,
    }
