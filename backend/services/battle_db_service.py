"""
Battle Database Service
Read/write battle_matches for history and leaderboard. Safe when migration not run.
"""
from typing import List, Dict, Any, Optional
from sqlalchemy import text, inspect


def _get_db():
    from src.db.models import db
    return db


def battle_tables_exist() -> bool:
    try:
        return 'battle_matches' in inspect(_get_db().engine).get_table_names()
    except Exception:
        return False


def record_battle(
    user_id: str,
    battle_id: str,
    opponent_type: str = 'ai',
    difficulty: str = 'balanced',
    result: str = 'win',
    points_delta: int = 0,
) -> Optional[int]:
    """Insert a battle match. Returns match id or None."""
    if not battle_tables_exist():
        return None
    try:
        db = _get_db()
        db.session.execute(
            text("""
                INSERT INTO battle_matches (user_id, battle_id, opponent_type, difficulty, result, points_delta)
                VALUES (:user_id, :battle_id, :opponent_type, :difficulty, :result, :points_delta)
            """),
            {
                'user_id': user_id,
                'battle_id': battle_id,
                'opponent_type': opponent_type,
                'difficulty': difficulty,
                'result': result,
                'points_delta': points_delta,
            }
        )
        row = db.session.execute(text("SELECT last_insert_rowid()")).scalar()
        db.session.commit()
        return row
    except Exception:
        try:
            _get_db().session.rollback()
        except Exception:
            pass
        return None


def get_battle_history(user_id: str, limit: int = 50) -> List[Dict[str, Any]]:
    if not battle_tables_exist():
        return []
    try:
        db = _get_db()
        rows = db.session.execute(
            text("""
                SELECT id, battle_id, opponent_type, difficulty, result, points_delta, created_at
                FROM battle_matches WHERE user_id = :user_id ORDER BY created_at DESC LIMIT :limit
            """),
            {'user_id': user_id, 'limit': limit}
        ).fetchall()
        return [
            {
                'id': r.id,
                'battle_id': r.battle_id,
                'opponent_type': r.opponent_type,
                'difficulty': r.difficulty,
                'result': r.result,
                'points_delta': r.points_delta,
                'created_at': r.created_at.isoformat() if hasattr(r.created_at, 'isoformat') else str(r.created_at),
            }
            for r in rows
        ]
    except Exception:
        return []


def get_battle_leaderboard(limit: int = 10) -> List[Dict[str, Any]]:
    """Leaderboard by wins (then by total battles)."""
    if not battle_tables_exist():
        return []
    try:
        db = _get_db()
        rows = db.session.execute(
            text("""
                SELECT user_id,
                    SUM(CASE WHEN result = 'win' THEN 1 ELSE 0 END) AS wins,
                    SUM(CASE WHEN result = 'loss' THEN 1 ELSE 0 END) AS losses,
                    SUM(CASE WHEN result = 'draw' THEN 1 ELSE 0 END) AS draws,
                    COUNT(*) AS total,
                    SUM(points_delta) AS total_points
                FROM battle_matches
                GROUP BY user_id
                ORDER BY wins DESC, total DESC
                LIMIT :limit
            """),
            {'limit': limit}
        ).fetchall()
        return [
            {
                'user_id': r.user_id,
                'wins': r.wins,
                'losses': r.losses,
                'draws': r.draws,
                'total': r.total,
                'total_points': r.total_points or 0,
            }
            for r in rows
        ]
    except Exception:
        return []
