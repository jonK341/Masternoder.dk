"""MN2 casino cashback — accrue on MN2 playthrough, claim once per day (Phase 7)."""
from __future__ import annotations

import json
import os
import threading
from datetime import datetime, timezone
from typing import Any, Dict, Optional

_BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_STATE = os.path.join(_BASE, "data", "casino_mn2_cashback.json")
_LOCK = threading.Lock()

# Default: 0.5% of MN2 wager volume accrues as claimable cashback.
_DEFAULT_RATE = 0.005
_MAX_DAILY_CLAIM = 0.5
_MIN_CLAIM = 0.0001


def _today() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _config() -> Dict[str, Any]:
    try:
        from backend.services.casino_service import _load_config

        block = (_load_config().get("mn2_cashback") or {})
        return block if isinstance(block, dict) else {}
    except Exception:
        return {}


def _rate() -> float:
    cfg = _config()
    if cfg.get("enabled") is False:
        return 0.0
    try:
        return max(0.0, min(0.05, float(cfg.get("rate") or _DEFAULT_RATE)))
    except (TypeError, ValueError):
        return _DEFAULT_RATE


def _load() -> Dict[str, Any]:
    if not os.path.isfile(_STATE):
        return {"users": {}}
    try:
        with open(_STATE, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {"users": {}}
    except Exception:
        return {"users": {}}


def _save(data: Dict[str, Any]) -> None:
    os.makedirs(os.path.dirname(_STATE), exist_ok=True)
    tmp = _STATE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    os.replace(tmp, _STATE)


def accrue(user_id: str, bet_mn2: float, *, game: str = "", bet_id: str = "") -> Optional[Dict[str, Any]]:
    """Accrue cashback from an MN2 wager. Returns accrual dict or None."""
    from backend.services.mn2_earn_auth import is_earn_eligible_user

    if not is_earn_eligible_user(user_id):
        return None
    rate = _rate()
    bet = float(bet_mn2 or 0)
    if rate <= 0 or bet <= 0:
        return None
    amount = round(bet * rate, 8)
    if amount <= 0:
        return None

    uid = str(user_id).strip()
    with _LOCK:
        data = _load()
        users = data.setdefault("users", {})
        row = users.setdefault(uid, {"pending_mn2": 0.0, "lifetime_accrued": 0.0, "lifetime_claimed": 0.0})
        row["pending_mn2"] = round(float(row.get("pending_mn2") or 0) + amount, 8)
        row["lifetime_accrued"] = round(float(row.get("lifetime_accrued") or 0) + amount, 8)
        row["last_game"] = str(game or "")[:64]
        row["last_bet_id"] = str(bet_id or "")[:64]
        row["updated_at"] = datetime.now(timezone.utc).isoformat()
        _save(data)

    return {
        "accrued": amount,
        "pending_mn2": float(row["pending_mn2"]),
        "rate": rate,
        "currency": "mn2",
    }


def status(user_id: str) -> Dict[str, Any]:
    uid = str(user_id or "").strip()
    cfg = _config()
    with _LOCK:
        data = _load()
        row = (data.get("users") or {}).get(uid) or {}
    return {
        "success": True,
        "enabled": cfg.get("enabled", True) is not False,
        "rate": _rate(),
        "pending_mn2": float(row.get("pending_mn2") or 0),
        "lifetime_accrued": float(row.get("lifetime_accrued") or 0),
        "lifetime_claimed": float(row.get("lifetime_claimed") or 0),
        "last_claim_day": row.get("last_claim_day"),
        "max_daily_claim_mn2": float(cfg.get("max_daily_claim_mn2") or _MAX_DAILY_CLAIM),
        "min_claim_mn2": float(cfg.get("min_claim_mn2") or _MIN_CLAIM),
    }


def claim(user_id: str, *, day: Optional[str] = None) -> Dict[str, Any]:
    """Claim pending MN2 cashback (once per UTC day, Gate S idempotent)."""
    from backend.services.mn2_earn_auth import require_earn_user

    ok, uid_or_err = require_earn_user(user_id)
    if not ok:
        return {"success": False, "error": uid_or_err}
    uid = uid_or_err
    claim_day = (str(day).strip()[:10] if day else _today())
    cfg = _config()
    min_claim = float(cfg.get("min_claim_mn2") or _MIN_CLAIM)
    max_claim = float(cfg.get("max_daily_claim_mn2") or _MAX_DAILY_CLAIM)

    with _LOCK:
        data = _load()
        users = data.setdefault("users", {})
        row = users.setdefault(uid, {"pending_mn2": 0.0, "lifetime_accrued": 0.0, "lifetime_claimed": 0.0})
        if row.get("last_claim_day") == claim_day:
            return {
                "success": False,
                "error": "already_claimed_today",
                "day": claim_day,
                "pending_mn2": float(row.get("pending_mn2") or 0),
            }
        pending = float(row.get("pending_mn2") or 0)
        if pending < min_claim:
            return {"success": False, "error": "below_min_claim", "pending_mn2": pending, "min_claim_mn2": min_claim}
        amount = round(min(pending, max_claim), 8)
        # Optimistic reserve — credit first, then persist if success.
        reserved_pending = round(pending - amount, 8)

    reference = f"casino_mn2_cashback:{uid}:{claim_day}"
    from backend.services.unified_points_database import unified_points_db
    from backend.services.mn2_ledger import append_entry
    from backend.services.activity_events_service import emit

    result = unified_points_db.add_points(
        uid,
        "mn2_balance",
        amount,
        source="casino_mn2_cashback",
        metadata={"reference": reference, "day": claim_day},
    )
    if result.get("duplicate"):
        with _LOCK:
            data = _load()
            row = data.setdefault("users", {}).setdefault(uid, {})
            row["last_claim_day"] = claim_day
            _save(data)
        return {"success": False, "error": "already_claimed_today", "day": claim_day, "duplicate": True}
    if not result.get("success"):
        return result

    with _LOCK:
        data = _load()
        row = data.setdefault("users", {}).setdefault(uid, {})
        row["pending_mn2"] = reserved_pending
        row["lifetime_claimed"] = round(float(row.get("lifetime_claimed") or 0) + amount, 8)
        row["last_claim_day"] = claim_day
        row["updated_at"] = datetime.now(timezone.utc).isoformat()
        _save(data)

    append_entry(
        user_id=uid,
        entry_type="casino_mn2_cashback",
        amount=amount,
        txid=reference,
        metadata={"day": claim_day},
    )
    emit(
        "casino_mn2_cashback",
        user_id=uid,
        channel="casino",
        text=f"+{amount} MN2 cashback",
        payload={"amount": amount, "day": claim_day},
    )
    return {
        "success": True,
        "mn2_awarded": amount,
        "amount_mn2": amount,
        "pending_mn2": reserved_pending,
        "day": claim_day,
    }
