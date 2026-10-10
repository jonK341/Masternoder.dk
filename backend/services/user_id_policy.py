"""Decide whether a request user id may be looked up.

Placeholders never hit the database. Any other value, including legacy ids
such as ``jon`` or ``Sander Sahk``, is looked up. Callers 404 only when the
lookup confirms the account is absent.
"""
import logging
import os
from typing import Optional, Tuple
from urllib.parse import unquote

from sqlalchemy import text

from src.db.models import db

logger = logging.getLogger(__name__)

_PLACEHOLDERS = frozenset({
    "",
    "default_user",
    "undefined",
    "null",
    "[object promise]",
})

_LOOKUP_TABLES = ("user_profiles", "user_accounts", "player_levels")


def normalize_user_id(raw) -> str:
    return unquote(str(raw or "")).strip()


def is_placeholder_user_id(raw) -> bool:
    value = normalize_user_id(raw)
    if not value:
        return True
    if value == "[object Promise]":
        return True
    return value.lower() in _PLACEHOLDERS


def rejection_for(raw) -> Optional[Tuple[dict, int]]:
    """Return (json body, 401) for placeholders. None means look the id up."""
    if not is_placeholder_user_id(raw):
        return None
    value = normalize_user_id(raw)
    reason = "missing or placeholder user id"
    logger.info("rejected user id value=%r status=401 reason=%s", value, reason)
    return {
        "success": False,
        "error": reason,
        "code": "user_unauthenticated",
        "user_id": value,
    }, 401


def missing_user_response(user_id: str) -> Tuple[dict, int]:
    value = normalize_user_id(user_id)
    logger.info("user id not in database value=%r status=404", value)
    return {
        "success": False,
        "error": "user not found",
        "code": "user_not_found",
        "user_id": value,
    }, 404


def user_exists(user_id: str) -> Optional[bool]:
    """True if a row or profile file exists, False if confirmed missing, None if unknown."""
    value = normalize_user_id(user_id)
    if is_placeholder_user_id(value):
        return False
    checked = False
    for table in _LOOKUP_TABLES:
        try:
            row = db.session.execute(
                text(f"SELECT 1 FROM {table} WHERE user_id = :uid LIMIT 1"),
                {"uid": value},
            ).first()
            checked = True
            if row:
                return True
        except Exception:
            try:
                db.session.rollback()
            except Exception:
                pass
    if _profile_file_exists(value):
        return True
    if not checked:
        return None
    return False


def _profile_file_exists(user_id: str) -> bool:
    if "/" in user_id or "\\" in user_id or user_id in (".", ".."):
        return False
    base = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    for folder in ("user_profiles", "unified_points"):
        path = os.path.join(base, "logs", folder, f"{user_id}.json")
        if os.path.isfile(path):
            return True
    return False
