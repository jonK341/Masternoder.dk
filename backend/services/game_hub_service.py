"""
Game Hub — unified overview for frontpage tabs: trophies, quests, game, battle, story.
"""
from __future__ import annotations

import json
import os
import time
from typing import Any, Dict, List, Optional, Tuple

try:
    import fcntl
except ImportError:  # Windows dev
    fcntl = None  # type: ignore

_OVERVIEW_CACHE: Dict[str, Tuple[float, Dict[str, Any]]] = {}
_OVERVIEW_CACHE_TTL_SEC = float(os.environ.get("GAME_HUB_OVERVIEW_CACHE_TTL", "45"))


def _overview_shared_cache_path() -> str:
    override = (os.environ.get("GAME_HUB_OVERVIEW_CACHE_FILE") or "").strip()
    if override:
        return override
    return os.path.join(_base_dir(), "logs", "game_hub_overview_cache.json")


def _resolve_uid_fallback(user_id: str) -> str:
    return user_id or 'default_user'


def _base_dir() -> str:
    return os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _load_stories_catalog() -> List[Dict[str, Any]]:
    path = os.path.join(_base_dir(), 'data', 'hunters_stories.json')
    if not os.path.isfile(path):
        return []
    try:
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f) or {}
        return list(data.get('stories') or data.get('items') or [])
    except (OSError, json.JSONDecodeError):
        return []


def mark_story_read(user_id: str, story_id: str) -> Dict[str, Any]:
    from backend.services.trophy_quest_service import mark_story_read as _mark
    return _mark(user_id, story_id)


def get_story_progress(user_id: str) -> Dict[str, Any]:
    from backend.services.trophy_quest_service import get_story_progress as _progress
    return _progress(user_id)


def _active_mission(quests: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """First in-progress quest for Game tab (#22)."""
    for q in quests:
        if q.get('claimed'):
            continue
        if q.get('complete'):
            continue
        return {
            'id': q.get('id'),
            'title': q.get('title'),
            'source': q.get('source'),
            'progress': q.get('progress', 0),
            'target': q.get('target', 1),
        }
    return None


def _read_shared_overview_cache(user_id: str) -> Optional[Dict[str, Any]]:
    if fcntl is None:
        return None
    path = _overview_shared_cache_path()
    if not os.path.isfile(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            fcntl.flock(f.fileno(), fcntl.LOCK_SH)
            try:
                store = json.load(f) or {}
            finally:
                fcntl.flock(f.fileno(), fcntl.LOCK_UN)
        entry = store.get(user_id)
        if not entry or not isinstance(entry, dict):
            return None
        ts = float(entry.get("ts") or 0)
        payload = entry.get("payload")
        if not isinstance(payload, dict):
            return None
        if (time.time() - ts) >= _OVERVIEW_CACHE_TTL_SEC:
            return None
        return payload
    except (OSError, json.JSONDecodeError, TypeError, ValueError):
        return None


def _write_shared_overview_cache(user_id: str, payload: Dict[str, Any]) -> None:
    if fcntl is None:
        return
    path = _overview_shared_cache_path()
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    now = time.time()
    store: Dict[str, Any] = {}
    try:
        if os.path.isfile(path):
            with open(path, "r", encoding="utf-8") as f:
                fcntl.flock(f.fileno(), fcntl.LOCK_SH)
                try:
                    store = json.load(f) or {}
                finally:
                    fcntl.flock(f.fileno(), fcntl.LOCK_UN)
    except (OSError, json.JSONDecodeError):
        store = {}
    store[user_id] = {"ts": now, "payload": payload}
    cutoff = now - (_OVERVIEW_CACHE_TTL_SEC * 2)
    store = {
        k: v
        for k, v in store.items()
        if isinstance(v, dict) and float(v.get("ts") or 0) >= cutoff
    }
    tmp = f"{path}.tmp"
    try:
        with open(tmp, "w", encoding="utf-8") as f:
            fcntl.flock(f.fileno(), fcntl.LOCK_EX)
            try:
                json.dump(store, f)
                f.flush()
                os.fsync(f.fileno())
            finally:
                fcntl.flock(f.fileno(), fcntl.LOCK_UN)
        os.replace(tmp, path)
    except OSError:
        try:
            os.unlink(tmp)
        except OSError:
            pass


def warm_overview_cache(user_id: str = "default_user") -> None:
    """Pre-build overview (uWSGI postfork / ops warm-up)."""
    get_overview(user_id)


def get_overview(user_id: str) -> Dict[str, Any]:
    user_id = _resolve_uid_fallback(user_id)
    now = time.time()
    cached = _OVERVIEW_CACHE.get(user_id)
    if cached and (now - cached[0]) < _OVERVIEW_CACHE_TTL_SEC:
        return cached[1]
    shared = _read_shared_overview_cache(user_id)
    if shared is not None:
        _OVERVIEW_CACHE[user_id] = (now, shared)
        return shared
    payload = _build_overview(user_id)
    _OVERVIEW_CACHE[user_id] = (now, payload)
    _write_shared_overview_cache(user_id, payload)
    return payload


def _build_overview(user_id: str) -> Dict[str, Any]:
    out: Dict[str, Any] = {'success': True, 'user_id': user_id, 'tabs': {}, 'summary': {}}

    unified_quests: List[Dict[str, Any]] = []
    claim_streak = {'days': 0, 'bonus_at_day': 7, 'bonus_mn2': 0.007}

    # Quests (also feeds summary + active mission)
    try:
        from backend.services.trophy_quest_service import get_unified_quests
        q = get_unified_quests(user_id)
        unified_quests = q.get('quests') or []
        claim_streak = q.get('claim_streak') or claim_streak
        active = [x for x in unified_quests if not x.get('claimed')]
        complete = [x for x in unified_quests if x.get('complete') and not x.get('claimed')]
        out['tabs']['quests'] = {
            'total': len(unified_quests),
            'claimable': len(complete),
            'active': len(active),
            'quests': unified_quests[:12],
            'trophy_quests': q.get('trophy_quests') or [],
            'platform_quests': q.get('platform_quests') or [],
            'ai_quests': q.get('ai_quests') or [],
            'casino_quests': q.get('casino_quests') or [],
            'claim_streak': claim_streak,
            'link': '/quests/',
        }
        out['summary']['claimable'] = len(complete)
        out['summary']['claim_streak'] = claim_streak
    except Exception:
        out['tabs']['quests'] = {'link': '/quests/', 'quests': []}
        out['summary']['claimable'] = 0

    # Trophies + mini leaderboard (#19)
    try:
        from backend.services.trophy_level_service import get_level_status
        from backend.services.trophies_db_service import get_user_trophies
        from backend.services.trophy_social_service import get_leaderboard
        level = get_level_status(user_id)
        unlocked = get_user_trophies(user_id) or []
        lb = get_leaderboard(limit=5, current_user=user_id)
        out['tabs']['trophies'] = {
            'collector_level': level.get('level'),
            'level_name': level.get('level_name'),
            'trophy_score': level.get('trophy_score'),
            'pending_income': level.get('pending_income'),
            'pending_income_mn2': level.get('pending_income_mn2'),
            'unlocked_count': len(unlocked),
            'leaderboard': lb.get('entries') or [],
            'your_rank': lb.get('current_user_rank'),
            'link': '/trophies/',
        }
    except Exception:
        out['tabs']['trophies'] = {'link': '/trophies/', 'unlocked_count': 0, 'leaderboard': []}

    # Game — hunter level + active mission (#22)
    try:
        from backend.services.unified_points_database import unified_points_db
        from backend.routes.hunters_game import get_user_level_info
        pts = {}
        if unified_points_db:
            raw = unified_points_db.get_all_points(user_id) or {}
            pts = raw.get('points', raw) if isinstance(raw, dict) else {}
        hunter = get_user_level_info(user_id) or {}
        mission = _active_mission(unified_quests)
        out['tabs']['game'] = {
            'level': pts.get('level', 1),
            'xp_total': pts.get('xp_total', 0),
            'game_points': pts.get('game_points', 0),
            'quest_points': pts.get('quest_points', 0),
            'hunter_level': hunter.get('current_level', 1),
            'hunter_title': hunter.get('title', 'Novice Hunter'),
            'hunter_xp': hunter.get('total_xp', 0),
            'active_mission': mission,
            'link': '/game/',
        }
    except Exception:
        out['tabs']['game'] = {'link': '/game/'}

    # Battle — last 3 matches (#20)
    try:
        from backend.services.unified_points_database import unified_points_db
        from backend.services.battle_db_service import get_battle_history
        bp = 0
        if unified_points_db:
            raw = unified_points_db.get_all_points(user_id) or {}
            pts = raw.get('points', raw) if isinstance(raw, dict) else {}
            bp = float(pts.get('battle_points', 0) or 0)
        recent = get_battle_history(user_id, limit=3) or []
        out['tabs']['battle'] = {
            'battle_points': bp,
            'recent_matches': recent,
            'wins': sum(1 for m in recent if m.get('result') == 'win'),
            'link': '/battle/',
            'quick_battle': '/battle/#quick',
        }
    except Exception:
        out['tabs']['battle'] = {'link': '/battle/', 'recent_matches': []}

    # Story — read progress + continue CTA (#21)
    try:
        catalog = _load_stories_catalog()
        progress = get_story_progress(user_id)
        stories = [
            {'title': s.get('title', s.get('id', 'Story')), 'id': s.get('id'), 'icon': s.get('icon', '📖')}
            for s in catalog[:5]
        ]
        cont = progress.get('continue') or {}
        out['tabs']['story'] = {
            'count': len(catalog),
            'stories': stories,
            'read_count': progress.get('read_count', 0),
            'read_percent': progress.get('percent', 0),
            'continue_story': cont,
            'continue_link': '/trophies/#stories' + (f"?story={cont.get('id')}" if cont.get('id') else ''),
            'link': '/trophies/#stories',
            'shop_link': '/shop/',
        }
    except Exception:
        out['tabs']['story'] = {'link': '/game/#stories', 'stories': []}

    if 'claimable' not in out['summary']:
        out['summary']['claimable'] = 0
    out['summary']['has_notifications'] = out['summary']['claimable'] > 0

    return out
