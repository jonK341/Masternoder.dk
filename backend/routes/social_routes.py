"""
Social structure routes — friends, crews, activity feed, challenges.
Players interact through the game: add friends, join crews, see activity, send challenges.
"""
import os
import json
import uuid
import hashlib
from datetime import datetime
from flask import Blueprint, jsonify, request

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SOCIAL_DATA_PATH = os.path.join(BASE_DIR, "data", "social_structure.json")
SOCIAL_NETWORKS_PATH = os.path.join(BASE_DIR, "data", "social_networks.json")

social_bp = Blueprint("social", __name__)


def _default_social() -> dict:
    return {
        "friends": {},
        "crews": [],
        "user_crews": {},
        "activity_feed": [],
        "challenges": [],
        "crew_invites": [],
        "referrals": {"codes": {}, "signups": []},
        "crypto": {"claims": {}, "total_mn2_earned": 0},
        "chat_messages": [],
        "moderation": {"blocks": {}, "reports": [], "hidden_activity": {}},
        "privacy": {},
        "schema_version": 2,
        "max_activity_items": 500,
        "max_friends_per_user": 100,
        "max_crew_members": 50,
        "max_chat_messages": 500,
    }


def _ensure_social_shape(data: dict) -> dict:
    defaults = _default_social()
    if not isinstance(data, dict):
        data = {}
    for key, value in defaults.items():
        if key not in data:
            data[key] = value
    if not isinstance(data.get("referrals"), dict):
        data["referrals"] = defaults["referrals"]
    data["referrals"].setdefault("codes", {})
    data["referrals"].setdefault("signups", [])
    if not isinstance(data.get("crypto"), dict):
        data["crypto"] = defaults["crypto"]
    data["crypto"].setdefault("claims", {})
    data["crypto"].setdefault("total_mn2_earned", 0)
    if not isinstance(data.get("chat_messages"), list):
        data["chat_messages"] = []
    if not isinstance(data.get("crew_invites"), list):
        data["crew_invites"] = []
    if not isinstance(data.get("moderation"), dict):
        data["moderation"] = defaults["moderation"]
    data["moderation"].setdefault("blocks", {})
    data["moderation"].setdefault("reports", [])
    data["moderation"].setdefault("hidden_activity", {})
    if not isinstance(data.get("privacy"), dict):
        data["privacy"] = {}
    data.setdefault("schema_version", defaults["schema_version"])
    return data


def _resolve_uid() -> str:
    try:
        from backend.services.account_resolution_service import resolve_user_id
        return resolve_user_id(from_body=True, from_query=True)
    except Exception:
        return (request.get_json(silent=True) or {}).get("user_id") or request.args.get("user_id") or "default_user"


def _load_social() -> dict:
    if not os.path.exists(SOCIAL_DATA_PATH):
        return _default_social()
    with open(SOCIAL_DATA_PATH, "r", encoding="utf-8") as f:
        return _ensure_social_shape(json.load(f))


def _save_social(data: dict) -> None:
    os.makedirs(os.path.dirname(SOCIAL_DATA_PATH), exist_ok=True)
    with open(SOCIAL_DATA_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def _display_name(uid: str) -> str:
    h = int(hashlib.md5(uid.encode()).hexdigest()[:4], 16)
    nouns = ["Hunter", "Master", "Creator", "Wizard", "Noder", "Seeker", "Ranger"]
    adjectives = ["Alpha", "Prime", "Swift", "Neon", "Gold", "Elite"]
    return adjectives[h % len(adjectives)] + " " + nouns[(h // len(adjectives)) % len(nouns)]


def push_activity(user_id: str, action_type: str, label: str, extra: dict = None) -> None:
    """Append an activity item to the feed. Call from battle, star_map, etc."""
    try:
        data = _load_social()
        feed = data.get("activity_feed", [])
        feed.insert(0, {
            "id": str(uuid.uuid4())[:8],
            "user_id": user_id,
            "action_type": action_type,
            "label": label,
            "ts": datetime.utcnow().isoformat() + "Z",
            "extra": extra or {},
        })
        data["activity_feed"] = feed[: data.get("max_activity_items", 500)]
        _save_social(data)
    except Exception:
        pass


def _utc_now_iso() -> str:
    return datetime.utcnow().isoformat() + "Z"


def _referral_code_for_user(user_id: str) -> str:
    digest = hashlib.md5(str(user_id).strip().encode("utf-8")).hexdigest()[:8].upper()
    return f"MN-{digest}"


def _social_progress(social: dict, user_id: str) -> dict:
    friends = (social.get("friends") or {}).get(user_id, [])
    crew_id = (social.get("user_crews") or {}).get(user_id)
    referrals = social.get("referrals") or {}
    signups = referrals.get("signups") or []
    successful_referrals = [
        r for r in signups
        if (r.get("referrer_user_id") or "").strip() == user_id
    ]
    chat_count = sum(1 for m in social.get("chat_messages", []) if (m.get("user_id") or "") == user_id)
    activity_count = sum(1 for e in social.get("activity_feed", []) if (e.get("user_id") or "") == user_id)
    return {
        "friends": len(friends),
        "crew_membership": 1 if crew_id else 0,
        "successful_referrals": len(successful_referrals),
        "chat_messages": chat_count,
        "activity_items": activity_count,
    }


def _social_crypto_options() -> list:
    return [
        {
            "id": "signup_signal",
            "name": "Signup Signal",
            "description": "Welcome MN2 reward for connecting your social identity.",
            "reward_mn2": 0.001,
            "requires": {},
            "repeatable": False,
            "cooldown_sec": 0,
        },
        {
            "id": "first_connection",
            "name": "First Connection",
            "description": "Add your first friend and claim a small progress reward.",
            "reward_mn2": 0.0015,
            "requires": {"friends": 1},
            "repeatable": True,
            "cooldown_sec": 7 * 24 * 60 * 60,
        },
        {
            "id": "crew_node",
            "name": "Crew Node",
            "description": "Join or create a crew to activate your social node.",
            "reward_mn2": 0.002,
            "requires": {"crew_membership": 1},
            "repeatable": True,
            "cooldown_sec": 7 * 24 * 60 * 60,
        },
        {
            "id": "chat_ping",
            "name": "Chat Ping",
            "description": "Send a message in the social chat to prove network activity.",
            "reward_mn2": 0.00075,
            "requires": {"chat_messages": 1},
            "repeatable": True,
            "cooldown_sec": 24 * 60 * 60,
        },
        {
            "id": "referral_relay",
            "name": "Referral Relay",
            "description": "Earn when another user signs up with your referral code.",
            "reward_mn2": 0.003,
            "requires": {"successful_referrals": 1},
            "repeatable": True,
            "cooldown_sec": 7 * 24 * 60 * 60,
        },
    ]


def _requirements_met(option: dict, progress: dict) -> bool:
    for key, required in (option.get("requires") or {}).items():
        if float(progress.get(key, 0) or 0) < float(required or 0):
            return False
    return True


def _parse_utc_iso(value: str):
    if not value:
        return None
    try:
        return datetime.fromisoformat(str(value).replace("Z", ""))
    except Exception:
        return None


def _seconds_until(value: str) -> int:
    target = _parse_utc_iso(value)
    if not target:
        return 0
    return max(0, int((target - datetime.utcnow()).total_seconds()))


def _social_crypto_status(social: dict, user_id: str) -> dict:
    progress = _social_progress(social, user_id)
    user_claims = (social.get("crypto") or {}).get("claims", {}).get(user_id, [])
    options = []
    for option in _social_crypto_options():
        option_claims = [claim for claim in user_claims if claim.get("option_id") == option["id"]]
        last_claim = option_claims[-1] if option_claims else None
        cooldown_remaining = _seconds_until((last_claim or {}).get("next_claim_at"))
        claimed = bool(option_claims) and not option.get("repeatable")
        unlocked = _requirements_met(option, progress)
        options.append({
            **option,
            "unlocked": unlocked,
            "claimed": claimed,
            "ready": unlocked and not claimed and cooldown_remaining <= 0,
            "cooldown_remaining_sec": cooldown_remaining,
            "last_claim_at": (last_claim or {}).get("claimed_at"),
            "next_claim_at": (last_claim or {}).get("next_claim_at"),
            "claims_count": len(option_claims),
        })
    return {
        "currency": "MN2",
        "progress": progress,
        "options": options,
        "claims": user_claims[-20:],
        "total_mn2_earned": round(float((social.get("crypto") or {}).get("total_mn2_earned", 0) or 0), 8),
    }


def _award_social_mn2(user_id: str, amount: float, metadata: dict) -> dict:
    from backend.services.unified_points_database import unified_points_db

    return unified_points_db.add_points(
        user_id,
        "mn2_balance",
        amount,
        source="social_crypto_reward",
        metadata=metadata,
    )


def _challenge_target_count(challenge: dict) -> int:
    target = challenge.get("target")
    if isinstance(target, dict):
        for key in ("count", "target", "target_count"):
            try:
                value = int(target.get(key) or 0)
                if value > 0:
                    return value
            except (TypeError, ValueError):
                pass
    try:
        value = int(target or 0)
        if value > 0:
            return value
    except (TypeError, ValueError):
        pass
    return 5


def _find_challenge(social: dict, challenge_id: str) -> dict:
    return next((c for c in social.get("challenges", []) if c.get("id") == challenge_id), None)


def _profile_identity(user_id: str) -> dict:
    identity = {"display_name": _display_name(user_id), "avatar": None}
    try:
        profile_path = os.path.join(BASE_DIR, "logs", "user_profiles", f"{user_id}.json")
        if not os.path.isfile(profile_path):
            return identity
        with open(profile_path, "r", encoding="utf-8") as f:
            profile = json.load(f) or {}
        prefs = _profile_preferences(profile)
        identity["display_name"] = (
            prefs.get("display_name")
            or prefs.get("username")
            or profile.get("username")
            or identity["display_name"]
        )
        avatar = prefs.get("avatar") or prefs.get("avatar_url") or profile.get("avatar_url")
        if isinstance(avatar, str) and (avatar.startswith("http://") or avatar.startswith("https://") or avatar.startswith("/")):
            identity["avatar"] = avatar
    except Exception:
        pass
    return identity


def _is_blocked(social: dict, actor_user_id: str, target_user_id: str) -> bool:
    blocks = (social.get("moderation") or {}).get("blocks") or {}
    actor_blocks = set(blocks.get(actor_user_id, []) or [])
    target_blocks = set(blocks.get(target_user_id, []) or [])
    return target_user_id in actor_blocks or actor_user_id in target_blocks


def _user_privacy(social: dict, user_id: str) -> dict:
    defaults = {
        "profile_visibility": "public",
        "activity_visibility": "public",
        "challenge_permissions": "friends",
    }
    raw = (social.get("privacy") or {}).get(user_id) or {}
    return {**defaults, **raw}


def _member_game_signals(user_id: str) -> dict:
    signals = {"xp_total": 0, "game_points": 0, "battle_wins": 0, "starmap_secured": 0}
    try:
        from backend.services.unified_points_database import unified_points_db

        points_res = unified_points_db.get_all_points(user_id) if unified_points_db else {}
        points = points_res.get("points", {}) if isinstance(points_res, dict) else {}
        signals["xp_total"] = float(points.get("xp_total") or points.get("xp") or 0)
        signals["game_points"] = float(points.get("game_points") or 0)
    except Exception:
        pass
    try:
        from backend.routes.battle_routes import _get_battle_stats

        battle = _get_battle_stats(user_id) or {}
        signals["battle_wins"] = int(battle.get("wins") or 0)
    except Exception:
        pass
    try:
        path = os.path.join(BASE_DIR, "data", "starmap25_invasions.json")
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                inv = json.load(f)
            signals["starmap_secured"] = len(((inv.get("users") or {}).get(user_id) or {}).get("invaded_ids", []) or [])
    except Exception:
        pass
    return signals


def _crew_score(social: dict, crew: dict) -> dict:
    members = set(crew.get("member_ids") or [])
    activity = sum(1 for e in social.get("activity_feed", []) if e.get("user_id") in members)
    chat = sum(1 for m in social.get("chat_messages", []) if m.get("user_id") in members)
    referrals = sum(1 for r in (social.get("referrals") or {}).get("signups", []) if r.get("referrer_user_id") in members)
    completed_challenges = sum(
        1 for c in social.get("challenges", [])
        if c.get("status") == "completed" and (c.get("from_user_id") in members or c.get("to_user_id") in members)
    )
    member_signals = [_member_game_signals(uid) for uid in members]
    xp_total = sum(s["xp_total"] for s in member_signals)
    game_points = sum(s["game_points"] for s in member_signals)
    battle_wins = sum(s["battle_wins"] for s in member_signals)
    starmap_secured = sum(s["starmap_secured"] for s in member_signals)
    game_score = int((xp_total / 100) + (game_points / 25) + (battle_wins * 8) + (starmap_secured * 10))
    social_score = (len(members) * 10) + (activity * 2) + chat + (referrals * 15) + (completed_challenges * 12) + game_score
    return {
        "activity_items": activity,
        "chat_messages": chat,
        "referrals": referrals,
        "completed_challenges": completed_challenges,
        "xp_total": round(xp_total, 2),
        "game_points": round(game_points, 2),
        "battle_wins": battle_wins,
        "starmap_secured": starmap_secured,
        "game_score": game_score,
        "social_score": social_score,
    }


def _notification_counts(social: dict, user_id: str) -> dict:
    pending_challenges = [
        c for c in social.get("challenges", [])
        if c.get("to_user_id") == user_id and c.get("status") == "pending"
    ]
    crew_invites = [
        i for i in social.get("crew_invites", [])
        if i.get("to_user_id") == user_id and i.get("status") == "pending"
    ]
    friends = (social.get("friends") or {}).get(user_id, [])
    leaderboard = _crew_leaderboard_rows(social)
    my_crew_id = (social.get("user_crews") or {}).get(user_id)
    my_rank = next((row["rank"] for row in leaderboard if row.get("id") == my_crew_id), None)
    return {
        "pending_challenges": len(pending_challenges),
        "crew_invites": len(crew_invites),
        "friends": len(friends),
        "crew_rank": my_rank,
        "total": len(pending_challenges) + len(crew_invites),
    }


def _crew_leaderboard_rows(social: dict) -> list:
    rows = []
    for crew in social.get("crews", []):
        score = _crew_score(social, crew)
        rows.append({
            "id": crew.get("id"),
            "name": crew.get("name"),
            "created_by": crew.get("created_by"),
            "member_count": len(crew.get("member_ids", []) or []),
            **score,
        })
    rows.sort(key=lambda r: (r.get("social_score", 0), r.get("member_count", 0)), reverse=True)
    for idx, row in enumerate(rows, start=1):
        row["rank"] = idx
    return rows


def _profile_preferences(profile: dict | None) -> dict:
    if not profile:
        return {}
    raw = profile.get("preferences") or {}
    if isinstance(raw, dict):
        return dict(raw)
    if isinstance(raw, str):
        try:
            parsed = json.loads(raw)
            return parsed if isinstance(parsed, dict) else {}
        except Exception:
            return {}
    return {}


def _social_appearance_scan(social: dict, user_id: str) -> dict:
    friends = list((social.get("friends") or {}).get(user_id, []))
    crew_id = (social.get("user_crews") or {}).get(user_id)
    crew = next((c for c in social.get("crews", []) if c.get("id") == crew_id), None)
    challenges = [
        c for c in social.get("challenges", [])
        if c.get("from_user_id") == user_id or c.get("to_user_id") == user_id
    ]
    referrals = [
        r for r in (social.get("referrals") or {}).get("signups", [])
        if r.get("referrer_user_id") == user_id
    ]
    chat_messages = [m for m in social.get("chat_messages", []) if m.get("user_id") == user_id]
    activity = [a for a in social.get("activity_feed", []) if a.get("user_id") == user_id]
    claims = ((social.get("crypto") or {}).get("claims") or {}).get(user_id, [])
    invites = [
        i for i in social.get("crew_invites", [])
        if i.get("from_user_id") == user_id or i.get("to_user_id") == user_id
    ]
    crew_rank = next((row.get("rank") for row in _crew_leaderboard_rows(social) if row.get("id") == crew_id), None)
    completed_challenges = [c for c in challenges if c.get("status") == "completed"]
    pending_challenges = [c for c in challenges if c.get("status") == "pending"]
    signal_score = (
        len(friends) * 10
        + (15 if crew else 0)
        + len(completed_challenges) * 12
        + len(referrals) * 15
        + min(len(chat_messages), 50) * 2
        + min(len(activity), 100)
        + len(claims) * 4
    )
    if signal_score >= 90:
        tier = "network_anchor"
    elif signal_score >= 45:
        tier = "active_connector"
    elif signal_score >= 15:
        tier = "emerging_node"
    else:
        tier = "quiet_profile"
    badges = []
    if friends:
        badges.append("friend_network")
    if crew:
        badges.append("crew_member")
    if referrals:
        badges.append("referrer")
    if chat_messages:
        badges.append("social_chat")
    if completed_challenges:
        badges.append("challenger")
    if claims:
        badges.append("mn2_social_rewards")
    return {
        "user_id": user_id,
        "display_name": _display_name(user_id),
        "scanned_at": _utc_now_iso(),
        "tier": tier,
        "signal_score": signal_score,
        "badges": badges,
        "summary": {
            "friends_count": len(friends),
            "crew": {
                "id": crew_id,
                "name": crew.get("name") if crew else None,
                "member_count": len(crew.get("member_ids", [])) if crew else 0,
                "rank": crew_rank,
            },
            "challenges_count": len(challenges),
            "completed_challenges_count": len(completed_challenges),
            "pending_challenges_count": len(pending_challenges),
            "referrals_count": len(referrals),
            "chat_messages_count": len(chat_messages),
            "activity_items_count": len(activity),
            "reward_claims_count": len(claims),
            "crew_invites_count": len(invites),
        },
        "appearance": {
            "headline": f"{_display_name(user_id)} · {tier.replace('_', ' ').title()}",
            "profile_labels": badges[:6],
            "public_social_url": f"/game?user_id={user_id}#social",
            "referral_code": _referral_code_for_user(user_id),
        },
        "recent": {
            "activity": activity[:10],
            "chat": chat_messages[-10:],
            "challenges": challenges[-10:],
            "referrals": referrals[-10:],
            "reward_claims": claims[-10:],
        },
    }


def _sync_social_appearance_to_profile(user_id: str, scan: dict) -> dict:
    from backend.services.user_onboarding import user_onboarding

    profile = user_onboarding.get_user_profile(user_id)
    if not profile:
        created = user_onboarding.create_new_user(
            {
                "referral_source": "social_appearance_scanner",
                "preferences": {},
            },
            user_id,
        )
        if not created.get("success"):
            return created
        profile = user_onboarding.get_user_profile(user_id)
    prefs = _profile_preferences(profile)
    prefs["social_network_appearance"] = scan
    prefs["social_network_appearance_updated_at"] = scan.get("scanned_at")
    return user_onboarding.update_user_profile(user_id, {"preferences": prefs})


# ---------------------------------------------------------------------------
# Friends
# ---------------------------------------------------------------------------

@social_bp.route("/api/social/friends", methods=["GET"])
def friends_list():
    """GET ?user_id= — list current user's friends with display names."""
    try:
        user_id = _resolve_uid()
        data = _load_social()
        friend_ids = (data.get("friends") or {}).get(user_id, [])
        friends = []
        for fid in friend_ids:
            identity = _profile_identity(fid)
            friends.append({"user_id": fid, "display_name": identity["display_name"], "avatar": identity.get("avatar")})
        return jsonify({"success": True, "user_id": user_id, "friends": friends}), 200
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@social_bp.route("/api/social/friends/add", methods=["POST"])
def friends_add():
    """POST { user_id, friend_id } — add friend (mutual)."""
    try:
        data = request.get_json(silent=True) or {}
        user_id = (data.get("user_id") or _resolve_uid()).strip()
        friend_id = (data.get("friend_id") or "").strip()
        if not friend_id or friend_id == user_id:
            return jsonify({"success": False, "error": "Invalid friend_id"}), 400
        social = _load_social()
        if _is_blocked(social, user_id, friend_id):
            return jsonify({"success": False, "error": "Friend request blocked by moderation settings"}), 403
        friends = social.get("friends", {})
        if user_id not in friends:
            friends[user_id] = []
        if friend_id not in friends[user_id]:
            max_f = social.get("max_friends_per_user", 100)
            if len(friends[user_id]) >= max_f:
                return jsonify({"success": False, "error": "Max friends reached"}), 400
            friends[user_id].append(friend_id)
        if friend_id not in friends:
            friends[friend_id] = []
        if user_id not in friends[friend_id]:
            friends[friend_id].append(user_id)
        social["friends"] = friends
        _save_social(social)
        return jsonify({
            "success": True,
            "user_id": user_id,
            "friend_id": friend_id,
            "display_name": _profile_identity(friend_id)["display_name"],
        }), 200
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@social_bp.route("/api/social/friends/remove", methods=["POST"])
def friends_remove():
    """POST { user_id, friend_id } — remove friend (mutual)."""
    try:
        data = request.get_json(silent=True) or {}
        user_id = (data.get("user_id") or _resolve_uid()).strip()
        friend_id = (data.get("friend_id") or "").strip()
        if not friend_id:
            return jsonify({"success": False, "error": "friend_id required"}), 400
        social = _load_social()
        friends = social.get("friends", {})
        for uid in (user_id, friend_id):
            if uid in friends and (friend_id if uid == user_id else user_id) in friends[uid]:
                friends[uid].remove(friend_id if uid == user_id else user_id)
        social["friends"] = friends
        _save_social(social)
        return jsonify({"success": True, "user_id": user_id, "friend_id": friend_id}), 200
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


# ---------------------------------------------------------------------------
# Activity feed
# ---------------------------------------------------------------------------

@social_bp.route("/api/social/activity", methods=["GET"])
def activity_feed():
    """GET ?user_id=&limit=30&friends_only=0 — activity feed (all or friends only)."""
    try:
        user_id = _resolve_uid()
        limit = min(100, max(5, int(request.args.get("limit", 30))))
        friends_only = request.args.get("friends_only", "0").strip().lower() in ("1", "true", "yes")
        social = _load_social()
        feed = social.get("activity_feed", [])
        hidden = set(((social.get("moderation") or {}).get("hidden_activity") or {}).get(user_id, []) or [])
        blocked = set(((social.get("moderation") or {}).get("blocks") or {}).get(user_id, []) or [])
        feed = [
            e for e in feed
            if e.get("id") not in hidden and e.get("user_id") not in blocked
        ]
        if friends_only:
            friend_ids = set((social.get("friends") or {}).get(user_id, []))
            friend_ids.add(user_id)
            feed = [e for e in feed if e.get("user_id") in friend_ids]
        else:
            feed = [
                e for e in feed
                if e.get("user_id") == user_id or _user_privacy(social, e.get("user_id", "")).get("activity_visibility") == "public"
            ]
        items = []
        for e in feed[:limit]:
            identity = _profile_identity(e.get("user_id", ""))
            items.append({
                "id": e.get("id"),
                "user_id": e.get("user_id"),
                "display_name": identity["display_name"],
                "avatar": identity.get("avatar"),
                "action_type": e.get("action_type"),
                "label": e.get("label"),
                "ts": e.get("ts"),
                "extra": e.get("extra", {}),
            })
        return jsonify({
            "success": True,
            "user_id": user_id,
            "activity": items,
            "limit": limit,
        }), 200
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@social_bp.route("/api/social/activity/push", methods=["POST"])
def activity_push():
    """POST { user_id, action_type, label, extra? } — push activity (e.g. from game actions)."""
    try:
        data = request.get_json(silent=True) or {}
        user_id = (data.get("user_id") or _resolve_uid()).strip()
        action_type = (data.get("action_type") or "activity").strip()
        label = (data.get("label") or "Did something").strip()
        extra = data.get("extra") if isinstance(data.get("extra"), dict) else {}
        push_activity(user_id, action_type, label, extra)
        return jsonify({"success": True, "user_id": user_id}), 200
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


# ---------------------------------------------------------------------------
# Crews (guilds)
# ---------------------------------------------------------------------------

@social_bp.route("/api/social/crews", methods=["GET"])
def crews_list():
    """GET ?user_id= — list all crews and current user's crew."""
    try:
        user_id = _resolve_uid()
        social = _load_social()
        crews = social.get("crews", [])
        user_crews = social.get("user_crews", {})
        my_crew_id = user_crews.get(user_id)
        crew_list = []
        for c in crews:
            crew_list.append({
                "id": c.get("id"),
                "name": c.get("name"),
                "member_count": len(c.get("member_ids", [])),
                "created_by": c.get("created_by"),
                "is_member": user_id in (c.get("member_ids") or []),
                "is_mine": c.get("id") == my_crew_id,
            })
        return jsonify({
            "success": True,
            "user_id": user_id,
            "crews": crew_list,
            "my_crew_id": my_crew_id,
        }), 200
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@social_bp.route("/api/social/crews/create", methods=["POST"])
def crews_create():
    """POST { user_id, name } — create a crew (user becomes owner and only member)."""
    try:
        data = request.get_json(silent=True) or {}
        user_id = (data.get("user_id") or _resolve_uid()).strip()
        name = (data.get("name") or "New Crew").strip()[:80]
        if not name:
            return jsonify({"success": False, "error": "name required"}), 400
        social = _load_social()
        if social.get("user_crews", {}).get(user_id):
            return jsonify({"success": False, "error": "Already in a crew; leave first"}), 400
        crew_id = "crew_" + str(uuid.uuid4())[:8]
        crew = {
            "id": crew_id,
            "name": name,
            "member_ids": [user_id],
            "created_by": user_id,
            "created_at": datetime.utcnow().isoformat() + "Z",
        }
        social.setdefault("crews", []).append(crew)
        social.setdefault("user_crews", {})[user_id] = crew_id
        _save_social(social)
        push_activity(user_id, "crew_created", f"Created crew «{name}»", {"crew_id": crew_id})
        return jsonify({
            "success": True,
            "user_id": user_id,
            "crew": {"id": crew_id, "name": name, "member_count": 1},
        }), 200
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@social_bp.route("/api/social/crews/join", methods=["POST"])
def crews_join():
    """POST { user_id, crew_id } — join a crew."""
    try:
        data = request.get_json(silent=True) or {}
        user_id = (data.get("user_id") or _resolve_uid()).strip()
        crew_id = (data.get("crew_id") or "").strip()
        if not crew_id:
            return jsonify({"success": False, "error": "crew_id required"}), 400
        social = _load_social()
        if social.get("user_crews", {}).get(user_id):
            return jsonify({"success": False, "error": "Already in a crew; leave first"}), 400
        crews = social.get("crews", [])
        crew = next((c for c in crews if c.get("id") == crew_id), None)
        if not crew:
            return jsonify({"success": False, "error": "Crew not found"}), 404
        members = crew.get("member_ids", [])
        max_m = social.get("max_crew_members", 50)
        if len(members) >= max_m:
            return jsonify({"success": False, "error": "Crew is full"}), 400
        if user_id in members:
            return jsonify({"success": True, "user_id": user_id, "crew_id": crew_id}), 200
        members.append(user_id)
        crew["member_ids"] = members
        social.setdefault("user_crews", {})[user_id] = crew_id
        _save_social(social)
        push_activity(user_id, "crew_join", f"Joined crew «{crew.get('name', crew_id)}»", {"crew_id": crew_id})
        return jsonify({
            "success": True,
            "user_id": user_id,
            "crew_id": crew_id,
            "crew_name": crew.get("name"),
        }), 200
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@social_bp.route("/api/social/crews/leave", methods=["POST"])
def crews_leave():
    """POST { user_id } — leave current crew."""
    try:
        user_id = (request.get_json(silent=True) or {}).get("user_id") or _resolve_uid()
        user_id = user_id.strip()
        social = _load_social()
        crew_id = social.get("user_crews", {}).get(user_id)
        if not crew_id:
            return jsonify({"success": True, "user_id": user_id, "message": "Not in a crew"}), 200
        crews = social.get("crews", [])
        crew = next((c for c in crews if c.get("id") == crew_id), None)
        if crew:
            members = crew.get("member_ids", [])
            if user_id in members:
                members.remove(user_id)
            crew["member_ids"] = members
            if not members:
                crews[:] = [c for c in crews if c.get("id") != crew_id]
        social.get("user_crews", {}).pop(user_id, None)
        _save_social(social)
        return jsonify({"success": True, "user_id": user_id, "left_crew_id": crew_id}), 200
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@social_bp.route("/api/social/crews/leaderboard", methods=["GET"])
def crews_leaderboard():
    """GET — rank crews by members, activity, chat, referrals, and completed challenges."""
    try:
        social = _load_social()
        return jsonify({
            "success": True,
            "leaderboard": _crew_leaderboard_rows(social),
        }), 200
    except Exception as e:
        return jsonify({"success": False, "error": str(e), "leaderboard": []}), 500


@social_bp.route("/api/social/crews/invites", methods=["GET"])
def crews_invites_list():
    """GET ?user_id= — list crew invites sent to or by current user."""
    try:
        user_id = _resolve_uid()
        social = _load_social()
        invites = [
            i for i in social.get("crew_invites", [])
            if i.get("to_user_id") == user_id or i.get("from_user_id") == user_id
        ]
        for invite in invites:
            invite["from_display_name"] = _display_name(invite.get("from_user_id", ""))
            invite["to_display_name"] = _display_name(invite.get("to_user_id", ""))
        return jsonify({"success": True, "user_id": user_id, "invites": invites[-50:]}), 200
    except Exception as e:
        return jsonify({"success": False, "error": str(e), "invites": []}), 500


@social_bp.route("/api/social/crews/invite", methods=["POST"])
def crews_invite():
    """POST { user_id, to_user_id } — invite a friend to the sender's current crew."""
    try:
        data = request.get_json(silent=True) or {}
        user_id = (data.get("user_id") or _resolve_uid()).strip()
        to_user_id = (data.get("to_user_id") or "").strip()
        if not to_user_id or to_user_id == user_id:
            return jsonify({"success": False, "error": "Invalid to_user_id"}), 400
        social = _load_social()
        if _is_blocked(social, user_id, to_user_id):
            return jsonify({"success": False, "error": "Invite blocked by moderation settings"}), 403
        crew_id = (social.get("user_crews") or {}).get(user_id)
        if not crew_id:
            return jsonify({"success": False, "error": "Join or create a crew first"}), 400
        if to_user_id not in (social.get("friends") or {}).get(user_id, []):
            return jsonify({"success": False, "error": "Can only invite friends"}), 400
        if (social.get("user_crews") or {}).get(to_user_id):
            return jsonify({"success": False, "error": "User is already in a crew"}), 400
        existing = next((
            i for i in social.get("crew_invites", [])
            if i.get("crew_id") == crew_id and i.get("to_user_id") == to_user_id and i.get("status") == "pending"
        ), None)
        if existing:
            return jsonify({"success": True, "invite": existing, "message": "Invite already pending"}), 200
        crew = next((c for c in social.get("crews", []) if c.get("id") == crew_id), {})
        invite = {
            "id": "inv_" + str(uuid.uuid4())[:8],
            "crew_id": crew_id,
            "crew_name": crew.get("name"),
            "from_user_id": user_id,
            "to_user_id": to_user_id,
            "status": "pending",
            "created_at": _utc_now_iso(),
        }
        social.setdefault("crew_invites", []).append(invite)
        _save_social(social)
        push_activity(user_id, "crew_invite", f"Invited {_display_name(to_user_id)} to crew «{crew.get('name', crew_id)}»", {"invite_id": invite["id"], "crew_id": crew_id})
        return jsonify({"success": True, "invite": invite}), 200
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@social_bp.route("/api/social/crews/invites/respond", methods=["POST"])
def crews_invites_respond():
    """POST { user_id, invite_id, action } — accept or decline a crew invite."""
    try:
        data = request.get_json(silent=True) or {}
        user_id = (data.get("user_id") or _resolve_uid()).strip()
        invite_id = (data.get("invite_id") or "").strip()
        action = (data.get("action") or "").strip().lower()
        if action not in ("accept", "decline"):
            return jsonify({"success": False, "error": "action must be accept or decline"}), 400
        social = _load_social()
        invite = next((i for i in social.get("crew_invites", []) if i.get("id") == invite_id), None)
        if not invite or invite.get("to_user_id") != user_id:
            return jsonify({"success": False, "error": "Invite not found"}), 404
        if invite.get("status") != "pending":
            return jsonify({"success": False, "error": "Invite already handled", "invite": invite}), 400
        if action == "decline":
            invite["status"] = "declined"
            invite["responded_at"] = _utc_now_iso()
            _save_social(social)
            return jsonify({"success": True, "invite": invite}), 200
        if (social.get("user_crews") or {}).get(user_id):
            return jsonify({"success": False, "error": "Already in a crew; leave first"}), 400
        crew = next((c for c in social.get("crews", []) if c.get("id") == invite.get("crew_id")), None)
        if not crew:
            return jsonify({"success": False, "error": "Crew not found"}), 404
        members = crew.setdefault("member_ids", [])
        if len(members) >= int(social.get("max_crew_members", 50) or 50):
            return jsonify({"success": False, "error": "Crew is full"}), 400
        if user_id not in members:
            members.append(user_id)
        social.setdefault("user_crews", {})[user_id] = crew.get("id")
        invite["status"] = "accepted"
        invite["responded_at"] = _utc_now_iso()
        _save_social(social)
        push_activity(user_id, "crew_invite_accept", f"Accepted crew invite to «{crew.get('name', crew.get('id'))}»", {"invite_id": invite_id, "crew_id": crew.get("id")})
        return jsonify({"success": True, "invite": invite, "crew_id": crew.get("id")}), 200
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


# ---------------------------------------------------------------------------
# Challenges (lightweight: invite to compete)
# ---------------------------------------------------------------------------

@social_bp.route("/api/social/challenges", methods=["GET"])
def challenges_list():
    """GET ?user_id= — list challenges involving current user (sent or received)."""
    try:
        user_id = _resolve_uid()
        social = _load_social()
        challenges = [
            c for c in social.get("challenges", [])
            if c.get("from_user_id") == user_id or c.get("to_user_id") == user_id
        ]
        return jsonify({
            "success": True,
            "user_id": user_id,
            "challenges": challenges[:50],
        }), 200
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@social_bp.route("/api/social/challenges/send", methods=["POST"])
def challenges_send():
    """POST { user_id, to_user_id, challenge_type, target? } — send a challenge (e.g. race to 5 investigations)."""
    try:
        data = request.get_json(silent=True) or {}
        user_id = (data.get("user_id") or _resolve_uid()).strip()
        to_user_id = (data.get("to_user_id") or "").strip()
        challenge_type = (data.get("challenge_type") or "race").strip()
        target = data.get("target")
        if not to_user_id or to_user_id == user_id:
            return jsonify({"success": False, "error": "Invalid to_user_id"}), 400
        social = _load_social()
        if _is_blocked(social, user_id, to_user_id):
            return jsonify({"success": False, "error": "Challenge blocked by moderation settings"}), 403
        permissions = _user_privacy(social, to_user_id).get("challenge_permissions")
        friend_ids = (social.get("friends") or {}).get(user_id, [])
        if permissions == "none":
            return jsonify({"success": False, "error": "User is not accepting challenges"}), 403
        if permissions == "friends" and to_user_id not in friend_ids:
            return jsonify({"success": False, "error": "Can only challenge friends"}), 400
        challenge_id = "ch_" + str(uuid.uuid4())[:8]
        challenge = {
            "id": challenge_id,
            "from_user_id": user_id,
            "to_user_id": to_user_id,
            "challenge_type": challenge_type,
            "target": target,
            "status": "pending",
            "created_at": datetime.utcnow().isoformat() + "Z",
        }
        social.setdefault("challenges", []).append(challenge)
        _save_social(social)
        push_activity(user_id, "challenge_sent", f"Challenged {_display_name(to_user_id)}", {"challenge_id": challenge_id})
        return jsonify({
            "success": True,
            "challenge_id": challenge_id,
            "from_user_id": user_id,
            "to_user_id": to_user_id,
            "challenge_type": challenge_type,
        }), 200
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@social_bp.route("/api/social/challenges/<challenge_id>/<action>", methods=["POST"])
def challenges_lifecycle(challenge_id: str, action: str):
    """POST — accept, decline, cancel, or complete a challenge."""
    try:
        action = (action or "").strip().lower()
        if action not in ("accept", "decline", "cancel", "complete"):
            return jsonify({"success": False, "error": "Unsupported challenge action"}), 400
        data = request.get_json(silent=True) or {}
        user_id = (data.get("user_id") or _resolve_uid()).strip()
        social = _load_social()
        challenge = _find_challenge(social, challenge_id)
        if not challenge:
            return jsonify({"success": False, "error": "Challenge not found"}), 404
        if action in ("accept", "decline") and challenge.get("to_user_id") != user_id:
            return jsonify({"success": False, "error": "Only the recipient can respond"}), 403
        if action == "cancel" and challenge.get("from_user_id") != user_id:
            return jsonify({"success": False, "error": "Only the sender can cancel"}), 403
        if action == "complete" and user_id not in (challenge.get("from_user_id"), challenge.get("to_user_id")):
            return jsonify({"success": False, "error": "Only challenge participants can complete"}), 403
        if challenge.get("status") in ("completed", "declined", "cancelled"):
            return jsonify({"success": False, "error": "Challenge is already closed", "challenge": challenge}), 400
        now = _utc_now_iso()
        if action == "accept":
            challenge["status"] = "in_progress"
            challenge["accepted_at"] = now
            challenge.setdefault("progress", {
                challenge.get("from_user_id"): 0,
                challenge.get("to_user_id"): 0,
            })
            label = f"Accepted challenge from {_display_name(challenge.get('from_user_id', ''))}"
        elif action == "decline":
            challenge["status"] = "declined"
            challenge["declined_at"] = now
            label = f"Declined challenge from {_display_name(challenge.get('from_user_id', ''))}"
        elif action == "cancel":
            challenge["status"] = "cancelled"
            challenge["cancelled_at"] = now
            label = f"Cancelled challenge to {_display_name(challenge.get('to_user_id', ''))}"
        else:
            challenge["status"] = "completed"
            challenge["completed_at"] = now
            challenge["winner_user_id"] = data.get("winner_user_id") or user_id
            label = f"Completed challenge against {_display_name(challenge.get('to_user_id' if user_id == challenge.get('from_user_id') else 'from_user_id', ''))}"
        _save_social(social)
        push_activity(user_id, f"challenge_{action}", label, {"challenge_id": challenge_id})
        return jsonify({"success": True, "challenge": challenge}), 200
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@social_bp.route("/api/social/challenges/progress", methods=["POST"])
def challenges_progress():
    """POST { user_id, challenge_id, progress_delta? | progress_value? } — update participant progress."""
    try:
        data = request.get_json(silent=True) or {}
        user_id = (data.get("user_id") or _resolve_uid()).strip()
        challenge_id = (data.get("challenge_id") or "").strip()
        social = _load_social()
        challenge = _find_challenge(social, challenge_id)
        if not challenge:
            return jsonify({"success": False, "error": "Challenge not found"}), 404
        if user_id not in (challenge.get("from_user_id"), challenge.get("to_user_id")):
            return jsonify({"success": False, "error": "Only challenge participants can update progress"}), 403
        if challenge.get("status") not in ("in_progress", "pending"):
            return jsonify({"success": False, "error": "Challenge is not active", "challenge": challenge}), 400
        progress = challenge.setdefault("progress", {
            challenge.get("from_user_id"): 0,
            challenge.get("to_user_id"): 0,
        })
        if data.get("progress_value") is not None:
            progress[user_id] = max(0, int(data.get("progress_value") or 0))
        else:
            progress[user_id] = max(0, int(progress.get(user_id, 0) or 0) + int(data.get("progress_delta", 1) or 1))
        challenge["status"] = "in_progress"
        challenge["updated_at"] = _utc_now_iso()
        target_count = _challenge_target_count(challenge)
        if int(progress.get(user_id, 0) or 0) >= target_count:
            challenge["status"] = "completed"
            challenge["completed_at"] = _utc_now_iso()
            challenge["winner_user_id"] = user_id
        _save_social(social)
        push_activity(user_id, "challenge_progress", f"Updated challenge progress ({progress.get(user_id, 0)}/{target_count})", {"challenge_id": challenge_id})
        return jsonify({"success": True, "challenge": challenge, "target_count": target_count}), 200
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@social_bp.route("/api/social/networks", methods=["GET"])
def social_networks_list():
    """GET — list social networks for share links (X, LinkedIn, Facebook, Mastodon). Used by content pages for consistent share UI."""
    try:
        if not os.path.exists(SOCIAL_NETWORKS_PATH):
            fallback = {
                "share_base_url": "https://masternoder.dk",
                "networks": [
                    {"id": "x", "name": "X (Twitter)", "icon": "𝕏", "color": "#000000", "share_url": "https://twitter.com/intent/tweet?text={text}&url={url}&hashtags=MasterNoder,HuntersGame", "encode_text": True},
                    {"id": "linkedin", "name": "LinkedIn", "icon": "in", "color": "#0a66c2", "share_url": "https://www.linkedin.com/sharing/share-offsite/?url={url}", "encode_text": False},
                    {"id": "facebook", "name": "Facebook", "icon": "f", "color": "#1877f2", "share_url": "https://www.facebook.com/sharer/sharer.php?u={url}", "encode_text": False},
                ],
                "default_share_text": "MasterNoder — AI video generation + Hunters Game",
            }
            return jsonify({"success": True, **fallback}), 200
        with open(SOCIAL_NETWORKS_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        return jsonify({"success": True, **data}), 200
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@social_bp.route("/api/social/summary", methods=["GET"])
def social_summary():
    """GET ?user_id= — one-shot summary: friends count, crew, activity count, pending challenges."""
    try:
        user_id = _resolve_uid()
        social = _load_social()
        friends = (social.get("friends") or {}).get(user_id, [])
        my_crew_id = (social.get("user_crews") or {}).get(user_id)
        crew = next((c for c in social.get("crews", []) if c.get("id") == my_crew_id), None)
        challenges = [
            c for c in social.get("challenges", [])
            if (c.get("to_user_id") == user_id and c.get("status") == "pending")
        ]
        return jsonify({
            "success": True,
            "user_id": user_id,
            "friends_count": len(friends),
            "crew": {"id": my_crew_id, "name": crew.get("name") if crew else None, "member_count": len(crew.get("member_ids", [])) if crew else 0},
            "pending_challenges_count": len(challenges),
            "notifications": _notification_counts(social, user_id),
            "referral_code": _referral_code_for_user(user_id),
            "social_crypto": _social_crypto_status(social, user_id),
        }), 200
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@social_bp.route("/api/social/notifications", methods=["GET"])
def social_notifications():
    """GET ?user_id= — notification counters for challenges, invites, friends, and crew rank."""
    try:
        user_id = _resolve_uid()
        social = _load_social()
        pending_challenges = [
            c for c in social.get("challenges", [])
            if c.get("to_user_id") == user_id and c.get("status") == "pending"
        ]
        crew_invites = [
            i for i in social.get("crew_invites", [])
            if i.get("to_user_id") == user_id and i.get("status") == "pending"
        ]
        return jsonify({
            "success": True,
            "user_id": user_id,
            "counts": _notification_counts(social, user_id),
            "pending_challenges": pending_challenges[-20:],
            "crew_invites": crew_invites[-20:],
        }), 200
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@social_bp.route("/api/social/appearance/scan", methods=["GET", "POST"])
def social_appearance_scan():
    """Detect a user's social network appearance and optionally sync it into profile preferences."""
    try:
        user_id = _resolve_uid()
        if request.method == "POST":
            data = request.get_json(silent=True) or {}
            user_id = (data.get("user_id") or user_id).strip()
            sync_profile = data.get("sync_profile", True) is not False
        else:
            sync_profile = request.args.get("sync_profile", "1").strip().lower() not in ("0", "false", "no")
        social = _load_social()
        scan = _social_appearance_scan(social, user_id)
        sync_result = None
        if sync_profile:
            sync_result = _sync_social_appearance_to_profile(user_id, scan)
            push_activity(user_id, "social_appearance_scan", "Synced social appearance to profile", {"tier": scan.get("tier"), "signal_score": scan.get("signal_score")})
        return jsonify({
            "success": True,
            "user_id": user_id,
            "scan": scan,
            "profile_synced": bool(sync_result and sync_result.get("success")),
            "profile_sync": sync_result,
        }), 200
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@social_bp.route("/api/social/privacy", methods=["GET", "POST"])
def social_privacy():
    """GET/POST social privacy settings for profile visibility, activity visibility, and challenge permissions."""
    try:
        user_id = _resolve_uid()
        social = _load_social()
        if request.method == "GET":
            return jsonify({"success": True, "user_id": user_id, "privacy": _user_privacy(social, user_id)}), 200
        data = request.get_json(silent=True) or {}
        updates = data.get("privacy") if isinstance(data.get("privacy"), dict) else data
        current = _user_privacy(social, user_id)
        allowed = {
            "profile_visibility": {"public", "friends", "private"},
            "activity_visibility": {"public", "friends", "private"},
            "challenge_permissions": {"public", "friends", "none"},
        }
        for key, values in allowed.items():
            if key in updates and updates[key] in values:
                current[key] = updates[key]
        social.setdefault("privacy", {})[user_id] = current
        _save_social(social)
        return jsonify({"success": True, "user_id": user_id, "privacy": current}), 200
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@social_bp.route("/api/social/moderation/block", methods=["POST"])
def social_moderation_block():
    """POST { user_id, target_user_id } — block another user."""
    try:
        data = request.get_json(silent=True) or {}
        user_id = (data.get("user_id") or _resolve_uid()).strip()
        target_user_id = (data.get("target_user_id") or "").strip()
        if not target_user_id or target_user_id == user_id:
            return jsonify({"success": False, "error": "Invalid target_user_id"}), 400
        social = _load_social()
        blocks = social.setdefault("moderation", {}).setdefault("blocks", {})
        blocked = blocks.setdefault(user_id, [])
        if target_user_id not in blocked:
            blocked.append(target_user_id)
        friends = social.setdefault("friends", {})
        if target_user_id in friends.get(user_id, []):
            friends[user_id].remove(target_user_id)
        if user_id in friends.get(target_user_id, []):
            friends[target_user_id].remove(user_id)
        _save_social(social)
        return jsonify({"success": True, "user_id": user_id, "blocked_user_ids": blocked}), 200
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@social_bp.route("/api/social/moderation/unblock", methods=["POST"])
def social_moderation_unblock():
    """POST { user_id, target_user_id } — unblock another user."""
    try:
        data = request.get_json(silent=True) or {}
        user_id = (data.get("user_id") or _resolve_uid()).strip()
        target_user_id = (data.get("target_user_id") or "").strip()
        social = _load_social()
        blocked = social.setdefault("moderation", {}).setdefault("blocks", {}).setdefault(user_id, [])
        if target_user_id in blocked:
            blocked.remove(target_user_id)
        _save_social(social)
        return jsonify({"success": True, "user_id": user_id, "blocked_user_ids": blocked}), 200
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@social_bp.route("/api/social/moderation/report", methods=["POST"])
def social_moderation_report():
    """POST { user_id, target_user_id?, activity_id?, reason } — report user or content."""
    try:
        data = request.get_json(silent=True) or {}
        user_id = (data.get("user_id") or _resolve_uid()).strip()
        report = {
            "id": "rep_" + str(uuid.uuid4())[:8],
            "user_id": user_id,
            "target_user_id": (data.get("target_user_id") or "").strip() or None,
            "activity_id": (data.get("activity_id") or "").strip() or None,
            "reason": (data.get("reason") or "unspecified").strip()[:300],
            "status": "open",
            "created_at": _utc_now_iso(),
        }
        social = _load_social()
        social.setdefault("moderation", {}).setdefault("reports", []).append(report)
        _save_social(social)
        return jsonify({"success": True, "report": report}), 200
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@social_bp.route("/api/social/activity/hide", methods=["POST"])
def social_activity_hide():
    """POST { user_id, activity_id } — hide an activity item for current user."""
    try:
        data = request.get_json(silent=True) or {}
        user_id = (data.get("user_id") or _resolve_uid()).strip()
        activity_id = (data.get("activity_id") or "").strip()
        if not activity_id:
            return jsonify({"success": False, "error": "activity_id required"}), 400
        social = _load_social()
        hidden = social.setdefault("moderation", {}).setdefault("hidden_activity", {}).setdefault(user_id, [])
        if activity_id not in hidden:
            hidden.append(activity_id)
        _save_social(social)
        return jsonify({"success": True, "user_id": user_id, "hidden_activity": hidden}), 200
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@social_bp.route("/api/social/agent/status", methods=["GET"])
def social_agent_status():
    """Agent-safe read-only social status for a user."""
    try:
        user_id = _resolve_uid()
        social = _load_social()
        return jsonify({
            "success": True,
            "user_id": user_id,
            "summary": {
                **_social_progress(social, user_id),
                "notifications": _notification_counts(social, user_id),
                "privacy": _user_privacy(social, user_id),
            },
            "appearance": _social_appearance_scan(social, user_id),
            "mutates": False,
        }), 200
    except Exception as e:
        return jsonify({"success": False, "error": str(e), "mutates": False}), 500


@social_bp.route("/api/social/agent/recommendations", methods=["GET"])
def social_agent_recommendations():
    """Agent-safe read-only next-action recommendations for social growth."""
    try:
        user_id = _resolve_uid()
        social = _load_social()
        progress = _social_progress(social, user_id)
        recommendations = []
        if progress["friends"] == 0:
            recommendations.append({"id": "add_friend", "label": "Add a first friend", "reason": "Unlocks friend rewards and challenges."})
        if progress["crew_membership"] == 0:
            recommendations.append({"id": "join_crew", "label": "Join or create a crew", "reason": "Unlocks crew leaderboard and crew-node rewards."})
        if progress["chat_messages"] == 0:
            recommendations.append({"id": "send_chat", "label": "Post in social chat", "reason": "Makes the profile visible in the social graph."})
        if progress["successful_referrals"] == 0:
            recommendations.append({"id": "share_referral", "label": "Share referral link", "reason": "Starts referral relay progress."})
        return jsonify({"success": True, "user_id": user_id, "recommendations": recommendations, "mutates": False}), 200
    except Exception as e:
        return jsonify({"success": False, "error": str(e), "recommendations": [], "mutates": False}), 500


@social_bp.route("/api/social/schema", methods=["GET"])
def social_schema():
    """Database migration readiness map for the current JSON-backed social state."""
    return jsonify({
        "success": True,
        "schema_version": 2,
        "current_store": "data/social_structure.json",
        "recommended_tables": [
            {"name": "social_friends", "indexes": ["user_id", "friend_id"], "unique": ["user_id", "friend_id"]},
            {"name": "social_crews", "indexes": ["id", "created_by"]},
            {"name": "social_crew_members", "indexes": ["crew_id", "user_id"], "unique": ["crew_id", "user_id"]},
            {"name": "social_challenges", "indexes": ["from_user_id", "to_user_id", "status", "created_at"]},
            {"name": "social_activity", "indexes": ["user_id", "action_type", "ts"]},
            {"name": "social_referrals", "indexes": ["referrer_user_id", "referred_user_id", "referral_code"]},
            {"name": "social_chat_messages", "indexes": ["user_id", "created_at", "room"]},
            {"name": "social_privacy", "indexes": ["user_id"]},
            {"name": "social_moderation", "indexes": ["user_id", "target_user_id", "status"]},
        ],
    }), 200


@social_bp.route("/api/social/rewards/status", methods=["GET"])
def social_rewards_status():
    """GET ?user_id= — claimable MN2 rewards for signup, progress, referrals, and social chat."""
    try:
        user_id = _resolve_uid()
        social = _load_social()
        referrals = social.setdefault("referrals", {"codes": {}, "signups": []})
        referrals.setdefault("codes", {})[_referral_code_for_user(user_id)] = user_id
        _save_social(social)
        return jsonify({
            "success": True,
            "user_id": user_id,
            "referral_code": _referral_code_for_user(user_id),
            "referral_link": f"https://masternoder.dk/game?ref={_referral_code_for_user(user_id)}#social",
            "crypto": _social_crypto_status(social, user_id),
        }), 200
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@social_bp.route("/api/social/rewards/claim", methods=["POST"])
def social_rewards_claim():
    """POST { user_id, option_id } — claim one social MN2 reward once when requirements are met."""
    try:
        data = request.get_json(silent=True) or {}
        user_id = (data.get("user_id") or _resolve_uid()).strip()
        option_id = (data.get("option_id") or "").strip()
        social = _load_social()
        status = _social_crypto_status(social, user_id)
        option = next((o for o in status["options"] if o.get("id") == option_id), None)
        if not option:
            return jsonify({"success": False, "error": "Unknown reward option"}), 404
        if option.get("claimed"):
            return jsonify({"success": False, "error": "Reward already claimed", "crypto": status}), 400
        if not option.get("unlocked"):
            return jsonify({
                "success": False,
                "error": "Reward is locked",
                "requires": option.get("requires", {}),
                "progress": status.get("progress", {}),
            }), 400
        if not option.get("ready"):
            return jsonify({
                "success": False,
                "error": "Reward cooldown active",
                "cooldown_remaining_sec": option.get("cooldown_remaining_sec", 0),
                "crypto": status,
            }), 429
        amount = float(option.get("reward_mn2") or 0)
        next_claim_at = None
        if option.get("repeatable") and int(option.get("cooldown_sec", 0) or 0) > 0:
            import datetime as _dt

            next_claim_at = (datetime.utcnow() + _dt.timedelta(seconds=int(option.get("cooldown_sec")))).isoformat() + "Z"
        award = _award_social_mn2(user_id, amount, {
            "option_id": option_id,
            "option_name": option.get("name"),
            "progress": status.get("progress", {}),
        })
        if not award.get("success"):
            return jsonify({"success": False, "error": award.get("error", "MN2 award failed")}), 500
        claim = {
            "option_id": option_id,
            "option_name": option.get("name"),
            "amount_mn2": amount,
            "claimed_at": _utc_now_iso(),
            "next_claim_at": next_claim_at,
            "repeatable": bool(option.get("repeatable")),
            "progress": status.get("progress", {}),
        }
        crypto = social.setdefault("crypto", {"claims": {}, "total_mn2_earned": 0})
        crypto.setdefault("claims", {}).setdefault(user_id, []).append(claim)
        crypto["total_mn2_earned"] = round(float(crypto.get("total_mn2_earned", 0) or 0) + amount, 8)
        _save_social(social)
        push_activity(user_id, "social_crypto_claim", f"Claimed {amount:.8f} MN2 from {option.get('name')}", {"option_id": option_id})
        return jsonify({
            "success": True,
            "claim": claim,
            "crypto": _social_crypto_status(_load_social(), user_id),
        }), 200
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@social_bp.route("/api/social/referrals", methods=["GET"])
def social_referrals():
    """GET ?user_id= — referral code, link, and successful signup list."""
    try:
        user_id = _resolve_uid()
        social = _load_social()
        referrals = social.setdefault("referrals", {"codes": {}, "signups": []})
        code = _referral_code_for_user(user_id)
        referrals.setdefault("codes", {})[code] = user_id
        _save_social(social)
        signups = [
            r for r in referrals.get("signups", [])
            if (r.get("referrer_user_id") or "") == user_id
        ]
        return jsonify({
            "success": True,
            "user_id": user_id,
            "referral_code": code,
            "referral_link": f"https://masternoder.dk/game?ref={code}#social",
            "successful_referrals": len(signups),
            "signups": signups[-50:],
        }), 200
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@social_bp.route("/api/social/referrals/register", methods=["POST"])
def social_referrals_register():
    """POST { user_id, referral_code } — connect a signup to a referrer."""
    try:
        data = request.get_json(silent=True) or {}
        user_id = (data.get("user_id") or _resolve_uid()).strip()
        referral_code = (data.get("referral_code") or "").strip().upper()
        if not referral_code:
            return jsonify({"success": False, "error": "referral_code required"}), 400
        social = _load_social()
        referrals = social.setdefault("referrals", {"codes": {}, "signups": []})
        codes = referrals.setdefault("codes", {})
        # Codes are deterministic, so recover a missing code by scanning known social users.
        referrer_user_id = codes.get(referral_code)
        if not referrer_user_id:
            known_users = set((social.get("friends") or {}).keys())
            known_users.update(e.get("user_id") for e in social.get("activity_feed", []) if e.get("user_id"))
            known_users.update(c.get("created_by") for c in social.get("crews", []) if c.get("created_by"))
            for known in known_users:
                code = _referral_code_for_user(known)
                codes[code] = known
                if code == referral_code:
                    referrer_user_id = known
        if not referrer_user_id:
            return jsonify({"success": False, "error": "Referral code not found"}), 404
        if referrer_user_id == user_id:
            return jsonify({"success": False, "error": "Cannot refer yourself"}), 400
        existing = next((r for r in referrals.get("signups", []) if r.get("referred_user_id") == user_id), None)
        if existing:
            return jsonify({"success": True, "referral": existing, "message": "Referral already registered"}), 200
        referral = {
            "id": "ref_" + str(uuid.uuid4())[:8],
            "referrer_user_id": referrer_user_id,
            "referred_user_id": user_id,
            "referral_code": referral_code,
            "registered_at": _utc_now_iso(),
        }
        referrals.setdefault("signups", []).append(referral)
        codes[_referral_code_for_user(user_id)] = user_id
        _save_social(social)
        push_activity(user_id, "social_referral_signup", f"Joined from {_display_name(referrer_user_id)} referral", {"referral_id": referral["id"]})
        return jsonify({"success": True, "referral": referral}), 200
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@social_bp.route("/api/social/login-options", methods=["GET"])
def social_login_options():
    """GET — login choices surfaced inside the social network UI."""
    try:
        providers = []
        try:
            from backend.services.social_auth_service import list_providers

            auth_data = list_providers()
            providers = auth_data.get("providers", []) if isinstance(auth_data, dict) else []
        except Exception:
            providers = []
        options = [
            {
                "id": p.get("id"),
                "label": str(p.get("id", "")).title(),
                "enabled": bool(p.get("enabled")),
                "configured": bool(p.get("configured")),
                "start_path": f"/api/auth/{p.get('id')}/start",
            }
            for p in providers
            if p.get("id") in ("github", "google")
        ]
        options.append({
            "id": "local_profile",
            "label": "Profile session",
            "enabled": True,
            "configured": True,
            "start_path": "/profile",
        })
        return jsonify({"success": True, "options": options}), 200
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@social_bp.route("/api/social/chat/messages", methods=["GET"])
def social_chat_messages():
    """GET ?limit=50 — social network chat room messages."""
    try:
        limit = min(100, max(1, int(request.args.get("limit", 50))))
        social = _load_social()
        messages = list(social.get("chat_messages", []))[-limit:]
        for msg in messages:
            identity = _profile_identity(msg.get("user_id", ""))
            msg["display_name"] = identity["display_name"]
            msg["avatar"] = identity.get("avatar")
        return jsonify({"success": True, "messages": messages, "count": len(messages)}), 200
    except Exception as e:
        return jsonify({"success": False, "error": str(e), "messages": []}), 500


@social_bp.route("/api/social/chat/send", methods=["POST"])
def social_chat_send():
    """POST { user_id, message } — send a message to the social room and mirror it into chat history."""
    try:
        data = request.get_json(silent=True) or {}
        user_id = (data.get("user_id") or _resolve_uid()).strip()
        message = (data.get("message") or "").strip()
        if not message:
            return jsonify({"success": False, "error": "message required"}), 400
        message = message[:1000]
        social = _load_social()
        identity = _profile_identity(user_id)
        msg = {
            "id": "msg_" + str(uuid.uuid4())[:8],
            "user_id": user_id,
            "display_name": identity["display_name"],
            "avatar": identity.get("avatar"),
            "message": message,
            "created_at": _utc_now_iso(),
            "room": "social",
        }
        chat_messages = social.setdefault("chat_messages", [])
        chat_messages.append(msg)
        social["chat_messages"] = chat_messages[-int(social.get("max_chat_messages", 500) or 500):]
        _save_social(social)
        push_activity(user_id, "social_chat", "Posted in social chat", {"message_id": msg["id"]})
        try:
            from backend.routes.chat_routes import save_message

            save_message("social_room", message, identity["display_name"], is_ai=False)
        except Exception:
            pass
        return jsonify({"success": True, "message": msg}), 200
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@social_bp.route("/api/social/monitor", methods=["GET"])
def social_monitor():
    """GET — operator snapshot for all social network data."""
    try:
        social = _load_social()
        users = set()
        for uid, friend_ids in (social.get("friends") or {}).items():
            users.add(uid)
            users.update(friend_ids or [])
        for crew in social.get("crews", []):
            users.add(crew.get("created_by"))
            users.update(crew.get("member_ids") or [])
        for item in social.get("activity_feed", []):
            users.add(item.get("user_id"))
        for item in social.get("chat_messages", []):
            users.add(item.get("user_id"))
        users = {u for u in users if u}
        friend_edges = sum(len(v or []) for v in (social.get("friends") or {}).values()) // 2
        referrals = social.get("referrals") or {}
        crypto = social.get("crypto") or {}
        moderation = social.get("moderation") or {}
        claims_by_user = crypto.get("claims") or {}
        total_claims = sum(len(v or []) for v in claims_by_user.values())
        total_claimed = 0.0
        for claims in claims_by_user.values():
            for claim in claims or []:
                total_claimed += float(claim.get("amount_mn2") or 0)
        top_connectors = sorted(
            [
                {
                    "user_id": uid,
                    "display_name": _display_name(uid),
                    "friends": len(friend_ids or []),
                }
                for uid, friend_ids in (social.get("friends") or {}).items()
            ],
            key=lambda row: row["friends"],
            reverse=True,
        )[:10]
        return jsonify({
            "success": True,
            "generated_at": _utc_now_iso(),
            "totals": {
                "users": len(users),
                "friend_edges": friend_edges,
                "crews": len(social.get("crews", [])),
                "activity_items": len(social.get("activity_feed", [])),
                "challenges": len(social.get("challenges", [])),
                "pending_challenges": sum(1 for c in social.get("challenges", []) if c.get("status") == "pending"),
                "completed_challenges": sum(1 for c in social.get("challenges", []) if c.get("status") == "completed"),
                "crew_invites": len(social.get("crew_invites", [])),
                "pending_crew_invites": sum(1 for i in social.get("crew_invites", []) if i.get("status") == "pending"),
                "referral_codes": len(referrals.get("codes", {}) or {}),
                "referral_signups": len(referrals.get("signups", []) or []),
                "chat_messages": len(social.get("chat_messages", [])),
                "reward_claims": total_claims,
                "reward_mn2_claimed": round(total_claimed, 8),
                "blocked_edges": sum(len(v or []) for v in (moderation.get("blocks") or {}).values()),
                "moderation_reports": len(moderation.get("reports", []) or []),
                "privacy_profiles": len(social.get("privacy", {}) or {}),
            },
            "top_connectors": top_connectors,
            "crew_leaderboard": _crew_leaderboard_rows(social)[:25],
            "crews": social.get("crews", [])[-50:],
            "recent_activity": social.get("activity_feed", [])[:25],
            "recent_chat": social.get("chat_messages", [])[-25:],
            "recent_referrals": (referrals.get("signups", []) or [])[-25:],
            "recent_crew_invites": social.get("crew_invites", [])[-25:],
        }), 200
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500
