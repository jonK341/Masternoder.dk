"""
AI User Controller & Account Builder
Full AI management of user accounts:
- Welcome + onboarding guidance via LLM
- Auto-assigns starter quests, achievements, notifications
- Monitors activity and generates personalized recommendations
- AI-driven engagement nudges (streak reminders, quest suggestions)
- Profiles users based on behavior and adapts experience
- AI Account Builder: auto-provisions, levels up, assigns skills, boosts accounts
- AI Account Health: detects gaps and auto-repairs accounts
- AI Control Panel: master dashboard with AI-managed account state
"""
import os
import json
import random
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List

_BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

SYSTEM_PROMPT = (
    "You are the AI Controller for MasterNoder.dk — a gamified learning and video generation platform. "
    "Users earn XP, coins, trophies, and achievements. They can battle agents, study communication psychology theories, "
    "read compendium rulebooks, generate videos, and complete daily quests. "
    "Speak concisely (2-4 sentences max). Be encouraging but not patronizing. "
    "Use the user's data to give specific, actionable advice."
)


def _llm_call(prompt: str, max_tokens: int = 200, timeout: int = 10) -> Optional[str]:
    """Call LLM with system prompt. Returns None on failure or timeout."""
    try:
        from backend.services.llm_service import chat, is_available
        if not is_available():
            return None
        result = chat(
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            temperature=0.7,
            max_tokens=max_tokens,
            timeout=timeout,
            task_type="speed",
        )
        if result.success and result.content:
            return result.content.strip()
    except Exception:
        pass
    return None


def _get_engagement(user_id: str):
    try:
        from backend.services import user_engagement as eng
        return eng
    except Exception:
        return None


# ==================== NEW USER ONBOARDING ====================

def onboard_new_user(user_id: str, username: str = "") -> Dict[str, Any]:
    """
    Full AI-driven onboarding for a new user.
    1. Records login streak
    2. Initializes quests
    3. Sends welcome notification
    4. Generates AI welcome message
    5. Checks initial achievements
    6. Creates starter favorites
    """
    eng = _get_engagement(user_id)
    results = {"success": True, "user_id": user_id, "actions": []}

    # 1. Record first login
    if eng:
        try:
            eng.record_login(user_id)
            results["actions"].append("login_streak_started")
        except Exception:
            pass

    # 2. Initialize daily quests
    if eng:
        try:
            eng.get_quests(user_id)
            results["actions"].append("quests_initialized")
        except Exception:
            pass

    # 3. Welcome notification
    if eng:
        try:
            eng.add_notification(
                user_id,
                title="Welcome to MasterNoder!",
                message=f"Hey {username or 'Hunter'}! Your adventure begins now. Complete daily quests to earn XP and coins. Start with the Compendium to learn the rules.",
                category="welcome",
                metadata={"type": "onboarding"},
            )
            results["actions"].append("welcome_notification_sent")
        except Exception:
            pass

    # 4. AI welcome message
    display_name = username or user_id
    ai_welcome = _llm_call(
        f"Generate a short, exciting welcome message for new user '{display_name}' joining MasterNoder. "
        f"Mention they can: generate videos, battle agents, study psychology theories, read the compendium, and earn trophies. "
        f"End with a specific first action suggestion."
    )
    if ai_welcome:
        results["ai_welcome"] = ai_welcome
        if eng:
            try:
                eng.add_notification(user_id, title="Your AI Guide", message=ai_welcome, category="ai_guide",
                                     metadata={"type": "ai_welcome"})
            except Exception:
                pass
        results["actions"].append("ai_welcome_generated")
    else:
        results["ai_welcome"] = (
            f"Welcome to MasterNoder, {display_name}! Your journey starts here. "
            "Try generating your first video or reading the Compendium to earn XP."
        )

    # 5. Check achievements (might unlock "first login" type)
    if eng:
        try:
            eng.check_achievements(user_id)
            results["actions"].append("achievements_checked")
        except Exception:
            pass

    # 6. Default settings
    if eng:
        try:
            eng.get_settings(user_id)
            results["actions"].append("settings_initialized")
        except Exception:
            pass

    return results


# ==================== AI ACTIVITY ANALYSIS ====================

def analyze_user_activity(user_id: str) -> Dict[str, Any]:
    """
    AI analyzes user's current state and generates personalized recommendations.
    Pulls data from all systems and uses LLM to create actionable advice.
    """
    # Gather user data
    user_data = _gather_user_state(user_id)

    prompt = (
        f"Analyze this user's current state and give 3 specific recommendations:\n"
        f"- Level: {user_data.get('level', 1)}, XP: {user_data.get('xp', 0)}, Coins: {user_data.get('coins', 0)}\n"
        f"- Login streak: {user_data.get('streak', 0)} days\n"
        f"- Battles: {user_data.get('battles', 0)}, Trophies: {user_data.get('trophies', 0)}\n"
        f"- Theories studied: {user_data.get('theories', 0)}/25\n"
        f"- Compendium pages read: {user_data.get('compendium_read', 0)}/25\n"
        f"- Quests completed today: {user_data.get('quests_done', 0)}\n"
        f"- Achievements: {user_data.get('achievements', 0)}/{user_data.get('achievements_total', 20)}\n"
        f"What should they focus on next? Be specific and encouraging."
    )
    ai_advice = _llm_call(prompt, max_tokens=300)

    return {
        "success": True,
        "user_id": user_id,
        "user_state": user_data,
        "ai_recommendations": ai_advice or _fallback_recommendations(user_data),
        "generated_at": datetime.utcnow().isoformat(),
    }


def _gather_user_state(user_id: str) -> Dict[str, Any]:
    state = {"level": 1, "xp": 0, "coins": 0, "streak": 0, "battles": 0,
             "trophies": 0, "theories": 0, "compendium_read": 0, "quests_done": 0,
             "achievements": 0, "achievements_total": 20}
    try:
        from backend.services.user_account_summary import get_points, get_game_progress
        pts = get_points(user_id)
        game = get_game_progress(user_id)
        state["level"] = game.get("current_level", 1)
        state["xp"] = pts.get("xp_total", 0)
        state["coins"] = pts.get("coins", 0)
        state["battles"] = pts.get("battle_points", 0)
        state["trophies"] = pts.get("trophies_collected", 0)
        state["theories"] = int(pts.get("communication_psychology_points", 0) / 15) if pts.get("communication_psychology_points") else 0
    except Exception:
        pass

    eng = _get_engagement(user_id)
    if eng:
        try:
            streak = eng.get_streak(user_id)
            state["streak"] = streak.get("current_streak", 0)
        except Exception:
            pass
        try:
            comp = eng.get_compendium_progress(user_id)
            state["compendium_read"] = comp.get("total_read", 0)
        except Exception:
            pass
        try:
            quests = eng.get_quests(user_id)
            done = sum(1 for q in quests.get("quests", []) if q.get("completed"))
            state["quests_done"] = done
        except Exception:
            pass
        try:
            achs = eng.get_achievements(user_id)
            state["achievements"] = achs.get("total_unlocked", 0)
            state["achievements_total"] = achs.get("total_available", 20)
        except Exception:
            pass
    return state


def _fallback_recommendations(data: Dict) -> str:
    recs = []
    if data.get("streak", 0) < 3:
        recs.append("Log in daily to build your streak — bonus XP at 3 and 7 days!")
    if data.get("compendium_read", 0) < 5:
        recs.append("Read some Compendium pages to unlock the Scholar achievement.")
    if data.get("battles", 0) == 0:
        recs.append("Try your first battle to earn battle points and unlock the First Blood achievement.")
    if data.get("quests_done", 0) == 0:
        recs.append("Check your daily quests — completing them gives bonus XP and coins.")
    if data.get("theories", 0) == 0:
        recs.append("Study a communication psychology theory to start your psychology journey.")
    if not recs:
        recs.append("Keep going! You're making great progress across the board.")
    return " ".join(recs[:3])


# ==================== AI ENGAGEMENT NUDGES ====================

def generate_engagement_nudge(user_id: str) -> Dict[str, Any]:
    """
    Generate a contextual engagement nudge based on what the user hasn't done recently.
    Called periodically or on page load.
    """
    eng = _get_engagement(user_id)
    state = _gather_user_state(user_id)
    nudge_type = "general"
    nudge_message = ""

    # Priority nudges based on gaps
    if state.get("streak", 0) == 0:
        nudge_type = "streak"
        nudge_message = "Start your login streak today! Log in daily for bonus XP rewards."
    elif state.get("quests_done", 0) == 0:
        nudge_type = "quest"
        nudge_message = "You have uncompleted daily quests. Complete them before reset for bonus rewards!"
    elif state.get("compendium_read", 0) < 3:
        nudge_type = "compendium"
        nudge_message = "The Compendium has 25 pages of knowledge. Read a few to earn compendium points!"
    elif state.get("battles", 0) == 0:
        nudge_type = "battle"
        nudge_message = "You haven't tried battles yet. Challenge an AI opponent for battle points!"
    elif state.get("theories", 0) < 5:
        nudge_type = "study"
        nudge_message = "Study communication psychology theories to unlock achievements and earn points."
    else:
        ai_nudge = _llm_call(
            f"The user has level {state.get('level')}, {state.get('xp')} XP, streak of {state.get('streak')} days, "
            f"and {state.get('achievements')}/{state.get('achievements_total')} achievements. "
            f"Give one short motivational nudge about what to do next.",
            max_tokens=100,
        )
        nudge_message = ai_nudge or "Great progress! Check your quests for today's challenges."
        nudge_type = "ai_generated"

    return {
        "success": True,
        "user_id": user_id,
        "nudge_type": nudge_type,
        "message": nudge_message,
    }


# ==================== AI QUEST SUGGESTIONS ====================

def suggest_next_actions(user_id: str, count: int = 3) -> Dict[str, Any]:
    """AI suggests specific next actions based on user state."""
    state = _gather_user_state(user_id)
    actions = []

    if state.get("quests_done", 0) < 5:
        actions.append({"action": "complete_quest", "label": "Complete a daily quest", "priority": "high", "path": "/api/user/quests"})
    if state.get("streak", 0) > 0 and state.get("streak", 0) < 7:
        actions.append({"action": "maintain_streak", "label": f"Keep your {state['streak']}-day streak alive!", "priority": "high", "path": "/api/user/streak"})
    if state.get("compendium_read", 0) < 25:
        next_page = state.get("compendium_read", 0) + 1
        path = f"/compendium/page-{next_page}.html" if next_page <= 10 else "/compendium/"
        actions.append({"action": "read_compendium", "label": f"Read Compendium page {next_page}", "priority": "medium", "path": path})
    if state.get("theories", 0) < 25:
        actions.append({"action": "study_theory", "label": "Study a new theory", "priority": "medium", "path": "/api/communication-psychology/theories"})
    if state.get("battles", 0) < 10:
        actions.append({"action": "battle", "label": "Fight a quick battle", "priority": "medium", "path": "/api/battle/quick"})
    if state.get("achievements", 0) < state.get("achievements_total", 20):
        actions.append({"action": "check_achievements", "label": "Check for new achievements", "priority": "low", "path": "/api/user/achievements/check"})

    actions.append({"action": "generate_video", "label": "Generate a video", "priority": "medium", "path": "/vidgenerator/generator/"})

    return {
        "success": True,
        "user_id": user_id,
        "suggested_actions": actions[:count],
        "total_available": len(actions),
    }


# ==================== AI USER PROFILING ====================

def profile_user(user_id: str) -> Dict[str, Any]:
    """
    AI builds a behavioral profile of the user:
    - Player archetype (explorer, achiever, socializer, competitor)
    - Engagement level (new, casual, active, power user)
    - Preferred activities
    - Risk of churn
    """
    state = _gather_user_state(user_id)

    # Determine engagement level
    xp = state.get("xp", 0)
    streak = state.get("streak", 0)
    if xp == 0 and streak == 0:
        engagement = "new"
    elif xp < 200 and streak < 3:
        engagement = "casual"
    elif xp < 1000 and streak < 7:
        engagement = "active"
    else:
        engagement = "power_user"

    # Determine archetype from activity distribution
    activities = {
        "explorer": state.get("compendium_read", 0) + state.get("theories", 0),
        "achiever": state.get("achievements", 0) + state.get("trophies", 0),
        "competitor": state.get("battles", 0),
        "creator": int(state.get("xp", 0) * 0.1),
    }
    archetype = max(activities, key=activities.get) if any(v > 0 for v in activities.values()) else "explorer"

    # Churn risk
    if streak == 0 and xp > 0:
        churn_risk = "high"
    elif streak < 3:
        churn_risk = "medium"
    else:
        churn_risk = "low"

    # AI personality summary (short timeout to avoid 502 on slow LLM)
    ai_profile = _llm_call(
        f"Create a brief 1-sentence personality profile for a user who is: "
        f"Level {state.get('level')}, {engagement} engagement, '{archetype}' archetype, "
        f"{state.get('streak')} day streak, {state.get('theories')}/25 theories studied, "
        f"{state.get('compendium_read')}/25 pages read, {state.get('battles')} battle points.",
        max_tokens=80,
        timeout=8,
    )

    return {
        "success": True,
        "user_id": user_id,
        "profile": {
            "engagement_level": engagement,
            "archetype": archetype,
            "churn_risk": churn_risk,
            "activity_scores": activities,
            "ai_summary": ai_profile or f"A {engagement} {archetype} with {'strong' if churn_risk == 'low' else 'room for'} engagement.",
        },
        "state": state,
    }


# ==================== AI HOOK INTO USER CREATION ====================

def on_user_created(user_id: str, username: str = "") -> Dict[str, Any]:
    """
    Master hook called after a new user is created.
    Triggers the full AI onboarding pipeline.
    """
    return onboard_new_user(user_id, username)


def on_user_activity(user_id: str, activity_type: str, metadata: Optional[Dict] = None) -> Dict[str, Any]:
    """
    Hook called on any user activity (generation, battle, study, etc.).
    Updates quests, checks achievements, and may generate nudges.
    """
    eng = _get_engagement(user_id)
    results = {"user_id": user_id, "activity": activity_type, "updates": []}

    if not eng:
        return results

    # Record login streak
    try:
        eng.record_login(user_id)
    except Exception:
        pass

    # Map activity to quest progress
    quest_map = {
        "video_generated": "generate_video",
        "theory_studied": "study_theory",
        "battle_completed": "win_battle",
        "compendium_read": "read_compendium",
        "xp_earned": "earn_xp",
    }
    quest_id = quest_map.get(activity_type)
    if quest_id:
        try:
            increment = (metadata or {}).get("amount", 1)
            result = eng.update_quest_progress(user_id, quest_id, increment)
            if result.get("completed"):
                results["updates"].append(f"Quest '{quest_id}' completed!")
                eng.add_notification(user_id, title="Quest Complete!", message=f"You completed the '{quest_id}' quest. Claim your reward!",
                                     category="quest", metadata={"quest_id": quest_id})
        except Exception:
            pass

    # Check achievements
    try:
        ach_result = eng.check_achievements(user_id)
        newly = ach_result.get("newly_unlocked", [])
        if newly:
            results["updates"].append(f"Achievements unlocked: {', '.join(newly)}")
    except Exception:
        pass

    return results


# ========================================================================
#  AI ACCOUNT BUILDER — actively builds up and manages user accounts
# ========================================================================

def _get_full_summary(user_id: str) -> Dict[str, Any]:
    """Fetch full account summary — single source of truth for AI decisions."""
    try:
        from backend.services.user_account_summary import get_full_account_summary
        return get_full_account_summary(user_id)
    except Exception:
        return {"user_id": user_id}


def _award_points(user_id: str, point_type: str, amount: float, source: str = "ai_controller"):
    try:
        from backend.services.unified_points_database import unified_points_db
        if unified_points_db:
            unified_points_db.add_points(user_id, point_type, amount, source=source)
            return True
    except Exception:
        pass
    return False


def account_health_check(user_id: str) -> Dict[str, Any]:
    """
    AI diagnoses the health of a user account.
    Detects missing features, gaps in data, stale engagement, and returns
    a prioritised repair plan.
    """
    summary = _get_full_summary(user_id)
    state = _gather_user_state(user_id)
    issues: List[Dict[str, Any]] = []
    repairs_available: List[Dict[str, Any]] = []

    # --- Profile completeness ---
    profile = summary.get("profile") or {}
    if not profile or not profile.get("username") or profile.get("username") == user_id:
        issues.append({"area": "profile", "severity": "high", "detail": "No username set"})
        repairs_available.append({"action": "set_username", "label": "Set a display name"})
    if not profile.get("onboarding_complete"):
        issues.append({"area": "onboarding", "severity": "high", "detail": "Onboarding incomplete"})
        repairs_available.append({"action": "complete_onboarding", "label": "Complete onboarding"})

    # --- Points health ---
    pts = summary.get("points") or {}
    if pts.get("xp_total", 0) == 0:
        issues.append({"area": "xp", "severity": "medium", "detail": "Zero XP"})
        repairs_available.append({"action": "award_starter_xp", "label": "Award starter XP"})
    if pts.get("coins", 0) == 0:
        issues.append({"area": "coins", "severity": "medium", "detail": "Zero coins"})
        repairs_available.append({"action": "award_starter_coins", "label": "Award starter coins"})

    # --- Engagement gaps ---
    if state.get("streak", 0) == 0:
        issues.append({"area": "streak", "severity": "low", "detail": "No active login streak"})
        repairs_available.append({"action": "record_login", "label": "Activate login streak"})
    quests = summary.get("quests") or {}
    if quests.get("completed_today", 0) == 0:
        issues.append({"area": "quests", "severity": "low", "detail": "No quests completed today"})
    achs = summary.get("achievements") or {}
    if achs.get("total_unlocked", 0) == 0:
        issues.append({"area": "achievements", "severity": "low", "detail": "No achievements unlocked"})
        repairs_available.append({"action": "check_achievements", "label": "Scan for achievable badges"})

    # --- Agent/skill gaps ---
    agents_assigned = 0
    try:
        from backend.services.user_agent_skills import user_agent_skills
        skills = user_agent_skills.get_user_skills(user_id) or {}
        agents_assigned = len(skills.get("assigned_agents", []))
    except Exception:
        pass
    if agents_assigned == 0:
        issues.append({"area": "agents", "severity": "high", "detail": "No agents assigned"})
        repairs_available.append({"action": "provision_agents", "label": "Assign full agent package"})

    # --- Battle / clan gaps ---
    battle = summary.get("battle") or {}
    if battle.get("total_battles", 0) == 0:
        issues.append({"area": "battle", "severity": "low", "detail": "No battles attempted"})
    clan = summary.get("battle", {}).get("clan")
    if not clan:
        repairs_available.append({"action": "join_clan", "label": "Auto-join first clan"})

    # --- Notifications ---
    notif = summary.get("notifications") or {}
    if notif.get("total", 0) == 0:
        issues.append({"area": "notifications", "severity": "low", "detail": "Empty notification inbox"})
        repairs_available.append({"action": "send_welcome_notification", "label": "Send welcome notification"})

    # Score
    max_score = 100
    deductions = sum({"high": 15, "medium": 8, "low": 3}.get(i["severity"], 0) for i in issues)
    health_score = max(0, max_score - deductions)

    return {
        "success": True,
        "user_id": user_id,
        "health_score": health_score,
        "health_grade": "A" if health_score >= 90 else "B" if health_score >= 75 else "C" if health_score >= 50 else "D",
        "total_issues": len(issues),
        "issues": issues,
        "repairs_available": repairs_available,
    }


def auto_repair_account(user_id: str) -> Dict[str, Any]:
    """
    AI automatically repairs all detectable account gaps.
    Runs health check, then executes every available repair action.
    """
    health = account_health_check(user_id)
    repairs = health.get("repairs_available", [])
    executed: List[str] = []
    eng = _get_engagement(user_id)

    for repair in repairs:
        action = repair["action"]
        try:
            if action == "award_starter_xp":
                _award_points(user_id, "xp_points", 100, source="ai_auto_repair")
                executed.append("Awarded 100 starter XP")

            elif action == "award_starter_coins":
                _award_points(user_id, "coins", 5.5, source="ai_auto_repair")
                executed.append("Awarded 5.5 starter coins")

            elif action == "record_login":
                if eng:
                    eng.record_login(user_id)
                    executed.append("Login streak activated")

            elif action == "check_achievements":
                if eng:
                    result = eng.check_achievements(user_id)
                    newly = result.get("newly_unlocked", [])
                    executed.append(f"Achievements scanned — unlocked {len(newly)}")

            elif action == "provision_agents":
                try:
                    from backend.services.user_onboarding import user_onboarding
                    prov = user_onboarding.provision_user_features(user_id)
                    executed.append(f"Full agent package provisioned (success={prov.get('success')})")
                except Exception as e:
                    executed.append(f"Agent provisioning attempted: {str(e)[:60]}")

            elif action == "complete_onboarding":
                try:
                    from backend.services.user_onboarding import user_onboarding
                    user_onboarding.update_user_profile(user_id, {"onboarding_complete": True})
                    executed.append("Onboarding marked complete")
                except Exception:
                    pass

            elif action == "join_clan":
                try:
                    from backend.routes.battle_routes import _BATTLE_CLANS
                    if _BATTLE_CLANS:
                        clan = _BATTLE_CLANS[0]
                        if user_id not in clan.get("members", []):
                            clan["members"].append(user_id)
                        executed.append(f"Joined clan '{clan.get('name', clan.get('id'))}'")
                except Exception:
                    pass

            elif action == "send_welcome_notification":
                if eng:
                    eng.add_notification(user_id, title="Welcome to MasterNoder!",
                                         message="Your AI Guide is ready. Check your quests and start earning!",
                                         category="ai_guide", metadata={"type": "auto_repair"})
                    executed.append("Welcome notification sent")

            elif action == "set_username":
                executed.append("Username needs manual input (skipped)")

        except Exception:
            pass

    # Re-check after repairs
    new_health = account_health_check(user_id)

    return {
        "success": True,
        "user_id": user_id,
        "repairs_executed": executed,
        "total_repairs": len(executed),
        "health_before": health["health_score"],
        "health_after": new_health["health_score"],
        "remaining_issues": new_health["total_issues"],
    }


def ai_build_account(user_id: str, username: str = "") -> Dict[str, Any]:
    """
    Master AI account builder. Executes a full build-up sequence:
    1. Ensure profile exists and is complete
    2. Provision all agents, skills, battle enrollment
    3. Award starter points (XP, coins)
    4. Initialise engagement (streak, quests, settings)
    5. Run onboarding pipeline (AI welcome, notifications)
    6. Check achievements
    7. Auto-repair any remaining gaps
    8. Generate AI strategy for the account
    """
    result = {
        "success": True,
        "user_id": user_id,
        "build_steps": [],
    }

    # 1. Ensure profile
    profile_exists = False
    try:
        from backend.services.user_onboarding import user_onboarding
        profile = user_onboarding.get_user_profile(user_id)
        if not profile:
            create_result = user_onboarding.create_new_user({
                "user_agent": "AI Account Builder",
                "ip_address": "127.0.0.1",
                "preferences": {"username": username} if username else {},
            }, user_id)
            result["build_steps"].append({"step": "create_profile", "success": create_result.get("success", False)})
            profile_exists = create_result.get("success", False)
        else:
            profile_exists = True
            result["build_steps"].append({"step": "profile_exists", "success": True})
    except Exception as e:
        result["build_steps"].append({"step": "create_profile", "success": False, "error": str(e)[:80]})

    # 2. Provision agents + skills + battle
    try:
        from backend.services.user_onboarding import user_onboarding
        prov = user_onboarding.provision_user_features(user_id)
        result["build_steps"].append({
            "step": "provision_features",
            "success": prov.get("success", False),
            "agents_granted": bool(prov.get("full_agent_access")),
            "clan": prov.get("battle_enrollment", {}).get("clan"),
            "tournament": prov.get("battle_enrollment", {}).get("tournament"),
        })
    except Exception as e:
        result["build_steps"].append({"step": "provision_features", "success": False, "error": str(e)[:80]})

    # 3. Award starter points
    points_awarded = {}
    starter_points = {
        "xp_points": 100,
        "coins": 5.5,
        "activity_points": 25,
        "knowledge_points": 10,
    }
    for ptype, amount in starter_points.items():
        if _award_points(user_id, ptype, amount, source="ai_account_builder"):
            points_awarded[ptype] = amount
    result["build_steps"].append({"step": "award_starter_points", "success": bool(points_awarded), "points": points_awarded})

    # 4. Initialise engagement
    eng = _get_engagement(user_id)
    if eng:
        try:
            eng.record_login(user_id)
            eng.get_quests(user_id)
            eng.get_settings(user_id)
            result["build_steps"].append({"step": "init_engagement", "success": True})
        except Exception:
            result["build_steps"].append({"step": "init_engagement", "success": False})

    # 5. AI onboarding
    onboard = onboard_new_user(user_id, username)
    result["build_steps"].append({"step": "ai_onboarding", "success": True, "actions": onboard.get("actions", [])})
    result["ai_welcome"] = onboard.get("ai_welcome", "")

    # 6. Achievements
    if eng:
        try:
            ach = eng.check_achievements(user_id)
            result["build_steps"].append({"step": "check_achievements", "success": True, "newly_unlocked": ach.get("newly_unlocked", [])})
        except Exception:
            pass

    # 7. Auto-repair remaining gaps
    repair = auto_repair_account(user_id)
    result["build_steps"].append({"step": "auto_repair", "repairs": repair.get("total_repairs", 0), "health_after": repair.get("health_after", 0)})

    # 8. AI strategy
    state = _gather_user_state(user_id)
    ai_strategy = _llm_call(
        f"A new account was just fully built up for user '{username or user_id}'. "
        f"They now have Level {state.get('level')}, {state.get('xp')} XP, {state.get('coins')} coins, "
        f"all agents assigned, battle enrollment active. "
        f"Create a 3-step 'first day' strategy for them to maximise progression. "
        f"Be specific with actions they should take.",
        max_tokens=200,
        timeout=8,
    )
    result["ai_strategy"] = ai_strategy or (
        "Step 1: Read Compendium pages 1-3 for quick XP. "
        "Step 2: Complete your daily quests for coin rewards. "
        "Step 3: Fight a quick battle to unlock the First Blood achievement."
    )

    # Final health score
    final_health = account_health_check(user_id)
    result["health_score"] = final_health["health_score"]
    result["health_grade"] = final_health["health_grade"]

    return result


def ai_boost_account(user_id: str, boost_type: str = "balanced") -> Dict[str, Any]:
    """
    AI applies a strategic boost to the account.
    boost_type: 'balanced' | 'xp' | 'coins' | 'battle' | 'knowledge' | 'social'
    """
    state = _gather_user_state(user_id)
    eng = _get_engagement(user_id)
    boosts_applied: List[str] = []

    boost_tables = {
        "balanced": {"xp_points": 50, "coins": 2.0, "activity_points": 15, "knowledge_points": 10},
        "xp": {"xp_points": 150, "activity_points": 30},
        "coins": {"coins": 10.0},
        "battle": {"battle_points": 30, "xp_points": 25},
        "knowledge": {"knowledge_points": 50, "communication_psychology_points": 20, "compendium_points": 15},
        "social": {"social_points": 40, "activity_points": 20},
    }
    table = boost_tables.get(boost_type, boost_tables["balanced"])

    for ptype, amount in table.items():
        if _award_points(user_id, ptype, amount, source=f"ai_boost_{boost_type}"):
            boosts_applied.append(f"+{amount} {ptype}")

    # Engagement rewards for the boost
    if eng:
        try:
            eng.add_notification(
                user_id,
                title=f"AI Boost Applied: {boost_type.title()}",
                message=f"Your AI Guide applied a {boost_type} boost! " + ", ".join(boosts_applied[:3]),
                category="ai_boost",
                metadata={"boost_type": boost_type},
            )
        except Exception:
            pass
        try:
            eng.check_achievements(user_id)
        except Exception:
            pass

    new_state = _gather_user_state(user_id)

    return {
        "success": True,
        "user_id": user_id,
        "boost_type": boost_type,
        "boosts_applied": boosts_applied,
        "state_before": state,
        "state_after": new_state,
    }


def ai_manage_skills(user_id: str) -> Dict[str, Any]:
    """
    AI reviews and manages agent skill assignments for the user.
    - Ensures full agent access
    - Recommends skill focus based on archetype
    - Levels up weak skills
    """
    result = {"success": True, "user_id": user_id, "actions": []}

    # Ensure full agent access
    try:
        from backend.services.user_agent_skills import user_agent_skills
        skills = user_agent_skills.get_user_skills(user_id) or {}
        agent_count = len(skills.get("assigned_agents", []))

        if agent_count == 0:
            try:
                from backend.services.user_onboarding import user_onboarding
                prov = user_onboarding.provision_user_features(user_id)
                result["actions"].append(f"Provisioned full agent access (success={prov.get('success')})")
                skills = user_agent_skills.get_user_skills(user_id) or {}
                agent_count = len(skills.get("assigned_agents", []))
            except Exception as e:
                result["actions"].append(f"Provision attempted: {str(e)[:60]}")

        result["total_agents"] = agent_count
        result["total_skills"] = len(skills.get("skills", []))

        # Get stats
        try:
            stats = user_agent_skills.get_skill_stats(user_id) or {}
            result["skill_stats"] = {
                "total_skills": stats.get("total_skills", 0),
                "average_level": stats.get("average_level", 0),
                "highest_level": stats.get("highest_level", 0),
            }
        except Exception:
            pass

        # AI recommends skills
        try:
            recs = user_agent_skills.recommend_skills(user_id) or {}
            result["ai_recommendations"] = recs.get("recommendations", [])[:5]
            result["actions"].append(f"Generated {len(result.get('ai_recommendations', []))} skill recommendations")
        except Exception:
            pass

    except Exception as e:
        result["actions"].append(f"Skill management error: {str(e)[:80]}")

    return result


def ai_level_up(user_id: str) -> Dict[str, Any]:
    """
    AI actively awards XP and progression.
    Decides how much XP to award based on current state.
    Triggers level-up if threshold met.
    """
    state = _gather_user_state(user_id)
    current_level = state.get("level", 1)
    current_xp = state.get("xp", 0)
    eng = _get_engagement(user_id)

    # AI decides reward based on engagement
    streak = state.get("streak", 0)
    quests_done = state.get("quests_done", 0)
    base_xp = 50
    bonus = 0
    reasons = []

    if streak >= 7:
        bonus += 30
        reasons.append(f"7+ day streak bonus (+30)")
    elif streak >= 3:
        bonus += 15
        reasons.append(f"3+ day streak bonus (+15)")
    if quests_done >= 3:
        bonus += 20
        reasons.append(f"Quest completion bonus (+20)")
    if state.get("compendium_read", 0) >= 10:
        bonus += 15
        reasons.append(f"Scholar bonus (+15)")
    if state.get("battles", 0) > 0:
        bonus += 10
        reasons.append(f"Battle veteran bonus (+10)")

    total_xp = base_xp + bonus
    _award_points(user_id, "xp_points", total_xp, source="ai_level_up")
    reasons.insert(0, f"Base XP award (+{base_xp})")

    new_state = _gather_user_state(user_id)
    leveled_up = new_state.get("level", 1) > current_level

    if leveled_up and eng:
        try:
            eng.add_notification(
                user_id,
                title=f"Level Up! You're now Level {new_state['level']}!",
                message=f"Your AI Guide awarded you {total_xp} XP. Keep progressing!",
                category="level_up",
                metadata={"level": new_state["level"], "xp_awarded": total_xp},
            )
        except Exception:
            pass

    return {
        "success": True,
        "user_id": user_id,
        "xp_awarded": total_xp,
        "reasons": reasons,
        "level_before": current_level,
        "level_after": new_state.get("level", current_level),
        "leveled_up": leveled_up,
        "total_xp": new_state.get("xp", 0),
    }


def ai_control_panel(user_id: str) -> Dict[str, Any]:
    """
    Master AI control panel for a user account.
    Returns the full AI-managed view: health, profile, state, strategy,
    available actions, and AI assessment.
    """
    state = _gather_user_state(user_id)
    health = account_health_check(user_id)
    profile_data = profile_user(user_id)

    # Available AI actions with descriptions
    actions = [
        {"action": "build", "label": "Full Account Build-Up", "description": "Create/rebuild the entire account from scratch with all features", "method": "POST", "path": "/api/user/ai/build"},
        {"action": "repair", "label": "Auto-Repair Account", "description": "Fix all detected issues automatically", "method": "POST", "path": "/api/user/ai/repair"},
        {"action": "boost", "label": "Apply AI Boost", "description": "Award strategic point boosts", "method": "POST", "path": "/api/user/ai/boost"},
        {"action": "level_up", "label": "AI Level-Up", "description": "Award XP based on engagement", "method": "POST", "path": "/api/user/ai/level-up"},
        {"action": "manage_skills", "label": "Manage Agent Skills", "description": "Review and optimise skill assignments", "method": "POST", "path": "/api/user/ai/manage-skills"},
        {"action": "analyze", "label": "Activity Analysis", "description": "AI analyzes activity and gives recommendations", "method": "GET", "path": "/api/user/ai/analyze"},
        {"action": "nudge", "label": "Engagement Nudge", "description": "Get a contextual motivation message", "method": "GET", "path": "/api/user/ai/nudge"},
        {"action": "next_actions", "label": "Suggested Actions", "description": "Get prioritised next steps", "method": "GET", "path": "/api/user/ai/next-actions"},
        {"action": "profile", "label": "AI Profile", "description": "Behavioral profiling and archetype", "method": "GET", "path": "/api/user/ai/profile"},
    ]

    # AI assessment (fast, no LLM)
    grade = health["health_grade"]
    archetype = profile_data.get("profile", {}).get("archetype", "explorer")
    engagement = profile_data.get("profile", {}).get("engagement_level", "new")
    churn = profile_data.get("profile", {}).get("churn_risk", "unknown")

    assessment = (
        f"Account grade {grade} | {engagement.title()} {archetype.title()} | "
        f"Churn risk: {churn} | {health['total_issues']} issues detected | "
        f"Level {state.get('level', 1)} with {state.get('xp', 0)} XP"
    )

    return {
        "success": True,
        "user_id": user_id,
        "ai_assessment": assessment,
        "health": {
            "score": health["health_score"],
            "grade": health["health_grade"],
            "issues": health["total_issues"],
            "repairs_available": len(health.get("repairs_available", [])),
        },
        "profile": profile_data.get("profile", {}),
        "state": state,
        "available_actions": actions,
        "managed_by": "AI User Controller v2",
    }
