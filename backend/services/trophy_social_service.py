"""
Trophy Social Service
Leaderboard, activity feed, showcase (pinned trophies), and user comparison for the
trophy site. Works with or without the trophy DB tables: leaderboard ranks by
trophy_points from data/user_points/*.json, showcase is file-based, and activity/compare
use the trophy DB when available.
"""
import os
import json
import time
import threading
from typing import List, Dict, Any, Optional

# Rarity weights for the rarity-weighted Trophy Score (Feature 21)
RARITY_WEIGHTS = {'common': 1, 'rare': 3, 'epic': 8, 'legendary': 20}

_LB_CACHE = {'ts': 0.0, 'data': None}
_LB_LOCK = threading.Lock()
_LB_TTL = 60.0


def _base_path() -> str:
    return os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _user_points_dir() -> str:
    return os.path.join(_base_path(), 'data', 'user_points')


def _showcase_dir() -> str:
    return os.path.join(_base_path(), 'data', 'trophy_showcase')


def trophy_score(unlocked_rarities) -> int:
    """Rarity-weighted score from an iterable of rarity strings."""
    return int(sum(RARITY_WEIGHTS.get(str(r or 'common'), 1) for r in unlocked_rarities))


def get_leaderboard(limit: int = 25, current_user: Optional[str] = None) -> Dict[str, Any]:
    """Top collectors ranked by trophy_points (scanned from user_points files, cached).

    Returns {'entries': [...], 'total_players': n, 'current_user_rank': r|None}.
    """
    now = time.time()
    with _LB_LOCK:
        cached = _LB_CACHE['data'] if (now - _LB_CACHE['ts'] < _LB_TTL) else None
    if cached is None:
        rows = []
        d = _user_points_dir()
        try:
            names = os.listdir(d)
        except OSError:
            names = []
        for name in names:
            if not name.endswith('.json'):
                continue
            try:
                with open(os.path.join(d, name), 'r', encoding='utf-8') as f:
                    data = json.load(f)
            except (OSError, ValueError):
                continue
            points = data.get('points', {}) if isinstance(data, dict) else {}
            tp = points.get('trophy_points', 0) or 0
            try:
                tp = float(tp)
            except (TypeError, ValueError):
                tp = 0.0
            if tp <= 0:
                continue
            uid = data.get('user_id') or name[:-5]
            rows.append({'user_id': uid, 'trophy_points': tp})
        rows.sort(key=lambda r: r['trophy_points'], reverse=True)
        with _LB_LOCK:
            _LB_CACHE['ts'] = now
            _LB_CACHE['data'] = rows
        cached = rows

    entries = []
    current_rank = None
    for i, r in enumerate(cached):
        rank = i + 1
        if r['user_id'] == current_user:
            current_rank = rank
        if rank <= limit:
            entries.append({
                'rank': rank,
                'user_id': r['user_id'],
                'trophy_points': int(r['trophy_points']),
                'is_current_user': r['user_id'] == current_user,
            })
    return {'entries': entries, 'total_players': len(cached), 'current_user_rank': current_rank}


def get_activity(user_id: str, limit: int = 15) -> List[Dict[str, Any]]:
    """Recent trophy unlocks for a user (from the trophy DB; empty if tables absent)."""
    try:
        from backend.services.trophies_db_service import get_user_trophies
        rows = get_user_trophies(user_id) or []
    except Exception:
        rows = []
    out = []
    for r in rows[:limit]:
        out.append({
            'trophy_id': r.get('id'),
            'name': r.get('name'),
            'icon': r.get('icon', '🏆'),
            'rarity': r.get('rarity', 'common'),
            'unlocked_at': r.get('unlocked_at'),
        })
    return out


def _showcase_path(user_id: str) -> str:
    safe = ''.join(c for c in str(user_id) if c.isalnum() or c in ('_', '-'))[:80] or 'default_user'
    return os.path.join(_showcase_dir(), safe + '.json')


def get_showcase(user_id: str) -> List[str]:
    """Pinned trophy ids for a user (max 6)."""
    try:
        with open(_showcase_path(user_id), 'r', encoding='utf-8') as f:
            data = json.load(f)
        ids = data.get('trophy_ids', []) if isinstance(data, dict) else []
        return [str(x) for x in ids][:6]
    except (OSError, ValueError):
        return []


def set_showcase(user_id: str, trophy_ids: List[str]) -> List[str]:
    """Replace a user's pinned trophies (max 6). Returns the saved list."""
    ids = []
    for x in (trophy_ids or []):
        sx = str(x)
        if sx and sx not in ids:
            ids.append(sx)
        if len(ids) >= 6:
            break
    try:
        os.makedirs(_showcase_dir(), exist_ok=True)
        with open(_showcase_path(user_id), 'w', encoding='utf-8') as f:
            json.dump({'user_id': user_id, 'trophy_ids': ids}, f)
    except OSError:
        pass
    return ids


def compare_users(user_a: str, user_b: str) -> Dict[str, Any]:
    """Unlocked trophy id sets for two users, for side-by-side comparison."""
    def unlocked_ids(uid):
        try:
            from backend.services.trophies_db_service import get_user_trophies
            return [str(t.get('id')) for t in (get_user_trophies(uid) or [])]
        except Exception:
            return []
    a_ids = unlocked_ids(user_a)
    b_ids = unlocked_ids(user_b)
    a_set, b_set = set(a_ids), set(b_ids)
    return {
        'user_a': {'user_id': user_a, 'unlocked': a_ids, 'count': len(a_ids)},
        'user_b': {'user_id': user_b, 'unlocked': b_ids, 'count': len(b_ids)},
        'a_only': sorted(a_set - b_set),
        'b_only': sorted(b_set - a_set),
        'shared': sorted(a_set & b_set),
    }
