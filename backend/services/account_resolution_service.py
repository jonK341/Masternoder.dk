"""
Account resolution for shop and PayPal.
Resolves user_id from: session > request param > user_identification (IP/fingerprint).
Ensures purchases are attached to the correct account.
"""
from typing import Optional, Tuple
from flask import request, session


def resolve_user_id_with_source(
    from_body: bool = True,
    from_query: bool = True,
    param_name: str = "user_id",
    use_session: bool = True,
    use_identification: bool = True,
) -> Tuple[str, str]:
    """
    Resolve user_id and the source it came from.
    Returns (user_id, source) where source is one of: "session", "query", "body", "identification", "default".
    """
    if use_session and session.get("user_id"):
        session_uid = str(session["user_id"]).strip()
        try:
            from backend.services.account_session_service import is_session_revoked
            if is_session_revoked(session_uid, request.headers.get("User-Agent", ""), request.remote_addr or ""):
                session.pop("user_id", None)
            else:
                return (session_uid, "session")
        except Exception:
            return (session_uid, "session")

    uid = None
    if from_body:
        try:
            data = request.get_json() or {}
            uid = data.get(param_name) or data.get("user_id")
            if uid and str(uid).strip():
                return (str(uid).strip(), "body")
        except Exception:
            pass
    if from_query:
        uid = request.args.get(param_name) or request.args.get("user_id")
        if uid and str(uid).strip() and str(uid).strip().lower() != "default_user":
            return (str(uid).strip(), "query")

    if use_identification:
        try:
            from backend.services.user_identification import user_identification
            result = user_identification.identify_or_create_user(request)
            if result.get("success") and result.get("user_id"):
                return (str(result["user_id"]).strip(), "identification")
        except Exception:
            pass

    return ("default_user", "default")


def resolve_user_id(
    from_body: bool = True,
    from_query: bool = True,
    param_name: str = "user_id",
    use_session: bool = True,
    use_identification: bool = True,
) -> str:
    """
    Resolve user_id with priority: session > request body/query > user_identification.
    Returns 'default_user' only if all sources fail.
    """
    # 1. Server-side session (set on login/create)
    if use_session and session.get("user_id"):
        session_uid = str(session["user_id"]).strip()
        try:
            from backend.services.account_session_service import is_session_revoked
            if is_session_revoked(session_uid, request.headers.get("User-Agent", ""), request.remote_addr or ""):
                session.pop("user_id", None)
            else:
                return session_uid
        except Exception:
            return session_uid

    # 2. Request body or query
    uid = None
    if from_body:
        try:
            data = request.get_json() or {}
            uid = data.get(param_name) or data.get("user_id")
        except Exception:
            pass
    if not uid and from_query:
        uid = request.args.get(param_name) or request.args.get("user_id")

    if uid and str(uid).strip() and str(uid).strip().lower() != "default_user":
        return str(uid).strip()

    # 3. User identification (IP + fingerprint fallback)
    if use_identification:
        try:
            from backend.services.user_identification import user_identification
            result = user_identification.identify_or_create_user(request)
            if result.get("success") and result.get("user_id"):
                return str(result["user_id"]).strip()
        except Exception:
            pass

    return "default_user"


def set_session_user(user_id: str) -> None:
    """Store user_id in server session (call after login/create)."""
    if user_id and str(user_id).strip():
        session["user_id"] = str(user_id).strip()
        session.permanent = True


def clear_session_user() -> None:
    """Clear user from session (logout)."""
    session.pop("user_id", None)


def has_valid_account(user_id: Optional[str] = None) -> bool:
    """Check if user has a non-default account (required for PayPal)."""
    uid = user_id or resolve_user_id()
    return bool(uid and uid.strip() and uid.strip().lower() != "default_user")
