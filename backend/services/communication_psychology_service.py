"""
Communication Psychology Service
25 theories integrated with unified points, profile, trophies, and starmap.
Uses database (comm_psych_theory_unlocks, comm_psych_activity_log) with file fallback.
"""
import os
import json
from typing import Dict, List, Any, Optional
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA_PATH = os.path.join(BASE_DIR, "data", "communication_psychology_theories.json")
USER_PROGRESS_DIR = os.path.join(BASE_DIR, "logs", "communication_psychology")
POINT_TYPE = "communication_psychology_points"
SOURCE = "communication_psychology"


def _load_theories() -> Dict[str, Any]:
    """Load theory definitions from JSON."""
    if not os.path.isfile(DATA_PATH):
        return {"theories": [], "categories": []}
    try:
        with open(DATA_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"theories": [], "categories": []}


def _user_progress_file(user_id: str) -> str:
    os.makedirs(USER_PROGRESS_DIR, exist_ok=True)
    safe_id = (user_id or "default_user").replace(os.path.sep, "_")
    return os.path.join(USER_PROGRESS_DIR, f"{safe_id}.json")


def _db_tables_exist() -> bool:
    try:
        from sqlalchemy import inspect
        from src.db.models import db
        t = inspect(db.engine).get_table_names()
        return "comm_psych_theory_unlocks" in t and "comm_psych_activity_log" in t
    except Exception:
        return False


def _load_user_progress_from_db(user_id: str) -> Optional[Dict[str, Any]]:
    """Load unlocked theory IDs and studied_at from database."""
    if not _db_tables_exist():
        return None
    try:
        from sqlalchemy import text
        from src.db.models import db
        from src.app import create_app
        app = create_app()
        with app.app_context():
            rows = db.session.execute(
                text("SELECT theory_id, unlocked_at FROM comm_psych_theory_unlocks WHERE user_id = :uid ORDER BY unlocked_at"),
                {"uid": user_id or "default_user"},
            ).fetchall()
        if not rows:
            return None
        unlocked_ids = [r[0] for r in rows]
        studied_at = {}
        for r in rows:
            studied_at[r[0]] = r[1].isoformat() if hasattr(r[1], "isoformat") else str(r[1])
        return {"unlocked_theory_ids": unlocked_ids, "studied_at": studied_at, "total_points_earned": 0}
    except Exception:
        return None


def _save_unlock_to_db(user_id: str, theory_id: str, metadata: Optional[Dict] = None) -> bool:
    if not _db_tables_exist():
        return False
    try:
        from sqlalchemy import text
        from src.db.models import db
        from src.app import create_app
        app = create_app()
        with app.app_context():
            db.session.execute(
                text("""
                    INSERT OR IGNORE INTO comm_psych_theory_unlocks (user_id, theory_id, metadata)
                    VALUES (:uid, :tid, :meta)
                """),
                {"uid": user_id or "default_user", "tid": theory_id, "meta": json.dumps(metadata or {})},
            )
            db.session.commit()
        return True
    except Exception:
        try:
            from src.db.models import db
            db.session.rollback()
        except Exception:
            pass
        return False


def _log_activity_to_db(user_id: str, activity_type: str, amount: float = 0, theory_id: Optional[str] = None, source: str = "", metadata: Optional[Dict] = None) -> bool:
    if not _db_tables_exist():
        return False
    try:
        from sqlalchemy import text
        from src.db.models import db
        from src.app import create_app
        app = create_app()
        with app.app_context():
            db.session.execute(
                text("""
                    INSERT INTO comm_psych_activity_log (user_id, activity_type, theory_id, amount, source, metadata)
                    VALUES (:uid, :atype, :tid, :amt, :src, :meta)
                """),
                {
                    "uid": user_id or "default_user",
                    "atype": activity_type,
                    "tid": theory_id,
                    "amt": amount,
                    "src": source[:100] if source else "",
                    "meta": json.dumps(metadata or {}),
                },
            )
            db.session.commit()
        return True
    except Exception:
        try:
            from src.db.models import db
            db.session.rollback()
        except Exception:
            pass
        return False


def _load_user_progress(user_id: str) -> Dict[str, Any]:
    """Load progress: DB first, then file fallback. Merge if both exist."""
    uid = user_id or "default_user"
    from_db = _load_user_progress_from_db(uid)
    path = _user_progress_file(uid)
    from_file = None
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                from_file = json.load(f)
        except Exception:
            pass
    if from_db and from_file:
        # Prefer DB; merge studied_at and ensure all DB unlocks are in list
        ids_db = set(from_db.get("unlocked_theory_ids", []))
        ids_file = set(from_file.get("unlocked_theory_ids", []))
        merged_ids = list(ids_db | ids_file)
        studied = dict(from_db.get("studied_at", {}))
        for k, v in (from_file.get("studied_at") or {}).items():
            if k not in studied:
                studied[k] = v
        return {
            "unlocked_theory_ids": merged_ids,
            "total_points_earned": from_file.get("total_points_earned", 0) or from_db.get("total_points_earned", 0),
            "studied_at": studied,
        }
    if from_db:
        return from_db
    if from_file:
        return from_file
    return {"unlocked_theory_ids": [], "total_points_earned": 0, "studied_at": {}}


def _save_user_progress(user_id: str, data: Dict[str, Any]) -> None:
    path = _user_progress_file(user_id or "default_user")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def get_theories_list() -> Dict[str, Any]:
    """Return all theories and categories for UI/starmap."""
    data = _load_theories()
    return {
        "success": True,
        "name": data.get("name", "Communication Psychology"),
        "description": data.get("description", ""),
        "categories": data.get("categories", []),
        "theories": data.get("theories", []),
    }


def get_user_progress(user_id: str) -> Dict[str, Any]:
    """Return user's unlocked theories and progress for profile/trophies."""
    theories_data = _load_theories()
    theories = {t["id"]: t for t in theories_data.get("theories", [])}
    progress = _load_user_progress(user_id)
    unlocked_ids = progress.get("unlocked_theory_ids", [])
    studied_at = progress.get("studied_at", {})

    # Enrich with theory details
    unlocked_theories = []
    for tid in unlocked_ids:
        if tid in theories:
            t = dict(theories[tid])
            t["unlocked_at"] = studied_at.get(tid)
            unlocked_theories.append(t)

    # Get communication_psychology_points from unified system
    total_points = progress.get("total_points_earned", 0)
    try:
        from backend.services.unified_points_database import unified_points_db
        if unified_points_db:
            res = unified_points_db.get_all_points(user_id)
            systems = res.get("systems", {}) or res.get("all_points", {}) or {}
            total_points = float(systems.get(POINT_TYPE, 0) or total_points)
    except Exception:
        pass

    return {
        "success": True,
        "user_id": user_id,
        "unlocked_theory_ids": unlocked_ids,
        "unlocked_theories": unlocked_theories,
        "unlocked_count": len(unlocked_ids),
        "total_theories": len(theories),
        "communication_psychology_points": total_points,
        "categories": theories_data.get("categories", []),
        "all_theories": theories_data.get("theories", []),
    }


def study_theory(user_id: str, theory_id: str) -> Dict[str, Any]:
    """
    Unlock a theory for the user, award communication_psychology_points, and check trophies.
    """
    theories_data = _load_theories()
    theories = {t["id"]: t for t in theories_data.get("theories", [])}
    if theory_id not in theories:
        return {"success": False, "error": "Unknown theory id"}

    progress = _load_user_progress(user_id)
    unlocked = progress.get("unlocked_theory_ids", [])
    if theory_id in unlocked:
        return {
            "success": True,
            "already_unlocked": True,
            "message": "Theory already studied",
            "user_id": user_id,
            "theory_id": theory_id,
        }

    theory = theories[theory_id]
    point_value = float(theory.get("point_value", 30))
    now = datetime.utcnow().isoformat()

    # Persist unlock: database first, then file
    _save_unlock_to_db(user_id, theory_id, metadata={"theory_name": theory.get("name"), "points": point_value})
    progress.setdefault("unlocked_theory_ids", []).append(theory_id)
    progress.setdefault("studied_at", {})[theory_id] = now
    progress["total_points_earned"] = progress.get("total_points_earned", 0) + point_value
    _save_user_progress(user_id, progress)
    _log_activity_to_db(user_id, "study", amount=point_value, theory_id=theory_id, source=SOURCE, metadata={"theory_name": theory.get("name")})

    # Award unified points
    try:
        from backend.services.unified_points_database import unified_points_db
        if unified_points_db:
            unified_points_db.add_points(
                user_id,
                POINT_TYPE,
                point_value,
                source=SOURCE,
                metadata={"theory_id": theory_id, "theory_name": theory.get("name")},
            )
    except Exception:
        pass

    # Trigger integration (optional)
    try:
        from backend.services.unified_points_trigger_integration import unified_points_trigger_integration
        if unified_points_trigger_integration and hasattr(unified_points_trigger_integration, "trigger_mapping"):
            if POINT_TYPE in unified_points_trigger_integration.trigger_mapping:
                unified_points_trigger_integration.award_points_with_trigger(
                    POINT_TYPE, user_id, int(point_value), metadata={"theory_id": theory_id}
                )
    except Exception:
        pass

    # Check and award walkthrough trophies
    _check_and_award_trophies(user_id, progress)

    # Sync: record domain sync for communication_psychology
    try:
        from backend.services.unified_points_sync import unified_points_sync_device
        unified_points_sync_device.record_domain_sync('communication_psychology', extra={"theory_id": theory_id})
    except Exception:
        pass

    crypto_reward = {}
    try:
        from backend.services.compendium_crypto_rewards_service import award_theory_study_reward
        crypto_reward = award_theory_study_reward(user_id, theory_id)
    except Exception:
        pass

    return {
        "success": True,
        "already_unlocked": False,
        "user_id": user_id,
        "theory_id": theory_id,
        "theory_name": theory.get("name"),
        "points_awarded": point_value,
        "unlocked_count": len(progress["unlocked_theory_ids"]),
        "crypto_reward": crypto_reward,
    }


def _check_and_award_trophies(user_id: str, progress: Optional[Dict] = None) -> None:
    """Award communication psychology walkthrough trophies when conditions are met."""
    if progress is None:
        progress = _load_user_progress(user_id)
    unlocked_count = len(progress.get("unlocked_theory_ids", []))
    try:
        from backend.services.unified_points_database import unified_points_db
        points_data = unified_points_db.get_all_points(user_id) if unified_points_db else {}
    except Exception:
        points_data = {}
    systems = points_data.get("systems", {}) or points_data.get("all_points", {}) or {}
    comm_points = float(systems.get(POINT_TYPE, 0) or progress.get("total_points_earned", 0))

    trophies_to_check = [
        ("comm_psych_first", unlocked_count >= 1),
        ("comm_psych_five", unlocked_count >= 5),
        ("comm_psych_ten", unlocked_count >= 10),
        ("comm_psych_master_25", unlocked_count >= 25),
        ("comm_psych_points_500", comm_points >= 500),
        ("comm_psych_points_1k", comm_points >= 1000),
        ("comm_psych_points_5k", comm_points >= 5000),
    ]
    for trophy_id, condition in trophies_to_check:
        if condition:
            try:
                from backend.services.trophies_db_service import award_trophy
                award_trophy(user_id, trophy_id)
            except Exception:
                pass


def award_points_for_activity(user_id: str, amount: float, source_activity: str, metadata: Optional[Dict] = None) -> Dict:
    """
    Award communication_psychology_points from external activities (e.g. generator with
    alternative_theories / conspiracy content, shop purchase, DNA + starmap combo).
    """
    if amount <= 0:
        return {"success": True, "amount": 0}
    try:
        from backend.services.unified_points_database import unified_points_db
        if unified_points_db:
            unified_points_db.add_points(
                user_id,
                POINT_TYPE,
                amount,
                source=source_activity,
                metadata=metadata or {},
            )
        _log_activity_to_db(user_id, "award", amount=amount, source=source_activity, metadata=metadata or {})
        progress = _load_user_progress(user_id)
        progress["total_points_earned"] = progress.get("total_points_earned", 0) + amount
        _save_user_progress(user_id, progress)
        _check_and_award_trophies(user_id, progress)
        try:
            from backend.services.unified_points_sync import unified_points_sync_device
            unified_points_sync_device.record_domain_sync('communication_psychology', extra={"source": source_activity})
        except Exception:
            pass
        return {"success": True, "amount": amount}
    except Exception as e:
        return {"success": False, "error": str(e), "amount": 0}
