"""
Unified Points Database
Stores and aggregates user points across all systems.

Implementation notes:
- **Canonical writes:** `add_points` persists to the file store first (`logs/unified_points/<user_id>.json`),
  then best-effort SQL (`player_levels`, `system_point_snapshots`, etc.).
- **Canonical reads:** `get_all_points` merges **file + DB** with `max()` per scalar and per `systems` key
  so UI/shop/profile never disagree when one backend lags the other.
- Uses SQLite tables created by existing migration scripts (e.g. player_levels, xp_history, system_point_snapshots).
- Works without ORM models (raw SQL via SQLAlchemy db.session.execute(text(...))).
"""
import logging
import os
import json
from contextlib import contextmanager
from datetime import datetime
from typing import Dict, Optional, Any

from sqlalchemy import text

_logger = logging.getLogger(__name__)


@contextmanager
def _unified_points_db_context():
    """
    Use the active Flask app during HTTP requests.
    Avoid calling create_app() on every read/write — that spins up the full app stack and can stall workers.
    """
    try:
        from flask import has_request_context

        if has_request_context():
            yield
            return
    except Exception:
        pass
    from src.app import create_app

    app = create_app()
    with app.app_context():
        yield


class UnifiedPointsDatabase:
    """DB-backed unified points store with sane defaults and fallbacks."""

    def __init__(self, base_dir: Optional[str] = None):
        self.base_dir = base_dir or os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        self.points_dir = os.path.join(self.base_dir, "logs", "unified_points")
        os.makedirs(self.points_dir, exist_ok=True)

    def _points_file(self, user_id: str) -> str:
        return os.path.join(self.points_dir, f"{user_id}.json")

    def _load_file_store(self, user_id: str) -> Dict[str, Any]:
        path = self._points_file(user_id)
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    return json.load(f) or {}
            except Exception:
                return {}
        return {}

    def _save_file_store(self, user_id: str, store: Dict[str, Any]) -> None:
        path = self._points_file(user_id)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(store, f, indent=2)

    def _ensure_player_level_row(self, db, user_id: str):
        # Production schemas may differ; try the most complete schema first, then fall back.
        try:
            db.session.execute(
                text(
                    """
                    INSERT OR IGNORE INTO player_levels (user_id, level, total_xp, current_level_xp, xp_to_next_level)
                    VALUES (:user_id, 1, 0, 0, 100)
                    """
                ),
                {"user_id": user_id},
            )
            return
        except Exception:
            pass

        try:
            db.session.execute(
                text(
                    """
                    INSERT OR IGNORE INTO player_levels (user_id, total_xp)
                    VALUES (:user_id, 0)
                    """
                ),
                {"user_id": user_id},
            )
            return
        except Exception:
            pass

        try:
            db.session.execute(
                text("INSERT OR IGNORE INTO player_levels (user_id) VALUES (:user_id)"),
                {"user_id": user_id},
            )
        except Exception:
            # If player_levels doesn't exist at all, we'll fall back to snapshots.
            pass

    def _award_points_file_fallback(self, user_id: str, point_type: str, amount: float, source: str, metadata: Optional[Dict[str, Any]] = None) -> Dict:
        pt = (point_type or "").strip()
        amt = float(amount or 0)
        if not pt:
            return {"success": False, "error": "point_type is required"}

        store = self._load_file_store(user_id)
        systems = store.get("systems") if isinstance(store.get("systems"), dict) else {}

        # XP stored in xp_total
        if pt in ("xp", "xp_points", "xp_total"):
            store["xp_total"] = float(store.get("xp_total", 0) or 0) + amt
        else:
            systems[pt] = float(systems.get(pt, 0) or 0) + amt
            if pt == "trophy_points":
                systems["trophies_collected"] = int(systems.get("trophies_collected", 0) or 0) + 1
            store["systems"] = systems

        # Derived level (simple, stable)
        xp_total = float(store.get("xp_total", 0) or 0)
        store["level"] = max(1, int(xp_total // 1000) + 1)
        store["updated_at"] = datetime.now().isoformat()
        store["last_source"] = source
        store["last_metadata"] = metadata or {}
        self._save_file_store(user_id, store)

        return {"success": True, "user_id": user_id, "point_type": pt, "amount": amt, "message": "Points updated (file)"}

    def add_points(self, user_id: str, point_type: str, amount: float, source: str = "system", metadata: Optional[Dict[str, Any]] = None) -> Dict:
        """Add points to a user for a given point_type."""
        pt = (point_type or "").strip()
        amt = float(amount or 0)
        if not pt:
            return {"success": False, "error": "point_type is required"}
        if amt == 0:
            return {"success": True, "user_id": user_id, "point_type": pt, "amount": 0, "message": "No-op"}

        # File store is the durable baseline (production schema varies)
        file_result = self._award_points_file_fallback(user_id, pt, amt, source, metadata)
        if file_result.get("success"):
            try:
                from backend.services.unified_points_sync import unified_points_sync_device
                unified_points_sync_device.record_points_activity()
            except Exception:
                pass

        # Best-effort DB write (never blocks file store success)
        try:
            from src.db.models import db

            with _unified_points_db_context():
                self._ensure_player_level_row(db, user_id)

                if pt in ("xp", "xp_points", "xp_total"):
                    try:
                        db.session.execute(
                            text("UPDATE player_levels SET total_xp = COALESCE(total_xp, 0) + :amt WHERE user_id = :user_id"),
                            {"amt": int(amt), "user_id": user_id},
                        )
                        db.session.commit()
                        file_result["db"] = "ok"
                    except Exception:
                        db.session.rollback()
                        file_result["db"] = "skipped"
                    return file_result

                # Non-XP snapshot table is optional; skip if not present
                try:
                    row = db.session.execute(
                        text(
                            """
                            SELECT point_value
                            FROM system_point_snapshots
                            WHERE user_id = :user_id AND system_name = :system_name
                            ORDER BY id DESC
                            LIMIT 1
                            """
                        ),
                        {"user_id": user_id, "system_name": pt},
                    ).fetchone()
                    current_total = float(row[0]) if row and row[0] is not None else 0.0
                    new_total = current_total + amt
                    
                    # Enhanced snapshot insert with new columns if they exist
                    try:
                        db.session.execute(
                            text(
                                """
                                INSERT INTO system_point_snapshots 
                                (user_id, system_name, point_value, previous_value, delta, snapshot_data, source, metadata, created_at, updated_at)
                                VALUES (:user_id, :system_name, :point_value, :previous_value, :delta, :snapshot_data, :source, :metadata, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                                """
                            ),
                            {
                                "user_id": user_id,
                                "system_name": pt,
                                "point_value": new_total,
                                "previous_value": current_total,
                                "delta": amt,
                                "snapshot_data": json.dumps(
                                    {
                                        "delta": amt,
                                        "source": source,
                                        "metadata": metadata or {},
                                        "recorded_at": datetime.now().isoformat(),
                                    }
                                ),
                                "source": source,
                                "metadata": json.dumps(metadata or {}),
                            },
                        )
                    except Exception:
                        # Fallback to old schema if new columns don't exist
                        db.session.execute(
                            text(
                                """
                                INSERT INTO system_point_snapshots (user_id, system_name, point_value, snapshot_data, created_at)
                                VALUES (:user_id, :system_name, :point_value, :snapshot_data, CURRENT_TIMESTAMP)
                                """
                            ),
                            {
                                "user_id": user_id,
                                "system_name": pt,
                                "point_value": new_total,
                                "snapshot_data": json.dumps(
                                    {
                                        "delta": amt,
                                        "source": source,
                                        "metadata": metadata or {},
                                        "recorded_at": datetime.now().isoformat(),
                                    }
                                ),
                            },
                        )
                    
                    # Log transaction if table exists
                    try:
                        db.session.execute(
                            text("""
                                INSERT INTO point_transactions
                                (user_id, system_name, transaction_type, amount, balance_before, balance_after, source, metadata, created_at)
                                VALUES (:user_id, :system_name, :transaction_type, :amount, :balance_before, :balance_after, :source, :metadata, CURRENT_TIMESTAMP)
                            """),
                            {
                                "user_id": user_id,
                                "system_name": pt,
                                "transaction_type": "credit",
                                "amount": amt,
                                "balance_before": current_total,
                                "balance_after": new_total,
                                "source": source,
                                "metadata": json.dumps(metadata or {})
                            },
                        )
                    except Exception:
                        # Transaction table might not exist yet
                        pass
                    
                    # Update usage stats if table exists
                    try:
                        existing = db.session.execute(
                            text("SELECT id FROM system_usage_stats WHERE user_id = :user_id AND system_name = :system_name"),
                            {"user_id": user_id, "system_name": pt},
                        ).fetchone()
                        
                        if existing:
                            db.session.execute(
                                text("""
                                    UPDATE system_usage_stats
                                    SET usage_count = usage_count + 1,
                                        total_points_earned = total_points_earned + :points,
                                        last_used_at = CURRENT_TIMESTAMP,
                                        updated_at = CURRENT_TIMESTAMP
                                    WHERE user_id = :user_id AND system_name = :system_name
                                """),
                                {"user_id": user_id, "system_name": pt, "points": amt},
                            )
                        else:
                            db.session.execute(
                                text("""
                                    INSERT INTO system_usage_stats
                                    (user_id, system_name, usage_count, total_points_earned, first_used_at, last_used_at, created_at, updated_at)
                                    VALUES (:user_id, :system_name, 1, :points, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                                """),
                                {"user_id": user_id, "system_name": pt, "points": amt},
                            )
                    except Exception:
                        # Usage stats table might not exist yet
                        pass
                    
                    db.session.commit()
                    file_result["db"] = "ok"
                except Exception:
                    db.session.rollback()
                    file_result["db"] = "skipped"
        except Exception:
            file_result["db"] = "skipped"

        return file_result

    @staticmethod
    def _float_max(a: Any, b: Any) -> float:
        try:
            return max(float(a or 0), float(b or 0))
        except (TypeError, ValueError):
            try:
                return float(a or 0)
            except (TypeError, ValueError):
                return float(b or 0)

    @staticmethod
    def _int_max(a: Any, b: Any) -> int:
        try:
            return max(int(float(a or 0)), int(float(b or 0)))
        except (TypeError, ValueError):
            return 0

    def _points_payload_from_file(self, user_id: str) -> Dict[str, Any]:
        """Normalized points dict from JSON file store only (no game_time keys)."""
        store = self._load_file_store(user_id)
        systems = store.get("systems") if isinstance(store.get("systems"), dict) else {}
        xp_total = int(float(store.get("xp_total", 0) or 0))
        level = int(store.get("level", max(1, int(xp_total // 1000) + 1)) or 1)
        trophies_collected = int(float(systems.get("trophies_collected", 0) or 0))
        points = {
            "xp_total": xp_total,
            "level": level,
            "activity_points": float(systems.get("activity_points", 0) or 0),
            "quest_points": float(systems.get("quest_points", 0) or 0),
            "stats_points_total": float(systems.get("stats_points_total", 0) or 0),
            "stats_points_available": float(systems.get("stats_points_available", 0) or 0),
            "achievements_earned": int(systems.get("achievements_earned", 0) or 0),
            "milestones_reached": int(systems.get("milestones_reached", 0) or 0),
            "trophy_points": float(systems.get("trophy_points", 0) or 0),
            "trophies_collected": trophies_collected,
            "coins": float(systems.get("coins", 0) or 0),
            "credits": float(systems.get("credits", 0) or 0),
            "battle_points": float(systems.get("battle_points", 0) or 0),
            "social_points": float(systems.get("social_points", 0) or 0),
            "knowledge_points": float(systems.get("knowledge_points", 0) or 0),
            "dna_manipulation_points": float(systems.get("dna_manipulation_points", 0) or 0),
            "dna_cloning_points": float(systems.get("dna_cloning_points", 0) or 0),
            "communication_psychology_points": float(systems.get("communication_psychology_points", 0) or 0),
            "compendium_points": float(systems.get("compendium_points", 0) or 0),
            "generation_points": float(systems.get("generation_points", 0) or 0),
            "game_points": float(systems.get("game_points", 0) or 0),
            "accuracy_grade": "A+",
            "mn2_balance": float(systems.get("mn2_balance", 0) or 0),
        }
        points["systems"] = {k: float(v or 0) for k, v in systems.items()}
        if "mn2_balance" not in points["systems"]:
            points["systems"]["mn2_balance"] = points.get("mn2_balance", 0)
        if "game_points" not in points["systems"]:
            points["systems"]["game_points"] = points.get("game_points", 0)
        return points

    def _points_payload_from_db(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Load points from DB only; return None if unavailable."""
        try:
            from src.db.models import db

            with _unified_points_db_context():
                self._ensure_player_level_row(db, user_id)

                level = 1
                xp_total = 0
                try:
                    pl = db.session.execute(
                        text("SELECT level, total_xp FROM player_levels WHERE user_id = :user_id LIMIT 1"),
                        {"user_id": user_id},
                    ).fetchone()
                    level = int(pl[0]) if pl and pl[0] is not None else 1
                    xp_total = int(pl[1]) if pl and pl[1] is not None else 0
                except Exception:
                    pl2 = db.session.execute(
                        text(
                            """
                            SELECT point_value
                            FROM system_point_snapshots
                            WHERE user_id = :user_id AND system_name = 'xp_total'
                            ORDER BY id DESC
                            LIMIT 1
                            """
                        ),
                        {"user_id": user_id},
                    ).fetchone()
                    xp_total = int(pl2[0]) if pl2 and pl2[0] is not None else 0
                    level = max(1, int(xp_total // 1000) + 1)

                rows = db.session.execute(
                    text(
                        """
                        SELECT s.system_name, s.point_value
                        FROM system_point_snapshots s
                        JOIN (
                            SELECT system_name, MAX(id) AS max_id
                            FROM system_point_snapshots
                            WHERE user_id = :user_id
                            GROUP BY system_name
                        ) t ON s.id = t.max_id
                        WHERE s.user_id = :user_id
                        """
                    ),
                    {"user_id": user_id},
                ).fetchall()

                snapshots = {r[0]: r[1] for r in rows} if rows else {}

                trophies_collected = 0
                try:
                    tr = db.session.execute(
                        text("SELECT COUNT(*) FROM user_trophy_unlocks WHERE user_id = :user_id"),
                        {"user_id": user_id},
                    ).fetchone()
                    trophies_collected = int(tr[0]) if tr and tr[0] is not None else 0
                except Exception:
                    pass

                points = {
                    "xp_total": xp_total,
                    "level": level,
                    "activity_points": float(snapshots.get("activity_points", 0) or 0),
                    "quest_points": float(snapshots.get("quest_points", 0) or 0),
                    "stats_points_total": float(snapshots.get("stats_points_total", 0) or 0),
                    "stats_points_available": float(snapshots.get("stats_points_available", 0) or 0),
                    "achievements_earned": int(snapshots.get("achievements_earned", 0) or 0),
                    "milestones_reached": int(snapshots.get("milestones_reached", 0) or 0),
                    "trophy_points": float(snapshots.get("trophy_points", 0) or 0),
                    "trophies_collected": trophies_collected,
                    "coins": float(snapshots.get("coins", 0) or 0),
                    "credits": float(snapshots.get("credits", 0) or 0),
                    "battle_points": float(snapshots.get("battle_points", 0) or 0),
                    "social_points": float(snapshots.get("social_points", 0) or 0),
                    "knowledge_points": float(snapshots.get("knowledge_points", 0) or 0),
                    "dna_manipulation_points": float(snapshots.get("dna_manipulation_points", 0) or 0),
                    "dna_cloning_points": float(snapshots.get("dna_cloning_points", 0) or 0),
                    "communication_psychology_points": float(snapshots.get("communication_psychology_points", 0) or 0),
                    "compendium_points": float(snapshots.get("compendium_points", 0) or 0),
                    "generation_points": float(snapshots.get("generation_points", 0) or 0),
                    "game_points": float(snapshots.get("game_points", 0) or 0),
                    "accuracy_grade": "A+",
                    "mn2_balance": float(snapshots.get("mn2_balance", 0) or 0),
                }
                points["systems"] = {k: float(v or 0) for k, v in snapshots.items()}
                if "mn2_balance" not in points["systems"]:
                    points["systems"]["mn2_balance"] = points.get("mn2_balance", 0)
                if "game_points" not in points["systems"]:
                    points["systems"]["game_points"] = points.get("game_points", 0)
                return points
        except Exception as e:
            _logger.debug("unified_points DB read failed for %s: %s", user_id, e)
            return None

    def _merge_points_payloads(self, file_pts: Dict[str, Any], db_pts: Dict[str, Any]) -> Dict[str, Any]:
        """Merge file and DB snapshots using max() so totals never look lower than either source."""
        numeric_keys = (
            "xp_total", "activity_points", "quest_points", "stats_points_total", "stats_points_available",
            "trophy_points", "coins", "credits", "battle_points", "social_points", "knowledge_points",
            "dna_manipulation_points", "dna_cloning_points", "communication_psychology_points",
            "compendium_points", "generation_points", "game_points", "mn2_balance",
        )
        int_keys = ("achievements_earned", "milestones_reached", "trophies_collected")
        out = {}
        for k in numeric_keys:
            out[k] = self._float_max(file_pts.get(k), db_pts.get(k))
        for k in int_keys:
            out[k] = self._int_max(file_pts.get(k), db_pts.get(k))
        out["level"] = max(int(file_pts.get("level", 1) or 1), int(db_pts.get("level", 1) or 1))
        out["accuracy_grade"] = file_pts.get("accuracy_grade") or db_pts.get("accuracy_grade") or "A+"

        fs = file_pts.get("systems") if isinstance(file_pts.get("systems"), dict) else {}
        ds = db_pts.get("systems") if isinstance(db_pts.get("systems"), dict) else {}
        keys = set(fs.keys()) | set(ds.keys())
        merged_sys = {}
        for k in keys:
            merged_sys[k] = self._float_max(fs.get(k), ds.get(k))
        out["systems"] = merged_sys
        return out

    def get_all_points(self, user_id: str = "default_user") -> Dict:
        """Return a normalized dict used by frontend unified counters (file + DB merged)."""
        file_pts = self._points_payload_from_file(user_id)
        db_pts = self._points_payload_from_db(user_id)
        if db_pts:
            points = self._merge_points_payloads(file_pts, db_pts)
        else:
            points = dict(file_pts)
        gt_boost = self.get_game_time_and_boosters(user_id)
        points["game_time_remaining_minutes"] = gt_boost.get("game_time_remaining_minutes", 0)
        points["active_boosters"] = gt_boost.get("active_boosters", [])
        return {"success": True, "user_id": user_id, "points": points}


    def add_game_time_minutes(self, user_id: str, minutes: int) -> Dict:
        """Add game time (e.g. from shop purchase) to user. Stored in file fallback."""
        if not user_id or minutes <= 0:
            return {"success": False, "error": "user_id and positive minutes required"}
        store = self._load_file_store(user_id)
        current = int(store.get("game_time_remaining_minutes", 0) or 0)
        store["game_time_remaining_minutes"] = current + minutes
        store["updated_at"] = datetime.now().isoformat()
        self._save_file_store(user_id, store)
        return {"success": True, "user_id": user_id, "added_minutes": minutes, "total_remaining": current + minutes}

    def add_booster(self, user_id: str, booster_id: str, duration_minutes: int, name: str = "") -> Dict:
        """Activate a booster for the user (e.g. from shop). Stored in file fallback."""
        if not user_id or not booster_id or duration_minutes <= 0:
            return {"success": False, "error": "user_id, booster_id and positive duration required"}
        from datetime import timedelta
        expires = (datetime.now() + timedelta(minutes=duration_minutes)).isoformat()
        store = self._load_file_store(user_id)
        boosters = list(store.get("active_boosters") or [])
        boosters.append({"id": booster_id, "expires_at": expires, "name": name or booster_id})
        store["active_boosters"] = boosters
        store["updated_at"] = datetime.now().isoformat()
        self._save_file_store(user_id, store)
        return {"success": True, "user_id": user_id, "booster_id": booster_id, "expires_at": expires}

    def get_game_time_and_boosters(self, user_id: str) -> Dict:
        """Return game_time_remaining_minutes and active_boosters (excluding expired)."""
        store = self._load_file_store(user_id)
        now = datetime.now()
        boosters = store.get("active_boosters") or []
        active = [b for b in boosters if isinstance(b, dict) and (b.get("expires_at") or "") > now.isoformat()]
        if active != boosters:
            store["active_boosters"] = active
            store["updated_at"] = now.isoformat()
            self._save_file_store(user_id, store)
        return {
            "game_time_remaining_minutes": int(store.get("game_time_remaining_minutes", 0) or 0),
            "active_boosters": active,
        }

    @staticmethod
    def _safe_int(val: Any, default: int = 0) -> int:
        try:
            return int(float(val))
        except (TypeError, ValueError):
            return default

    def get_all_users_points(self) -> Dict[str, Dict[str, Any]]:
        """
        All users with file-backed unified points (for leaderboards).
        Scans logs/unified_points/*.json — fast, no per-user create_app().
        """
        merged: Dict[str, Dict[str, Any]] = {}
        try:
            if not os.path.isdir(self.points_dir):
                return merged
            for fn in os.listdir(self.points_dir):
                if not fn.endswith(".json"):
                    continue
                uid = fn[:-5]
                if not uid:
                    continue
                raw = self._load_file_store(uid)
                if not raw:
                    continue
                xp = self._safe_int(raw.get("xp_total", raw.get("xp", 0)))
                lvl = self._safe_int(raw.get("level", max(1, xp // 1000 + 1)), 1)
                systems = raw.get("systems") if isinstance(raw.get("systems"), dict) else {}
                merged[uid] = {
                    "xp_total": xp,
                    "level": lvl,
                    "systems": systems,
                }
        except Exception:
            return merged
        return merged


# Global instance
unified_points_db = UnifiedPointsDatabase()

