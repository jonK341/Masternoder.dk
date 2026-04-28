"""
Monetization 25 levers — load levers, agent assignments, and AI recommendations.
Hooks the 25 installed monetization levers to AI and agents to drive revenue.
"""
import os
import json
from typing import Dict, List, Any, Optional

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
LEVERS_PATH = os.path.join(BASE_DIR, "data", "monetization_levers.json")
ASSIGNMENTS_PATH = os.path.join(BASE_DIR, "data", "monetization_agent_assignments.json")


def load_levers() -> List[Dict[str, Any]]:
    if not os.path.exists(LEVERS_PATH):
        return []
    try:
        with open(LEVERS_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data.get("levers", []) or []
    except Exception:
        return []


def load_assignments() -> Dict[str, Dict[str, str]]:
    """user_id -> { lever_id -> agent_id }"""
    if not os.path.exists(ASSIGNMENTS_PATH):
        return {}
    try:
        with open(ASSIGNMENTS_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data.get("assignments", {}) or {}
    except Exception:
        return {}


def save_assignments(assignments: Dict[str, Dict[str, str]]) -> None:
    os.makedirs(os.path.dirname(ASSIGNMENTS_PATH), exist_ok=True)
    with open(ASSIGNMENTS_PATH, "w", encoding="utf-8") as f:
        json.dump({"assignments": assignments}, f, indent=2)


def assign_agent_to_lever(user_id: str, lever_id: str, agent_id: str) -> Dict[str, Any]:
    levers = load_levers()
    if not any(l.get("id") == lever_id for l in levers):
        return {"success": False, "error": "Lever not found"}
    assignments = load_assignments()
    if user_id not in assignments:
        assignments[user_id] = {}
    assignments[user_id][lever_id] = agent_id
    save_assignments(assignments)
    return {"success": True, "user_id": user_id, "lever_id": lever_id, "agent_id": agent_id}


def get_levers_with_assignments(user_id: str) -> List[Dict[str, Any]]:
    levers = load_levers()
    assignments = load_assignments().get(user_id, {})
    out = []
    for lev in levers:
        entry = dict(lev)
        entry["assigned_agent"] = assignments.get(lev.get("id", ""))
        out.append(entry)
    return out


def get_ai_recommendations(user_id: str, max_levers: int = 5) -> Dict[str, Any]:
    """Use LLM to recommend which monetization levers to focus on for this user (e.g. from their points/shop behaviour)."""
    levers = load_levers()
    if not levers:
        return {"success": True, "recommendations": [], "reasoning": "No levers configured."}
    try:
        from backend.services.unified_points_database import unified_points_db
        points_data = unified_points_db.get_all_points(user_id)
        pts = (points_data or {}).get("points", points_data) if isinstance(points_data, dict) else {}
        if not pts and isinstance(points_data, dict):
            pts = points_data
        systems = pts.get("systems", {}) or {}
        game_pts = int(float(systems.get("game_points", 0) or 0))
        battle_pts = int(float(systems.get("battle_points", 0) or 0))
        coins = int(float(systems.get("coins", 0) or 0))
        level = int(pts.get("level", 1) or 1)
    except Exception:
        game_pts = battle_pts = coins = 0
        level = 1
    lever_names = [l.get("name", l.get("domain", "")) for l in levers[:15]]
    try:
        from backend.services.llm_service import complete as llm_complete
        r = llm_complete(
            prompt=(
                "A user has level %d, game_points %d, battle_points %d, coins %d. "
                "From these 25 monetization levers (first 15 shown: %s), pick exactly %d levers that would help this user make or spend money most effectively. "
                "Return strict JSON: {\"lever_names\": [\"Name1\", \"Name2\", ...], \"reasoning\": \"One short sentence why these levers.\"}"
                % (level, game_pts, battle_pts, coins, ", ".join(lever_names), min(max_levers, 5))
            ),
            system_prompt="Output strict JSON only. No markdown.",
            task_type="speed",
            max_tokens=200,
            temperature=0.6,
        )
        if r.success and r.content:
            raw = r.content.strip().strip("`").strip()
            if raw.lower().startswith("json"):
                raw = raw[4:].strip()
            parsed = json.loads(raw)
            lever_names_out = parsed.get("lever_names", [])[:max_levers]
            reasoning = parsed.get("reasoning", "")
            matched = []
            for name in lever_names_out:
                for l in levers:
                    if l.get("name") == name or l.get("domain", "").replace("_", " ") == name:
                        matched.append(l)
                        break
            return {"success": True, "recommendations": matched, "reasoning": reasoning}
    except Exception:
        pass
    fallback = levers[:max_levers]
    return {"success": True, "recommendations": fallback, "reasoning": "Default: first levers by priority."}
