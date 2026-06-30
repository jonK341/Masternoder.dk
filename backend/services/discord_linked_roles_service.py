"""Discord Linked Roles — OAuth verification URL + role connection metadata (M8 / casino VIP)."""
from __future__ import annotations

import json
import os
import secrets
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Dict, List, Optional

_BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_STATE_PATH = os.path.join(_BASE, "data", "oauth_state.json")
_STATE_TTL_SEC = 600
_PLATFORM_NAME = "MasterNoder2"

# Discord metadata comparison types (application-role-connection-metadata)
_TYPE_NUMBER_GT = 2
_TYPE_BOOLEAN_EQ = 7

_METADATA_SCHEMA: List[Dict[str, Any]] = [
    {
        "key": "mn2_balance",
        "name": "MN2 balance",
        "description": "Linked MasterNoder account MN2 balance (greater than)",
        "type": _TYPE_NUMBER_GT,
    },
    {
        "key": "casino_vip",
        "name": "Casino VIP",
        "description": "Eligible for casino Discord VIP (linked account + MN2 threshold)",
        "type": _TYPE_BOOLEAN_EQ,
    },
    {
        "key": "hosting_vip",
        "name": "Hosting VIP",
        "description": "Paid hosting customer with linked Discord",
        "type": _TYPE_BOOLEAN_EQ,
    },
    {
        "key": "account_linked",
        "name": "Account linked",
        "description": "MasterNoder site account linked to this Discord user",
        "type": _TYPE_BOOLEAN_EQ,
    },
]


def _base_url() -> str:
    return (os.getenv("SOCIAL_AUTH_BASE_URL") or os.getenv("BASE_URL") or "https://masternoder.dk").rstrip("/")


def _client_id() -> str:
    return (os.getenv("DISCORD_CLIENT_ID") or os.getenv("DISCORD_OAUTH_CLIENT_ID") or "").strip()


def _client_secret() -> str:
    return (os.getenv("DISCORD_CLIENT_SECRET") or os.getenv("DISCORD_OAUTH_CLIENT_SECRET") or "").strip()


def _bot_token() -> str:
    return (os.getenv("DISCORD_BOT_TOKEN") or "").strip()


def linked_role_redirect_uri() -> str:
    override = (os.getenv("DISCORD_LINKED_ROLE_REDIRECT_URI") or "").strip()
    if override:
        return override
    return f"{_base_url()}/api/discord/linked-role/callback"


def linked_role_verification_url() -> str:
    override = (os.getenv("DISCORD_LINKED_ROLE_VERIFICATION_URL") or "").strip()
    if override:
        return override
    return f"{_base_url()}/api/discord/linked-role"


def configured() -> bool:
    return bool(_client_id() and _client_secret())


def _load_state_store() -> Dict[str, Dict]:
    if not os.path.isfile(_STATE_PATH):
        return {}
    try:
        with open(_STATE_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _save_state_store(data: Dict[str, Dict]) -> None:
    os.makedirs(os.path.dirname(_STATE_PATH), exist_ok=True)
    with open(_STATE_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def _purge_states_in(store: Dict[str, Dict]) -> None:
    import time

    now = int(time.time())
    stale = [k for k, v in store.items() if (v or {}).get("expires_at", 0) <= now]
    for k in stale:
        store.pop(k, None)


def _store_state(state: str, payload: Dict[str, Any]) -> None:
    import time

    data = _load_state_store()
    _purge_states_in(data)
    row = dict(payload)
    row["expires_at"] = int(time.time()) + _STATE_TTL_SEC
    data[state] = row
    _save_state_store(data)


def _consume_state(state: str) -> Optional[Dict[str, Any]]:
    import time

    data = _load_state_store()
    _purge_states_in(data)
    payload = data.pop(state, None)
    _save_state_store(data)
    if not payload:
        return None
    if payload.get("expires_at", 0) < int(time.time()):
        return None
    return payload


def build_oauth_start(*, user_id_hint: Optional[str] = None) -> Dict[str, Any]:
    if not configured():
        return {"success": False, "error": "discord_oauth_not_configured"}
    state = secrets.token_urlsafe(32)
    _store_state(state, {"provider": "linked_role", "user_id_hint": (user_id_hint or "").strip() or None})
    params = {
        "client_id": _client_id(),
        "redirect_uri": linked_role_redirect_uri(),
        "response_type": "code",
        "state": state,
        "scope": "role_connections.write identify",
        "prompt": "consent",
    }
    auth_url = "https://discord.com/api/oauth2/authorize?" + urllib.parse.urlencode(params)
    return {
        "success": True,
        "auth_url": auth_url,
        "state": state,
        "verification_url": linked_role_verification_url(),
        "redirect_uri": linked_role_redirect_uri(),
    }


def _exchange_code(code: str) -> Dict[str, Any]:
    body = urllib.parse.urlencode(
        {
            "client_id": _client_id(),
            "client_secret": _client_secret(),
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": linked_role_redirect_uri(),
        }
    ).encode("utf-8")
    req = urllib.request.Request(
        "https://discord.com/api/v10/oauth2/token",
        data=body,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            return {"success": True, "token": json.loads(resp.read().decode("utf-8"))}
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:300]
        return {"success": False, "error": f"token_exchange_failed:{exc.code}", "detail": detail}
    except Exception as exc:
        return {"success": False, "error": str(exc)}


def _fetch_oauth_user(access_token: str) -> Dict[str, Any]:
    req = urllib.request.Request(
        "https://discord.com/api/v10/oauth2/@me",
        headers={"Authorization": f"Bearer {access_token}"},
        method="GET",
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return {"success": True, "profile": json.loads(resp.read().decode("utf-8"))}
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:300]
        return {"success": False, "error": f"oauth_profile_failed:{exc.code}", "detail": detail}
    except Exception as exc:
        return {"success": False, "error": str(exc)}


def build_metadata_for_user(user_id: str) -> Dict[str, Any]:
    from backend.services.discord_link_service import get_discord_id_for_user, link_status

    uid = (user_id or "").strip()
    if not uid:
        return {
            "account_linked": 0,
            "mn2_balance": 0,
            "casino_vip": 0,
            "hosting_vip": 0,
        }

    status = link_status(uid)
    mn2_balance = int(float(status.get("mn2_balance") or 0))
    casino_vip = 0
    try:
        from backend.services.casino_social_service import check_vip_discord_eligibility

        casino = check_vip_discord_eligibility(uid)
        casino_vip = 1 if casino.get("eligible") else 0
    except Exception:
        casino_vip = 1 if status.get("casino_vip_eligible") else 0

    hosting_vip = 1 if status.get("hosting_vip_eligible") else 0
    account_linked = 1 if get_discord_id_for_user(uid) else 0
    return {
        "account_linked": account_linked,
        "mn2_balance": mn2_balance,
        "casino_vip": casino_vip,
        "hosting_vip": hosting_vip,
    }


def build_metadata_for_discord(discord_user_id: str) -> Dict[str, Any]:
    from backend.services.discord_link_service import get_user_id_for_discord

    user_id = get_user_id_for_discord(discord_user_id)
    if not user_id:
        return {
            "account_linked": 0,
            "mn2_balance": 0,
            "casino_vip": 0,
            "hosting_vip": 0,
        }
    meta = build_metadata_for_user(user_id)
    meta["account_linked"] = 1
    return meta


def push_role_connection(access_token: str, metadata: Dict[str, Any]) -> Dict[str, Any]:
    client_id = _client_id()
    if not client_id:
        return {"success": False, "error": "missing_client_id"}
    url = f"https://discord.com/api/v10/users/@me/applications/{client_id}/role-connection"
    body = json.dumps(
        {
            "platform_name": _PLATFORM_NAME,
            "metadata": metadata,
        }
    ).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=body,
        headers={
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        },
        method="PUT",
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            raw = resp.read().decode("utf-8")
            payload = json.loads(raw) if raw else {}
            return {"success": True, "role_connection": payload, "metadata": metadata}
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:300]
        return {"success": False, "error": f"push_metadata_failed:{exc.code}", "detail": detail}
    except Exception as exc:
        return {"success": False, "error": str(exc)}


def register_metadata_schema() -> Dict[str, Any]:
    client_id = _client_id()
    token = _bot_token()
    if not client_id or not token:
        return {"success": False, "error": "missing_discord_client_id_or_bot_token"}
    url = f"https://discord.com/api/v10/applications/{client_id}/role-connections/metadata"
    body = json.dumps(_METADATA_SCHEMA).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=body,
        headers={
            "Authorization": f"Bot {token}",
            "Content-Type": "application/json",
        },
        method="PUT",
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            raw = resp.read().decode("utf-8")
            records = json.loads(raw) if raw else []
            return {"success": True, "records": records}
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:300]
        return {"success": False, "error": f"register_schema_failed:{exc.code}", "detail": detail}
    except Exception as exc:
        return {"success": False, "error": str(exc)}


def metadata_schema() -> List[Dict[str, Any]]:
    return list(_METADATA_SCHEMA)


def handle_callback(code: str, state: str, *, user_id_hint: Optional[str] = None) -> Dict[str, Any]:
    if not configured():
        return {"success": False, "error": "discord_oauth_not_configured"}
    state_payload = _consume_state(state)
    if not state_payload or state_payload.get("provider") != "linked_role":
        return {"success": False, "error": "invalid_or_expired_state"}

    token_res = _exchange_code(code)
    if not token_res.get("success"):
        return token_res
    access_token = (token_res.get("token") or {}).get("access_token")
    if not access_token:
        return {"success": False, "error": "missing_access_token"}

    profile_res = _fetch_oauth_user(access_token)
    if not profile_res.get("success"):
        return profile_res
    profile = profile_res.get("profile") or {}
    discord_user = profile.get("user") or {}
    discord_id = str(discord_user.get("id") or "").strip()
    if not discord_id:
        return {"success": False, "error": "missing_discord_user_id"}

    hint = (user_id_hint or state_payload.get("user_id_hint") or "").strip() or None
    user_id = None
    if hint and hint != "default_user":
        try:
            from backend.services.discord_link_service import link_user

            link_user(hint, discord_id)
            user_id = hint
        except Exception:
            pass
    if not user_id:
        from backend.services.discord_link_service import get_user_id_for_discord

        user_id = get_user_id_for_discord(discord_id)

    metadata = build_metadata_for_discord(discord_id)
    push_res = push_role_connection(access_token, metadata)
    if not push_res.get("success"):
        return push_res

    return {
        "success": True,
        "discord_id": discord_id,
        "user_id": user_id,
        "metadata": metadata,
        "verification_url": linked_role_verification_url(),
    }
