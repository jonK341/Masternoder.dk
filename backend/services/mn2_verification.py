"""
MN2 withdrawal verification (Phase 10): optional gate so only verified users can withdraw.
When withdrawal_requires_verification is true in config, user_id must be in the verified list.
List is stored in data/mn2_verified_users.json; maintain via file edit or ops API.
See docs/MASTERNODER2_CRYPTO_INTEGRATION_EXPANDED.md Phase 10.
"""
import os
import json
import threading
from typing import List, Set

_LOCK = threading.Lock()
_FILENAME = "mn2_verified_users.json"


def _data_dir() -> str:
    base = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    return os.path.join(base, "data")


def _path() -> str:
    return os.path.join(_data_dir(), _FILENAME)


def _load_ids() -> Set[str]:
    p = _path()
    with _LOCK:
        if not os.path.exists(p):
            return set()
        try:
            with open(p, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, list):
                return {str(x).strip() for x in data if (x or "").strip()}
            if isinstance(data, dict) and "user_ids" in data:
                return {str(x).strip() for x in (data["user_ids"] or []) if (x or "").strip()}
            return set()
        except Exception:
            return set()


def _save_ids(ids: Set[str]) -> None:
    os.makedirs(_data_dir(), exist_ok=True)
    with _LOCK:
        with open(_path(), "w", encoding="utf-8") as f:
            json.dump({"user_ids": sorted(ids)}, f, indent=2)


def is_verified(user_id: str) -> bool:
    """True if user_id is in the verified list (case-sensitive strip, no empty)."""
    uid = (user_id or "").strip()
    if not uid:
        return False
    return uid in _load_ids()


def add_verified(user_id: str) -> bool:
    """Add user_id to verified list. Returns True if added (was not already in)."""
    uid = (user_id or "").strip()
    if not uid:
        return False
    ids = _load_ids()
    if uid in ids:
        return False
    ids.add(uid)
    _save_ids(ids)
    return True


def remove_verified(user_id: str) -> bool:
    """Remove user_id from verified list. Returns True if removed."""
    uid = (user_id or "").strip()
    if not uid:
        return False
    ids = _load_ids()
    if uid not in ids:
        return False
    ids.discard(uid)
    _save_ids(ids)
    return True


def list_verified() -> List[str]:
    """Return sorted list of verified user_ids (for admin)."""
    return sorted(_load_ids())
