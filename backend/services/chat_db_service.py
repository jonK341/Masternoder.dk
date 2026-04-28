"""
Chat Database Service
Persist chat_sessions and chat_messages. Safe when migration not run.
"""
from typing import List, Dict, Any, Optional
from sqlalchemy import text, inspect


def _get_db():
    from src.db.models import db
    return db


def chat_tables_exist() -> bool:
    try:
        return 'chat_messages' in inspect(_get_db().engine).get_table_names()
    except Exception:
        return False


def _get_or_create_session(user_id: str) -> Optional[int]:
    """Get existing session id for user_id or create one. Returns session_id or None."""
    if not chat_tables_exist():
        return None
    try:
        db = _get_db()
        row = db.session.execute(
            text("SELECT id FROM chat_sessions WHERE user_id = :uid ORDER BY id DESC LIMIT 1"),
            {'uid': user_id}
        ).first()
        if row:
            return row[0]
        db.session.execute(
            text("INSERT INTO chat_sessions (user_id) VALUES (:uid)"),
            {'uid': user_id}
        )
        rid = db.session.execute(text("SELECT last_insert_rowid()")).scalar()
        db.session.commit()
        return rid
    except Exception:
        try:
            db.session.rollback()
        except Exception:
            pass
        return None


def save_message(room_id: str, user_id: str, username: str, message: str, is_ai: bool = False) -> bool:
    """Append a message to the room (session). room_id is e.g. 'global'. Returns True if saved in DB."""
    session_id = _get_or_create_session(room_id)
    if session_id is None:
        return False
    try:
        db = _get_db()
        db.session.execute(
            text("""INSERT INTO chat_messages (session_id, user_id, username, message, is_ai)
                    VALUES (:sid, :uid, :username, :msg, :is_ai)"""),
            {'sid': session_id, 'uid': user_id, 'username': username or user_id, 'msg': message, 'is_ai': 1 if is_ai else 0}
        )
        db.session.commit()
        try:
            from backend.services.unified_points_sync import unified_points_sync_device
            unified_points_sync_device.record_domain_sync('social')
        except Exception:
            pass
        return True
    except Exception:
        try:
            db.session.rollback()
        except Exception:
            pass
        return False


def load_chat_history(room_id: str, limit: int = 50) -> Optional[List[Dict[str, Any]]]:
    """Load recent messages for room (e.g. 'global'). Returns None if DB not available."""
    if not chat_tables_exist():
        return None
    try:
        db = _get_db()
        row = db.session.execute(
            text("SELECT id FROM chat_sessions WHERE user_id = :uid ORDER BY id DESC LIMIT 1"),
            {'uid': room_id}
        ).first()
        if not row:
            return []
        session_id = row[0]
        rows = db.session.execute(
            text("""SELECT user_id, username, message, is_ai, created_at
                     FROM chat_messages WHERE session_id = :sid ORDER BY created_at ASC LIMIT :lim"""),
            {'sid': session_id, 'lim': limit}
        ).fetchall()
        out = []
        for r in rows:
            out.append({
                'user_id': r[0],
                'username': r[1] or r[0],
                'message': r[2],
                'is_ai': bool(r[3]),
                'timestamp': (r[4].isoformat() if hasattr(r[4], 'isoformat') else str(r[4])) if r[4] else None,
            })
        return out
    except Exception:
        return None


def get_messages_since(room_id: str, since_iso: str, limit: int = 100) -> Optional[List[Dict[str, Any]]]:
    """Messages for room after given timestamp. Returns None if DB not available."""
    history = load_chat_history(room_id, limit=limit)
    if history is None:
        return None
    try:
        from datetime import datetime
        since = datetime.fromisoformat(since_iso.replace('Z', '+00:00'))
    except Exception:
        return history
    out = []
    for m in history:
        ts = m.get('timestamp') or ''
        try:
            t = datetime.fromisoformat(ts.replace('Z', '+00:00'))
            if t > since:
                out.append(m)
        except Exception:
            out.append(m)
    return out


def clear_history(room_id: str) -> bool:
    """Delete all messages for the room (session). Returns True if DB cleared."""
    if not chat_tables_exist():
        return False
    try:
        db = _get_db()
        db.session.execute(text("DELETE FROM chat_messages WHERE session_id IN (SELECT id FROM chat_sessions WHERE user_id = :uid)"), {'uid': room_id})
        db.session.execute(text("DELETE FROM chat_sessions WHERE user_id = :uid"), {'uid': room_id})
        db.session.commit()
        return True
    except Exception:
        try:
            db.session.rollback()
        except Exception:
            pass
        return False
