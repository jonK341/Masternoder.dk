"""Decide whether a request user id is safe to look up.

Placeholders and display names were reaching profile and points routes and
coming back as a vague HTTP 400. Callers get 401 for missing identity and 404
when the token is not a user id, with the reason written to the log.
"""
import logging
import re
from typing import Optional, Tuple
from urllib.parse import unquote

logger = logging.getLogger(__name__)

_PLACEHOLDERS = frozenset({
    "",
    "default_user",
    "default",
    "anonymous",
    "null",
    "undefined",
    "none",
    "user",
    "[object promise]",
})

# Ids minted by user identification: user_<fingerprint-or-hash>.
_CANONICAL_RE = re.compile(r"^user_[A-Za-z0-9_]{4,120}$")


def normalize_user_id(raw) -> str:
    return unquote(str(raw or "")).strip()


def is_canonical_user_id(raw) -> bool:
    return bool(_CANONICAL_RE.match(normalize_user_id(raw)))


def rejection_for(raw) -> Optional[Tuple[dict, int]]:
    """Return (json body, status) when the id must not be queried, else None."""
    value = normalize_user_id(raw)
    lowered = value.lower()
    if not value or lowered in _PLACEHOLDERS:
        reason = "missing or placeholder user id"
        status = 401
        code = "user_unauthenticated"
    elif not is_canonical_user_id(value):
        reason = "not a user id"
        status = 404
        code = "user_not_found"
    else:
        return None
    logger.info(
        "rejected user id value=%r status=%s reason=%s",
        value,
        status,
        reason,
    )
    return {
        "success": False,
        "error": reason,
        "code": code,
        "user_id": value,
    }, status
