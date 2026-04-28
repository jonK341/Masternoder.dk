"""
Generator/Jobs Database Service
Persist video_generation_jobs. Safe when migration not run.
"""
import json
from typing import Dict, Any, Optional, List
from sqlalchemy import text, inspect


def _get_db():
    from src.db.models import db
    return db


def generator_tables_exist() -> bool:
    try:
        return 'video_generation_jobs' in inspect(_get_db().engine).get_table_names()
    except Exception:
        return False


def _row_to_job(r) -> Optional[Dict[str, Any]]:
    if not r:
        return None
    try:
        config = r[6]
        if isinstance(config, str):
            try:
                config = json.loads(config) if config else {}
            except (json.JSONDecodeError, TypeError):
                config = {}
        else:
            config = config if config is not None else {}
    except (IndexError, TypeError):
        config = {}
    try:
        clips = r[7]
        if isinstance(clips, str):
            try:
                clips = json.loads(clips) if clips else []
            except (json.JSONDecodeError, TypeError):
                clips = []
        else:
            clips = clips if clips is not None else []
    except (IndexError, TypeError):
        clips = []
    return {
        'id': r[0],
        'user_id': r[1],
        'type': r[2],
        'status': r[3],
        'progress': r[4] or 0,
        'theme': r[5],
        'config': config,
        'clips': clips,
        'video_url': r[8],
        'error_message': r[9],
        'estimated_time': r[10] or 0,
        'actual_time': r[11] or 0,
        'points_earned': float(r[12] or 0),
        'created_at': r[13].isoformat() if hasattr(r[13], 'isoformat') else r[13],
        'updated_at': r[14].isoformat() if hasattr(r[14], 'isoformat') else r[14],
        'completed_at': r[15].isoformat() if r[15] and hasattr(r[15], 'isoformat') else r[15],
    }


def get_job(job_id: str) -> Optional[Dict[str, Any]]:
    """Get video job by id. Returns None if not in DB or tables missing."""
    if not generator_tables_exist():
        return None
    try:
        db = _get_db()
        r = db.session.execute(
            text("""
                SELECT job_id, user_id, job_type, status, progress, theme, config, clips, video_url,
                       error_message, estimated_time, actual_time, points_earned, created_at, updated_at, completed_at
                FROM video_generation_jobs WHERE job_id = :jid
            """),
            {"jid": job_id}
        ).fetchone()
        return _row_to_job(r)
    except Exception:
        return None


def save_job(job_data: Dict[str, Any]) -> bool:
    """Insert or replace job. Returns True if saved."""
    if not generator_tables_exist():
        return False
    try:
        db = _get_db()
        jid = job_data.get('job_id') or job_data.get('id')
        if not jid:
            return False
        cfg = job_data.get('config')
        clips = job_data.get('clips', [])
        db.session.execute(
            text("""
                INSERT INTO video_generation_jobs
                (job_id, user_id, job_type, status, progress, theme, config, clips, video_url,
                 error_message, estimated_time, actual_time, points_earned, completed_at)
                VALUES (:job_id, :user_id, :job_type, :status, :progress, :theme, :config, :clips, :video_url,
                        :error_message, :estimated_time, :actual_time, :points_earned, :completed_at)
                ON CONFLICT(job_id) DO UPDATE SET
                    user_id=excluded.user_id, job_type=excluded.job_type, status=excluded.status,
                    progress=excluded.progress, theme=excluded.theme, config=excluded.config, clips=excluded.clips,
                    video_url=excluded.video_url, error_message=excluded.error_message,
                    estimated_time=excluded.estimated_time, actual_time=excluded.actual_time,
                    points_earned=excluded.points_earned, completed_at=excluded.completed_at,
                    updated_at=CURRENT_TIMESTAMP
            """),
            {
                "job_id": jid,
                "user_id": job_data.get('user_id'),
                "job_type": job_data.get('job_type') or job_data.get('type', 'documentary'),
                "status": job_data.get('status', 'pending'),
                "progress": int(job_data.get('progress', 0)),
                "theme": job_data.get('theme'),
                "config": json.dumps(cfg) if not isinstance(cfg, str) else cfg,
                "clips": json.dumps(clips) if not isinstance(clips, str) else clips,
                "video_url": job_data.get('video_url'),
                "error_message": job_data.get('error_message'),
                "estimated_time": int(job_data.get('estimated_time', 0)),
                "actual_time": int(job_data.get('actual_time', 0)),
                "points_earned": float(job_data.get('points_earned', 0)),
                "completed_at": job_data.get('completed_at'),
            }
        )
        db.session.commit()
        return True
    except Exception:
        try:
            db.session.rollback()
        except Exception:
            pass
        return False


def list_jobs(user_id: Optional[str] = None, limit: int = 50) -> Optional[List[Dict[str, Any]]]:
    """List recent jobs, optionally by user_id. Returns None if tables missing."""
    if not generator_tables_exist():
        return None
    try:
        db = _get_db()
        if user_id:
            rows = db.session.execute(
                text("""
                    SELECT job_id, user_id, job_type, status, progress, theme, config, clips, video_url,
                           error_message, estimated_time, actual_time, points_earned, created_at, updated_at, completed_at
                    FROM video_generation_jobs WHERE user_id = :uid ORDER BY created_at DESC LIMIT :lim
                """),
                {"uid": user_id, "lim": limit}
            ).fetchall()
        else:
            rows = db.session.execute(
                text("""
                    SELECT job_id, user_id, job_type, status, progress, theme, config, clips, video_url,
                           error_message, estimated_time, actual_time, points_earned, created_at, updated_at, completed_at
                    FROM video_generation_jobs ORDER BY created_at DESC LIMIT :lim
                """),
                {"lim": limit}
            ).fetchall()
        return [_row_to_job(r) for r in rows if r]
    except Exception:
        return None


def get_job_statistics(user_id: Optional[str] = None, days: int = 7) -> Optional[Dict[str, Any]]:
    """Aggregate job counts by status; optional user_id and last N days. Returns None if tables missing."""
    if not generator_tables_exist():
        return None
    try:
        db = _get_db()
        base_sql = """
            SELECT status, COUNT(*) as cnt FROM video_generation_jobs
            WHERE created_at >= datetime('now', :days_offset)
        """
        params = {"days_offset": f'-{int(days)} days'}
        if user_id:
            base_sql += " AND user_id = :uid"
            params["uid"] = user_id
        base_sql += " GROUP BY status"
        rows = db.session.execute(text(base_sql), params).fetchall()
        by_status = {r[0]: r[1] for r in rows if r}
        total = sum(by_status.values())
        return {
            "total_jobs": total,
            "by_status": by_status,
            "days": days,
            "user_id": user_id,
        }
    except Exception:
        return None


def get_job_performance(user_id: Optional[str] = None, limit: int = 100) -> Optional[Dict[str, Any]]:
    """Simple performance stats: completed count, failed count, success rate, avg actual_time. Returns None if tables missing."""
    if not generator_tables_exist():
        return None
    try:
        db = _get_db()
        where = "WHERE status IN ('completed', 'failed', 'error')"
        params = {"lim": limit}
        if user_id:
            where += " AND user_id = :uid"
            params["uid"] = user_id
        rows = db.session.execute(
            text(f"""
                SELECT status, actual_time FROM video_generation_jobs
                {where}
                ORDER BY created_at DESC LIMIT :lim
            """),
            params
        ).fetchall()
        completed = sum(1 for r in rows if r[0] == 'completed')
        failed = sum(1 for r in rows if r[0] in ('failed', 'error'))
        times = [r[1] for r in rows if r[0] == 'completed' and r[1] is not None and r[1] > 0]
        avg_time_sec = sum(times) / len(times) if times else 0
        total = completed + failed
        success_rate = (completed / total * 100) if total else 0
        return {
            "completed_count": completed,
            "failed_count": failed,
            "success_rate_percent": round(success_rate, 1),
            "success_rate": round(success_rate / 100.0, 2),
            "avg_completion_time_seconds": round(avg_time_sec, 1),
            "avg_speed": round(avg_time_sec, 1),
            "sample_size": total,
        }
    except Exception:
        return None


def get_job_count(user_id: Optional[str] = None) -> Optional[int]:
    """Total job count, optionally by user_id. Returns None if tables missing."""
    if not generator_tables_exist():
        return None
    try:
        db = _get_db()
        if user_id:
            r = db.session.execute(
                text("SELECT COUNT(*) FROM video_generation_jobs WHERE user_id = :uid"),
                {"uid": user_id}
            ).scalar()
        else:
            r = db.session.execute(text("SELECT COUNT(*) FROM video_generation_jobs")).scalar()
        return int(r) if r is not None else 0
    except Exception:
        return None


def get_theme_distribution(user_id: Optional[str] = None, days: int = 30) -> Optional[Dict[str, int]]:
    """Count jobs by theme (theme column or config). Returns None if tables missing."""
    if not generator_tables_exist():
        return None
    try:
        db = _get_db()
        params = {"days_offset": f"-{int(days)} days"}
        where = "WHERE created_at >= datetime('now', :days_offset)"
        if user_id:
            where += " AND user_id = :uid"
            params["uid"] = user_id
        rows = db.session.execute(
            text(f"""
                SELECT COALESCE(theme, 'default') as t, COUNT(*) as cnt
                FROM video_generation_jobs {where}
                GROUP BY t
            """),
            params
        ).fetchall()
        return {r[0]: r[1] for r in rows if r}
    except Exception:
        return None
