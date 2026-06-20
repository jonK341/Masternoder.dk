"""
Trophy Collector Level Service
Derives collector level from rarity-weighted trophy score and accrues passive
trophy_points income over time. Income is collected on demand (POST /api/trophies/level/collect).
"""
from __future__ import annotations

import json
import os
import threading
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from backend.services.trophy_social_service import RARITY_WEIGHTS, trophy_score

_LEVELS_CACHE: Dict[str, Any] = {'mtime': None, 'data': None}
_LEVELS_LOCK = threading.Lock()


def _base_path() -> str:
    return os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _levels_path() -> str:
    return os.path.join(_base_path(), 'data', 'trophy_levels.json')


def _income_dir() -> str:
    d = os.path.join(_base_path(), 'data', 'trophy_income')
    os.makedirs(d, exist_ok=True)
    return d


def _income_path(user_id: str) -> str:
    safe = ''.join(c if c.isalnum() or c in '-_' else '_' for c in str(user_id))
    return os.path.join(_income_dir(), f'{safe}.json')


def load_level_config() -> Dict[str, Any]:
    path = _levels_path()
    try:
        mtime = os.path.getmtime(path)
    except OSError:
        return {'levels': [], 'max_accrual_hours': 72}
    with _LEVELS_LOCK:
        if _LEVELS_CACHE['mtime'] == mtime and _LEVELS_CACHE['data'] is not None:
            return _LEVELS_CACHE['data']
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f) or {}
        except (OSError, json.JSONDecodeError):
            data = {'levels': [], 'max_accrual_hours': 72}
        _LEVELS_CACHE['mtime'] = mtime
        _LEVELS_CACHE['data'] = data
        return data


def _definitions_by_id() -> dict:
    """Load trophy definitions without importing routes (avoids circular import)."""
    path = os.path.join(_base_path(), 'data', 'trophy_definitions.json')
    try:
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f) or {}
    except (OSError, json.JSONDecodeError):
        return {}
    out = {}
    for t in data.get('trophies', []):
        tid = t.get('id')
        if tid:
            out[str(tid)] = t
    return out


def _user_trophy_score(user_id: str) -> int:
    """Rarity-weighted score from unlocked trophies."""
    rarities: List[str] = []
    try:
        from backend.services.trophies_db_service import get_user_trophies
        unlocked = get_user_trophies(user_id) or []
        defs = _definitions_by_id()
        for t in unlocked:
            tid = str(t.get('id') or '')
            rarities.append((defs.get(tid) or {}).get('rarity', 'common'))
    except Exception:
        pass
    if not rarities:
        try:
            from backend.services.unified_points_database import unified_points_db
            if unified_points_db:
                pts = unified_points_db.get_all_points(user_id) or {}
                points = pts.get('points', pts) if isinstance(pts, dict) else {}
                tp = float(points.get('trophy_points', 0) or 0)
                # Rough fallback: 1 score per 100 trophy points
                return max(0, int(tp / 100))
        except Exception:
            pass
        return 0
    return trophy_score(rarities)


def _level_for_score(score: int, levels: List[Dict]) -> Dict[str, Any]:
    current = levels[0] if levels else {'level': 1, 'name': 'Novice', 'daily_income': 0}
    for lvl in levels:
        if score >= int(lvl.get('min_score', 0) or 0):
            current = lvl
        else:
            break
    return current


def _next_level(current: Dict, levels: List[Dict]) -> Optional[Dict[str, Any]]:
    cur = int(current.get('level', 1) or 1)
    for lvl in levels:
        if int(lvl.get('level', 0) or 0) == cur + 1:
            return lvl
    return None


def _load_income_state(user_id: str) -> Dict[str, Any]:
    path = _income_path(user_id)
    if os.path.exists(path):
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f) or {}
        except (OSError, json.JSONDecodeError):
            pass
    return {}


def _save_income_state(user_id: str, state: Dict[str, Any]) -> None:
    path = _income_path(user_id)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


def _parse_iso(ts: Optional[str]) -> Optional[datetime]:
    if not ts:
        return None
    try:
        dt = datetime.fromisoformat(str(ts).replace('Z', '+00:00'))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except (ValueError, TypeError):
        return None


def _accrued_amount(daily_income: float, hours_elapsed: float, max_hours: float, decimals: int = 2) -> float:
    if daily_income <= 0 or hours_elapsed <= 0:
        return 0.0
    capped = min(hours_elapsed, max_hours)
    return round(daily_income * (capped / 24.0), decimals)


def unlock_mn2_for_rarity(rarity: Optional[str], cfg: Optional[Dict[str, Any]] = None) -> float:
    """MN2 bonus when unlocking a trophy (by rarity table in trophy_levels.json)."""
    data = cfg or load_level_config()
    table = data.get('unlock_mn2_by_rarity') or {}
    return float(table.get(str(rarity or 'common'), 0) or 0)


def _credit_mn2(user_id: str, amount: float, source: str, metadata: Optional[Dict[str, Any]] = None) -> bool:
    if amount <= 0:
        return True
    try:
        from backend.services.unified_points_database import unified_points_db
        if unified_points_db:
            res = unified_points_db.add_points(
                user_id, 'mn2_balance', amount,
                source=source,
                metadata=metadata or {},
            )
            if res.get('success'):
                try:
                    from backend.services.mn2_ledger import append_entry
                    append_entry(user_id, 'trophy_reward', amount, metadata={
                        'source': source,
                        **(metadata or {}),
                    })
                except Exception:
                    pass
                return True
    except Exception:
        pass
    return False


def get_level_status(user_id: str) -> Dict[str, Any]:
    """Full collector level status including pending income."""
    cfg = load_level_config()
    levels = sorted(cfg.get('levels') or [], key=lambda x: int(x.get('level', 0) or 0))
    max_hours = float(cfg.get('max_accrual_hours', 72) or 72)
    score = _user_trophy_score(user_id)
    current = _level_for_score(score, levels)
    nxt = _next_level(current, levels)
    daily = float(current.get('daily_income', 0) or 0)
    daily_mn2 = float(current.get('daily_income_mn2', 0) or 0)
    hourly = round(daily / 24.0, 4)
    hourly_mn2 = round(daily_mn2 / 24.0, 8)

    state = _load_income_state(user_id)
    now = datetime.now(timezone.utc)
    last_collect = _parse_iso(state.get('last_collect_at'))
    if last_collect is None:
        # First visit: start accrual from now (no retroactive windfall)
        last_collect = now
        state['last_collect_at'] = now.isoformat()
        _save_income_state(user_id, state)

    hours_elapsed = max(0.0, (now - last_collect).total_seconds() / 3600.0)
    pending = _accrued_amount(daily, hours_elapsed, max_hours, 2)
    pending_mn2 = _accrued_amount(daily_mn2, hours_elapsed, max_hours, 8)
    cap_reached = hours_elapsed >= max_hours

    progress_pct = 100.0
    score_to_next = 0
    if nxt:
        cur_min = int(current.get('min_score', 0) or 0)
        next_min = int(nxt.get('min_score', 0) or 0)
        score_to_next = max(0, next_min - score)
        span = max(1, next_min - cur_min)
        progress_pct = round(min(100.0, max(0.0, (score - cur_min) / span * 100)), 1)

    return {
        'user_id': user_id,
        'trophy_score': score,
        'level': int(current.get('level', 1) or 1),
        'level_name': current.get('name', 'Novice Collector'),
        'level_icon': current.get('icon', '🏆'),
        'crypto_currency': cfg.get('crypto_currency', 'MN2'),
        'daily_income': daily,
        'daily_income_mn2': daily_mn2,
        'hourly_income': hourly,
        'hourly_income_mn2': hourly_mn2,
        'unlock_bonus_pct': float(current.get('unlock_bonus_pct', 0) or 0),
        'pending_income': pending,
        'pending_income_mn2': pending_mn2,
        'cap_reached': cap_reached,
        'max_accrual_hours': max_hours,
        'hours_since_collect': round(hours_elapsed, 2),
        'last_collect_at': state.get('last_collect_at'),
        'lifetime_collected': float(state.get('lifetime_collected', 0) or 0),
        'lifetime_collected_mn2': float(state.get('lifetime_collected_mn2', 0) or 0),
        'unlock_mn2_by_rarity': cfg.get('unlock_mn2_by_rarity') or {},
        'next_level': {
            'level': int(nxt.get('level', 0) or 0),
            'name': nxt.get('name'),
            'min_score': int(nxt.get('min_score', 0) or 0),
            'daily_income': float(nxt.get('daily_income', 0) or 0),
            'daily_income_mn2': float(nxt.get('daily_income_mn2', 0) or 0),
            'score_needed': score_to_next,
            'progress_pct': progress_pct,
        } if nxt else None,
        'levels': levels,
    }


def collect_income(user_id: str) -> Dict[str, Any]:
    """Credit accrued trophy_points + MN2 income and reset the accrual clock."""
    status = get_level_status(user_id)
    amount = float(status.get('pending_income', 0) or 0)
    amount_mn2 = float(status.get('pending_income_mn2', 0) or 0)
    if amount <= 0 and amount_mn2 <= 0:
        return {
            'success': True,
            'user_id': user_id,
            'collected': 0,
            'collected_mn2': 0,
            'message': 'Nothing to collect yet',
            'level': status.get('level'),
            'daily_income': status.get('daily_income'),
            'daily_income_mn2': status.get('daily_income_mn2'),
        }

    credited = False
    credited_mn2 = False
    try:
        from backend.services.unified_points_database import unified_points_db
        if unified_points_db and amount > 0:
            res = unified_points_db.add_points(
                user_id, 'trophy_points', amount,
                source='trophy_income',
                metadata={
                    'collector_level': status.get('level'),
                    'daily_income': status.get('daily_income'),
                    'hours_accrued': status.get('hours_since_collect'),
                },
            )
            credited = bool(res.get('success'))
    except Exception:
        credited = False

    if amount_mn2 > 0:
        credited_mn2 = _credit_mn2(
            user_id, amount_mn2, 'trophy_income',
            metadata={
                'collector_level': status.get('level'),
                'daily_income_mn2': status.get('daily_income_mn2'),
                'hours_accrued': status.get('hours_since_collect'),
            },
        )

    state = _load_income_state(user_id)
    now = datetime.now(timezone.utc).isoformat()
    state['last_collect_at'] = now
    state['lifetime_collected'] = round(float(state.get('lifetime_collected', 0) or 0) + amount, 2)
    state['lifetime_collected_mn2'] = round(float(state.get('lifetime_collected_mn2', 0) or 0) + amount_mn2, 8)
    state['last_collected_amount'] = amount
    state['last_collected_amount_mn2'] = amount_mn2
    _save_income_state(user_id, state)

    return {
        'success': credited or credited_mn2 or (amount <= 0 and amount_mn2 <= 0),
        'user_id': user_id,
        'collected': amount,
        'collected_mn2': amount_mn2,
        'crypto_currency': status.get('crypto_currency', 'MN2'),
        'credited': credited,
        'credited_mn2': credited_mn2,
        'level': status.get('level'),
        'level_name': status.get('level_name'),
        'daily_income': status.get('daily_income'),
        'daily_income_mn2': status.get('daily_income_mn2'),
        'lifetime_collected': state['lifetime_collected'],
        'lifetime_collected_mn2': state['lifetime_collected_mn2'],
        'last_collect_at': now,
    }


def trophy_unlock_mn2_amount(user_id: str, defn: Dict[str, Any]) -> float:
    """MN2 for a trophy unlock: explicit mn2_reward, else rarity table × collector bonus."""
    explicit = defn.get('mn2_reward')
    if explicit is not None:
        base = float(explicit or 0)
    else:
        base = unlock_mn2_for_rarity(defn.get('rarity'))
    if base <= 0:
        return 0.0
    try:
        score = _user_trophy_score(user_id)
        levels = sorted((load_level_config().get('levels') or []), key=lambda x: int(x.get('level', 0) or 0))
        current = _level_for_score(score, levels)
        bonus_pct = float(current.get('unlock_bonus_pct', 0) or 0)
        return round(base * (1 + bonus_pct / 100.0), 8)
    except Exception:
        return round(base, 8)


def credit_trophy_unlock_mn2(user_id: str, defn: Dict[str, Any], trophy_id: str) -> Dict[str, Any]:
    """Credit MN2 for a new trophy unlock (idempotent caller must gate on new unlock only)."""
    amt = trophy_unlock_mn2_amount(user_id, defn)
    if amt <= 0:
        return {'mn2_reward': 0, 'credited_mn2': False, 'crypto_currency': 'MN2'}
    ok = _credit_mn2(
        user_id, amt, 'trophy_unlock',
        metadata={'trophy_id': trophy_id, 'rarity': defn.get('rarity')},
    )
    return {'mn2_reward': amt, 'credited_mn2': ok, 'crypto_currency': 'MN2'}
