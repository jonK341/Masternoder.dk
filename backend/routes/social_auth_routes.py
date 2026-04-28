"""
Social Auth Routes
Unified top-5 social login endpoints.
"""
from flask import Blueprint, jsonify, redirect, request
from backend.services.account_resolution_service import set_session_user

from backend.services.social_auth_service import (
    build_start_url,
    handle_callback,
    list_providers,
    validate_return_url,
)

social_auth_bp = Blueprint("social_auth", __name__)
_AUTH_RATE = {}
_ALLOWED_PROVIDERS = frozenset({"github", "google"})


def _client_ip() -> str:
    fwd = (request.headers.get("X-Forwarded-For") or "").split(",")[0].strip()
    return fwd or request.remote_addr or "unknown"


def _rate_limit(key: str, limit: int, window_sec: int) -> bool:
    import time
    now = int(time.time())
    bucket = _AUTH_RATE.get(key, [])
    cutoff = now - window_sec
    bucket = [t for t in bucket if t > cutoff]
    if len(bucket) >= limit:
        _AUTH_RATE[key] = bucket
        return False
    bucket.append(now)
    _AUTH_RATE[key] = bucket
    return True


@social_auth_bp.route("/api/auth/providers", methods=["GET"])
def auth_providers():
    """Return enabled social auth providers (GitHub, Google)."""
    data = list_providers()
    providers = data.get("providers", []) if isinstance(data, dict) else []
    out = []
    for pid in _ALLOWED_PROVIDERS:
        p = next((x for x in providers if x.get("id") == pid), {})
        out.append({
            "id": pid,
            "enabled": bool(p.get("enabled")),
            "configured": bool(p.get("configured")),
            "start_path": f"/api/auth/{pid}/start",
            "callback_path": f"/api/auth/{pid}/callback",
        })
    return jsonify({"success": True, "providers": out}), 200


@social_auth_bp.route("/api/auth/<provider>/start", methods=["GET"])
def auth_start(provider: str):
    """
    Start OAuth flow.
    Query:
      user_id_hint - optional existing user
      return_url   - optional final redirect URL
      redirect     - if 1/true, respond with HTTP redirect to provider
    """
    if provider not in _ALLOWED_PROVIDERS:
        return jsonify({
            "success": False,
            "error": f"{provider} login disabled",
            "allowed_providers": list(_ALLOWED_PROVIDERS),
        }), 400

    user_id_hint = request.args.get("user_id_hint")
    return_url = request.args.get("return_url")
    do_redirect = (request.args.get("redirect") or "").lower() in ("1", "true", "yes")
    if not _rate_limit(f"start:{_client_ip()}:{provider}", limit=20, window_sec=60):
        return jsonify({"success": False, "error": "Too Many Requests"}), 429
    result = build_start_url(provider, user_id_hint=user_id_hint, return_url=return_url)
    if not result.get("success"):
        return jsonify(result), 400
    if do_redirect:
        return redirect(result["auth_url"], code=302)
    return jsonify(result), 200


@social_auth_bp.route("/api/auth/<provider>/callback", methods=["GET"])
def auth_callback(provider: str):
    """
    OAuth callback endpoint.
    Returns JSON by default; if return_url exists, redirects with user_id and provider.
    """
    if provider not in _ALLOWED_PROVIDERS:
        return jsonify({
            "success": False,
            "error": f"{provider} callback disabled",
            "allowed_providers": list(_ALLOWED_PROVIDERS),
        }), 400

    code = request.args.get("code")
    state = request.args.get("state")
    if not _rate_limit(f"callback:{_client_ip()}:{provider}", limit=30, window_sec=60):
        return jsonify({"success": False, "error": "Too Many Requests"}), 429
    if not code or not state:
        return jsonify({"success": False, "error": "Missing code/state"}), 400
    result = handle_callback(provider, code, state)
    if not result.get("success"):
        return jsonify(result), 400

    # Bind account to current server session for same-window continuity.
    user_id = result.get("user_id")
    if user_id:
        set_session_user(user_id)
        result["session_bound"] = True

    return_url = result.get("return_url")
    safe_return_url = validate_return_url(return_url)
    if safe_return_url:
        sep = "&" if "?" in return_url else "?"
        url = (
            f"{safe_return_url}{sep}"
            f"auth_success=1&provider={provider}&user_id={result.get('user_id')}"
        )
        return redirect(url, code=302)
    return jsonify(result), 200
