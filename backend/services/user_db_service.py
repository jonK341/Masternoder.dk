"""
User Database Service
Creates, reads, and updates users in the user_accounts and user_profiles tables.
Safe to call from any context — uses Flask's current app context or creates one.
"""
import json
from datetime import datetime
from typing import Dict, Any, Optional

from sqlalchemy import text


def _get_db():
    from src.db.models import db
    return db


def _in_app_context(fn):
    """Run fn inside a Flask app context. Reuse existing context if available."""
    from flask import has_app_context
    if has_app_context():
        return fn()
    try:
        from flask import current_app
        with current_app.app_context():
            return fn()
    except RuntimeError:
        pass
    try:
        from src.app import create_app
        app = create_app()
        with app.app_context():
            return fn()
    except Exception:
        return None


def ensure_user_account(
    user_id: str,
    username: Optional[str] = None,
    email: Optional[str] = None,
    auth_provider: str = "local",
    ip_address: Optional[str] = None,
    device_fingerprint: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Ensure a user_accounts row exists. Creates if missing, updates last_login if existing.
    Returns {"created": bool, "user_id": str, "account": dict}.
    """
    def _run():
        db = _get_db()
        row = db.session.execute(
            text("SELECT id, user_id, username, email, is_premium, role, last_login, created_at FROM user_accounts WHERE user_id = :uid"),
            {"uid": user_id},
        ).fetchone()

        if row:
            db.session.execute(
                text("UPDATE user_accounts SET last_login = :now, last_ip = :ip WHERE user_id = :uid"),
                {"now": datetime.utcnow().isoformat(), "ip": ip_address, "uid": user_id},
            )
            db.session.commit()
            return {
                "created": False,
                "user_id": user_id,
                "account": {
                    "id": row[0], "user_id": row[1], "username": row[2], "email": row[3],
                    "is_premium": bool(row[4]), "role": row[5],
                    "last_login": datetime.utcnow().isoformat(), "created_at": str(row[7]),
                },
            }

        db.session.execute(
            text("""
                INSERT INTO user_accounts (user_id, username, email, auth_provider, last_login, last_ip, device_fingerprint, role)
                VALUES (:uid, :uname, :email, :auth, :now, :ip, :fp, 'player')
            """),
            {
                "uid": user_id,
                "uname": username or user_id,
                "email": email,
                "auth": auth_provider,
                "now": datetime.utcnow().isoformat(),
                "ip": ip_address,
                "fp": device_fingerprint,
            },
        )
        db.session.commit()

        return {
            "created": True,
            "user_id": user_id,
            "account": {
                "user_id": user_id, "username": username or user_id,
                "email": email, "is_premium": False, "role": "player",
                "last_login": datetime.utcnow().isoformat(),
                "created_at": datetime.utcnow().isoformat(),
            },
        }

    try:
        return _in_app_context(_run) or {"created": False, "user_id": user_id, "account": None, "error": "no app context"}
    except Exception as e:
        return {"created": False, "user_id": user_id, "account": None, "error": str(e)}


def ensure_user_profile(
    user_id: str,
    username: Optional[str] = None,
    preferences: Optional[Dict] = None,
    scraped_info: Optional[Dict] = None,
    agent_skillset_id: Optional[str] = None,
    assigned_agent_ids: Optional[list] = None,
) -> Dict[str, Any]:
    """
    Ensure a user_profiles row exists. Creates if missing.
    """
    def _run():
        db = _get_db()
        row = db.session.execute(
            text("SELECT id FROM user_profiles WHERE user_id = :uid"),
            {"uid": user_id},
        ).fetchone()

        if row:
            return {"created": False, "user_id": user_id}

        db.session.execute(
            text("""
                INSERT INTO user_profiles (user_id, username, preferences, scraped_info, agent_skillset_id, assigned_agent_ids, lifecycle_stage)
                VALUES (:uid, :uname, :prefs, :scraped, :skillset, :agents, 'new')
            """),
            {
                "uid": user_id,
                "uname": username or user_id,
                "prefs": json.dumps(preferences or {}),
                "scraped": json.dumps(scraped_info or {}),
                "skillset": agent_skillset_id,
                "agents": json.dumps(assigned_agent_ids or []),
            },
        )
        db.session.commit()
        return {"created": True, "user_id": user_id}

    try:
        return _in_app_context(_run) or {"created": False, "user_id": user_id, "error": "no app context"}
    except Exception as e:
        return {"created": False, "user_id": user_id, "error": str(e)}


def update_last_login(user_id: str, ip_address: Optional[str] = None) -> bool:
    """Update last_login timestamp for a user."""
    def _run():
        db = _get_db()
        db.session.execute(
            text("UPDATE user_accounts SET last_login = :now, last_ip = :ip WHERE user_id = :uid"),
            {"now": datetime.utcnow().isoformat(), "ip": ip_address, "uid": user_id},
        )
        db.session.commit()
        return True
    try:
        return _in_app_context(_run) or False
    except Exception:
        return False


def update_lifecycle_stage(user_id: str, stage: str) -> bool:
    """Update lifecycle_stage in user_profiles."""
    def _run():
        db = _get_db()
        db.session.execute(
            text("UPDATE user_profiles SET lifecycle_stage = :stage, updated_at = :now WHERE user_id = :uid"),
            {"stage": stage, "now": datetime.utcnow().isoformat(), "uid": user_id},
        )
        db.session.commit()
        return True
    try:
        return _in_app_context(_run) or False
    except Exception:
        return False


def get_user_account(user_id: str) -> Optional[Dict[str, Any]]:
    """Get user account from DB. Returns None if not found."""
    def _run():
        db = _get_db()
        row = db.session.execute(
            text("SELECT id, user_id, username, email, is_premium, role, last_login, last_ip, device_fingerprint, created_at FROM user_accounts WHERE user_id = :uid"),
            {"uid": user_id},
        ).fetchone()
        if not row:
            return None
        return {
            "id": row[0], "user_id": row[1], "username": row[2], "email": row[3],
            "is_premium": bool(row[4]), "role": row[5], "last_login": str(row[6]) if row[6] else None,
            "last_ip": row[7], "device_fingerprint": row[8], "created_at": str(row[9]) if row[9] else None,
        }
    try:
        return _in_app_context(_run)
    except Exception:
        return None


def get_all_users(limit: int = 100, offset: int = 0) -> Dict[str, Any]:
    """List all user accounts."""
    def _run():
        db = _get_db()
        rows = db.session.execute(
            text("SELECT user_id, username, email, is_premium, role, last_login, created_at FROM user_accounts ORDER BY created_at DESC LIMIT :lim OFFSET :off"),
            {"lim": limit, "off": offset},
        ).fetchall()
        total = db.session.execute(text("SELECT COUNT(*) FROM user_accounts")).scalar()
        return {
            "total": total,
            "users": [
                {"user_id": r[0], "username": r[1], "email": r[2], "is_premium": bool(r[3]),
                 "role": r[4], "last_login": str(r[5]) if r[5] else None, "created_at": str(r[6]) if r[6] else None}
                for r in rows
            ],
        }
    try:
        return _in_app_context(_run) or {"total": 0, "users": []}
    except Exception:
        return {"total": 0, "users": []}
