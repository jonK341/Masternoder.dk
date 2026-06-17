"""Shared auth gate for MN2 earn/credit actions (Gate S)."""
from __future__ import annotations

from typing import Optional, Tuple

_ANON = frozenset({"", "default_user", "anon", "anonymous", "guest", "null", "undefined"})


def is_earn_eligible_user(user_id: Optional[str]) -> bool:
    uid = (user_id or "").strip()
    if not uid or uid.lower() in _ANON:
        return False
    if uid.startswith("anon_") or uid.startswith("temp_"):
        return False
    return True


def require_earn_user(user_id: Optional[str]) -> Tuple[bool, str]:
    if is_earn_eligible_user(user_id):
        return True, (user_id or "").strip()
    return False, "authenticated_user_required"
