"""Discord Play Site — separate play surface (like /chat/) for Discord-linked users."""
from __future__ import annotations

import json
import os
import secrets
from datetime import datetime, timezone
from typing import Any, Dict, Optional

_BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_TOKENS_PATH = os.path.join(_BASE, "logs", "discord_play", "tokens.json")
_BASE_URL = (os.environ.get("BASE_URL") or "https://masternoder.dk").rstrip("/")


def _load_tokens() -> Dict[str, Any]:
    if not os.path.isfile(_TOKENS_PATH):
        return {"tokens": {}}
    try:
        with open(_TOKENS_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {"tokens": {}}
    except Exception:
        return {"tokens": {}}


def _save_tokens(data: Dict[str, Any]) -> None:
    os.makedirs(os.path.dirname(_TOKENS_PATH), exist_ok=True)
    tmp = _TOKENS_PATH + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    os.replace(tmp, _TOKENS_PATH)


def create_play_session(
    user_id: str,
    *,
    discord_id: Optional[str] = None,
    venue: str = "casino",
    currency: str = "usd",
) -> Dict[str, Any]:
    uid = (user_id or "").strip()
    if not uid:
        return {"success": False, "error": "user_id required"}
    token = secrets.token_urlsafe(24)
    data = _load_tokens()
    tokens = data.setdefault("tokens", {})
    tokens[token] = {
        "user_id": uid,
        "discord_id": discord_id,
        "venue": venue,
        "currency": currency,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "expires_at": datetime.now(timezone.utc).timestamp() + 3600,
    }
    data["tokens"] = tokens
    _save_tokens(data)
    play_url = f"{_BASE_URL}/discord-play/?token={token}&venue={venue}&currency={currency}"
    return {
        "success": True,
        "token": token,
        "play_url": play_url,
        "expires_in_sec": 3600,
        "venue": venue,
        "currency": currency,
    }


def validate_play_token(token: str) -> Dict[str, Any]:
    tok = (token or "").strip()
    if not tok:
        return {"success": False, "error": "token_required"}
    data = _load_tokens()
    row = (data.get("tokens") or {}).get(tok)
    if not row:
        return {"success": False, "error": "invalid_token"}
    if datetime.now(timezone.utc).timestamp() > float(row.get("expires_at") or 0):
        return {"success": False, "error": "expired"}
    return {"success": True, **row}


def get_play_site_config(token: Optional[str] = None) -> Dict[str, Any]:
    from backend.services.casino_uber_games_service import get_uber_catalog
    from backend.services.casino_ai_entertainment_service import list_hosts

    session = validate_play_token(token) if token else {"success": False}
    uid = session.get("user_id") if session.get("success") else None
    monetization = {}
    try:
        path = os.path.join(_BASE, "data", "casino_monetization_v13.json")
        with open(path, "r", encoding="utf-8") as f:
            monetization = json.load(f)
    except Exception:
        pass
    payments = [
        p for p in (monetization.get("payment_options") or [])
        if "discord_play" in (p.get("channels") or [])
    ]
    out: Dict[str, Any] = {
        "success": True,
        "site": "discord-play",
        "base_url": _BASE_URL,
        "session": session if session.get("success") else None,
        "uber": get_uber_catalog(venue=session.get("venue") if session.get("success") else None),
        "payment_options": payments,
        "money_makers": monetization.get("money_makers") or [],
        "main_casino_href": f"{_BASE_URL}/casino/",
    }
    if uid:
        out["ai_hosts"] = list_hosts(uid)
        try:
            from backend.services.casino_network_rewards_service import get_network_status
            out["network"] = get_network_status(uid)
        except Exception:
            pass
    return out
