"""
Social Auth Service
Unified OAuth start/callback for top providers.
"""
import base64
import hashlib
import json
import os
import secrets
import time
import urllib.parse
from typing import Dict, Optional, Tuple

import requests

_BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_STATE_TTL_SEC = 600
_state_store: Dict[str, Dict] = {}
_ALLOWED_RETURN_HOSTS = {
    "masternoder.dk",
    "www.masternoder.dk",
    "127.0.0.1",
    "localhost",
}


def _now() -> int:
    return int(time.time())


def _base_url() -> str:
    return (os.getenv("SOCIAL_AUTH_BASE_URL") or "https://masternoder.dk").rstrip("/")


def _provider_defs() -> Dict[str, Dict]:
    base = _base_url()
    return {
        "google": {
            "client_id": os.getenv("GOOGLE_CLIENT_ID"),
            "client_secret": os.getenv("GOOGLE_CLIENT_SECRET"),
            "auth_url": "https://accounts.google.com/o/oauth2/v2/auth",
            "token_url": "https://oauth2.googleapis.com/token",
            "user_url": "https://openidconnect.googleapis.com/v1/userinfo",
            "scope": "openid email profile",
            "redirect_uri": f"{base}/api/auth/google/callback",
            "revoke_url": "https://oauth2.googleapis.com/revoke",
        },
        "facebook": {
            "client_id": os.getenv("FACEBOOK_CLIENT_ID"),
            "client_secret": os.getenv("FACEBOOK_CLIENT_SECRET"),
            "auth_url": "https://www.facebook.com/v20.0/dialog/oauth",
            "token_url": "https://graph.facebook.com/v20.0/oauth/access_token",
            "user_url": "https://graph.facebook.com/me?fields=id,name,email,picture",
            "scope": "email,public_profile",
            "redirect_uri": f"{base}/api/auth/facebook/callback",
            "revoke_url": "https://graph.facebook.com/me/permissions",
        },
        "microsoft": {
            "tenant": os.getenv("MICROSOFT_TENANT_ID", "common"),
            "client_id": os.getenv("MICROSOFT_CLIENT_ID"),
            "client_secret": os.getenv("MICROSOFT_CLIENT_SECRET"),
            "auth_url": "https://login.microsoftonline.com/{tenant}/oauth2/v2.0/authorize",
            "token_url": "https://login.microsoftonline.com/{tenant}/oauth2/v2.0/token",
            "user_url": "https://graph.microsoft.com/v1.0/me",
            "scope": "openid email profile User.Read",
            "redirect_uri": f"{base}/api/auth/microsoft/callback",
        },
        "github": {
            "client_id": os.getenv("GITHUB_CLIENT_ID"),
            "client_secret": os.getenv("GITHUB_CLIENT_SECRET"),
            "auth_url": "https://github.com/login/oauth/authorize",
            "token_url": "https://github.com/login/oauth/access_token",
            "user_url": "https://api.github.com/user",
            "email_url": "https://api.github.com/user/emails",
            "scope": "read:user user:email",
            "redirect_uri": f"{base}/api/auth/github/callback",
            "revoke_url": "https://api.github.com/applications/{client_id}/grant",
        },
        "apple": {
            "client_id": os.getenv("APPLE_CLIENT_ID"),
            "client_secret": os.getenv("APPLE_CLIENT_SECRET"),
            "auth_url": "https://appleid.apple.com/auth/authorize",
            "token_url": "https://appleid.apple.com/auth/token",
            "scope": "name email",
            "redirect_uri": f"{base}/api/auth/apple/callback",
            "revoke_url": "https://appleid.apple.com/auth/revoke",
        },
    }


def list_providers() -> Dict:
    defs = _provider_defs()
    out = []
    for key, cfg in defs.items():
        out.append({
            "id": key,
            "enabled": bool(cfg.get("client_id")),
            "configured": bool(cfg.get("client_id") and cfg.get("client_secret")),
            "redirect_uri": cfg.get("redirect_uri"),
        })
    return {"success": True, "providers": out}


def _purge_states():
    t = _now()
    stale = [k for k, v in _state_store.items() if v.get("expires_at", 0) <= t]
    for k in stale:
        _state_store.pop(k, None)


def _store_state(state: str, payload: Dict):
    _purge_states()
    payload = dict(payload)
    payload["expires_at"] = _now() + _STATE_TTL_SEC
    _state_store[state] = payload


def _consume_state(state: str) -> Optional[Dict]:
    _purge_states()
    payload = _state_store.pop(state, None)
    if not payload:
        return None
    if payload.get("expires_at", 0) < _now():
        return None
    return payload


def _pkce() -> Tuple[str, str]:
    verifier = base64.urlsafe_b64encode(secrets.token_bytes(48)).decode().rstrip("=")
    challenge = hashlib.sha256(verifier.encode("utf-8")).digest()
    challenge = base64.urlsafe_b64encode(challenge).decode().rstrip("=")
    return verifier, challenge


def build_start_url(provider: str, user_id_hint: Optional[str] = None, return_url: Optional[str] = None) -> Dict:
    defs = _provider_defs()
    cfg = defs.get(provider)
    if not cfg:
        return {"success": False, "error": f"Unknown provider: {provider}"}
    if not cfg.get("client_id"):
        return {"success": False, "error": f"{provider} not configured"}

    safe_return_url = validate_return_url(return_url)
    if return_url and not safe_return_url:
        return {"success": False, "error": "Invalid return_url"}

    state = secrets.token_urlsafe(32)
    nonce = secrets.token_urlsafe(24)
    code_verifier, code_challenge = _pkce()
    _store_state(state, {
        "provider": provider,
        "nonce": nonce,
        "code_verifier": code_verifier,
        "user_id_hint": user_id_hint,
        "return_url": safe_return_url,
    })

    auth_url = cfg["auth_url"].format(tenant=cfg.get("tenant", "common"))
    params = {
        "client_id": cfg["client_id"],
        "redirect_uri": cfg["redirect_uri"],
        "response_type": "code",
        "state": state,
    }
    if cfg.get("scope"):
        params["scope"] = cfg["scope"]
    if provider in ("google", "microsoft", "apple"):
        params["nonce"] = nonce
    if provider in ("google", "microsoft", "github"):
        params["code_challenge"] = code_challenge
        params["code_challenge_method"] = "S256"
    if provider == "google":
        params["access_type"] = "offline"
        params["include_granted_scopes"] = "true"
        params["prompt"] = "consent"

    url = f"{auth_url}?{urllib.parse.urlencode(params)}"
    return {"success": True, "provider": provider, "auth_url": url}


def _exchange_token(provider: str, code: str, state_payload: Dict) -> Dict:
    cfg = _provider_defs()[provider]
    token_url = cfg["token_url"].format(tenant=cfg.get("tenant", "common"))
    data = {
        "code": code,
        "client_id": cfg["client_id"],
        "client_secret": cfg["client_secret"],
        "redirect_uri": cfg["redirect_uri"],
        "grant_type": "authorization_code",
    }
    if provider in ("google", "microsoft", "github"):
        data["code_verifier"] = state_payload.get("code_verifier")
    headers = {"Accept": "application/json"}
    r = requests.post(token_url, data=data, headers=headers, timeout=20)
    if r.status_code >= 400:
        return {"success": False, "error": f"Token exchange failed ({r.status_code})", "details": r.text[:500]}
    try:
        payload = r.json()
    except Exception:
        return {"success": False, "error": "Token exchange returned non-JSON"}
    if payload.get("error"):
        return {"success": False, "error": str(payload.get("error")), "details": payload}
    return {"success": True, "token": payload}


def _fetch_profile(provider: str, access_token: str) -> Dict:
    cfg = _provider_defs()[provider]
    headers = {"Authorization": f"Bearer {access_token}"}
    if provider == "github":
        headers["Accept"] = "application/vnd.github+json"
    if provider in ("google", "facebook", "microsoft", "github"):
        r = requests.get(cfg["user_url"], headers=headers, timeout=20)
        if r.status_code >= 400:
            return {"success": False, "error": f"Profile fetch failed ({r.status_code})", "details": r.text[:500]}
        profile = r.json()
        if provider == "github" and not profile.get("email"):
            er = requests.get(cfg["email_url"], headers=headers, timeout=20)
            if er.status_code < 400:
                emails = er.json() if isinstance(er.json(), list) else []
                primary = next((e for e in emails if e.get("primary")), None) or (emails[0] if emails else None)
                if primary:
                    profile["email"] = primary.get("email")
        if provider == "microsoft":
            profile.setdefault("email", profile.get("mail") or profile.get("userPrincipalName"))
        return {"success": True, "profile": profile}
    return {"success": False, "error": f"{provider} profile fetch not implemented"}


def _load_json(path: str) -> Dict:
    if not os.path.isfile(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _save_json(path: str, data: Dict):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def _token_store_path() -> str:
    return os.path.join(_BASE, "data", "oauth_tokens.json")


def oauth_token_storage_enabled() -> bool:
    return (os.getenv("SOCIAL_AUTH_STORE_TOKENS") or "").strip().lower() in {"1", "true", "yes", "on"}


def _sanitize_token_payload(token: Dict) -> Dict:
    allowed = {"access_token", "refresh_token", "token_type", "scope", "expires_in", "id_token"}
    return {k: v for k, v in (token or {}).items() if k in allowed and v}


def _store_oauth_token(user_id: str, provider: str, token: Dict, provider_user_id: str = "") -> None:
    if not oauth_token_storage_enabled():
        return
    path = _token_store_path()
    data = _load_json(path)
    users = data.setdefault("users", {})
    providers = users.setdefault(user_id, {})
    providers[provider] = {
        "provider_user_id": provider_user_id,
        "token": _sanitize_token_payload(token),
        "stored_at": _now(),
    }
    _save_json(path, data)


def _load_oauth_token(user_id: str, provider: str) -> Optional[Dict]:
    data = _load_json(_token_store_path())
    entry = data.get("users", {}).get(user_id, {}).get(provider)
    return entry if isinstance(entry, dict) else None


def _remove_oauth_token(user_id: str, provider: str) -> None:
    data = _load_json(_token_store_path())
    users = data.get("users", {})
    providers = users.get(user_id, {})
    if provider in providers:
        providers.pop(provider, None)
        _save_json(_token_store_path(), data)


def revoke_oauth_provider(user_id: str, provider: str) -> Dict:
    """Revoke stored OAuth tokens when token storage and provider support are available."""
    defs = _provider_defs()
    cfg = defs.get(provider)
    if not cfg:
        return {"success": False, "error": f"Unknown provider: {provider}"}
    if not oauth_token_storage_enabled():
        return {"success": False, "revocation_supported": False, "error": "OAuth token storage is disabled"}
    entry = _load_oauth_token(user_id, provider)
    token = (entry or {}).get("token") or {}
    access_token = token.get("access_token")
    refresh_token = token.get("refresh_token")
    revoke_url = cfg.get("revoke_url")
    if not entry or not revoke_url:
        return {"success": False, "revocation_supported": False, "error": "No revocable token is stored for this provider"}
    try:
        if provider == "google":
            r = requests.post(revoke_url, data={"token": refresh_token or access_token}, timeout=20)
        elif provider == "facebook":
            r = requests.delete(revoke_url, params={"access_token": access_token}, timeout=20)
        elif provider == "github":
            url = revoke_url.format(client_id=cfg.get("client_id"))
            r = requests.delete(url, auth=(cfg.get("client_id"), cfg.get("client_secret")), json={"access_token": access_token}, timeout=20)
        elif provider == "apple":
            r = requests.post(revoke_url, data={"client_id": cfg.get("client_id"), "client_secret": cfg.get("client_secret"), "token": refresh_token or access_token}, timeout=20)
        else:
            return {"success": False, "revocation_supported": False, "error": f"Revocation not implemented for {provider}"}
        if r.status_code >= 400:
            return {"success": False, "revocation_supported": True, "error": f"Provider revoke failed ({r.status_code})", "details": r.text[:300]}
        _remove_oauth_token(user_id, provider)
        return {"success": True, "revocation_supported": True, "revoked": True}
    except Exception as e:
        return {"success": False, "revocation_supported": True, "error": str(e)}


def _user_id_from_email(email: str) -> str:
    h = hashlib.md5(email.lower().encode("utf-8")).hexdigest()[:12]
    return f"user_{h}"


def _upsert_social_mapping(provider: str, provider_user_id: str, user_id: str):
    path = os.path.join(_BASE, "logs", "user_identifiers", "social_mappings.json")
    data = _load_json(path)
    key = f"{provider}:{provider_user_id}"
    data[key] = user_id
    _save_json(path, data)


def _find_user_by_social(provider: str, provider_user_id: str) -> Optional[str]:
    path = os.path.join(_BASE, "logs", "user_identifiers", "social_mappings.json")
    data = _load_json(path)
    return data.get(f"{provider}:{provider_user_id}")


def _upsert_email_mapping(email: str, user_id: str):
    path = os.path.join(_BASE, "logs", "user_identifiers", "email_mappings.json")
    data = _load_json(path)
    data[email.lower()] = user_id
    _save_json(path, data)


def _find_user_by_email(email: str) -> Optional[str]:
    path = os.path.join(_BASE, "logs", "user_identifiers", "email_mappings.json")
    data = _load_json(path)
    return data.get(email.lower())


def _normalize_social_profile(provider: str, profile: Dict) -> Dict:
    pid = str(profile.get("sub") or profile.get("id") or profile.get("user_id") or "").strip()
    email = (profile.get("email") or "").strip().lower() or None
    name = (
        profile.get("name")
        or profile.get("displayName")
        or profile.get("login")
        or profile.get("given_name")
        or profile.get("username")
        or f"{provider}_user"
    )
    avatar = profile.get("picture")
    if isinstance(avatar, dict):
        avatar = avatar.get("data", {}).get("url")
    return {"provider_user_id": pid, "email": email, "name": str(name)[:80], "avatar": avatar}


def _ensure_user_from_social(provider: str, norm: Dict, token: Optional[Dict] = None) -> Dict:
    from backend.services.user_onboarding import user_onboarding

    provider_user_id = norm.get("provider_user_id")
    if not provider_user_id:
        return {"success": False, "error": "Missing provider user id"}

    user_id = _find_user_by_social(provider, provider_user_id)
    if not user_id and norm.get("email"):
        user_id = _find_user_by_email(norm["email"])

    if not user_id:
        if norm.get("email"):
            user_id = _user_id_from_email(norm["email"])
        else:
            user_id = f"user_{provider}_{hashlib.md5(provider_user_id.encode('utf-8')).hexdigest()[:12]}"
        create_result = user_onboarding.create_new_user(
            request_data={
                "referral_source": f"oauth_{provider}",
                "preferences": {"username": norm.get("name")},
            },
            user_id=user_id,
        )
        if not create_result.get("success") and not create_result.get("existing"):
            return {"success": False, "error": create_result.get("error", "Failed to create user")}

    _upsert_social_mapping(provider, provider_user_id, user_id)
    if norm.get("email"):
        _upsert_email_mapping(norm["email"], user_id)
    _store_oauth_token(user_id, provider, token or {}, provider_user_id)

    update_data = {"username": norm.get("name")}
    profile = user_onboarding.get_user_profile(user_id) or {}
    prefs = profile.get("preferences")
    try:
        prefs_obj = json.loads(prefs) if isinstance(prefs, str) else (prefs if isinstance(prefs, dict) else {})
    except Exception:
        prefs_obj = {}
    prefs_obj["social_auth"] = {
        "provider": provider,
        "provider_user_id": provider_user_id,
        "email": norm.get("email"),
        "avatar": norm.get("avatar"),
        "linked_at": int(time.time()),
    }
    update_data["preferences"] = prefs_obj
    user_onboarding.update_user_profile(user_id, update_data)
    return {"success": True, "user_id": user_id}


def handle_callback(provider: str, code: str, state: str) -> Dict:
    defs = _provider_defs()
    if provider not in defs:
        return {"success": False, "error": f"Unknown provider: {provider}"}
    state_payload = _consume_state(state)
    if not state_payload or state_payload.get("provider") != provider:
        return {"success": False, "error": "Invalid or expired state"}
    token_res = _exchange_token(provider, code, state_payload)
    if not token_res.get("success"):
        return token_res
    access_token = token_res["token"].get("access_token")
    if not access_token:
        return {"success": False, "error": "Missing access token"}
    profile_res = _fetch_profile(provider, access_token)
    if not profile_res.get("success"):
        return profile_res
    normalized = _normalize_social_profile(provider, profile_res["profile"])
    user_res = _ensure_user_from_social(provider, normalized, token_res.get("token"))
    if not user_res.get("success"):
        return user_res
    return {
        "success": True,
        "provider": provider,
        "user_id": user_res["user_id"],
        "email": normalized.get("email"),
        "name": normalized.get("name"),
        "return_url": state_payload.get("return_url"),
    }


def validate_return_url(return_url: Optional[str]) -> Optional[str]:
    """
    Allow only safe in-app return URLs:
    - relative paths (/vidgenerator/...)
    - absolute URLs on known hosts
    """
    if not return_url:
        return None
    v = str(return_url).strip()
    if not v:
        return None
    if v.startswith("/"):
        return v
    try:
        parsed = urllib.parse.urlparse(v)
        if parsed.scheme not in ("http", "https"):
            return None
        host = (parsed.hostname or "").lower()
        if host not in _ALLOWED_RETURN_HOSTS:
            return None
        return v
    except Exception:
        return None
