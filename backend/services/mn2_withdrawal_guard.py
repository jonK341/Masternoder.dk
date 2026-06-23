"""
MN2 withdrawal address guard — new-address cooling-off (defense in depth).

A withdrawal to an address this user has never withdrawn to before is registered
with a first-seen timestamp and held until `cooldown_hours` elapses. This blunts
"steal a session and instantly drain to my address" attacks: a brand-new payout
address can't be used until the cooling-off window passes, giving the real owner
(and ops monitoring) time to react. Addresses already used by the user are trusted.

Storage: data/mn2_withdrawal_addresses.json
  { "<user_id>": { "<address>": {"first_seen": iso, "withdrawals": int} } }
"""
import json
import os
import threading
from datetime import datetime, timezone
from typing import Any, Dict

_LOCK = threading.Lock()
_BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_PATH = os.path.join(_BASE_DIR, "data", "mn2_withdrawal_addresses.json")


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _iso() -> str:
    return _utcnow().isoformat()


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


def check_address(user_id: str, address: str, cooldown_hours: float) -> Dict[str, Any]:
    """
    Decide whether `user_id` may withdraw to `address` right now.

    Registers a never-seen address (first_seen=now). Returns:
      {"allowed": True}                              -> proceed
      {"allowed": False, "code": "address_cooldown",
       "seconds_remaining": int, "first_seen": iso,
       "first_time": bool}                            -> blocked, try later
    A non-positive cooldown disables the gate (address still recorded on success).
    """
    uid = (user_id or "").strip()
    addr = (address or "").strip()
    if not uid or not addr:
        return {"allowed": True}

    try:
        cooldown = float(cooldown_hours or 0)
    except (TypeError, ValueError):
        cooldown = 0.0

    now = _utcnow()
    with _LOCK:
        data = _load()
        user = data.setdefault(uid, {})
        rec = user.get(addr)
        first_time = rec is None
        if first_time:
            rec = {"first_seen": _iso(), "withdrawals": 0}
            user[addr] = rec
            _save(data)

        if cooldown <= 0:
            return {"allowed": True, "first_time": first_time}

        try:
            first_seen = datetime.fromisoformat(str(rec["first_seen"]).replace("Z", "+00:00"))
        except Exception:
            first_seen = now
        elapsed_h = (now - first_seen).total_seconds() / 3600.0
        if elapsed_h >= cooldown:
            return {"allowed": True, "first_time": first_time}

        remaining = int(round((cooldown - elapsed_h) * 3600))
        return {
            "allowed": False,
            "code": "address_cooldown",
            "first_time": first_time,
            "first_seen": rec["first_seen"],
            "seconds_remaining": max(1, remaining),
            "cooldown_hours": cooldown,
        }


def record_success(user_id: str, address: str) -> None:
    """Increment the withdrawal counter for a (user, address) after a successful send."""
    uid = (user_id or "").strip()
    addr = (address or "").strip()
    if not uid or not addr:
        return
    with _LOCK:
        data = _load()
        user = data.setdefault(uid, {})
        rec = user.get(addr) or {"first_seen": _iso(), "withdrawals": 0}
        rec["withdrawals"] = int(rec.get("withdrawals", 0) or 0) + 1
        rec["last_used"] = _iso()
        user[addr] = rec
        _save(data)
