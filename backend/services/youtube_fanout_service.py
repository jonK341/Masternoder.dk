"""YouTube integration — community queue, subscribe rewards, status."""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Any, Dict, Optional

_BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_CONFIG_PATH = os.path.join(_BASE, "data", "social_platform_fanout_config.json")
_STATE_DIR = os.path.join(_BASE, "logs", "youtube_subscribers")
_CLAIMS_PATH = os.path.join(_STATE_DIR, "subscribe_claims.json")
_BASE_URL = (os.environ.get("BASE_URL") or "https://masternoder.dk").rstrip("/")


def _load_config() -> Dict[str, Any]:
    if not os.path.isfile(_CONFIG_PATH):
        return {}
    try:
        with open(_CONFIG_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def get_youtube_status(*, user_id: Optional[str] = None) -> Dict[str, Any]:
    cfg = _load_config()
    yt = cfg.get("platforms", {}).get("youtube", {})
    rewards = cfg.get("referral_rewards", {})
    claimed = False
    if user_id:
        try:
            if os.path.isfile(_CLAIMS_PATH):
                with open(_CLAIMS_PATH, "r", encoding="utf-8") as f:
                    claims = json.load(f)
                claimed = user_id in (claims.get("users") or {})
        except Exception:
            pass
    return {
        "success": True,
        "channel_url": yt.get("channel_url") or "https://www.youtube.com/@masternoder",
        "discovery_rotator": yt.get("discovery_rotator") or [],
        "subscribe_reward_mn2": float(rewards.get("youtube_subscribe_mn2") or 0.01),
        "subscribe_claimed": claimed,
        "api_configured": bool((os.environ.get("YOUTUBE_API_KEY") or "").strip()),
        "embed_ctas": [
            {"label": "Casino clips", "url": f"{_BASE_URL}/casino/?tab=social"},
            {"label": "Podcast hub", "url": f"{_BASE_URL}/podcast/"},
            {"label": "Camgirls studio", "url": f"{_BASE_URL}/camgirls/"},
        ],
    }


def claim_subscribe_reward(user_id: str) -> Dict[str, Any]:
    uid = (user_id or "").strip()
    if not uid or uid == "default_user":
        return {"success": False, "error": "user_id required"}
    cfg = _load_config()
    amount = float((cfg.get("referral_rewards") or {}).get("youtube_subscribe_mn2") or 0.01)
    os.makedirs(_STATE_DIR, exist_ok=True)
    claims: Dict[str, Any] = {"users": {}}
    if os.path.isfile(_CLAIMS_PATH):
        try:
            with open(_CLAIMS_PATH, "r", encoding="utf-8") as f:
                claims = json.load(f)
        except Exception:
            pass
    users = claims.setdefault("users", {})
    if uid in users:
        return {"success": False, "error": "already_claimed"}
    try:
        from backend.services.unified_points_database import unified_points_db

        unified_points_db.add_points(uid, "mn2_balance", amount, source="youtube_subscribe", metadata={"platform": "youtube"})
    except Exception as exc:
        return {"success": False, "error": str(exc)}
    users[uid] = {"claimed_at": datetime.now(timezone.utc).isoformat(), "mn2": amount}
    tmp = _CLAIMS_PATH + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(claims, f, indent=2)
    os.replace(tmp, _CLAIMS_PATH)
    return {"success": True, "granted_mn2": amount, "message": "Subscribe reward credited — verify you follow our channel."}
