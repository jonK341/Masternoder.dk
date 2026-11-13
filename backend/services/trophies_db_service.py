"""
Trophies Database Service
Read/write trophy_definitions and user_trophy_unlocks. Safe when migration not run.
"""
import json
import os
from typing import List, Dict, Any, Optional
from sqlalchemy import text, inspect


def _get_db():
    from src.db.models import db
    return db


def _definition_for_id(trophy_id: str) -> Dict[str, Any]:
    """Load one trophy definition from the JSON source of truth (no route import)."""
    try:
        base = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        path = os.path.join(base, 'data', 'trophy_definitions.json')
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        for t in (data.get('trophies') or []):
            if str(t.get('id')) == str(trophy_id):
                return dict(t)
    except Exception:
        pass
    return {'id': trophy_id}


def trophies_tables_exist() -> bool:
    try:
        return 'trophy_definitions' in inspect(_get_db().engine).get_table_names()
    except Exception:
        return False


def get_trophy_definitions() -> List[Dict[str, Any]]:
    if not trophies_tables_exist():
        return []
    try:
        db = _get_db()
        rows = db.session.execute(
            text("SELECT id, name, description, category, icon, rarity FROM trophy_definitions")
        ).fetchall()
        return [
            {'id': r.id, 'name': r.name, 'description': r.description or '', 'category': r.category or '',
             'icon': r.icon or '🏆', 'rarity': r.rarity or 'common'}
            for r in rows
        ]
    except Exception:
        return []


def get_user_trophies(user_id: str) -> List[Dict[str, Any]]:
    """Trophies unlocked by user (with definition joined when available).

    Falls back to unlock rows alone when ``trophy_definitions`` is empty so JSON-only
    definitions still count as owned for sync/eligibility.
    """
    if not trophies_tables_exist():
        return []
    try:
        db = _get_db()
        rows = db.session.execute(
            text("""
                SELECT t.id, t.name, t.description, t.category, t.icon, t.rarity, u.unlocked_at
                FROM user_trophy_unlocks u
                JOIN trophy_definitions t ON t.id = u.trophy_id
                WHERE u.user_id = :user_id
                ORDER BY u.unlocked_at DESC
            """),
            {'user_id': user_id}
        ).fetchall()
        if rows:
            return [
                {
                    'id': r.id, 'name': r.name, 'description': r.description or '', 'category': r.category or '',
                    'icon': r.icon or '🏆', 'rarity': r.rarity or 'common',
                    'unlocked_at': r.unlocked_at.isoformat() if hasattr(r.unlocked_at, 'isoformat') else str(r.unlocked_at),
                }
                for r in rows
            ]
        # No join hits (definitions table empty) — still return unlock ids from JSON metadata.
        unlock_rows = db.session.execute(
            text("""
                SELECT trophy_id, unlocked_at FROM user_trophy_unlocks
                WHERE user_id = :user_id ORDER BY unlocked_at DESC
            """),
            {'user_id': user_id}
        ).fetchall()
        out = []
        for r in unlock_rows:
            defn = _definition_for_id(str(r.trophy_id))
            out.append({
                'id': r.trophy_id,
                'name': defn.get('name') or r.trophy_id,
                'description': defn.get('description') or '',
                'category': defn.get('category') or '',
                'icon': defn.get('icon') or '🏆',
                'rarity': defn.get('rarity') or 'common',
                'unlocked_at': r.unlocked_at.isoformat() if hasattr(r.unlocked_at, 'isoformat') else str(r.unlocked_at),
            })
        return out
    except Exception:
        return []


def award_trophy(user_id: str, trophy_id: str, reward: Optional[float] = None) -> bool:
    """Record trophy unlock and add trophy_points / MN2. Returns True only on a new unlock."""
    if not trophies_tables_exist():
        return False
    try:
        db = _get_db()
        existing = db.session.execute(
            text("SELECT 1 FROM user_trophy_unlocks WHERE user_id = :user_id AND trophy_id = :trophy_id"),
            {'user_id': user_id, 'trophy_id': trophy_id},
        ).fetchone()
        newly_unlocked = existing is None
        db.session.execute(
            text("INSERT OR IGNORE INTO user_trophy_unlocks (user_id, trophy_id) VALUES (:user_id, :trophy_id)"),
            {'user_id': user_id, 'trophy_id': trophy_id}
        )
        db.session.commit()
        if newly_unlocked:
            amount = float(reward) if reward is not None else 100.0
            try:
                from backend.services.unified_points_database import unified_points_db
                if unified_points_db:
                    unified_points_db.add_points(
                        user_id, 'trophy_points', amount,
                        source='trophy', metadata={'trophy_id': trophy_id}
                    )
            except Exception:
                pass
            # Tough trophies (epic/legendary, or explicit mn2_reward) pay MasterNoder2 coins.
            try:
                from backend.services.trophy_level_service import credit_trophy_unlock_mn2
                defn = _definition_for_id(str(trophy_id))
                if reward is not None and 'reward' not in defn:
                    defn['reward'] = reward
                credit_trophy_unlock_mn2(user_id, defn, str(trophy_id))
            except Exception:
                pass
            try:
                from backend.services.user_engagement import on_trophy_unlocked
                on_trophy_unlocked(user_id)
            except Exception:
                pass
        try:
            from backend.services.unified_points_sync import unified_points_sync_device
            unified_points_sync_device.record_domain_sync('trophies')
        except Exception:
            pass
        return newly_unlocked
    except Exception:
        try:
            _get_db().session.rollback()
        except Exception:
            pass
        return False
