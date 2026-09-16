"""
Trophies Database Service
Read/write trophy_definitions and user_trophy_unlocks. Safe when migration not run.
"""
from typing import List, Dict, Any, Optional
from sqlalchemy import text, inspect


def _get_db():
    from src.db.models import db
    return db


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
    """Trophies unlocked by user (with definition joined)."""
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
        return [
            {
                'id': r.id, 'name': r.name, 'description': r.description or '', 'category': r.category or '',
                'icon': r.icon or '🏆', 'rarity': r.rarity or 'common',
                'unlocked_at': r.unlocked_at.isoformat() if hasattr(r.unlocked_at, 'isoformat') else str(r.unlocked_at),
            }
            for r in rows
        ]
    except Exception:
        return []


def award_trophy(user_id: str, trophy_id: str, reward: Optional[float] = None) -> bool:
    """Record trophy unlock and add trophy_points to unified points DB. Returns True if recorded or already owned."""
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
        return True
    except Exception:
        try:
            _get_db().session.rollback()
        except Exception:
            pass
        return False
