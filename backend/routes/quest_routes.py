"""
Quest AI Routes — dynamic quest generation powered by DeepSeek R1 reasoning.

Endpoints:
  GET  /api/quests/daily              — get or generate today's 3 daily quests
  POST /api/quests/generate           — generate custom quest from user profile
  POST /api/quests/complete           — mark quest complete, award XP
  GET  /api/quests/active?user_id=X   — get user's active/completed quests
"""
import json
import time
import hashlib
from datetime import datetime, timezone
from flask import Blueprint, jsonify, request

quest_bp = Blueprint("quests", __name__)

# ---------------------------------------------------------------------------
# In-memory cache for daily quests (refreshes at midnight UTC)
# ---------------------------------------------------------------------------
_daily_cache: dict = {}   # {date_str: [quest, ...]}
_user_quests:  dict = {}  # {user_id: [{quest_id, title, completed, xp, ...}]}


def _today_str() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _make_quest_id(title: str, date: str) -> str:
    return hashlib.md5((title + date).encode()).hexdigest()[:10]


def _mn2_reward_for_quest(quest: dict) -> float:
    """Resolve MN2 payout for a quest (explicit field or difficulty/xp heuristic)."""
    if quest.get("mn2_reward") is not None:
        try:
            return round(float(quest["mn2_reward"]), 8)
        except (TypeError, ValueError):
            pass
    diff = (quest.get("difficulty") or "medium").strip().lower()
    by_diff = {"easy": 0.01, "medium": 0.025, "hard": 0.05}
    if diff in by_diff:
        return by_diff[diff]
    try:
        xp = int(quest.get("xp_reward") or 100)
    except (TypeError, ValueError):
        xp = 100
    return round(min(0.1, max(0.005, xp / 5000.0)), 8)


def _ensure_quest_mn2(quest: dict) -> dict:
    if quest.get("mn2_reward") is None:
        quest = dict(quest)
        quest["mn2_reward"] = _mn2_reward_for_quest(quest)
    return quest


# ---------------------------------------------------------------------------
# Quest generation helpers
# ---------------------------------------------------------------------------

def _generate_daily_quests() -> list:
    """Generate 3 daily quests using DeepSeek R1 (reason tier)."""
    today = _today_str()
    system = (
        "You are the Quest Master for MasterNoder.dk — an AI video generation platform with RPG mechanics. "
        "Generate exactly 3 unique daily quests for all users. Quests should involve platform actions: "
        "creating videos, chatting with AI, battling agents, earning points, exploring features. "
        "Return ONLY valid JSON: {\"quests\": [{\"title\": str, \"description\": str, \"objective\": str, "
        "\"xp_reward\": int, \"mn2_reward\": float, \"category\": str, \"difficulty\": \"easy|medium|hard\", "
        "\"action_type\": str, \"target_count\": int}]}"
    )
    user_msg = (
        f"Today is {today}. Generate 3 varied daily quests: one easy (50-100 XP, ~0.01 MN2), "
        "one medium (150-250 XP, ~0.025 MN2), one hard (300-500 XP, ~0.05 MN2). "
        "Mix categories: video creation, AI chat, battle, exploration, social."
    )
    try:
        from backend.services.llm_service import chat
        resp = chat(
            messages=[
                {"role": "system", "content": system},
                {"role": "user",   "content": user_msg},
            ],
            task_type="reason",
            max_tokens=800,
            temperature=0.9,
        )
        if resp.success:
            raw = resp.content.strip().lstrip("```json").lstrip("```").rstrip("```").strip()
            data = json.loads(raw)
            quests = data.get("quests") or []
            enriched = []
            for q in quests:
                q["quest_id"] = _make_quest_id(q.get("title", ""), today)
                q["date"]     = today
                enriched.append(_ensure_quest_mn2(q))
            return enriched[:3]
    except Exception:
        pass

    # Fallback quests if LLM fails
    return [
        {"quest_id": _make_quest_id("Create a Video", today), "title": "Video Creator",
         "description": "Create your first AI video of the day.",
         "objective": "Generate 1 video", "xp_reward": 75, "mn2_reward": 0.01, "category": "creation",
         "difficulty": "easy", "action_type": "create_video", "target_count": 1, "date": today},
        {"quest_id": _make_quest_id("Chat Master", today), "title": "AI Conversationalist",
         "description": "Have a meaningful chat with the AI assistant.",
         "objective": "Send 5 messages", "xp_reward": 150, "mn2_reward": 0.025, "category": "social",
         "difficulty": "medium", "action_type": "send_message", "target_count": 5, "date": today},
        {"quest_id": _make_quest_id("Battle Champion", today), "title": "Arena Champion",
         "description": "Win 3 battles in the agent arena.",
         "objective": "Win 3 battles", "xp_reward": 350, "mn2_reward": 0.05, "category": "battle",
         "difficulty": "hard", "action_type": "win_battle", "target_count": 3, "date": today},
    ]


def _generate_personal_quest(user_id: str, preferences: dict) -> dict:
    """Generate a personalised quest for a specific user using Groq (speed tier)."""
    interests = preferences.get("interests", [])
    skill_level = preferences.get("skill_level", "intermediate")
    favorite_category = preferences.get("category", "video creation")

    system = (
        "You are the Quest Master for MasterNoder.dk. Generate ONE personalised quest for this user. "
        "Return ONLY valid JSON: {\"title\": str, \"description\": str, \"objective\": str, "
        "\"xp_reward\": int, \"mn2_reward\": float, \"category\": str, \"difficulty\": str, \"action_type\": str, \"target_count\": int, "
        "\"personal_note\": str}"
    )
    user_msg = (
        f"User interests: {interests}. Skill level: {skill_level}. "
        f"Favorite area: {favorite_category}. "
        "Create an exciting quest that matches their profile. Make it creative and motivating."
    )
    try:
        from backend.services.llm_service import chat
        resp = chat(
            messages=[
                {"role": "system", "content": system},
                {"role": "user",   "content": user_msg},
            ],
            task_type="speed",
            max_tokens=400,
            temperature=0.9,
        )
        if resp.success:
            raw = resp.content.strip().lstrip("```json").lstrip("```").rstrip("```").strip()
            quest = json.loads(raw)
            quest["quest_id"]   = _make_quest_id(quest.get("title", "") + user_id, _today_str())
            quest["date"]       = _today_str()
            quest["personalised"] = True
            return _ensure_quest_mn2(quest)
    except Exception:
        pass

    return {
        "quest_id": _make_quest_id("personal" + user_id, _today_str()),
        "title": "Explorer's Challenge",
        "description": "Explore a new feature of MasterNoder today.",
        "objective": "Discover 1 new feature",
        "xp_reward": 200,
        "mn2_reward": 0.025,
        "category": favorite_category,
        "difficulty": "medium",
        "action_type": "explore",
        "target_count": 1,
        "date": _today_str(),
        "personalised": True,
    }


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@quest_bp.route("/api/quests/daily", methods=["GET"])
def daily_quests():
    """
    Get today's 3 AI-generated daily quests.
    Cached per day — same quests for all users, refreshes at midnight UTC.
    Query: ?user_id=X (optional, to include user completion status)
    """
    try:
        today = _today_str()
        if today not in _daily_cache:
            _daily_cache.clear()
            _daily_cache[today] = _generate_daily_quests()

        quests = [_ensure_quest_mn2(q) for q in _daily_cache[today]]

        # Annotate with user completion if user_id provided
        user_id = (request.args.get("user_id") or "").strip()
        if user_id and user_id in _user_quests:
            completed_ids = {uq["quest_id"] for uq in _user_quests[user_id] if uq.get("completed")}
            quests = [dict(q, completed=q["quest_id"] in completed_ids) for q in quests]

        return jsonify({
            "success": True,
            "date": today,
            "quests": quests,
            "refreshes_at": today + "T00:00:00Z (next day UTC)",
        }), 200

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@quest_bp.route("/api/quests/generate", methods=["POST"])
def generate_quest():
    """
    Generate a personalised quest for a specific user.

    Body: {
      "user_id": "X",
      "preferences": {"interests": [...], "skill_level": "...", "category": "..."}
    }
    """
    try:
        data = request.get_json(silent=True) or {}
        user_id = (data.get("user_id") or "").strip()
        prefs   = data.get("preferences") or {}

        if not user_id:
            return jsonify({"success": False, "error": "user_id required"}), 200

        # Try to enrich preferences from stored profile
        try:
            from backend.services.user_profile import user_profile
            profile = user_profile.get_profile(user_id) or {}
            if not prefs.get("interests") and profile.get("interests"):
                prefs["interests"] = profile["interests"]
        except Exception:
            pass

        quest = _generate_personal_quest(user_id, prefs)

        # Add to user's active quests
        if user_id not in _user_quests:
            _user_quests[user_id] = []
        _user_quests[user_id].append(dict(quest, completed=False, started_at=_today_str()))

        return jsonify({"success": True, "quest": quest}), 200

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@quest_bp.route("/api/quests/complete", methods=["POST"])
def complete_quest():
    """
    Mark a quest as completed and award XP.

    Body: {"user_id": "X", "quest_id": "abc123"}
    """
    try:
        data = request.get_json(silent=True) or {}
        user_id  = (data.get("user_id")  or "").strip()
        quest_id = (data.get("quest_id") or "").strip()

        if not user_id or not quest_id:
            return jsonify({"success": False, "error": "user_id and quest_id required"}), 200

        user_list = _user_quests.get(user_id) or []
        if any(uq.get("quest_id") == quest_id and uq.get("completed") for uq in user_list):
            return jsonify({"success": False, "error": "Quest already completed"}), 200

        # Find the quest (daily or personal)
        today   = _today_str()
        all_q   = (_daily_cache.get(today) or []) + (_user_quests.get(user_id) or [])
        quest   = next((q for q in all_q if q.get("quest_id") == quest_id), None)

        if not quest:
            return jsonify({"success": False, "error": "Quest not found"}), 200

        quest = _ensure_quest_mn2(quest)
        xp_reward = quest.get("xp_reward", 100)
        mn2_reward = _mn2_reward_for_quest(quest)

        # Award XP
        awarded = False
        try:
            from backend.services.unified_points_database import unified_points_db
            unified_points_db.add_points(user_id, xp_reward, "quest_complete", quest.get("title", "Quest"))
            awarded = True
        except Exception:
            pass

        mn2_awarded = 0.0
        mn2_credited = False
        if mn2_reward > 0:
            try:
                from backend.services.unified_points_database import unified_points_db
                from backend.services.mn2_ledger import append_entry

                meta = {
                    "quest_id": quest_id,
                    "quest_title": quest.get("title"),
                    "xp_reward": xp_reward,
                    "difficulty": quest.get("difficulty"),
                }
                result = unified_points_db.add_points(
                    user_id,
                    "mn2_balance",
                    mn2_reward,
                    source="quest_complete",
                    metadata=meta,
                )
                if result.get("success", True):
                    mn2_credited = True
                    mn2_awarded = mn2_reward
                    try:
                        append_entry(
                            user_id=user_id,
                            entry_type="quest_reward",
                            amount=mn2_reward,
                            metadata=meta,
                        )
                    except Exception:
                        pass
            except Exception:
                pass
        try:
            from backend.services.unified_points_sync import unified_points_sync_device
            unified_points_sync_device.record_domain_sync('quests')
        except Exception:
            pass

        # Agent skill trigger (analytics_agent or assigned agent)
        try:
            from backend.services.agent_db_service import agent_db_service
            from backend.services.user_agent_skills import user_agent_skills
            skills_data = user_agent_skills.get_user_skills(user_id)
            assigned = skills_data.get('assigned_agents', [])
            target = next((a for a in assigned if 'analytics' in a or 'learning' in a), assigned[0] if assigned else None)
            if target:
                agent_db_service.record_agent_activity(
                    user_id=user_id, agent_id=target,
                    action='skill_execution', skill='track_metrics',
                    xp_gained=15, points_gained=float(xp_reward),
                    metadata={'quest_id': quest_id, 'quest_title': quest.get('title', '')},
                )
                user_agent_skills.level_up_skill(user_id, 'track_metrics', experience=15)
        except Exception:
            pass

        # Mark completed in user's quest list
        if user_id not in _user_quests:
            _user_quests[user_id] = []
        existing = next((uq for uq in _user_quests[user_id] if uq.get("quest_id") == quest_id), None)
        if existing:
            existing["completed"]    = True
            existing["completed_at"] = _today_str()
        else:
            _user_quests[user_id].append(dict(quest, completed=True, completed_at=_today_str()))

        # AI celebration message
        celebration = ""
        try:
            from backend.services.llm_service import chat
            resp = chat(
                messages=[{"role": "user", "content":
                    f"The player just completed the quest '{quest.get('title')}' and earned {xp_reward} XP! "
                    "Write ONE short (max 15 words) celebratory message. Be enthusiastic and epic."}],
                task_type="speed",
                max_tokens=40,
                temperature=1.0,
            )
            if resp.success:
                celebration = resp.content.strip().strip('"')
        except Exception:
            pass

        celebration_msg = celebration or f"Quest complete! +{xp_reward} XP!"
        if mn2_credited and mn2_awarded > 0:
            celebration_msg += f" +{mn2_awarded:.4f} MN2"

        return jsonify({
            "success": True,
            "quest_id": quest_id,
            "quest_title": quest.get("title"),
            "xp_awarded": xp_reward if awarded else 0,
            "xp_reward": xp_reward,
            "mn2_reward": mn2_reward,
            "mn2_awarded": mn2_awarded if mn2_credited else 0,
            "mn2_credited": mn2_credited,
            "celebration": celebration_msg,
            "points_awarded": awarded,
        }), 200

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@quest_bp.route("/api/quests/active", methods=["GET"])
def active_quests():
    """
    Get all active + completed quests for a user.
    Query: ?user_id=X
    """
    try:
        user_id = (request.args.get("user_id") or "").strip()
        if not user_id:
            return jsonify({"success": False, "error": "user_id required"}), 200

        today  = _today_str()
        daily  = _daily_cache.get(today) or []
        personal = [q for q in (_user_quests.get(user_id) or []) if q.get("personalised")]

        completed_ids = {uq["quest_id"] for uq in (_user_quests.get(user_id) or []) if uq.get("completed")}

        all_quests = [dict(q, completed=q["quest_id"] in completed_ids) for q in daily] + personal

        total_xp_available = sum(q.get("xp_reward", 0) for q in all_quests if not q.get("completed"))
        total_xp_earned    = sum(q.get("xp_reward", 0) for q in all_quests if q.get("completed"))

        return jsonify({
            "success": True,
            "user_id": user_id,
            "date": today,
            "quests": all_quests,
            "stats": {
                "total": len(all_quests),
                "completed": len(completed_ids),
                "xp_earned_today": total_xp_earned,
                "xp_available": total_xp_available,
            },
        }), 200

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500
