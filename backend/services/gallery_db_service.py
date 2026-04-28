"""
Gallery Database Service
Record views and downloads; optional catalog. Safe when migration not run.
"""
from typing import List, Dict, Any, Optional
from sqlalchemy import text, inspect


def _get_db():
    from src.db.models import db
    return db


def gallery_tables_exist() -> bool:
    try:
        return 'gallery_downloads' in inspect(_get_db().engine).get_table_names()
    except Exception:
        return False


def record_view(user_id: str, item_id: str) -> bool:
    """Record or update last_viewed_at for user/item. Returns True if recorded."""
    if not gallery_tables_exist():
        return False
    try:
        db = _get_db()
        db.session.execute(
            text("""INSERT INTO user_gallery_state (user_id, item_id, last_viewed_at)
                    VALUES (:uid, :iid, CURRENT_TIMESTAMP)
                    ON CONFLICT(user_id, item_id) DO UPDATE SET last_viewed_at = CURRENT_TIMESTAMP"""),
            {'uid': user_id, 'iid': item_id}
        )
        db.session.commit()
        return True
    except Exception:
        try:
            db.session.rollback()
        except Exception:
            pass
        return False


def record_download(user_id: str, item_id: str) -> bool:
    """Record a download. Returns True if recorded."""
    if not gallery_tables_exist():
        return False
    try:
        db = _get_db()
        db.session.execute(
            text("INSERT INTO gallery_downloads (user_id, item_id) VALUES (:uid, :iid)"),
            {'uid': user_id, 'iid': item_id}
        )
        db.session.commit()
        return True
    except Exception:
        try:
            db.session.rollback()
        except Exception:
            pass
        return False


def get_user_downloads(user_id: str, limit: int = 100) -> Optional[List[Dict[str, Any]]]:
    """List downloads for user. Returns None if DB not available."""
    if not gallery_tables_exist():
        return None
    try:
        db = _get_db()
        rows = db.session.execute(
            text("SELECT item_id, downloaded_at FROM gallery_downloads WHERE user_id = :uid ORDER BY downloaded_at DESC LIMIT :lim"),
            {'uid': user_id, 'lim': limit}
        ).fetchall()
        return [{'item_id': r[0], 'downloaded_at': (r[1].isoformat() if hasattr(r[1], 'isoformat') else str(r[1])) if r[1] else None} for r in rows]
    except Exception:
        return None


def upsert_gallery_item(
    item_id: str,
    title: str = None,
    file_path: str = None,
    status: str = 'completed',
    duration: int = 0,
    category_name: str = None,
    description: str = None,
    prompt: str = None,
    quality_level: str = None,
    quality_score: float = None,
) -> bool:
    """Insert or replace a gallery item (for syncing from filesystem). Returns True if written."""
    if not gallery_tables_exist():
        return False
    try:
        db = _get_db()
        db.session.execute(
            text("""INSERT INTO gallery_items (id, title, file_path, status, duration, category_name, description, prompt, quality_level, quality_score, updated_at)
                    VALUES (:id, :title, :path, :status, :duration, :cat, :desc, :prompt, :qlevel, :qscore, CURRENT_TIMESTAMP)
                    ON CONFLICT(id) DO UPDATE SET title=:title, file_path=COALESCE(:path, file_path), status=:status, duration=:duration,
                    category_name=:cat, description=:desc, prompt=:prompt, quality_level=:qlevel, quality_score=:qscore, updated_at=CURRENT_TIMESTAMP"""),
            {
                'id': item_id, 'title': title or item_id, 'path': file_path, 'status': status, 'duration': duration,
                'cat': category_name, 'desc': description, 'prompt': prompt, 'qlevel': quality_level, 'qscore': quality_score
            }
        )
        db.session.commit()
        try:
            from backend.services.unified_points_sync import unified_points_sync_device
            unified_points_sync_device.record_domain_sync('gallery')
        except Exception:
            pass
        return True
    except Exception:
        try:
            db.session.rollback()
        except Exception:
            pass
        return False
