"""Casino social hub — friends, feed, challenges, crew board (wraps platform social)."""
from __future__ import annotations

import json
import os
from typing import Any, Dict, List, Optional

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_CONFIG_PATH = os.path.join(_ROOT, "data", "casino_social_config.json")
_NETWORKS_PATH = os.path.join(_ROOT, "data", "social_networks.json")


def _load_config() -> Dict[str, Any]:
    if not os.path.isfile(_CONFIG_PATH):
        return {}
    try:
        with open(_CONFIG_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _casino_feed_match(action_type: str, extra: Optional[Dict[str, Any]] = None) -> bool:
    at = (action_type or "").strip().lower()
    cfg = _load_config()
    prefixes = cfg.get("feed_action_prefixes") or ["casino_"]
    if any(at.startswith(p) for p in prefixes):
        return True
    if at in ("challenge_sent", "challenge_accepted", "challenge_completed"):
        extra = extra or {}
        ct = (extra.get("challenge_type") or extra.get("challenge_id") or "")
        if isinstance(ct, str) and ct.startswith("casino_"):
            return True
    if (extra or {}).get("channel") == "casino":
        return True
    return False


def push_casino_activity(
    user_id: str,
    action_type: str,
    label: str,
    extra: Optional[Dict[str, Any]] = None,
) -> None:
    """Append casino-tagged item to the global social activity feed."""
    try:
        from backend.routes.social_routes import push_activity

        payload = dict(extra or {})
        payload.setdefault("channel", "casino")
        at = action_type if action_type.startswith("casino_") else f"casino_{action_type}"
        push_activity(user_id, at, label, payload)
    except Exception:
        pass


def push_casino_bet_activity(
    user_id: str,
    game: str,
    outcome: str,
    net: float,
    payout: float,
    currency: str,
    jackpot_award: Optional[Dict[str, Any]] = None,
) -> None:
    if jackpot_award:
        amt = jackpot_award.get("amount") or jackpot_award.get("award") or payout
        push_casino_activity(
            user_id,
            "casino_jackpot",
            f"Jackpot hit on {game} ({currency.upper()})",
            {"game": game, "currency": currency, "amount": amt, "outcome": outcome},
        )
        return
    if outcome in ("win", "jackpot", "payout") and net > 0:
        push_casino_activity(
            user_id,
            "casino_win",
            f"Won {game} (+{net} {currency})",
            {"game": game, "currency": currency, "net": net, "payout": payout},
        )


def _friend_ids(user_id: str) -> List[str]:
    try:
        from backend.routes.social_routes import _load_social

        social = _load_social()
        return list((social.get("friends") or {}).get(user_id, []) or [])
    except Exception:
        return []


def _display_name(user_id: str) -> str:
    try:
        from backend.routes.social_routes import _display_name as dn

        return dn(user_id)
    except Exception:
        return user_id[:12]


def get_casino_feed(
    user_id: str,
    *,
    friends_only: bool = False,
    limit: int = 30,
) -> Dict[str, Any]:
    limit = max(1, min(int(limit or 30), 100))
    try:
        from backend.routes.social_routes import _load_social

        social = _load_social()
        feed = social.get("activity_feed") or []
        peers = set(_friend_ids(user_id))
        peers.add(user_id)
        rows: List[Dict[str, Any]] = []
        for item in feed:
            if not isinstance(item, dict):
                continue
            uid = item.get("user_id") or ""
            extra = item.get("extra") if isinstance(item.get("extra"), dict) else {}
            if not _casino_feed_match(item.get("action_type") or "", extra):
                continue
            if friends_only and uid not in peers:
                continue
            rows.append({
                "id": item.get("id"),
                "user_id": uid,
                "display_name": _display_name(uid),
                "action_type": item.get("action_type"),
                "label": item.get("label"),
                "ts": item.get("ts"),
                "extra": extra,
            })
            if len(rows) >= limit:
                break
        return {
            "success": True,
            "user_id": user_id,
            "friends_only": friends_only,
            "feed": rows,
        }
    except Exception as exc:
        return {"success": False, "error": str(exc)}


def get_casino_social_hub(user_id: str, *, period: str = "today") -> Dict[str, Any]:
    cfg = _load_config()
    friends = _friend_ids(user_id)
    friend_rows = [
        {"user_id": fid, "display_name": _display_name(fid)}
        for fid in friends[:100]
    ]
    summary: Dict[str, Any] = {}
    crews: List[Dict[str, Any]] = []
    challenges: List[Dict[str, Any]] = []
    try:
        from backend.routes.social_routes import _load_social

        social = _load_social()
        my_crew_id = (social.get("user_crews") or {}).get(user_id)
        crew = next((c for c in social.get("crews", []) if c.get("id") == my_crew_id), None)
        pending = [
            c for c in social.get("challenges", [])
            if c.get("to_user_id") == user_id and c.get("status") == "pending"
        ]
        challenges = [
            c for c in social.get("challenges", [])
            if c.get("from_user_id") == user_id or c.get("to_user_id") == user_id
        ][:30]
        crews = [
            {
                "id": c.get("id"),
                "name": c.get("name"),
                "member_count": len(c.get("member_ids") or []),
                "is_mine": c.get("id") == my_crew_id,
            }
            for c in (social.get("crews") or [])[:40]
        ]
        summary = {
            "friends_count": len(friends),
            "crew": {
                "id": my_crew_id,
                "name": crew.get("name") if crew else None,
                "member_count": len(crew.get("member_ids", [])) if crew else 0,
            },
            "pending_challenges_count": len(pending),
        }
    except Exception:
        summary = {"friends_count": len(friends), "crew": None, "pending_challenges_count": 0}

    from backend.services import casino_service

    mini_board = casino_service.get_social_mini_board(
        user_id, period=period, limit=8, currency="coins",
    )
    feed = get_casino_feed(user_id, friends_only=False, limit=25)
    share_networks: Dict[str, Any] = {}
    try:
        if os.path.isfile(_NETWORKS_PATH):
            with open(_NETWORKS_PATH, "r", encoding="utf-8") as f:
                share_networks = json.load(f)
    except Exception:
        pass
    try:
        from backend.services.casino_social_service import get_preferences

        share_prefs = get_preferences(user_id)
    except Exception:
        share_prefs = {"share_wins": False}

    return {
        "success": True,
        "user_id": user_id,
        "summary": summary,
        "friends": friend_rows,
        "crews": crews,
        "challenges": challenges,
        "feed": feed.get("feed") or [],
        "mini_board": mini_board.get("leaderboard") or [],
        "peer_count": mini_board.get("peer_count") or len(friends),
        "challenge_types": cfg.get("challenge_types") or [],
        "share_networks": share_networks,
        "share_prefs": share_prefs,
        "share_default_text": cfg.get("share_default_text") or "",
    }


def send_casino_challenge(
    user_id: str,
    to_user_id: str,
    challenge_type: str,
    target: Optional[int] = None,
) -> Dict[str, Any]:
    cfg = _load_config()
    allowed = {row.get("id") for row in (cfg.get("challenge_types") or []) if row.get("id")}
    ct = (challenge_type or "").strip()
    if ct not in allowed:
        return {"success": False, "error": "invalid_challenge_type"}
    if not to_user_id or to_user_id == user_id:
        return {"success": False, "error": "invalid_to_user_id"}
    if to_user_id not in _friend_ids(user_id):
        return {"success": False, "error": "friends_only"}
    if target is None:
        for row in cfg.get("challenge_types") or []:
            if row.get("id") == ct:
                target = int(row.get("default_target") or 5)
                break
    try:
        import uuid
        from datetime import datetime

        from backend.routes.social_routes import _load_social, _save_social, push_activity

        social = _load_social()
        challenge_id = "ch_" + str(uuid.uuid4())[:8]
        challenge = {
            "id": challenge_id,
            "from_user_id": user_id,
            "to_user_id": to_user_id,
            "challenge_type": ct,
            "target": target,
            "status": "pending",
            "created_at": datetime.utcnow().isoformat() + "Z",
            "channel": "casino",
        }
        social.setdefault("challenges", []).append(challenge)
        _save_social(social)
        push_activity(
            user_id,
            "challenge_sent",
            f"Casino challenge: {_display_name(to_user_id)}",
            {"challenge_id": challenge_id, "challenge_type": ct, "channel": "casino"},
        )
        return {"success": True, "challenge": challenge}
    except Exception as exc:
        return {"success": False, "error": str(exc)}


def build_win_share_url(user_id: str, game: str, net: float, currency: str) -> Dict[str, Any]:
    from backend.services.casino_social_service import anonymize_user, may_share_win

    cfg = _load_config()
    base = "https://masternoder.dk/casino/?tab=social"
    text = (
        f"{anonymize_user(user_id)} just won at {game} "
        f"(+{net} {currency}) on MasterNoder Casino!"
    )
    return {
        "success": True,
        "share_ok": may_share_win(user_id),
        "share_url": base,
        "share_text": text,
        "default_share_text": cfg.get("share_default_text") or text,
    }
