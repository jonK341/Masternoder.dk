"""
Unified Points Sync Device — single source of truth for the point system and site-wide sync.

OUTLINE / PROGRESS:
==================
1. State storage: Database (sync_state, sync_domain_state) with JSON fallback
2. Audit: All sync events logged to sync_audit table
3. Health: Success/failure counts in sync_health table
4. Error logging: Sync failures logged to error_logging service
5. Domains: 30+ domains tracked (points, users, profiles, battle, shop, etc.)

AUDITING & LOGGING STATEMENT:
- Every record_domain_sync and record_points_activity is audited.
- Failures are logged to error_logging and sync_health.
- State is persisted to database; JSON fallback for backward compatibility.
"""
import os
import json
from datetime import datetime, date
from typing import Dict, Optional, Any, List

_BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_SYNC_STATE_FILE = os.path.join(_BASE_DIR, "logs", "unified_points_sync", "sync_state.json")

# All sync domains — add new domains here when connecting a feature
SYNC_DOMAINS = [
    "unified_points", "users", "profiles",
    "aggregator", "trophies", "achievements", "battle", "shop", "quests",
    "leaderboards", "analytics", "compendium", "generator", "gallery",
    "stats", "social", "points", "agent_skillsets", "agent_knowledge",
    "game", "paypal", "login", "onboarding",
    "communication_psychology", "dna", "game_save", "agent_activity",
    "referral", "notifications", "auto_save", "templates",
]


# =============================================================================
# DATABASE HELPERS — State stored in DB; fallback to JSON
# =============================================================================

# Avoid re-entry: do not call create_app() from inside app creation (e.g. during blueprint import).
_app_creation_in_progress = False

def _get_db():
    """Get database with app context. Returns (app, db) or None. Never calls create_app() during app creation."""
    if _app_creation_in_progress:
        return None
    try:
        from src.app import create_app
        from src.db.models import db
        app = create_app()
        return app, db
    except Exception:
        return None


def _load_state_from_db() -> Optional[Dict[str, Any]]:
    """Load sync state from database. Returns None if DB unavailable."""
    ctx = _get_db()
    if not ctx:
        return None
    app, db = ctx
    try:
        with app.app_context():
            from sqlalchemy import text
            row = db.session.execute(
                text("SELECT last_sync_at, last_sync_source, sync_count, state_json FROM sync_state WHERE id = 1")
            ).fetchone()
            if row:
                domains = {}
                if row[3]:
                    try:
                        domains = json.loads(row[3])
                    except Exception:
                        pass
                return {
                    "last_sync_at": row[0],
                    "last_sync_source": row[1],
                    "sync_count": int(row[2] or 0),
                    "domains": domains,
                    "per_user": domains.get("_per_user", {}),
                }
    except Exception:
        pass
    return None


def _save_state_to_db(state: Dict[str, Any]) -> bool:
    """Save sync state to database. Returns True on success."""
    ctx = _get_db()
    if not ctx:
        return False
    app, db = ctx
    try:
        with app.app_context():
            from sqlalchemy import text
            domains_json = json.dumps(state.get("domains", {}))
            db.session.execute(
                text("""
                    UPDATE sync_state SET
                        last_sync_at = :last_sync_at,
                        last_sync_source = :last_sync_source,
                        sync_count = :sync_count,
                        state_json = :state_json,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = 1
                """),
                {
                    "last_sync_at": state.get("last_sync_at"),
                    "last_sync_source": state.get("last_sync_source"),
                    "sync_count": state.get("sync_count", 0),
                    "state_json": domains_json,
                }
            )
            db.session.commit()
            return True
    except Exception as e:
        try:
            db.session.rollback()
        except Exception:
            pass
        _log_sync_error("save_state", str(e), {"state_keys": list(state.keys())})
        return False


def _load_domain_from_db(domain: str) -> Optional[Dict]:
    """Load single domain state from sync_domain_state table."""
    ctx = _get_db()
    if not ctx:
        return None
    app, db = ctx
    try:
        with app.app_context():
            from sqlalchemy import text
            row = db.session.execute(
                text("SELECT last_sync_at, count, extra_json FROM sync_domain_state WHERE domain = :d"),
                {"d": domain}
            ).fetchone()
            if row:
                return {"last_sync_at": row[0], "count": row[1], "extra": json.loads(row[2]) if row[2] else {}}
    except Exception:
        pass
    return None


def _save_domain_to_db(domain: str, last_sync_at: str, count: Optional[int], extra: Optional[Dict]) -> bool:
    """Upsert domain state in sync_domain_state table."""
    ctx = _get_db()
    if not ctx:
        return False
    app, db = ctx
    try:
        with app.app_context():
            from sqlalchemy import text
            extra_json = json.dumps(extra or {})
            db.session.execute(
                text("""
                    INSERT INTO sync_domain_state (domain, last_sync_at, count, extra_json, updated_at)
                    VALUES (:d, :lsa, :c, :ex, CURRENT_TIMESTAMP)
                    ON CONFLICT(domain) DO UPDATE SET
                        last_sync_at = excluded.last_sync_at,
                        count = excluded.count,
                        extra_json = excluded.extra_json,
                        updated_at = CURRENT_TIMESTAMP
                """),
                {"d": domain, "lsa": last_sync_at, "c": count, "ex": extra_json}
            )
            db.session.commit()
            return True
    except Exception as e:
        try:
            db.session.rollback()
        except Exception:
            pass
        _log_sync_error("save_domain", str(e), {"domain": domain})
        return False


# =============================================================================
# AUDIT & ERROR LOGGING
# =============================================================================

def _log_sync_audit(domain: str, event_type: str, source: str = None, user_id: str = None,
                    count: int = None, extra: Dict = None, success: bool = True, error_message: str = None):
    """Append event to sync_audit table. Auditing statement: all sync events are logged."""
    ctx = _get_db()
    if not ctx:
        return
    app, db = ctx
    try:
        with app.app_context():
            from sqlalchemy import text
            db.session.execute(
                text("""
                    INSERT INTO sync_audit (domain, event_type, source, user_id, count, extra_json, success, error_message)
                    VALUES (:d, :et, :src, :uid, :c, :ex, :ok, :err)
                """),
                {
                    "d": domain, "et": event_type, "src": source, "uid": user_id,
                    "c": count, "ex": json.dumps(extra or {}), "ok": 1 if success else 0, "err": error_message
                }
            )
            db.session.commit()
    except Exception:
        try:
            db.session.rollback()
        except Exception:
            pass


def _log_sync_health(domain: str, success: bool, error_message: str = None):
    """Update sync_health table with success/failure count for the day."""
    ctx = _get_db()
    if not ctx:
        return
    app, db = ctx
    try:
        with app.app_context():
            from sqlalchemy import text
            today = date.today().isoformat()
            if success:
                db.session.execute(text("""
                    INSERT INTO sync_health (domain, metric_date, success_count, last_success_at, updated_at)
                    VALUES (:d, :dt, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                    ON CONFLICT(domain, metric_date) DO UPDATE SET
                        success_count = success_count + 1,
                        last_success_at = CURRENT_TIMESTAMP,
                        updated_at = CURRENT_TIMESTAMP
                """), {"d": domain, "dt": today})
            else:
                db.session.execute(text("""
                    INSERT INTO sync_health (domain, metric_date, failure_count, last_failure_at, last_error_message, updated_at)
                    VALUES (:d, :dt, 1, CURRENT_TIMESTAMP, :err, CURRENT_TIMESTAMP)
                    ON CONFLICT(domain, metric_date) DO UPDATE SET
                        failure_count = failure_count + 1,
                        last_failure_at = CURRENT_TIMESTAMP,
                        last_error_message = :err,
                        updated_at = CURRENT_TIMESTAMP
                """), {"d": domain, "dt": today, "err": error_message})
            db.session.commit()
    except Exception:
        try:
            db.session.rollback()
        except Exception:
            pass


def _log_sync_error(context: str, error_message: str, additional_data: Dict = None):
    """Log sync failure to error_logging service. Statement: sync failures are audited and logged."""
    try:
        from backend.services.error_logging import error_logger
        error_logger.log_error(
            Exception(error_message),
            error_type="sync_failure",
            endpoint=f"/sync/{context}",
            additional_data={"context": context, **(additional_data or {})}
        )
    except Exception:
        print(f"[Sync] Error logging failed: {error_message}")


# =============================================================================
# JSON FALLBACK (backward compatibility when DB unavailable)
# =============================================================================

def _load_sync_state() -> Dict[str, Any]:
    """Load state: DB first, then JSON file fallback."""
    state = _load_state_from_db()
    if state is not None:
        return state
    os.makedirs(os.path.dirname(_SYNC_STATE_FILE), exist_ok=True)
    if os.path.exists(_SYNC_STATE_FILE):
        try:
            with open(_SYNC_STATE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {
        "last_sync_at": None,
        "last_sync_source": None,
        "sync_count": 0,
        "per_user": {},
        "domains": {d: {"last_sync_at": None, "count": None} for d in SYNC_DOMAINS},
    }


def _save_sync_state(state: Dict[str, Any]) -> None:
    """Save state: DB first, then JSON file. Log failures."""
    if "domains" not in state:
        state["domains"] = {d: {"last_sync_at": None, "count": None} for d in SYNC_DOMAINS}
    for d in SYNC_DOMAINS:
        if d not in state["domains"]:
            state["domains"][d] = {"last_sync_at": None, "count": None}

    ok = _save_state_to_db(state)
    if not ok:
        _log_sync_error("_save_sync_state", "DB save failed, using JSON fallback")

    try:
        os.makedirs(os.path.dirname(_SYNC_STATE_FILE), exist_ok=True)
        with open(_SYNC_STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2)
    except Exception as e:
        _log_sync_error("_save_sync_state", f"JSON fallback save failed: {e}")


# =============================================================================
# UNIFIED POINTS SYNC DEVICE
# =============================================================================

class UnifiedPointsSyncDevice:
    """
    Strong device: single entry point for unified point system.
    - get_canonical(user_id): canonical point state
    - register_award(...): write-through to file + DB
    - sync_now(user_id?): reconcile and persist
    - record_domain_sync(domain, count?, extra?): audit domain sync
    - record_points_activity(): called from add_points
    - get_sync_status(): for /api/sync/status
    - get_sync_audit(limit?): recent audit entries
    - get_sync_health(): success/failure metrics per domain
    """

    def __init__(self):
        self._state = _load_sync_state()
        self._points_db = None
        self._points_enhanced = None

    def _get_points_db(self):
        if self._points_db is None:
            try:
                from backend.services.unified_points_database import unified_points_db
                self._points_db = unified_points_db
            except Exception:
                pass
        return self._points_db

    def _get_enhanced(self):
        if self._points_enhanced is None:
            try:
                from backend.services.unified_points_database_enhanced import unified_points_db_enhanced
                self._points_enhanced = unified_points_db_enhanced
            except Exception:
                pass
        return self._points_enhanced

    def get_canonical(self, user_id: str) -> Dict[str, Any]:
        """Return canonical point state for user."""
        db = self._get_points_db()
        if db:
            result = db.get_all_points(user_id)
            if result and result.get("success"):
                return result
        return {"success": True, "user_id": user_id, "points": {}, "xp_total": 0, "level": 1}

    def register_award(
        self,
        user_id: str,
        point_type: str,
        amount: float,
        source: str = "sync_device",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Award points through the sync device."""
        db = self._get_points_db()
        if db:
            out = db.add_points(user_id, point_type, amount, source=source, metadata=metadata or {})
        else:
            out = {"success": False, "error": "Unified points database not available"}
        if out.get("success"):
            self._state["sync_count"] = self._state.get("sync_count", 0) + 1
            self._state["last_sync_at"] = datetime.utcnow().isoformat()
            self._state["last_sync_source"] = source
            self._state.setdefault("per_user", {})[user_id] = datetime.utcnow().isoformat()
            _save_sync_state(self._state)
            _log_sync_audit("unified_points", "register_award", source=source, user_id=user_id)
        return out

    def sync_now(self, user_id: Optional[str] = None) -> Dict[str, Any]:
        """Run a sync pass. Updates global state."""
        if user_id:
            canonical = self.get_canonical(user_id)
            self._state.setdefault("per_user", {})[user_id] = datetime.utcnow().isoformat()
        self._state["last_sync_at"] = datetime.utcnow().isoformat()
        self._state["last_sync_source"] = "sync_now"
        _save_sync_state(self._state)
        _log_sync_audit("unified_points", "sync_now", source="sync_now", user_id=user_id)
        return {
            "success": True,
            "last_sync_at": self._state["last_sync_at"],
            "user_id": user_id,
            "message": "Sync state updated",
        }

    def record_points_activity(self) -> None:
        """Call when points are awarded (from add_points). Updates sync_count and unified_points domain."""
        self._state["sync_count"] = self._state.get("sync_count", 0) + 1
        self._state["last_sync_at"] = datetime.utcnow().isoformat()
        self._state["last_sync_source"] = "points_award"
        self.record_domain_sync("unified_points", count=self._state["sync_count"])
        _save_sync_state(self._state)

    def record_domain_sync(
        self,
        domain: str,
        count: Optional[int] = None,
        extra: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Record a sync for a domain. Auditing: every call is logged to sync_audit.
        Health: success/failure tracked in sync_health.
        """
        if domain not in SYNC_DOMAINS:
            _log_sync_audit(domain, "invalid_domain", success=False, error_message=f"Domain not in SYNC_DOMAINS")
            return
        self._state.setdefault("domains", {})
        self._state["domains"].setdefault(domain, {"last_sync_at": None, "count": None})
        now = datetime.utcnow().isoformat()
        self._state["domains"][domain]["last_sync_at"] = now
        if count is not None:
            self._state["domains"][domain]["count"] = count
        if extra:
            self._state["domains"][domain].setdefault("extra", {}).update(extra)
        self._state["last_sync_at"] = now
        try:
            _save_sync_state(self._state)
            _save_domain_to_db(domain, now, count, extra)
            _log_sync_audit(domain, "domain_sync", count=count, extra=extra, success=True)
            _log_sync_health(domain, True)
        except Exception as e:
            _log_sync_error("record_domain_sync", str(e), {"domain": domain})
            _log_sync_health(domain, False, str(e))
            _log_sync_audit(domain, "domain_sync", success=False, error_message=str(e))

    def get_sync_status(self) -> Dict[str, Any]:
        """Return full sync device status for /api/sync/status."""
        domains = self._state.get("domains") or {}
        out = {
            "unified_points": {
                "last_sync_at": self._state.get("last_sync_at"),
                "last_sync_source": self._state.get("last_sync_source"),
                "sync_count": self._state.get("sync_count", 0),
            },
            "users": domains.get("users", {}),
            "profiles": domains.get("profiles", {}),
            "domains": {d: domains.get(d, {"last_sync_at": None, "count": None}) for d in SYNC_DOMAINS},
            "device": "unified_points_sync",
        }
        return out

    def get_sync_audit(self, limit: int = 50) -> List[Dict]:
        """Return recent sync audit entries for dashboard/history."""
        ctx = _get_db()
        if not ctx:
            return []
        app, db = ctx
        try:
            with app.app_context():
                from sqlalchemy import text
                rows = db.session.execute(
                    text("""
                        SELECT domain, event_type, source, user_id, count, success, error_message, created_at
                        FROM sync_audit ORDER BY id DESC LIMIT :lim
                    """),
                    {"lim": limit}
                ).fetchall()
                return [
                    {
                        "domain": r[0], "event_type": r[1], "source": r[2], "user_id": r[3],
                        "count": r[4], "success": bool(r[5]), "error_message": r[6],
                        "created_at": r[7].isoformat() if hasattr(r[7], "isoformat") else str(r[7])
                    }
                    for r in rows
                ]
        except Exception:
            return []

    def get_sync_health(self) -> Dict[str, Any]:
        """Return sync health metrics (success/failure counts per domain for today)."""
        ctx = _get_db()
        if not ctx:
            return {}
        app, db = ctx
        try:
            with app.app_context():
                from sqlalchemy import text
                today = date.today().isoformat()
                rows = db.session.execute(
                    text("""
                        SELECT domain, success_count, failure_count, last_success_at, last_failure_at, last_error_message
                        FROM sync_health WHERE metric_date = :dt
                    """),
                    {"dt": today}
                ).fetchall()
                return {
                    r[0]: {
                        "success_count": r[1] or 0,
                        "failure_count": r[2] or 0,
                        "last_success_at": r[3],
                        "last_failure_at": r[4],
                        "last_error_message": r[5],
                    }
                    for r in rows
                }
        except Exception:
            return {}


unified_points_sync_device = UnifiedPointsSyncDevice()
