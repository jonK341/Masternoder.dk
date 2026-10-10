"""Discord Linked Roles — OAuth verification + role connection metadata."""
from __future__ import annotations

import json
import os
import secrets
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Dict, Optional

_BASE_URL = (os.environ.get("SOCIAL_AUTH_BASE_URL") or "https://masternoder.dk").rstrip("/")
_VERIFY_REDIRECT = f"{_BASE_URL}/api/discord/role-connection/callback"
_SCOPES = "identify role_connections.write"


def portal_urls() -> Dict[str, str]:
    return {
        "interactions_endpoint_url": f"{_BASE_URL}/api/discord/interactions",
        "terms_of_service_url": f"{_BASE_URL}/legal/terms/",
        "privacy_policy_url": f"{_BASE_URL}/legal/privacy/",
        "linked_roles_verification_url": _VERIFY_REDIRECT,
        "linked_roles_user_page": f"{_BASE_URL}/discord/verify/",
    }


def _app_id() -> str:
    return (
        os.environ.get("DISCORD_APPLICATION_ID")
        or os.environ.get("DISCORD_CLIENT_ID")
        or ""
    ).strip()


def _client_secret() -> str:
    return (os.environ.get("DISCORD_CLIENT_SECRET") or os.environ.get("DISCORD_OAUTH_CLIENT_SECRET") or "").strip()


def build_authorize_url(*, state: Optional[str] = None) -> Dict[str, Any]:
    client_id = _app_id()
    if not client_id:
        return {"success": False, "error": "DISCORD_APPLICATION_ID not configured"}
    st = state or secrets.token_urlsafe(16)
    params = urllib.parse.urlencode({
        "client_id": client_id,
        "redirect_uri": _VERIFY_REDIRECT,
        "response_type": "code",
        "scope": _SCOPES,
        "state": st,
        "prompt": "consent",
    })
    return {
        "success": True,
        "authorize_url": f"https://discord.com/api/oauth2/authorize?{params}",
        "redirect_uri": _VERIFY_REDIRECT,
        "state": st,
    }


def _exchange_code(code: str) -> Dict[str, Any]:
    client_id = _app_id()
    secret = _client_secret()
    if not client_id or not secret:
        return {"success": False, "error": "discord_oauth_not_configured"}
    data = urllib.parse.urlencode({
        "client_id": client_id,
        "client_secret": secret,
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": _VERIFY_REDIRECT,
    }).encode("utf-8")
    req = urllib.request.Request(
        "https://discord.com/api/oauth2/token",
        data=data,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            return {"success": True, "token": json.loads(resp.read().decode("utf-8"))}
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")[:400]
        return {"success": False, "error": body or str(exc), "status": exc.code}


def _discord_user(access_token: str) -> Dict[str, Any]:
    req = urllib.request.Request(
        "https://discord.com/api/users/@me",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return {"success": True, "user": json.loads(resp.read().decode("utf-8"))}
    except Exception as exc:
        return {"success": False, "error": str(exc)}


def _push_role_metadata(access_token: str, metadata: Dict[str, str]) -> Dict[str, Any]:
    app_id = _app_id()
    if not app_id:
        return {"success": False, "error": "missing_application_id"}
    body = json.dumps({
        "platform_name": "MasterNoder",
        "platform_username": "masternoder",
        "metadata": metadata,
    }).encode("utf-8")
    req = urllib.request.Request(
        f"https://discord.com/api/v10/users/@me/applications/{app_id}/role-connection",
        data=body,
        headers={
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        },
        method="PUT",
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
            return {"success": True, "result": json.loads(raw) if raw else {}}
    except urllib.error.HTTPError as exc:
        err = exc.read().decode("utf-8", errors="replace")[:400]
        return {"success": False, "error": err or str(exc), "status": exc.code}


def _site_user_for_discord(discord_id: str) -> Optional[str]:
    try:
        from backend.services.discord_controller_service import _user_id_for_discord
        return _user_id_for_discord(discord_id)
    except Exception:
        return None


def handle_oauth_callback(code: str) -> Dict[str, Any]:
    """Complete Linked Roles verification after Discord redirects with ?code=."""
    tok = _exchange_code(code)
    if not tok.get("success"):
        return tok
    access = (tok.get("token") or {}).get("access_token")
    if not access:
        return {"success": False, "error": "no_access_token"}
    user_r = _discord_user(access)
    if not user_r.get("success"):
        return user_r
    discord_user = user_r.get("user") or {}
    discord_id = str(discord_user.get("id") or "")
    site_uid = _site_user_for_discord(discord_id)

    hosting = False
    if site_uid:
        try:
            from backend.services.discord_hosting_vip_service import user_has_paid_hosting
            hosting = user_has_paid_hosting(site_uid)
        except Exception:
            pass

    metadata = {
        "linked": "1" if site_uid else "0",
        "hosting_customer": "1" if hosting else "0",
    }
    push = _push_role_metadata(access, metadata)
    if site_uid and hosting:
        try:
            from backend.services.discord_hosting_vip_service import grant_hosting_vip_role
            grant_hosting_vip_role(site_uid, reason="linked_role_verify")
        except Exception:
            pass

    return {
        "success": push.get("success", False),
        "discord_id": discord_id,
        "site_user_linked": bool(site_uid),
        "hosting_customer": hosting,
        "metadata": metadata,
        "role_connection": push,
    }
