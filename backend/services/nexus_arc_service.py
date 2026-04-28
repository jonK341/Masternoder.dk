"""
Nexus arc — level definitions, user progress doc, blurbs (LLM or template), streak, co-op hints.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
from datetime import date, timedelta
from typing import Any, Dict, List, Optional, Tuple

_BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_NEXUS_LEVELS_PATH = os.path.join(_BASE_DIR, "data", "nexus_arc_levels.json")
_NEXUS_CLAIMS_DIR = os.path.join(_BASE_DIR, "logs", "hunter_nexus_claims")
_STORIES_PATH = os.path.join(_BASE_DIR, "data", "hunters_stories.json")

_LEVELS_CACHE: Optional[Dict[str, Any]] = None
_REWARDS_CACHE: Optional[Dict[str, Dict[str, int]]] = None


def load_nexus_levels_file() -> Dict[str, Any]:
    global _LEVELS_CACHE
    if _LEVELS_CACHE is not None:
        return _LEVELS_CACHE
    if not os.path.exists(_NEXUS_LEVELS_PATH):
        _LEVELS_CACHE = {"version": 0, "levels": []}
        return _LEVELS_CACHE
    with open(_NEXUS_LEVELS_PATH, "r", encoding="utf-8") as f:
        _LEVELS_CACHE = json.load(f) or {}
    return _LEVELS_CACHE


def build_level_rewards() -> Dict[str, Dict[str, int]]:
    global _REWARDS_CACHE
    if _REWARDS_CACHE is not None:
        return _REWARDS_CACHE
    data = load_nexus_levels_file()
    out: Dict[str, Dict[str, int]] = {}
    for lv in data.get("levels") or []:
        lid = (lv.get("id") or "").strip()
        if not lid:
            continue
        out[lid] = {
            "xp": int(lv.get("xp") or 0),
            "game_points": int(lv.get("game_points") or 0),
        }
    _REWARDS_CACHE = out
    return out


def _claims_path(user_id: str) -> str:
    os.makedirs(_NEXUS_CLAIMS_DIR, exist_ok=True)
    safe = "".join(c for c in (user_id or "default_user") if c.isalnum() or c in ("-", "_"))[:120] or "default_user"
    return os.path.join(_NEXUS_CLAIMS_DIR, f"{safe}.json")


def load_user_doc(user_id: str) -> Dict[str, Any]:
    path = _claims_path(user_id)
    if not os.path.exists(path):
        return {
            "claimed": [],
            "faction": None,
            "daily_bonus_date": None,
            "streak_count": 0,
            "streak_last_day": None,
        }
    try:
        with open(path, "r", encoding="utf-8") as f:
            doc = json.load(f) or {}
    except Exception:
        doc = {}
    if not isinstance(doc.get("claimed"), list):
        doc["claimed"] = []
    if "faction" not in doc:
        doc["faction"] = None
    if doc.get("faction") not in (None, "pathfinder", "vanguard", "weaver"):
        doc["faction"] = None
    doc.setdefault("daily_bonus_date", None)
    doc.setdefault("streak_count", 0)
    doc.setdefault("streak_last_day", None)
    return doc


def save_user_doc(user_id: str, doc: Dict[str, Any]) -> None:
    path = _claims_path(user_id)
    from datetime import datetime

    doc["updated_at"] = datetime.utcnow().isoformat() + "Z"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(doc, f, indent=2)


def update_streak_on_visit(doc: Dict[str, Any]) -> Dict[str, Any]:
    today = date.today().isoformat()
    yesterday = (date.today() - timedelta(days=1)).isoformat()
    last = doc.get("streak_last_day")
    count = int(doc.get("streak_count") or 0)
    if last == today:
        return doc
    if last == yesterday:
        count = max(1, count + 1)
    else:
        count = 1
    doc["streak_count"] = count
    doc["streak_last_day"] = today
    return doc


def friends_count(user_id: str) -> int:
    try:
        from backend.routes.social_routes import _load_social

        data = _load_social()
        return len((data.get("friends") or {}).get(user_id, []) or [])
    except Exception:
        return 0


def battle_total(user_id: str) -> int:
    try:
        from backend.routes.battle_routes import _get_battle_stats

        st = _get_battle_stats(user_id) or {}
        return int(st.get("total_battles") or st.get("total") or 0)
    except Exception:
        return 0


def trophy_story_echo() -> Optional[str]:
    if not os.path.exists(_STORIES_PATH):
        return None
    try:
        with open(_STORIES_PATH, "r", encoding="utf-8") as f:
            data = json.load(f) or {}
        stories = data.get("stories") or []
        if not stories:
            return None
        s = stories[0]
        hook = (s.get("hook") or "").strip()
        if hook:
            return hook[:280]
        lines = (s.get("setting") or {}).get("lines") or []
        if lines:
            return str(lines[0])[:280]
    except Exception:
        pass
    return None


def _hash_seed(*parts: str) -> int:
    h = hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()
    return int(h[:8], 16)


def template_blurb(level_id: str, title: str, story: str, user_id: str, play_seed: str) -> str:
    """Deterministic 'AI-like' one-liner when LLM unavailable."""
    seed = _hash_seed(level_id, user_id, play_seed or "0", date.today().isoformat())
    frames = [
        "Tonight the lattice reads «{t}» as: {s}",
        "A whisper under the signal: {s} ({t})",
        "The director tags this beat—{t}: {s}",
        "Echo log: {s} …filed under {t}.",
        "Calibration note for {t}: {s}",
    ]
    short = (story[:120] + "…") if len(story) > 120 else story
    f = frames[seed % len(frames)]
    return f.format(t=title, s=short)


def llm_blurb(level_title: str, story: str, mood: str) -> Optional[str]:
    key = os.environ.get("OPENAI_API_KEY")
    if not key or not story:
        return None
    try:
        from openai import OpenAI

        client = OpenAI(api_key=key)
        msg = (
            "Write ONE short atmospheric sentence (max 220 characters) for a game chapter card. "
            "No quotes, no meta, no 'as an AI'. Title: "
            + level_title
            + ". Canon line: "
            + story[:400]
            + ". Mood hint: "
            + (mood or "reflective")
        )
        r = client.chat.completions.create(
            model=os.environ.get("NEXUS_BLURB_MODEL", "gpt-4o-mini"),
            messages=[{"role": "user", "content": msg}],
            max_tokens=100,
            temperature=0.9,
        )
        text = (r.choices[0].message.content or "").strip()
        text = re.sub(r"\s+", " ", text)
        return text[:280] if text else None
    except Exception:
        return None


def build_blurbs(
    user_id: str,
    level_ids: List[str],
    play_seed: str,
    director_mood: str,
    use_llm: bool,
) -> Dict[str, Any]:
    data = load_nexus_levels_file()
    by_id = {str(lv.get("id")): lv for lv in (data.get("levels") or [])}
    out: Dict[str, str] = {}
    source = "template"
    for lid in level_ids:
        lv = by_id.get(lid)
        if not lv:
            continue
        title = str(lv.get("title") or lid)
        story = str(lv.get("story") or "")
        text = None
        if use_llm:
            text = llm_blurb(title, story, director_mood)
            if text:
                source = "llm"
        if not text:
            text = template_blurb(lid, title, story, user_id, play_seed)
        out[lid] = text
    return {"blurbs": out, "source": source}


def copilot_suggestion(claimed: List[str], levels: List[Dict[str, Any]]) -> Dict[str, str]:
    """Suggest next tab from first unclaimed level's gate (rules-based)."""
    claimed_set = set(claimed or [])
    for lv in levels:
        lid = lv.get("id")
        if lid in claimed_set:
            continue
        gate = lv.get("gate")
        gates = lv.get("gates")
        if gates and isinstance(gates, dict) and not gate:
            return {"next_tab": "campaign", "reason": "Pick Pathfinder, Vanguard, or Weaver—split gates ahead."}
        if gates and isinstance(gates, dict):
            gate = list(gates.values())[0] if gates else None
        if not gate:
            return {"next_tab": "overview", "reason": "Claim the next chapter from Trophy Hunt."}
        gt = gate.get("type")
        if gt == "tab":
            return {"next_tab": str(gate.get("tab")), "reason": "Open this tab once to satisfy the chapter gate."}
        if gt == "clicks":
            return {"next_tab": "overview", "reason": "Relax-click in Trophy Hunt to pass the gate."}
        if gt == "battle_total_min":
            return {"next_tab": "battle", "reason": "Run a battle, then return—stats must show at least one match."}
        if gt == "friends_min":
            return {"next_tab": "social", "reason": "Add friends in Social—the weave needs allies."}
        if gt == "faction_chosen":
            return {"next_tab": "campaign", "reason": "Pick Pathfinder, Vanguard, or Weaver to unlock Season 2."}
        return {"next_tab": "campaign", "reason": "Check Nexus arc for the next requirement."}
    return {"next_tab": "profile", "reason": "Arc complete—tune your profile."}


def daily_challenge_for_today(user_id: str) -> Dict[str, Any]:
    seed = _hash_seed(user_id, date.today().isoformat())
    challenges = [
        {"id": "d1", "title": "Open Star Map", "tab": "starmap25"},
        {"id": "d2", "title": "Scan Timeline", "tab": "timeline"},
        {"id": "d3", "title": "Visit Social", "tab": "social"},
        {"id": "d4", "title": "Peek Rewards", "tab": "rewards"},
        {"id": "d5", "title": "Read Walkthrough", "tab": "walkthrough"},
    ]
    c = challenges[seed % len(challenges)]
    return c
