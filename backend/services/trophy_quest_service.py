"""
Unified trophy + platform quest service (Game Hub Option C).
File-backed progress, window-based unlock tracking, claim with trophy_points + MN2.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
from datetime import date, datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Set

_TROPHY_QUEST_ID = re.compile(r'^(daily|weekly)_\d{4}-\d{2}-\d{2}_')

_QUEST_DIR = None
_CLAIM_STREAK_DAYS = 7
_CLAIM_STREAK_MN2 = 0.007


def _base() -> str:
    return os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _quest_dir() -> str:
    global _QUEST_DIR
    if _QUEST_DIR is None:
        _QUEST_DIR = os.path.join(_base(), 'data', 'trophy_quests')
        os.makedirs(_QUEST_DIR, exist_ok=True)
    return _QUEST_DIR


def _state_path(user_id: str) -> str:
    safe = ''.join(c if c.isalnum() or c in '-_' else '_' for c in str(user_id))
    return os.path.join(_quest_dir(), f'{safe}.json')


def _load_state(user_id: str) -> Dict[str, Any]:
    path = _state_path(user_id)
    if os.path.exists(path):
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f) or {}
        except (OSError, json.JSONDecodeError):
            pass
    return {}


def _save_state(user_id: str, state: Dict[str, Any]) -> None:
    with open(_state_path(user_id), 'w', encoding='utf-8') as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


def _definitions_by_id() -> dict:
    path = os.path.join(_base(), 'data', 'trophy_definitions.json')
    try:
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f) or {}
    except (OSError, json.JSONDecodeError):
        return {}
    return {str(t.get('id')): t for t in data.get('trophies', []) if t.get('id')}


def _unlocked_ids(user_id: str) -> Set[str]:
    try:
        from backend.services.trophies_db_service import get_user_trophies
        return {str(t.get('id')) for t in (get_user_trophies(user_id) or [])}
    except Exception:
        return set()


def _category_members() -> Dict[str, List[str]]:
    by_cat: Dict[str, List[str]] = {}
    for tid, d in _definitions_by_id().items():
        if d.get('hidden') or d.get('category') == 'seasonal':
            continue
        by_cat.setdefault(d.get('category', 'special'), []).append(tid)
    return by_cat


def _seeded_index(seed: str, modulo: int) -> int:
    h = int(hashlib.sha256(seed.encode('utf-8')).hexdigest(), 16)
    return h % max(1, modulo)


def _quest_rewards(scope: str) -> Dict[str, float]:
    if scope == 'daily':
        return {'trophy_points': 100, 'mn2': 0.001}
    return {'trophy_points': 500, 'mn2': 0.01}


def _claim_streak_info(state: Dict[str, Any]) -> Dict[str, Any]:
    return {
        'days': int(state.get('claim_streak_days') or 0),
        'last_claim_date': state.get('claim_streak_last'),
        'bonus_mn2': _CLAIM_STREAK_MN2,
        'bonus_at_day': _CLAIM_STREAK_DAYS,
    }


def _record_claim_streak(user_id: str, state: Dict[str, Any]) -> Optional[float]:
    """Track consecutive days with at least one quest claim; award MN2 at 7 days."""
    today = date.today().isoformat()
    yesterday = (date.today() - timedelta(days=1)).isoformat()
    last = state.get('claim_streak_last')
    count = int(state.get('claim_streak_days') or 0)
    if last != today:
        if last == yesterday:
            count += 1
        else:
            count = 1
        state['claim_streak_last'] = today
        state['claim_streak_days'] = count

    bonus_mn2 = None
    if count >= _CLAIM_STREAK_DAYS and state.get('claim_streak_bonus_at') != today:
        if count == _CLAIM_STREAK_DAYS or count % _CLAIM_STREAK_DAYS == 0:
            try:
                from backend.services.trophy_level_service import _credit_mn2
                if _credit_mn2(
                    user_id,
                    _CLAIM_STREAK_MN2,
                    'quest_claim_streak',
                    metadata={'streak_days': count},
                ):
                    bonus_mn2 = _CLAIM_STREAK_MN2
                    state['claim_streak_bonus_at'] = today
            except Exception:
                pass
    return bonus_mn2


def _build_ai_quests(user_id: str) -> List[Dict[str, Any]]:
    quests: List[Dict[str, Any]] = []
    try:
        from backend.routes.quest_routes import get_daily_quests_for_hub
        for q in get_daily_quests_for_hub(user_id):
            completed = bool(q.get('completed'))
            target = int(q.get('target_count') or 1)
            quests.append({
                'id': q.get('quest_id'),
                'source': 'ai',
                'scope': 'daily',
                'title': q.get('title') or 'AI Quest',
                'description': q.get('description') or q.get('objective') or '',
                'target': target,
                'progress': target if completed else 0,
                'complete': completed,
                'claimed': completed,
                'reward': 0,
                'xp_reward': int(q.get('xp_reward') or 0),
                'mn2_reward': float(q.get('mn2_reward') or 0),
                'difficulty': q.get('difficulty'),
                'category': q.get('category'),
            })
    except Exception:
        pass
    return quests


def _build_casino_quests(user_id: str) -> List[Dict[str, Any]]:
    quests: List[Dict[str, Any]] = []
    try:
        from backend.services.casino_service import get_daily_quests
        data = get_daily_quests(user_id) or {}
        for q in data.get('quests') or []:
            completed = bool(q.get('completed'))
            claimed = bool(q.get('claimed'))
            quests.append({
                'id': q.get('id'),
                'source': 'casino',
                'scope': 'daily',
                'title': q.get('title') or q.get('id'),
                'description': q.get('description') or '',
                'target': int(q.get('target') or 1),
                'progress': int(q.get('progress') or 0),
                'complete': completed,
                'claimed': claimed,
                'reward': int(q.get('reward_coins') or 0),
                'xp_reward': 0,
                'mn2_reward': 0,
                'coin_reward': int(q.get('reward_coins') or 0),
            })
    except Exception:
        pass
    return quests


def _build_trophy_quests(user_id: str) -> List[Dict[str, Any]]:
    today = date.today()
    week_start = today - timedelta(days=today.weekday())
    week_end = week_start + timedelta(days=7)
    by_cat = _category_members()
    cats = sorted(by_cat.keys())
    unlocked = _unlocked_ids(user_id)
    state = _load_state(user_id)
    quests = []

    for scope, seed_date, expires in (
        ('daily', today.isoformat(), (today + timedelta(days=1)).isoformat()),
        ('weekly', week_start.isoformat(), week_end.isoformat()),
    ):
        if not cats:
            continue
        cat = cats[_seeded_index(seed_date + ':cat', len(cats))]
        members = sorted(by_cat.get(cat, []))
        qid = f'{scope}_{seed_date}_{cat}'
        baseline_key = f'baseline_{qid}'
        baseline = state.get(baseline_key)
        if baseline is None:
            baseline = sum(1 for m in members if m in unlocked)
            state[baseline_key] = baseline
        current_in_cat = sum(1 for m in members if m in unlocked)
        progress = max(0, current_in_cat - int(baseline or 0))
        target = 1 if scope == 'daily' else 3
        rewards = _quest_rewards(scope)
        claimed = bool(state.get(f'claimed_{qid}'))
        quests.append({
            'id': qid,
            'source': 'trophy',
            'scope': scope,
            'category': cat,
            'title': f"{'Daily' if scope == 'daily' else 'Weekly'}: unlock {target} {cat} trophy",
            'target': target,
            'progress': min(progress, target),
            'complete': progress >= target,
            'claimed': claimed,
            'reward': rewards['trophy_points'],
            'mn2_reward': rewards['mn2'],
            'expires': expires,
        })
    _save_state(user_id, state)
    return quests


def get_unified_quests(user_id: str) -> Dict[str, Any]:
    """Trophy + platform + AI daily + casino quests."""
    trophy_q = _build_trophy_quests(user_id)
    platform_q: List[Dict[str, Any]] = []
    try:
        from backend.services.user_engagement import get_quests
        eng = get_quests(user_id) or {}
        for q in eng.get('quests') or []:
            platform_q.append({
                'id': q.get('id'),
                'source': 'platform',
                'scope': q.get('type', 'daily'),
                'title': q.get('title'),
                'description': q.get('description'),
                'target': q.get('target', 1),
                'progress': q.get('progress', 0),
                'complete': bool(q.get('completed')),
                'claimed': bool(q.get('claimed')),
                'reward': q.get('coin_reward', 0),
                'xp_reward': q.get('xp_reward', 0),
                'mn2_reward': 0.0005 if q.get('type') == 'daily' else 0.002,
            })
    except Exception:
        pass
    ai_q = _build_ai_quests(user_id)
    casino_q = _build_casino_quests(user_id)
    state = _load_state(user_id)
    streak = _claim_streak_info(state)
    all_quests = trophy_q + platform_q + ai_q + casino_q
    return {
        'success': True,
        'user_id': user_id,
        'date': date.today().isoformat(),
        'quests': all_quests,
        'trophy_quests': trophy_q,
        'platform_quests': platform_q,
        'ai_quests': ai_q,
        'casino_quests': casino_q,
        'claim_streak': streak,
    }


def is_trophy_quest_id(quest_id: str) -> bool:
    return bool(_TROPHY_QUEST_ID.match(str(quest_id or '')))


def _stories_catalog_ids() -> Set[str]:
    path = os.path.join(_base(), 'data', 'hunters_stories.json')
    try:
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f) or {}
        return {str(s.get('id')) for s in (data.get('stories') or data.get('items') or []) if s.get('id')}
    except (OSError, json.JSONDecodeError):
        return set()


def get_story_progress(user_id: str) -> Dict[str, Any]:
    """Read progress for hunter stories (Game Hub Story tab)."""
    read_ids: List[str] = []
    last_id = None
    state = _load_state(user_id)
    raw = state.get('stories_read') or []
    if isinstance(raw, list):
        read_ids = [str(x) for x in raw]
    last_id = state.get('last_story_id')

    catalog_ids = _stories_catalog_ids()
    total = len(catalog_ids)
    read_set = set(read_ids) & catalog_ids
    read_count = len(read_set)

    continue_story = None
    for sid in sorted(catalog_ids):
        if sid not in read_set:
            continue_story = {'id': sid}
            break
    if continue_story:
        path = os.path.join(_base(), 'data', 'hunters_stories.json')
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f) or {}
            for s in data.get('stories') or []:
                if str(s.get('id')) == continue_story['id']:
                    continue_story['title'] = s.get('title', continue_story['id'])
                    continue_story['icon'] = s.get('icon', '📖')
                    break
        except (OSError, json.JSONDecodeError):
            continue_story.setdefault('title', continue_story['id'])
            continue_story.setdefault('icon', '📖')

    return {
        'total': total,
        'read_count': read_count,
        'read_ids': sorted(read_set),
        'percent': round((read_count / total) * 100) if total else 0,
        'continue': continue_story,
        'last_story_id': last_id,
    }


def mark_story_read(user_id: str, story_id: str) -> Dict[str, Any]:
    """Record that a hunter story was read/opened."""
    story_id = str(story_id or '').strip()
    if not story_id:
        return {'success': False, 'error': 'story_id required'}
    catalog_ids = _stories_catalog_ids()
    if catalog_ids and story_id not in catalog_ids:
        return {'success': False, 'error': 'story_not_found'}

    state = _load_state(user_id)
    read = state.get('stories_read') or []
    if not isinstance(read, list):
        read = []
    if story_id not in read:
        read.append(story_id)
    state['stories_read'] = read
    state['last_story_id'] = story_id
    state[f'story_read_at_{story_id}'] = datetime.now(timezone.utc).isoformat()
    _save_state(user_id, state)
    progress = get_story_progress(user_id)
    return {'success': True, 'story_id': story_id, **progress}


def claim_quest(user_id: str, quest_id: str) -> Dict[str, Any]:
    """Claim trophy, platform, AI, or casino quest."""
    if not quest_id:
        return {'success': False, 'error': 'quest_id required'}

    unified = get_unified_quests(user_id)
    meta = next((x for x in unified.get('quests', []) if x.get('id') == quest_id), None)
    source = (meta or {}).get('source')

    if source == 'ai':
        try:
            from backend.routes.quest_routes import complete_quest_for_user
            result = complete_quest_for_user(user_id, quest_id)
            if result.get('success'):
                state = _load_state(user_id)
                bonus = _record_claim_streak(user_id, state)
                _save_state(user_id, state)
                if bonus:
                    result['streak_bonus_mn2'] = bonus
                result['claim_streak'] = _claim_streak_info(state)
            return result
        except Exception as e:
            return {'success': False, 'error': str(e)}

    if source == 'casino':
        try:
            from backend.services.casino_service import claim_daily_quest
            result = claim_daily_quest(user_id, quest_id)
            if result.get('success'):
                state = _load_state(user_id)
                bonus = _record_claim_streak(user_id, state)
                _save_state(user_id, state)
                if bonus:
                    result['streak_bonus_mn2'] = bonus
                result['claim_streak'] = _claim_streak_info(state)
            return result
        except Exception as e:
            return {'success': False, 'error': str(e)}

    if not is_trophy_quest_id(quest_id):
        try:
            from backend.services.user_engagement import claim_quest_reward
            result = claim_quest_reward(user_id, quest_id)
            if result.get('success'):
                state = _load_state(user_id)
                bonus = _record_claim_streak(user_id, state)
                _save_state(user_id, state)
                if bonus:
                    result['streak_bonus_mn2'] = bonus
                result['claim_streak'] = _claim_streak_info(state)
            return result
        except Exception as e:
            return {'success': False, 'error': str(e)}

    quests = _build_trophy_quests(user_id)
    q = next((x for x in quests if x['id'] == quest_id), None)
    if not q:
        return {'success': False, 'error': 'Quest not found'}
    if not q.get('complete'):
        return {'success': False, 'error': 'Quest not complete'}
    state = _load_state(user_id)
    if state.get(f'claimed_{quest_id}'):
        return {'success': True, 'already_claimed': True, 'quest_id': quest_id}

    pts = float(q.get('reward') or 0)
    mn2 = float(q.get('mn2_reward') or 0)
    credited = False
    credited_mn2 = False
    try:
        from backend.services.unified_points_database import unified_points_db
        if unified_points_db and pts > 0:
            credited = bool(unified_points_db.add_points(
                user_id, 'trophy_points', pts, source='trophy_quest',
                metadata={'quest_id': quest_id},
            ).get('success'))
    except Exception:
        pass
    if mn2 > 0:
        try:
            from backend.services.trophy_level_service import _credit_mn2
            credited_mn2 = _credit_mn2(user_id, mn2, 'trophy_quest', metadata={'quest_id': quest_id})
        except Exception:
            pass

    state[f'claimed_{quest_id}'] = True
    state[f'claimed_at_{quest_id}'] = datetime.now(timezone.utc).isoformat()
    streak_bonus = _record_claim_streak(user_id, state)
    _save_state(user_id, state)
    out = {
        'success': credited or credited_mn2 or pts <= 0,
        'quest_id': quest_id,
        'reward': pts,
        'mn2_reward': mn2,
        'credited': credited,
        'credited_mn2': credited_mn2,
        'claim_streak': _claim_streak_info(state),
    }
    if streak_bonus:
        out['streak_bonus_mn2'] = streak_bonus
    return out
