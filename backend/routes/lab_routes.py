"""
Lab research progression (catalog-driven unlocks + unified points) + co-created technologies.
"""
import json
import os
import re
import uuid
from datetime import datetime, timedelta, timezone
from flask import Blueprint, jsonify, request
from sqlalchemy import text

try:
    from src.db.models import db
except ImportError:
    try:
        from vidgenerator.src.db.models import db
    except ImportError:
        db = None

lab_bp = Blueprint("lab", __name__)

_BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_DATA_DIR = os.path.join(_BASE_DIR, "data")
_LAB_V2_RULEBOOK_FILE = "rulebook_lab_v2.json"
_AGENT_KNOWLEDGE_FILE = "agent_learning_knowledge.json"
_LAB_CATALOG_CACHE: list = []
_LAB_CATALOG_MTIME: float = 0.0


def _load_data_json(filename: str):
    path = os.path.join(_DATA_DIR, filename)
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def _load_lab_catalog() -> list:
    global _LAB_CATALOG_CACHE, _LAB_CATALOG_MTIME
    path = os.path.join(_DATA_DIR, "lab_progression_catalog.json")
    try:
        mtime = os.path.getmtime(path)
    except Exception:
        mtime = 0.0
    if _LAB_CATALOG_CACHE and mtime and mtime == _LAB_CATALOG_MTIME:
        return _LAB_CATALOG_CACHE
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        raw = data.get("upgrades") if isinstance(data, dict) else None
        if isinstance(raw, list):
            _LAB_CATALOG_CACHE = [u for u in raw if isinstance(u, dict) and isinstance(u.get("id"), str)]
            _LAB_CATALOG_MTIME = mtime
    except Exception:
        _LAB_CATALOG_CACHE = []
    return _LAB_CATALOG_CACHE


def _lab_catalog_by_id() -> dict:
    return {u["id"]: u for u in _load_lab_catalog() if isinstance(u.get("id"), str)}


LAB_CATALOG_IDS = frozenset()  # filled after first catalog load


def _ensure_catalog_ids():
    global LAB_CATALOG_IDS, CHAPTER2_TOTAL
    ids = frozenset(_lab_catalog_by_id().keys())
    if ids != LAB_CATALOG_IDS:
        LAB_CATALOG_IDS = ids
        CHAPTER2_TOTAL = len(LAB_CATALOG_IDS) if LAB_CATALOG_IDS else 25


CHAPTER2_TOTAL = 25  # overwritten on first access via property pattern — set below after load

_ensure_catalog_ids()
CHAPTER2_TOTAL = len(LAB_CATALOG_IDS) if LAB_CATALOG_IDS else 25

EXPLORE_COOLDOWN_SEC = 3 * 3600
DEEP_SCAN_COOLDOWN_SEC = 12 * 3600
LAB_RESEARCH_PROJECT_COOLDOWN_SEC = 6 * 3600
LAB_TECH_DRAFT_COOLDOWN_SEC = 1 * 3600
LAB_AGENT_REFINE_COOLDOWN_SEC = 10 * 3600


def _now_utc():
    return datetime.now(timezone.utc)


def _parse_iso_utc(s):
    if not isinstance(s, str) or not s.strip():
        return None
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00"))
    except Exception:
        return None


def _seconds_remaining_until(until_dt, now=None):
    now = now or _now_utc()
    return max(0, int((until_dt - now).total_seconds()))


def _lab_research_reenable_map(prof: dict) -> dict:
    raw = prof.get("lab_research_reenable_after")
    return {k: v for k, v in raw.items()} if isinstance(raw, dict) else {}


def _prune_research_reenable(reenable, now=None):
    now = now or _now_utc()
    out = {}
    for k, v in reenable.items():
        if not isinstance(k, str):
            continue
        dt = _parse_iso_utc(v) if isinstance(v, str) else None
        if dt and dt > now:
            out[k] = dt.isoformat()
    return out


def _research_cooldown_remaining_sec(prof: dict, node_id: str, researched: set) -> int:
    if node_id in researched:
        return 0
    until_s = _lab_research_reenable_map(prof).get(node_id)
    dt = _parse_iso_utc(until_s) if isinstance(until_s, str) else None
    if not dt:
        return 0
    return _seconds_remaining_until(dt)


def _points_slice_for_lab(user_id: str) -> dict:
    out = {
        "xp_total": 0,
        "game_points": 0,
        "battle_points": 0,
        "activity_points": 0,
        "coins": 0,
    }
    try:
        from backend.services.unified_points_database import unified_points_db
        if not unified_points_db or not hasattr(unified_points_db, "get_all_points"):
            return out
        res = unified_points_db.get_all_points(user_id)
        if not isinstance(res, dict) or not res.get("success"):
            return out
        p = res.get("points") or {}
        if not isinstance(p, dict):
            return out

        def _f(k):
            try:
                return float(p.get(k) or 0)
            except (TypeError, ValueError):
                return 0.0

        out["xp_total"] = int(_f("xp_total"))
        out["game_points"] = _f("game_points")
        out["battle_points"] = _f("battle_points")
        out["activity_points"] = _f("activity_points")
        out["coins"] = _f("coins")
    except Exception:
        pass
    return out


def _level_info_for_lab(user_id: str) -> dict:
    try:
        from backend.routes.hunters_game import get_user_level_info
        li = get_user_level_info(user_id)
        return li if isinstance(li, dict) else {}
    except Exception:
        return {}


def _unlock_ok(entry: dict, level_info: dict, pts: dict, research_ids: set) -> bool:
    u = entry.get("unlock") if isinstance(entry.get("unlock"), dict) else {}
    if not u:
        return True
    level = int((level_info or {}).get("current_level") or 1)
    if u.get("min_hunter_level") and level < int(u["min_hunter_level"]):
        return False
    tx = int((level_info or {}).get("total_xp") or 0)
    if u.get("min_total_xp") and tx < int(u["min_total_xp"]):
        return False
    uxp = int(pts.get("xp_total") or 0)
    if u.get("min_unified_xp_total") and uxp < int(u["min_unified_xp_total"]):
        return False
    if u.get("min_game_points") and float(pts.get("game_points") or 0) < float(u["min_game_points"]):
        return False
    if u.get("min_battle_points") and float(pts.get("battle_points") or 0) < float(u["min_battle_points"]):
        return False
    for req in u.get("requires_researched") or []:
        if not isinstance(req, str) or req not in research_ids:
            return False
    if u.get("min_researched_total"):
        if len(research_ids) < int(u["min_researched_total"]):
            return False
    return True


def _unlock_summary(entry: dict) -> str:
    u = entry.get("unlock") if isinstance(entry.get("unlock"), dict) else {}
    if not u:
        return "Available immediately."
    parts = []
    if u.get("min_hunter_level"):
        parts.append(f"Hunter level {int(u['min_hunter_level'])}+")
    if u.get("min_total_xp"):
        parts.append(f"{int(u['min_total_xp'])}+ hunter XP")
    if u.get("min_unified_xp_total"):
        parts.append(f"{int(u['min_unified_xp_total'])}+ unified XP")
    if u.get("min_game_points"):
        parts.append(f"{u['min_game_points']}+ game points")
    if u.get("min_battle_points"):
        parts.append(f"{u['min_battle_points']}+ battle points")
    if u.get("min_researched_total"):
        parts.append(f"{int(u['min_researched_total'])}+ researched nodes")
    reqs = [r for r in (u.get("requires_researched") or []) if isinstance(r, str)]
    if reqs:
        by_id = _lab_catalog_by_id()
        labels = [by_id.get(r, {}).get("name") or r for r in reqs]
        parts.append("Requires " + ", ".join(labels))
    return "; ".join(parts) + "."


def _first_research_awards(entry: dict) -> list:
    raw = entry.get("first_research_points")
    if not isinstance(raw, dict):
        return []
    out = []
    for k, v in raw.items():
        if not isinstance(k, str):
            continue
        try:
            amt = float(v)
        except (TypeError, ValueError):
            continue
        if amt > 0:
            out.append((k, amt))
    return out


def _lab_tier(researched_count: int, exploration_count: int) -> str:
    score = researched_count * 2 + exploration_count * 4
    if score >= 90:
        return "Architect"
    if score >= 55:
        return "Strategist"
    if score >= 28:
        return "Explorer"
    if score >= 8:
        return "Apprentice"
    return "Novice"


MAX_LAB_TECHNOLOGIES = 24
LAB_TECH_CATEGORIES = frozenset({
    "general", "video", "agents", "electric_magnet", "shop", "battle", "mn2", "debugger", "social",
})
LAB_TECH_ID_RE = re.compile(r"^lt_[a-f0-9]{8,24}$")
LAB_PROJECT_ID_RE = re.compile(r"^lrp_[a-f0-9]{8,24}$")

LAB_TOOL_REGISTRY = [
    {"id": "research_grid", "name": "Research Grid", "agent": "lab_agent", "status": "live", "cooldown": "node re-research: 1h/3h/10h"},
    {"id": "research_projects", "name": "Research Projects", "agent": "lab_project_agent", "status": "live", "cooldown": "new project: 6h"},
    {"id": "exploration_pulse", "name": "Exploration Pulse", "agent": "explorer_agent", "status": "live", "cooldown": "3h"},
    {"id": "deep_scan", "name": "Deep Scan", "agent": "deep_scan_agent", "status": "live", "cooldown": "12h"},
    {"id": "co_tech", "name": "Co-Tech Lifecycle", "agent": "co_tech_agent", "status": "live", "cooldown": "draft 1h; refine 10h"},
    {"id": "roundtable", "name": "Round Table Room", "agent": "roundtable_agent", "status": "live", "cooldown": "none"},
    {"id": "research_logbook", "name": "Profile Logbook", "agent": "profile_agent", "status": "live", "cooldown": "read-only"},
    {"id": "point_results", "name": "Unified Point Results", "agent": "points_agent", "status": "live", "cooldown": "read-only"},
    {"id": "monitor_4d", "name": "4D Research Monitor", "agent": "monitor_agent", "status": "live", "cooldown": "sound is user-triggered"},
    {"id": "idea_board", "name": "Idea Board", "agent": "idea_board_agent", "status": "live", "cooldown": "pin 30m spacing"},
    {"id": "systems_check", "name": "Systems Audit", "agent": "systems_agent", "status": "live", "cooldown": "on-demand"},
    {"id": "lab_news", "name": "Lab News Feed", "agent": "news_agent", "status": "live", "cooldown": "read-only"},
    {"id": "ai_copilot", "name": "AI Copilot", "agent": "copilot_agent", "status": "live", "cooldown": "read-only recommendations"},
    {"id": "crypto_rewards", "name": "Crypto Rewards Bridge", "agent": "mn2_lab_agent", "status": "live", "cooldown": "display-only"},
]

LAB_TODO_TEMPLATE = [
    "Read Lab V2.1 status and next milestone.",
    "Scan lab news for platform updates.",
    "Run systems check and fix any failing endpoints.",
    "Pin one idea to the idea board.",
    "Check recommended next research node.",
    "Review active research project cooldown.",
    "Run exploration pulse when ready.",
    "Run deep scan when ready.",
    "Invite one agent to refine a co-tech draft.",
    "Browse lab shop SKUs and trophy rewards.",
]


def _load_lab_v2_rulebook() -> dict:
    data = _load_data_json(_LAB_V2_RULEBOOK_FILE)
    if not isinstance(data, dict):
        return {
            "available": False,
            "name": "Lab V2.0",
            "version": "LAB_V2",
            "rules": [],
            "pillars": [],
            "agent_knowledge_topics": [],
        }
    data = dict(data)
    data["available"] = True
    return data


def _agent_knowledge_matches_lab(entry: dict) -> bool:
    if not isinstance(entry, dict):
        return False
    refs = entry.get("rulebook_ref")
    ref_text = " ".join([str(r) for r in refs]) if isinstance(refs, list) else str(refs or "")
    haystack = " ".join([
        str(entry.get("id") or ""),
        str(entry.get("title") or ""),
        str(entry.get("text") or ""),
        ref_text,
    ]).lower()
    return "lab" in haystack or "research" in haystack or "lab_v2" in haystack


def _lab_agent_knowledge_summary(rulebook: dict) -> dict:
    embedded_topics = rulebook.get("agent_knowledge_topics")
    embedded = embedded_topics if isinstance(embedded_topics, list) else []
    raw = _load_data_json(_AGENT_KNOWLEDGE_FILE)
    entries = raw.get("entries") if isinstance(raw, dict) else []
    learned = [e for e in entries if _agent_knowledge_matches_lab(e)] if isinstance(entries, list) else []
    return {
        "embedded_count": len(embedded),
        "learned_count": len(learned),
        "total_count": len(embedded) + len(learned),
        "topics": embedded[:8],
        "learned_entries": learned[-5:],
        "source_file": _AGENT_KNOWLEDGE_FILE,
    }


def _lab_v2_milestones(summary: dict, prof: dict) -> list:
    researched = int(summary.get("researched_count") or 0)
    explorations = int(summary.get("exploration_count") or 0)
    deep_scans = int(summary.get("deep_scan_count") or 0)
    projects = len(_lab_projects_list_from_profile(prof))
    techs = len(_lab_technologies_list_from_profile(prof))
    roundtable = len(_lab_roundtable_from_profile(prof))
    score = researched * 2 + explorations * 4 + deep_scans * 7 + projects * 5 + techs * 5 + roundtable
    systems_ok = 1 if prof.get("lab_last_systems_check_ok_at") else 0
    chapter5 = sum(1 for uid in (prof.get("lab_chapter2_research") or []) if isinstance(uid, str) and uid.startswith("c5_"))
    milestones = [
        {"id": "first_research", "name": "Research first lab node", "progress": min(researched, 1), "target": 1},
        {"id": "first_pulse", "name": "Run first exploration pulse", "progress": min(explorations, 1), "target": 1},
        {"id": "first_deep_scan", "name": "Run first deep scan", "progress": min(deep_scans, 1), "target": 1},
        {"id": "first_project", "name": "Start first research project", "progress": min(projects, 1), "target": 1},
        {"id": "first_co_tech", "name": "Draft first co-created technology", "progress": min(techs, 1), "target": 1},
        {"id": "first_roundtable", "name": "Post first roundtable message", "progress": min(roundtable, 1), "target": 1},
        {"id": "ten_nodes", "name": "Research ten lab nodes", "progress": min(researched, 10), "target": 10},
        {"id": "strategist_tier", "name": "Reach Strategist tier", "progress": min(score, 55), "target": 55},
        {"id": "chapter5_first", "name": "Research first Chapter V node", "progress": min(chapter5, 1), "target": 1},
        {"id": "systems_check", "name": "Run systems audit (all green)", "progress": systems_ok, "target": 1},
        {"id": "architect_tier", "name": "Reach Architect tier", "progress": min(score, 90), "target": 90},
    ]
    for item in milestones:
        item["complete"] = int(item["progress"]) >= int(item["target"])
    return milestones


def _lab_v2_next_milestone(milestones: list) -> dict:
    for item in milestones:
        if isinstance(item, dict) and not item.get("complete"):
            return item
    return {"id": "v2_foundation_complete", "name": "Lab V2.0 foundation complete", "progress": 1, "target": 1, "complete": True}


def _resolve_uid() -> str:
    try:
        from backend.services.account_resolution_service import resolve_user_id
        return resolve_user_id(from_body=True, from_query=True)
    except Exception:
        return request.args.get("user_id") or (request.get_json(silent=True) or {}).get("user_id") or "default_user"


def _loads_profile(raw) -> dict:
    if not raw:
        return {}
    try:
        out = json.loads(raw) if isinstance(raw, str) else {}
        return out if isinstance(out, dict) else {}
    except Exception:
        return {}


def chapter2_public_summary(user_id: str) -> dict:
    """Read-only lab research counts (all catalog chapters) for embedding in other APIs."""
    _ensure_catalog_ids()
    out = {
        "researched_count": 0,
        "total": len(LAB_CATALOG_IDS) if LAB_CATALOG_IDS else CHAPTER2_TOTAL,
        "researched_ids": [],
        "bonuses_claimed": 0,
    }
    if not user_id or not db:
        return out
    try:
        from flask import has_app_context
        if not has_app_context():
            return out
        row = db.session.execute(
            text("SELECT profile_data FROM hunters_profiles WHERE user_id = :uid LIMIT 1"),
            {"uid": user_id},
        ).fetchone()
        if not row or row[0] is None:
            return out
        data = _loads_profile(row[0])
        raw_ids = data.get("lab_chapter2_research")
        ids = [i for i in raw_ids if isinstance(i, str) and i in LAB_CATALOG_IDS] if isinstance(raw_ids, list) else []
        raw_aw = data.get("lab_chapter2_bonus_awarded")
        aw = [a for a in raw_aw if isinstance(a, str)] if isinstance(raw_aw, list) else []
        by_id = _lab_catalog_by_id()
        bonus_hits = 0
        for aid in set(aw):
            ent = by_id.get(aid)
            if ent and _first_research_awards(ent):
                bonus_hits += 1
        out["researched_ids"] = ids
        out["researched_count"] = len(ids)
        out["bonuses_claimed"] = bonus_hits
        out["total"] = len(LAB_CATALOG_IDS) if LAB_CATALOG_IDS else out["total"]
    except Exception:
        pass
    return out


def lab_public_summary(user_id: str) -> dict:
    """Lab tier + exploration pulse (for game/battle bridge and profile-adjacent UI)."""
    base = dict(chapter2_public_summary(user_id))
    exploration_count = 0
    explore_remaining = 0
    deep_scan_count = 0
    deep_scan_remaining = 0
    if user_id and db:
        try:
            from flask import has_app_context
            if has_app_context():
                row = db.session.execute(
                    text("SELECT profile_data FROM hunters_profiles WHERE user_id = :uid LIMIT 1"),
                    {"uid": user_id},
                ).fetchone()
                if row and row[0]:
                    data = _loads_profile(row[0])
                    le = data.get("lab_exploration") if isinstance(data.get("lab_exploration"), dict) else {}
                    exploration_count = int(le.get("count") or 0)
                    last = le.get("last_at")
                    if isinstance(last, str) and last:
                        try:
                            lu = datetime.fromisoformat(last.replace("Z", "+00:00"))
                            delta = (datetime.now(timezone.utc) - lu).total_seconds()
                            if delta < EXPLORE_COOLDOWN_SEC:
                                explore_remaining = int(EXPLORE_COOLDOWN_SEC - delta)
                        except Exception:
                            pass
                    ds = data.get("lab_deep_scan") if isinstance(data.get("lab_deep_scan"), dict) else {}
                    deep_scan_count = int(ds.get("count") or 0)
                    deep_last = ds.get("last_at")
                    if isinstance(deep_last, str) and deep_last:
                        try:
                            dlu = datetime.fromisoformat(deep_last.replace("Z", "+00:00"))
                            delta = (datetime.now(timezone.utc) - dlu).total_seconds()
                            if delta < DEEP_SCAN_COOLDOWN_SEC:
                                deep_scan_remaining = int(DEEP_SCAN_COOLDOWN_SEC - delta)
                        except Exception:
                            pass
        except Exception:
            pass
    base["exploration_count"] = exploration_count
    base["explore_cooldown_remaining_sec"] = explore_remaining
    base["explore_ready"] = explore_remaining <= 0
    base["deep_scan_count"] = deep_scan_count
    base["deep_scan_cooldown_remaining_sec"] = deep_scan_remaining
    base["deep_scan_ready"] = deep_scan_remaining <= 0
    base["lab_tier"] = _lab_tier(int(base.get("researched_count") or 0), exploration_count)
    return base


def _hp_read(user_id: str) -> dict:
    """hunters_profiles row → profile dict (empty if no row)."""
    out = {"db": False, "row": False, "profile": {}}
    if not db or not user_id:
        return out
    try:
        from flask import has_app_context, has_request_context
        if not has_app_context() or not has_request_context():
            return out
        out["db"] = True
        row = db.session.execute(
            text("SELECT profile_data FROM hunters_profiles WHERE user_id = :uid LIMIT 1"),
            {"uid": user_id},
        ).fetchone()
        if not row:
            return out
        out["row"] = True
        out["profile"] = _loads_profile(row[0])
    except Exception:
        pass
    return out


def _hp_write(user_id: str, profile: dict) -> bool:
    if not db or not user_id:
        return False
    blob = json.dumps(profile, separators=(",", ":"))
    try:
        from flask import has_app_context, has_request_context
        if not has_app_context() or not has_request_context():
            return False
        row = db.session.execute(
            text("SELECT 1 FROM hunters_profiles WHERE user_id = :uid LIMIT 1"),
            {"uid": user_id},
        ).fetchone()
        if row:
            db.session.execute(
                text(
                    "UPDATE hunters_profiles SET profile_data = :blob, "
                    "updated_at = CURRENT_TIMESTAMP WHERE user_id = :uid"
                ),
                {"blob": blob, "uid": user_id},
            )
        else:
            db.session.execute(
                text(
                    "INSERT INTO hunters_profiles (user_id, profile_data, agent_tech_enabled, updated_at) "
                    "VALUES (:uid, :blob, 1, CURRENT_TIMESTAMP)"
                ),
                {"uid": user_id, "blob": blob},
            )
        db.session.commit()
        return True
    except Exception:
        try:
            db.session.rollback()
        except Exception:
            pass
        return False


def _lab_technologies_list_from_profile(prof: dict) -> list:
    raw = prof.get("lab_technologies")
    if not isinstance(raw, list):
        return []
    out = []
    for item in raw:
        if isinstance(item, dict) and isinstance(item.get("id"), str) and LAB_TECH_ID_RE.match(item["id"]):
            out.append(item)
    return out


def _lab_projects_list_from_profile(prof: dict) -> list:
    raw = prof.get("lab_research_projects")
    if not isinstance(raw, list):
        return []
    out = []
    for item in raw:
        if isinstance(item, dict) and isinstance(item.get("id"), str) and LAB_PROJECT_ID_RE.match(item["id"]):
            out.append(item)
    return out


def _lab_roundtable_from_profile(prof: dict) -> list:
    raw = prof.get("lab_roundtable")
    if not isinstance(raw, list):
        return []
    out = []
    for item in raw:
        if isinstance(item, dict) and isinstance(item.get("message"), str):
            out.append(item)
    return out[-60:]


def _project_cooldown_remaining_sec(prof: dict) -> int:
    raw = prof.get("lab_next_research_project_at")
    dt = _parse_iso_utc(raw) if isinstance(raw, str) else None
    if not dt:
        return 0
    return _seconds_remaining_until(dt)


def _point_systems_for_lab(user_id: str) -> dict:
    try:
        from backend.services.unified_points_database import unified_points_db
        if not unified_points_db or not hasattr(unified_points_db, "get_all_points"):
            return {"success": False, "points": {}, "systems": {}}
        res = unified_points_db.get_all_points(user_id)
        if isinstance(res, dict):
            pts = res.get("points") if isinstance(res.get("points"), dict) else res
            systems = res.get("systems") if isinstance(res.get("systems"), dict) else {}
            if not systems:
                systems = {k: v for k, v in pts.items() if isinstance(v, (int, float))}
            return {"success": bool(res.get("success", True)), "points": pts, "systems": systems}
    except Exception:
        pass
    return {"success": False, "points": {}, "systems": {}}


def _lab_events_from_profile(prof: dict, limit: int = 40) -> list:
    by_id = _lab_catalog_by_id()
    events = []
    for rid in _sanitize_ids(prof.get("lab_chapter2_research") or []):
        ent = by_id.get(rid, {})
        events.append({
            "type": "research",
            "label": ent.get("name") or rid,
            "detail": ent.get("tier") or "Lab node",
            "at": prof.get("lab_chapter2_updated_at"),
        })
    le = prof.get("lab_exploration") if isinstance(prof.get("lab_exploration"), dict) else {}
    if le.get("last_at"):
        events.append({
            "type": "exploration",
            "label": f"Exploration pulse #{int(le.get('count') or 0)}",
            "detail": "+3 activity, +1 game, +6 hunter XP",
            "at": le.get("last_at"),
        })
    ds = prof.get("lab_deep_scan") if isinstance(prof.get("lab_deep_scan"), dict) else {}
    if ds.get("last_at"):
        events.append({
            "type": "deep_scan",
            "label": f"Deep scan #{int(ds.get('count') or 0)}",
            "detail": "+9 activity, +4 game, +20 hunter XP",
            "at": ds.get("last_at"),
        })
    for project in _lab_projects_list_from_profile(prof):
        events.append({
            "type": "project",
            "label": project.get("title") or project.get("id"),
            "detail": f"{project.get('track', 'general')} · {project.get('status', 'active')}",
            "at": project.get("updated_at") or project.get("created_at"),
        })
    for tech in _lab_technologies_list_from_profile(prof):
        events.append({
            "type": "technology",
            "label": tech.get("name") or tech.get("id"),
            "detail": f"{tech.get('category', 'general')} · {tech.get('status', 'draft')}",
            "at": tech.get("updated_at") or tech.get("created_at"),
        })
    events.sort(key=lambda e: e.get("at") or "", reverse=True)
    return events[:limit]


def lab_profile_logbook(user_id: str) -> dict:
    """Read-only profile logbook section: lab progress + latest events."""
    summ = lab_public_summary(user_id)
    hp = _hp_read(user_id)
    prof = hp.get("profile") or {}
    return {
        "success": True,
        "summary": summ,
        "events": _lab_events_from_profile(prof, 20) if hp.get("db") else [],
        "projects": _lab_projects_list_from_profile(prof)[:10] if hp.get("db") else [],
        "project_cooldown_remaining_sec": _project_cooldown_remaining_sec(prof) if hp.get("db") else 0,
    }


def _run_agent_refine(name: str, pitch: str, co_agent_id: str) -> str:
    """LLM partner notes for a user-proposed lab technology (best-effort)."""
    stub = (
        "Agent refinement (offline): tighten one measurable success metric, list one API or UI surface to touch first, "
        "and run one Electric Magnet verification after a debugger assign→complete cycle."
    )
    try:
        from backend.services.llm_service import complete as llm_complete

        r = llm_complete(
            prompt=(
                f"Lab co-design on MasterNoder.dk.\n"
                f"Technology title: {name}\n"
                f"User pitch: {pitch}\n"
                f"Partner agent id: {co_agent_id}\n\n"
                "Respond with 4–6 short bullet lines: risks, first experiment, integration hooks "
                "(video generator, shop, trophies, debugger, MN2 wallet, lab agent tech). Max ~220 words. Plain text."
            ),
            system_prompt="You are a senior product engineer helping users and agents co-invent platform features. Be concrete.",
            task_type="speed",
            max_tokens=400,
            temperature=0.45,
        )
        if getattr(r, "success", False) and (getattr(r, "content", None) or "").strip():
            return (r.content or "").strip()[:12000]
    except Exception:
        pass
    return stub


def _sanitize_ids(ids) -> list:
    _ensure_catalog_ids()
    if not isinstance(ids, list):
        return []
    out = []
    for i in ids:
        if isinstance(i, str) and i in LAB_CATALOG_IDS:
            out.append(i)
    return list(dict.fromkeys(out))


@lab_bp.route("/api/lab/chapter2-research", methods=["GET"])
def lab_chapter2_get():
    """Return researched Chapter II upgrade ids for the resolved user."""
    user_id = _resolve_uid()
    if not db:
        return jsonify({"success": True, "user_id": user_id, "researched_ids": [], "storage": "none"}), 200
    try:
        from flask import has_app_context, has_request_context
        if not has_app_context() or not has_request_context():
            return jsonify({"success": True, "user_id": user_id, "researched_ids": [], "storage": "none"}), 200
        row = db.session.execute(
            text("SELECT profile_data FROM hunters_profiles WHERE user_id = :uid LIMIT 1"),
            {"uid": user_id},
        ).fetchone()
        if not row or row[0] is None:
            return jsonify({"success": True, "user_id": user_id, "researched_ids": [], "storage": "db"}), 200
        data = _loads_profile(row[0])
        raw_ids = data.get("lab_chapter2_research")
        if isinstance(raw_ids, list):
            _ensure_catalog_ids()
            ids = [i for i in raw_ids if isinstance(i, str) and i in LAB_CATALOG_IDS]
        else:
            ids = []
        summ = chapter2_public_summary(user_id)
        return jsonify({
            "success": True,
            "user_id": user_id,
            "researched_ids": ids,
            "research_count": len(ids),
            "research_total": len(LAB_CATALOG_IDS) if LAB_CATALOG_IDS else CHAPTER2_TOTAL,
            "bonuses_claimed": summ.get("bonuses_claimed", 0),
            "storage": "db",
        }), 200
    except Exception as e:
        return jsonify({"success": False, "user_id": user_id, "researched_ids": [], "error": str(e)}), 200


@lab_bp.route("/api/lab/chapter2-research", methods=["POST"])
def lab_chapter2_post():
    """Replace Chapter II research list with validated ids (full client state)."""
    user_id = _resolve_uid()
    body = request.get_json(silent=True) or {}
    ids = _sanitize_ids(body.get("researched_ids") or body.get("ids") or [])
    if not db:
        return jsonify({"success": True, "user_id": user_id, "researched_ids": ids, "storage": "none", "bonuses_applied": []}), 200
    try:
        from flask import has_app_context, has_request_context
        if not has_app_context() or not has_request_context():
            return jsonify({"success": True, "user_id": user_id, "researched_ids": ids, "storage": "none", "bonuses_applied": []}), 200

        row = db.session.execute(
            text("SELECT profile_data FROM hunters_profiles WHERE user_id = :uid LIMIT 1"),
            {"uid": user_id},
        ).fetchone()
        prof = _loads_profile(row[0]) if row else {}
        old_ids = set(_sanitize_ids(prof.get("lab_chapter2_research") or []))
        new_ids = set(ids)
        newly_on = new_ids - old_ids
        removed = old_ids - new_ids

        level_info = _level_info_for_lab(user_id)
        pts = _points_slice_for_lab(user_id)
        by_id = _lab_catalog_by_id()

        now = _now_utc()
        reenable = _prune_research_reenable(_lab_research_reenable_map(prof), now)
        for r in removed:
            ent_rm = by_id.get(r)
            if not ent_rm:
                continue
            try:
                cd_sec = int(ent_rm.get("research_cooldown_sec") or 0)
            except (TypeError, ValueError):
                cd_sec = 0
            if cd_sec > 0:
                reenable[r] = (now + timedelta(seconds=cd_sec)).isoformat()

        for rid in sorted(newly_on):
            rem_cd = _research_cooldown_remaining_sec({"lab_research_reenable_after": reenable}, rid, old_ids)
            if rem_cd > 0:
                return jsonify({
                    "success": False,
                    "error": "research_cooldown",
                    "locked_id": rid,
                    "cooldown_remaining_sec": rem_cd,
                    "message": "This node is on re-research cooldown (timer starts when you clear it).",
                }), 429

        for rid in sorted(newly_on):
            ent = by_id.get(rid)
            if not ent:
                return jsonify({"success": False, "error": f"Unknown research id: {rid}"}), 400
            if not _unlock_ok(ent, level_info, pts, new_ids):
                return jsonify({
                    "success": False,
                    "error": "unlock_failed",
                    "locked_id": rid,
                    "message": "Progress requirements not met for this lab node (level, XP, points, or prerequisites).",
                }), 400

        raw_aw = prof.get("lab_chapter2_bonus_awarded")
        bonus_awarded = {a for a in raw_aw if isinstance(a, str)} if isinstance(raw_aw, list) else set()
        bonuses_applied = []

        for rid in sorted(newly_on):
            ent = by_id.get(rid)
            if not ent or rid in bonus_awarded:
                continue
            awards = _first_research_awards(ent)
            if not awards:
                continue
            any_ok = False
            for pt, amt in awards:
                try:
                    from backend.services.unified_points_database import unified_points_db
                    if unified_points_db and hasattr(unified_points_db, "add_points"):
                        unified_points_db.add_points(
                            user_id,
                            pt,
                            float(amt),
                            "lab_research_first",
                            {"upgrade_id": rid, "chapter": ent.get("chapter")},
                        )
                    bonuses_applied.append({"upgrade_id": rid, "point_type": pt, "amount": amt})
                    any_ok = True
                except Exception:
                    pass
            if any_ok:
                bonus_awarded.add(rid)

        xp_burst = 0
        for rid in sorted(newly_on):
            ent = by_id.get(rid)
            if not ent:
                continue
            ch = int(ent.get("chapter") or 2)
            xp_burst += 4 if ch <= 2 else 7
        xp_burst = min(xp_burst, 100)
        if xp_burst > 0:
            try:
                from backend.routes.hunters_game import award_xp
                award_xp(
                    user_id,
                    {"xp": xp_burst},
                    xp_source="lab_research",
                    xp_action_type="research_nodes",
                )
            except Exception:
                pass

        if bonuses_applied or xp_burst > 0:
            try:
                from backend.services.unified_points_sync import unified_points_sync_device
                unified_points_sync_device.record_domain_sync("lab")
            except Exception:
                pass

        prof["lab_chapter2_research"] = ids
        prof["lab_chapter2_bonus_awarded"] = sorted(bonus_awarded)
        prof["lab_chapter2_updated_at"] = datetime.now(timezone.utc).isoformat()
        prof["lab_research_reenable_after"] = _prune_research_reenable(reenable, now)
        blob = json.dumps(prof, separators=(",", ":"))

        if row:
            db.session.execute(
                text(
                    "UPDATE hunters_profiles SET profile_data = :blob, "
                    "updated_at = CURRENT_TIMESTAMP WHERE user_id = :uid"
                ),
                {"blob": blob, "uid": user_id},
            )
        else:
            db.session.execute(
                text(
                    "INSERT INTO hunters_profiles (user_id, profile_data, agent_tech_enabled, updated_at) "
                    "VALUES (:uid, :blob, 1, CURRENT_TIMESTAMP)"
                ),
                {"uid": user_id, "blob": blob},
            )
        db.session.commit()
        return jsonify({
            "success": True,
            "user_id": user_id,
            "researched_ids": ids,
            "research_count": len(ids),
            "research_total": len(LAB_CATALOG_IDS) if LAB_CATALOG_IDS else CHAPTER2_TOTAL,
            "bonuses_applied": bonuses_applied,
            "xp_awarded_hunter": xp_burst,
            "storage": "db",
        }), 200
    except Exception as e:
        if db:
            try:
                db.session.rollback()
            except Exception:
                pass
        return jsonify({"success": False, "user_id": user_id, "error": str(e)}), 500


@lab_bp.route("/api/lab/progression", methods=["GET"])
def lab_progression_get():
    """Catalog + unlock flags for the current user (game + unified points aware)."""
    user_id = _resolve_uid()
    _ensure_catalog_ids()
    level_info = _level_info_for_lab(user_id)
    pts = _points_slice_for_lab(user_id)
    researched: set = set()
    prof_row: dict = {}
    if db:
        try:
            from flask import has_app_context, has_request_context
            if has_app_context() and has_request_context():
                row = db.session.execute(
                    text("SELECT profile_data FROM hunters_profiles WHERE user_id = :uid LIMIT 1"),
                    {"uid": user_id},
                ).fetchone()
                if row and row[0]:
                    prof_row = _loads_profile(row[0])
                    raw_ids = prof_row.get("lab_chapter2_research")
                    if isinstance(raw_ids, list):
                        researched = {i for i in raw_ids if isinstance(i, str) and i in LAB_CATALOG_IDS}
        except Exception:
            pass
    catalog_out = []
    for ent in _load_lab_catalog():
        eid = ent.get("id")
        if not isinstance(eid, str):
            continue
        unlocked = _unlock_ok(ent, level_info, pts, researched)
        cd_rem = _research_cooldown_remaining_sec(prof_row, eid, researched)
        on = eid in researched
        interactable = on or (unlocked and cd_rem <= 0)
        catalog_out.append({
            **{k: v for k, v in ent.items() if k != "unlock"},
            "unlock_summary": _unlock_summary(ent),
            "unlocked": unlocked,
            "researched": on,
            "cooldown_remaining_sec": cd_rem,
            "interactable": interactable,
        })
    summ = lab_public_summary(user_id)
    return jsonify({
        "success": True,
        "user_id": user_id,
        "hunter_level": int((level_info or {}).get("current_level") or 1),
        "hunter_total_xp": int((level_info or {}).get("total_xp") or 0),
        "points": pts,
        "catalog": catalog_out,
        "lab_tier": summ.get("lab_tier"),
        "exploration_count": summ.get("exploration_count", 0),
        "explore_ready": summ.get("explore_ready", True),
        "explore_cooldown_remaining_sec": summ.get("explore_cooldown_remaining_sec", 0),
        "deep_scan_count": summ.get("deep_scan_count", 0),
        "deep_scan_ready": summ.get("deep_scan_ready", True),
        "deep_scan_cooldown_remaining_sec": summ.get("deep_scan_cooldown_remaining_sec", 0),
    }), 200


@lab_bp.route("/api/lab/research-log", methods=["GET"])
def lab_research_log_get():
    """Compact timeline for lab research, exploration pulses, and co-tech lifecycle."""
    user_id = _resolve_uid()
    hp = _hp_read(user_id)
    if not hp.get("db"):
        return jsonify({"success": True, "user_id": user_id, "events": [], "storage": "none"}), 200
    prof = hp.get("profile") or {}
    return jsonify({"success": True, "user_id": user_id, "events": _lab_events_from_profile(prof), "storage": "db"}), 200


@lab_bp.route("/api/lab/share-card", methods=["GET"])
def lab_share_card_get():
    """Shareable text card for profile/social embeds."""
    user_id = _resolve_uid()
    summ = lab_public_summary(user_id)
    card = (
        f"MasterNoder Lab: {summ.get('lab_tier', 'Novice')} tier · "
        f"{summ.get('researched_count', 0)}/{summ.get('total', 0)} nodes · "
        f"{summ.get('exploration_count', 0)} pulses · "
        f"{summ.get('deep_scan_count', 0)} deep scans"
    )
    return jsonify({"success": True, "user_id": user_id, "card": card, "summary": summ}), 200


@lab_bp.route("/api/lab/overview", methods=["GET"])
def lab_overview_get():
    """Unified lab results for the site: tools, points, projects, roundtable, monitor, todos."""
    user_id = _resolve_uid()
    hp = _hp_read(user_id)
    prof = hp.get("profile") or {}
    summ = lab_public_summary(user_id)
    events = _lab_events_from_profile(prof, 20) if hp.get("db") else []
    projects = _lab_projects_list_from_profile(prof) if hp.get("db") else []
    techs = _lab_technologies_list_from_profile(prof) if hp.get("db") else []
    roundtable = _lab_roundtable_from_profile(prof) if hp.get("db") else []
    points = _point_systems_for_lab(user_id)
    monitor = {
        "title": "4D Research Monitor",
        "dimensions": {
            "research": int(summ.get("researched_count") or 0),
            "agent_presence": len(roundtable) + len(techs),
            "economy": float((points.get("points") or {}).get("game_points") or 0) + float((points.get("points") or {}).get("activity_points") or 0),
            "time": int(summ.get("explore_cooldown_remaining_sec") or 0) + int(summ.get("deep_scan_cooldown_remaining_sec") or 0),
        },
        "sound_palette": ["low_orbit", "signal_ping", "roundtable_chime"],
        "activity": events[:10],
    }
    todos = [{"id": f"lab_todo_{i + 1}", "text": text, "done": False} for i, text in enumerate(LAB_TODO_TEMPLATE)]
    return jsonify({
        "success": True,
        "user_id": user_id,
        "summary": summ,
        "tools": LAB_TOOL_REGISTRY,
        "point_systems": points,
        "projects": projects[:24],
        "project_cooldown_remaining_sec": _project_cooldown_remaining_sec(prof) if hp.get("db") else 0,
        "roundtable": roundtable[-20:],
        "technologies": techs[:24],
        "monitor": monitor,
        "todos": todos,
        "profile_logbook": lab_profile_logbook(user_id),
        "storage": "db" if hp.get("db") else "none",
    }), 200


@lab_bp.route("/api/lab/v2/status", methods=["GET"])
def lab_v2_status_get():
    """Read-only Lab V2.0 status contract for UI panels and agents."""
    user_id = _resolve_uid()
    hp = _hp_read(user_id)
    prof = hp.get("profile") or {}
    summary = lab_public_summary(user_id)
    milestones = _lab_v2_milestones(summary, prof)
    rulebook = _load_lab_v2_rulebook()
    rules = rulebook.get("rules") if isinstance(rulebook.get("rules"), list) else []
    pillars = rulebook.get("pillars") if isinstance(rulebook.get("pillars"), list) else []
    projects = _lab_projects_list_from_profile(prof)
    techs = _lab_technologies_list_from_profile(prof)
    roundtable = _lab_roundtable_from_profile(prof)
    agent_knowledge = _lab_agent_knowledge_summary(rulebook)
    researched_count = int(summary.get("researched_count") or 0)
    exploration_count = int(summary.get("exploration_count") or 0)
    deep_scan_count = int(summary.get("deep_scan_count") or 0)
    progression_score = (
        researched_count * 2
        + exploration_count * 4
        + deep_scan_count * 7
        + len(projects) * 5
        + len(techs) * 5
        + len(roundtable)
    )
    return jsonify({
        "success": True,
        "version": "2.1-hub-upgrade",
        "user_id": user_id,
        "rulebook": {
            "id": "lab_v2",
            "file": _LAB_V2_RULEBOOK_FILE,
            "available": bool(rulebook.get("available")),
            "name": rulebook.get("name", "Lab V2.0"),
            "version": rulebook.get("version", "LAB_V2"),
            "description": rulebook.get("description", ""),
            "pillars": pillars,
            "rule_count": len(rules),
        },
        "progression": {
            "tier": summary.get("lab_tier", "Novice"),
            "score": progression_score,
            "researched_count": researched_count,
            "total_research_nodes": int(summary.get("total") or len(LAB_CATALOG_IDS) or CHAPTER2_TOTAL),
            "exploration_count": exploration_count,
            "deep_scan_count": deep_scan_count,
            "projects_count": len(projects),
            "technologies_count": len(techs),
            "roundtable_count": len(roundtable),
            "next_milestone": _lab_v2_next_milestone(milestones),
        },
        "milestones": milestones,
        "agent_knowledge": agent_knowledge,
        "tech": {
            "read_only_first_slice": True,
            "profile_storage": "db" if hp.get("db") else "none",
            "profile_row": bool(hp.get("row")),
            "catalog_nodes": len(_load_lab_catalog()),
            "tools": [t.get("id") for t in LAB_TOOL_REGISTRY],
            "endpoints": [
                "/api/lab/v2/status",
                "/api/lab/progression",
                "/api/lab/overview",
                "/api/lab/research-log",
                "/api/lab/systems-check",
                "/api/lab/idea-board",
                "/api/lab/news",
                "/api/rulebooks/agent-knowledge",
            ],
            "bridges": ["star_map", "unified_points", "agents", "shop", "sync", "trophies", "mn2_crypto"],
        },
    }), 200


@lab_bp.route("/api/lab/projects", methods=["GET"])
def lab_projects_get():
    """Research projects with a 6h creation cooldown."""
    user_id = _resolve_uid()
    hp = _hp_read(user_id)
    prof = hp.get("profile") or {}
    return jsonify({
        "success": True,
        "user_id": user_id,
        "projects": _lab_projects_list_from_profile(prof) if hp.get("db") else [],
        "project_cooldown_remaining_sec": _project_cooldown_remaining_sec(prof) if hp.get("db") else 0,
        "cooldown_sec": LAB_RESEARCH_PROJECT_COOLDOWN_SEC,
        "storage": "db" if hp.get("db") else "none",
    }), 200


@lab_bp.route("/api/lab/projects", methods=["POST"])
def lab_projects_post():
    """Create a research project and make its cooldown/profile logbook visible."""
    user_id = _resolve_uid()
    body = request.get_json(silent=True) or {}
    title = (body.get("title") or "").strip()
    question = (body.get("question") or body.get("description") or "").strip()
    track = (body.get("track") or "general").strip().lower()[:40] or "general"
    agent_id = (body.get("agent_id") or "lab_project_agent").strip()[:80] or "lab_project_agent"
    if len(title) < 2 or len(title) > 120:
        return jsonify({"success": False, "error": "title must be 2-120 characters"}), 400
    if len(question) < 8 or len(question) > 2000:
        return jsonify({"success": False, "error": "question must be 8-2000 characters"}), 400
    hp = _hp_read(user_id)
    if not hp.get("db"):
        return jsonify({"success": False, "error": "Research projects require the hunters profile database."}), 503
    prof = dict(hp.get("profile") or {})
    now = _now_utc()
    rem = _project_cooldown_remaining_sec(prof)
    if rem > 0:
        return jsonify({
            "success": False,
            "error": "project_cooldown",
            "project_cooldown_remaining_sec": rem,
            "message": "New lab research projects are on a 6h cooldown per profile.",
        }), 429
    projects = _lab_projects_list_from_profile(prof)
    pid = "lrp_" + uuid.uuid4().hex[:12]
    entry = {
        "id": pid,
        "title": title,
        "question": question,
        "track": track,
        "agent_id": agent_id,
        "status": "active",
        "progress": 0,
        "created_at": now.isoformat(),
        "updated_at": now.isoformat(),
        "next_review_at": (now + timedelta(hours=24)).isoformat(),
    }
    projects.append(entry)
    prof["lab_research_projects"] = projects[-24:]
    prof["lab_research_projects_updated_at"] = now.isoformat()
    prof["lab_next_research_project_at"] = (now + timedelta(seconds=LAB_RESEARCH_PROJECT_COOLDOWN_SEC)).isoformat()
    table = _lab_roundtable_from_profile(prof)
    table.append({
        "speaker": agent_id,
        "role": "agent",
        "message": f"Opened research project: {title}. First step: define one measurable result.",
        "topic": track,
        "created_at": now.isoformat(),
    })
    prof["lab_roundtable"] = table[-60:]
    if not _hp_write(user_id, prof):
        return jsonify({"success": False, "error": "could not save profile"}), 500
    return jsonify({
        "success": True,
        "user_id": user_id,
        "project": entry,
        "project_cooldown_sec": LAB_RESEARCH_PROJECT_COOLDOWN_SEC,
        "storage": "db",
    }), 200


@lab_bp.route("/api/lab/roundtable/messages", methods=["POST"])
def lab_roundtable_messages_post():
    """Append a researcher/agent message to the lab round table."""
    user_id = _resolve_uid()
    body = request.get_json(silent=True) or {}
    message = (body.get("message") or "").strip()
    speaker = (body.get("speaker") or "Researcher").strip()[:80] or "Researcher"
    role = (body.get("role") or "researcher").strip().lower()
    topic = (body.get("topic") or "tech_progression").strip()[:80] or "tech_progression"
    if role not in {"researcher", "agent"}:
        role = "researcher"
    if len(message) < 2 or len(message) > 1200:
        return jsonify({"success": False, "error": "message must be 2-1200 characters"}), 400
    hp = _hp_read(user_id)
    if not hp.get("db"):
        return jsonify({"success": False, "error": "database not available"}), 503
    prof = dict(hp.get("profile") or {})
    entry = {
        "speaker": speaker,
        "role": role,
        "message": message,
        "topic": topic,
        "created_at": _now_utc().isoformat(),
    }
    table = _lab_roundtable_from_profile(prof)
    table.append(entry)
    prof["lab_roundtable"] = table[-60:]
    prof["lab_roundtable_updated_at"] = entry["created_at"]
    if not _hp_write(user_id, prof):
        return jsonify({"success": False, "error": "could not save profile"}), 500
    return jsonify({"success": True, "user_id": user_id, "message": entry, "roundtable": prof["lab_roundtable"], "storage": "db"}), 200


@lab_bp.route("/api/lab/explore", methods=["POST"])
def lab_explore_post():
    """Exploration pulse: unified points + hunter XP on cooldown (profile-backed)."""
    user_id = _resolve_uid()
    body = request.get_json(silent=True) or {}
    mode = "deep_scan" if (body.get("mode") or "").strip().lower() == "deep_scan" else "pulse"
    cooldown_sec = DEEP_SCAN_COOLDOWN_SEC if mode == "deep_scan" else EXPLORE_COOLDOWN_SEC
    profile_key = "lab_deep_scan" if mode == "deep_scan" else "lab_exploration"
    if not db:
        return jsonify({"success": False, "error": "database not available"}), 503
    try:
        from flask import has_app_context, has_request_context
        if not has_app_context() or not has_request_context():
            return jsonify({"success": False, "error": "no request context"}), 503

        hp = _hp_read(user_id)
        if not hp.get("db"):
            return jsonify({"success": False, "error": "database not available"}), 503
        prof = dict(hp.get("profile") or {})
        le = prof.get(profile_key) if isinstance(prof.get(profile_key), dict) else {}
        now = datetime.now(timezone.utc)
        last = le.get("last_at")
        if isinstance(last, str) and last:
            try:
                lu = datetime.fromisoformat(last.replace("Z", "+00:00"))
                if (now - lu).total_seconds() < cooldown_sec:
                    rem = int(cooldown_sec - (now - lu).total_seconds())
                    return jsonify({
                        "success": False,
                        "error": "cooldown",
                        "mode": mode,
                        "cooldown_remaining_sec": max(0, rem),
                    }), 429
            except Exception:
                pass

        le["last_at"] = now.isoformat()
        le["count"] = int(le.get("count") or 0) + 1
        prof[profile_key] = le
        prof[f"{profile_key}_updated_at"] = now.isoformat()

        awarded = []
        activity_award = 9.0 if mode == "deep_scan" else 3.0
        game_award = 4.0 if mode == "deep_scan" else 1.0
        xp_award = 20 if mode == "deep_scan" else 6
        reason = "lab_deep_scan" if mode == "deep_scan" else "lab_explore"
        try:
            from backend.services.unified_points_database import unified_points_db
            if unified_points_db and hasattr(unified_points_db, "add_points"):
                unified_points_db.add_points(user_id, "activity_points", activity_award, reason, {"pulse": le["count"], "mode": mode})
                unified_points_db.add_points(user_id, "game_points", game_award, reason, {"pulse": le["count"], "mode": mode})
            awarded.append({"point_type": "activity_points", "amount": int(activity_award)})
            awarded.append({"point_type": "game_points", "amount": int(game_award)})
        except Exception:
            awarded = []

        try:
            from backend.routes.hunters_game import award_xp
            award_xp(user_id, {"xp": xp_award}, xp_source=reason, xp_action_type=mode)
        except Exception:
            pass

        if not _hp_write(user_id, prof):
            return jsonify({"success": False, "error": "could not save profile"}), 500
        try:
            from backend.services.unified_points_sync import unified_points_sync_device
            unified_points_sync_device.record_domain_sync("lab")
        except Exception:
            pass
        return jsonify({
            "success": True,
            "user_id": user_id,
            "mode": mode,
            "exploration_count": le["count"],
            "awarded": awarded,
            "xp_awarded_hunter": xp_award,
            "cooldown_sec": cooldown_sec,
            "explore_cooldown_sec": cooldown_sec,
        }), 200
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


def _draft_cooldown_remaining_sec(prof: dict) -> int:
    raw = prof.get("lab_next_tech_draft_at")
    dt = _parse_iso_utc(raw) if isinstance(raw, str) else None
    if not dt:
        return 0
    return _seconds_remaining_until(dt)


def _refine_cooldown_remaining_sec(item: dict) -> int:
    raw = item.get("next_agent_refine_at")
    dt = _parse_iso_utc(raw) if isinstance(raw, str) else None
    if not dt:
        return 0
    return _seconds_remaining_until(dt)


@lab_bp.route("/api/lab/technologies", methods=["GET"])
def lab_technologies_get():
    """List co-created lab technology drafts for the resolved user."""
    user_id = _resolve_uid()
    hp = _hp_read(user_id)
    if not hp.get("db"):
        return jsonify({
            "success": True,
            "user_id": user_id,
            "technologies": [],
            "draft_cooldown_remaining_sec": 0,
            "storage": "none",
        }), 200
    prof = hp.get("profile") or {}
    techs = _lab_technologies_list_from_profile(prof)
    out_techs = []
    for t in techs:
        if not isinstance(t, dict):
            continue
        td = dict(t)
        td["refine_cooldown_remaining_sec"] = _refine_cooldown_remaining_sec(td)
        out_techs.append(td)
    return jsonify({
        "success": True,
        "user_id": user_id,
        "technologies": out_techs,
        "draft_cooldown_remaining_sec": _draft_cooldown_remaining_sec(prof),
        "storage": "db",
    }), 200


@lab_bp.route("/api/lab/technologies", methods=["POST"])
def lab_technologies_post():
    """Create a draft technology (user + optional agent partner id for later refinement)."""
    user_id = _resolve_uid()
    body = request.get_json(silent=True) or {}
    name = (body.get("name") or "").strip()
    pitch = (body.get("pitch") or body.get("description") or "").strip()
    category = (body.get("category") or "general").strip().lower()
    co_agent_id = (body.get("co_agent_id") or body.get("agent_id") or "lab_agent").strip()[:80] or "lab_agent"

    if len(name) < 2 or len(name) > 120:
        return jsonify({"success": False, "error": "name must be 2–120 characters"}), 400
    if len(pitch) < 8 or len(pitch) > 4000:
        return jsonify({"success": False, "error": "pitch must be 8–4000 characters"}), 400
    if category not in LAB_TECH_CATEGORIES:
        category = "general"

    hp = _hp_read(user_id)
    if not hp.get("db"):
        return jsonify({
            "success": False,
            "error": "Lab technology drafts require the hunters profile database (run migrations / enable DB).",
        }), 503

    prof = dict(hp.get("profile") or {})
    now_dt = _now_utc()
    next_draft = prof.get("lab_next_tech_draft_at")
    ndt = _parse_iso_utc(next_draft) if isinstance(next_draft, str) else None
    if ndt and ndt > now_dt:
        return jsonify({
            "success": False,
            "error": "draft_cooldown",
            "draft_cooldown_remaining_sec": _seconds_remaining_until(ndt, now_dt),
            "message": "New lab technology drafts are on a 1h cooldown per profile.",
        }), 429

    techs = _lab_technologies_list_from_profile(prof)
    if len(techs) >= MAX_LAB_TECHNOLOGIES:
        return jsonify({"success": False, "error": f"max {MAX_LAB_TECHNOLOGIES} technologies per profile"}), 400

    tid = "lt_" + uuid.uuid4().hex[:12]
    ts_iso = datetime.now(timezone.utc).isoformat()
    entry = {
        "id": tid,
        "name": name,
        "pitch": pitch,
        "category": category,
        "co_agent_id": co_agent_id,
        "status": "draft",
        "agent_notes": None,
        "created_at": ts_iso,
        "updated_at": ts_iso,
    }
    techs.append(entry)
    prof["lab_technologies"] = techs
    prof["lab_technologies_updated_at"] = ts_iso
    prof["lab_next_tech_draft_at"] = (now_dt + timedelta(seconds=LAB_TECH_DRAFT_COOLDOWN_SEC)).isoformat()
    if not _hp_write(user_id, prof):
        return jsonify({"success": False, "error": "could not save profile"}), 500
    return jsonify({"success": True, "user_id": user_id, "technology": entry, "storage": "db"}), 200


@lab_bp.route("/api/lab/technologies/<tech_id>/agent-refine", methods=["POST"])
def lab_technologies_agent_refine(tech_id: str):
    """Run agent refinement on one draft (updates agent_notes + status)."""
    user_id = _resolve_uid()
    tid = (tech_id or "").strip().lower()
    if not LAB_TECH_ID_RE.match(tid):
        return jsonify({"success": False, "error": "invalid technology id"}), 400

    hp = _hp_read(user_id)
    if not hp.get("db"):
        return jsonify({"success": False, "error": "database not available"}), 503

    prof = dict(hp.get("profile") or {})
    techs = _lab_technologies_list_from_profile(prof)
    found = None
    for i, t in enumerate(techs):
        if isinstance(t, dict) and t.get("id") == tid:
            found = i
            break
    if found is None:
        return jsonify({"success": False, "error": "technology not found"}), 404

    item = dict(techs[found])
    now = _now_utc()
    nra = item.get("next_agent_refine_at")
    nda = _parse_iso_utc(nra) if isinstance(nra, str) else None
    if nda and nda > now:
        return jsonify({
            "success": False,
            "error": "refine_cooldown",
            "refine_cooldown_remaining_sec": _seconds_remaining_until(nda, now),
            "message": "Agent refine is on a 10h cooldown per draft.",
        }), 429

    name = (item.get("name") or "").strip() or "Untitled"
    pitch = (item.get("pitch") or "").strip()
    co_agent = (item.get("co_agent_id") or "lab_agent").strip()[:80] or "lab_agent"
    notes = _run_agent_refine(name, pitch, co_agent)
    item["agent_notes"] = notes
    item["status"] = "agent_suggested"
    item["updated_at"] = datetime.now(timezone.utc).isoformat()
    item["next_agent_refine_at"] = (now + timedelta(seconds=LAB_AGENT_REFINE_COOLDOWN_SEC)).isoformat()
    techs[found] = item
    prof["lab_technologies"] = techs
    prof["lab_technologies_updated_at"] = item["updated_at"]
    if not _hp_write(user_id, prof):
        return jsonify({"success": False, "error": "could not save profile"}), 500
    return jsonify({"success": True, "user_id": user_id, "technology": item, "storage": "db"}), 200


@lab_bp.route("/api/lab/technologies/<tech_id>/status", methods=["POST"])
def lab_technologies_status_post(tech_id: str):
    """Move a co-created technology through draft/agent_suggested/user_accepted/archived."""
    user_id = _resolve_uid()
    tid = (tech_id or "").strip().lower()
    if not LAB_TECH_ID_RE.match(tid):
        return jsonify({"success": False, "error": "invalid technology id"}), 400
    body = request.get_json(silent=True) or {}
    status = (body.get("status") or "").strip().lower()
    allowed = {"draft", "agent_suggested", "user_accepted", "archived"}
    if status not in allowed:
        return jsonify({"success": False, "error": "invalid status", "allowed": sorted(allowed)}), 400

    hp = _hp_read(user_id)
    if not hp.get("db"):
        return jsonify({"success": False, "error": "database not available"}), 503

    prof = dict(hp.get("profile") or {})
    techs = _lab_technologies_list_from_profile(prof)
    found = None
    for i, t in enumerate(techs):
        if isinstance(t, dict) and t.get("id") == tid:
            found = i
            break
    if found is None:
        return jsonify({"success": False, "error": "technology not found"}), 404

    item = dict(techs[found])
    item["status"] = status
    item["updated_at"] = datetime.now(timezone.utc).isoformat()
    techs[found] = item
    prof["lab_technologies"] = techs
    prof["lab_technologies_updated_at"] = item["updated_at"]
    if not _hp_write(user_id, prof):
        return jsonify({"success": False, "error": "could not save profile"}), 500
    return jsonify({"success": True, "user_id": user_id, "technology": item, "storage": "db"}), 200


MAX_LAB_IDEA_BOARD = 48
LAB_IDEA_ID_RE = re.compile(r"^lib_[a-f0-9]{8,24}$")
LAB_IDEA_PIN_COOLDOWN_SEC = 30 * 60


def _lab_idea_board_from_profile(prof: dict) -> list:
    raw = prof.get("lab_idea_board")
    if not isinstance(raw, list):
        return []
    out = []
    for row in raw:
        if isinstance(row, dict) and isinstance(row.get("id"), str):
            out.append(row)
    return out


def _idea_pin_cooldown_remaining_sec(prof: dict) -> int:
    until = prof.get("lab_next_idea_pin_at")
    if not until:
        return 0
    dt = _parse_iso_utc(until)
    if not dt:
        return 0
    return _seconds_remaining_until(dt)


def _load_platform_news_lab(limit: int = 12) -> list:
    data = _load_data_json("platform_news.json")
    if not isinstance(data, dict):
        return []
    items = data.get("items") or []
    lab_items = []
    for row in items:
        if not isinstance(row, dict):
            continue
        ch = (row.get("channel") or row.get("category") or "").lower()
        if ch == "lab" or "lab" in (row.get("id") or "").lower():
            lab_items.append(row)
    lab_items.sort(key=lambda x: x.get("date") or "", reverse=True)
    return lab_items[:limit] if limit > 0 else lab_items


@lab_bp.route("/api/lab/news", methods=["GET"])
def lab_news_get():
    """Lab-channel news plus featured platform items tagged for the hub."""
    limit = request.args.get("limit", 12, type=int)
    items = _load_platform_news_lab(limit)
    return jsonify({"success": True, "news": items, "count": len(items), "channel": "lab"}), 200


@lab_bp.route("/api/lab/systems-check", methods=["GET"])
def lab_systems_check_get():
    """Recheck all lab hub API functions (in-process line checks)."""
    from flask import current_app
    from backend.services.lab_systems_checks import run_lab_systems_checks

    user_id = _resolve_uid()
    report = run_lab_systems_checks(current_app, user_id)
    hp = _hp_read(user_id)
    prof = dict(hp.get("profile") or {})
    if report.get("all_ok"):
        prof["lab_last_systems_check_ok_at"] = datetime.now(timezone.utc).isoformat()
        if hp.get("db"):
            _hp_write(user_id, prof)
    return jsonify({"success": True, "user_id": user_id, **report}), 200


@lab_bp.route("/api/lab/idea-board", methods=["GET"])
def lab_idea_board_get():
    """Pinned lab ideas for the hub idea board."""
    user_id = _resolve_uid()
    hp = _hp_read(user_id)
    prof = hp.get("profile") or {}
    ideas = _lab_idea_board_from_profile(prof) if hp.get("db") else []
    return jsonify({
        "success": True,
        "user_id": user_id,
        "ideas": ideas[-MAX_LAB_IDEA_BOARD:],
        "pin_cooldown_remaining_sec": _idea_pin_cooldown_remaining_sec(prof) if hp.get("db") else 0,
        "storage": "db" if hp.get("db") else "none",
    }), 200


@lab_bp.route("/api/lab/idea-board", methods=["POST"])
def lab_idea_board_post():
    """Pin a new idea to the lab idea board (30m spacing)."""
    user_id = _resolve_uid()
    body = request.get_json(silent=True) or {}
    title = (body.get("title") or "").strip()[:120]
    body_text = (body.get("body") or body.get("pitch") or "").strip()[:2000]
    track = (body.get("track") or "general").strip().lower()[:40]
    if len(title) < 2 or len(body_text) < 4:
        return jsonify({"success": False, "error": "title (2+) and body (4+) required"}), 400

    hp = _hp_read(user_id)
    if not hp.get("db"):
        return jsonify({"success": False, "error": "database not available"}), 503

    prof = dict(hp.get("profile") or {})
    cd = _idea_pin_cooldown_remaining_sec(prof)
    if cd > 0:
        return jsonify({
            "success": False,
            "error": "pin_cooldown",
            "pin_cooldown_remaining_sec": cd,
        }), 429

    ideas = _lab_idea_board_from_profile(prof)
    now = datetime.now(timezone.utc)
    item = {
        "id": "lib_" + uuid.uuid4().hex[:12],
        "title": title,
        "body": body_text,
        "track": track or "general",
        "status": "pinned",
        "created_at": now.isoformat(),
        "updated_at": now.isoformat(),
    }
    ideas.append(item)
    prof["lab_idea_board"] = ideas[-MAX_LAB_IDEA_BOARD:]
    prof["lab_idea_board_updated_at"] = item["updated_at"]
    prof["lab_next_idea_pin_at"] = (now + timedelta(seconds=LAB_IDEA_PIN_COOLDOWN_SEC)).isoformat()
    if not _hp_write(user_id, prof):
        return jsonify({"success": False, "error": "could not save profile"}), 500
    return jsonify({"success": True, "user_id": user_id, "idea": item, "storage": "db"}), 200


@lab_bp.route("/api/lab/idea-board/<idea_id>/status", methods=["POST"])
def lab_idea_board_status_post(idea_id: str):
    """Archive or promote an idea on the board."""
    user_id = _resolve_uid()
    iid = (idea_id or "").strip().lower()
    if not LAB_IDEA_ID_RE.match(iid):
        return jsonify({"success": False, "error": "invalid idea id"}), 400
    body = request.get_json(silent=True) or {}
    status = (body.get("status") or "").strip().lower()
    allowed = {"pinned", "in_progress", "shipped", "archived"}
    if status not in allowed:
        return jsonify({"success": False, "error": "invalid status", "allowed": sorted(allowed)}), 400

    hp = _hp_read(user_id)
    if not hp.get("db"):
        return jsonify({"success": False, "error": "database not available"}), 503

    prof = dict(hp.get("profile") or {})
    ideas = _lab_idea_board_from_profile(prof)
    found = None
    for i, row in enumerate(ideas):
        if isinstance(row, dict) and row.get("id") == iid:
            found = i
            break
    if found is None:
        return jsonify({"success": False, "error": "idea not found"}), 404

    item = dict(ideas[found])
    item["status"] = status
    item["updated_at"] = datetime.now(timezone.utc).isoformat()
    ideas[found] = item
    prof["lab_idea_board"] = ideas
    prof["lab_idea_board_updated_at"] = item["updated_at"]
    if not _hp_write(user_id, prof):
        return jsonify({"success": False, "error": "could not save profile"}), 500
    return jsonify({"success": True, "user_id": user_id, "idea": item, "storage": "db"}), 200
