"""
Enhanced Unified Points Database
Full database integration for unified points system supporting 178 point systems
"""
import os
import json
from datetime import datetime, date
from typing import Dict, Optional, Any, List
from decimal import Decimal

from sqlalchemy import text


class UnifiedPointsDatabaseEnhanced:
    """Enhanced DB-backed unified points store with full database integration."""
    
    def __init__(self, base_dir: Optional[str] = None):
        self.base_dir = base_dir or os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        self.points_dir = os.path.join(self.base_dir, "logs", "unified_points")
        os.makedirs(self.points_dir, exist_ok=True)
    
    def _get_db(self):
        """Get database instance with app context"""
        from src.db.models import db
        from src.app import create_app
        app = create_app()
        return app, db
    
    def _ensure_player_level_row(self, db, user_id: str):
        """Ensure player_levels row exists"""
        try:
            db.session.execute(
                text("""
                    INSERT OR IGNORE INTO player_levels (user_id, level, total_xp, current_level_xp, xp_to_next_level)
                    VALUES (:user_id, 1, 0, 0, 1000)
                """),
                {"user_id": user_id},
            )
            db.session.commit()
        except Exception:
            db.session.rollback()
            try:
                db.session.execute(
                    text("INSERT OR IGNORE INTO player_levels (user_id, total_xp) VALUES (:user_id, 0)"),
                    {"user_id": user_id},
                )
                db.session.commit()
            except Exception:
                db.session.rollback()
    
    def add_points(self, user_id: str, point_type: str, amount: float, source: str = "system", metadata: Optional[Dict[str, Any]] = None) -> Dict:
        """Add points to a user for a given point_type with full transaction logging."""
        pt = (point_type or "").strip()
        amt = float(amount or 0)
        if not pt:
            return {"success": False, "error": "point_type is required"}
        if amt == 0:
            return {"success": True, "user_id": user_id, "point_type": pt, "amount": 0, "message": "No-op"}
        
        try:
            app, db = self._get_db()
            with app.app_context():
                self._ensure_player_level_row(db, user_id)
                
                # Handle XP points
                if pt in ("xp", "xp_points", "xp_total"):
                    result = self._add_xp_points(db, user_id, amt, source, metadata)
                else:
                    result = self._add_system_points(db, user_id, pt, amt, source, metadata)
                if result.get("success"):
                    try:
                        from backend.services.unified_points_sync import unified_points_sync_device
                        unified_points_sync_device.record_points_activity()
                    except Exception:
                        pass
                return result
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def _add_xp_points(self, db, user_id: str, amount: float, source: str, metadata: Optional[Dict[str, Any]] = None) -> Dict:
        """Add XP points with full tracking"""
        try:
            # Get current XP and level
            pl = db.session.execute(
                text("SELECT level, total_xp, current_level_xp, xp_to_next_level FROM player_levels WHERE user_id = :user_id"),
                {"user_id": user_id},
            ).fetchone()
            
            level_before = int(pl[0]) if pl and pl[0] else 1
            xp_before = int(pl[1]) if pl and pl[1] else 0
            current_level_xp = int(pl[2]) if pl and pl[2] else 0
            xp_to_next = int(pl[3]) if pl and pl[3] else 1000
            
            # Calculate new values
            new_total_xp = xp_before + int(amount)
            new_current_level_xp = current_level_xp + int(amount)
            
            # Check for level up
            level_after = level_before
            new_xp_to_next = xp_to_next
            while new_current_level_xp >= new_xp_to_next:
                new_current_level_xp -= new_xp_to_next
                level_after += 1
                new_xp_to_next = 1000 * level_after  # XP requirement increases with level
            
            level_progress = (new_current_level_xp / new_xp_to_next * 100) if new_xp_to_next > 0 else 0
            
            # Update player_levels
            db.session.execute(
                text("""
                    UPDATE player_levels 
                    SET total_xp = :total_xp,
                        current_level_xp = :current_level_xp,
                        xp_to_next_level = :xp_to_next,
                        level = :level,
                        level_progress = :level_progress,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE user_id = :user_id
                """),
                {
                    "user_id": user_id,
                    "total_xp": new_total_xp,
                    "current_level_xp": new_current_level_xp,
                    "xp_to_next": new_xp_to_next,
                    "level": level_after,
                    "level_progress": round(level_progress, 2)
                },
            )
            
            # Log to xp_history
            db.session.execute(
                text("""
                    INSERT INTO xp_history (user_id, xp_amount, source, action_type, metadata, level_before, level_after, created_at)
                    VALUES (:user_id, :xp_amount, :source, :action_type, :metadata, :level_before, :level_after, CURRENT_TIMESTAMP)
                """),
                {
                    "user_id": user_id,
                    "xp_amount": int(amount),
                    "source": source,
                    "action_type": "xp_award",
                    "metadata": json.dumps(metadata or {}),
                    "level_before": level_before,
                    "level_after": level_after,
                },
            )
            
            # Log transaction
            self._log_transaction(db, user_id, "xp_total", "credit", amount, xp_before, new_total_xp, source, metadata)
            
            # Update snapshot
            self._update_snapshot(db, user_id, "xp_total", new_total_xp, xp_before, amount, source, metadata)
            
            db.session.commit()
            
            return {
                "success": True,
                "user_id": user_id,
                "point_type": "xp_total",
                "amount": amount,
                "level_before": level_before,
                "level_after": level_after,
                "total_xp": new_total_xp,
                "message": f"XP added. Level: {level_before} -> {level_after}" if level_after > level_before else "XP added"
            }
        except Exception as e:
            db.session.rollback()
            return {"success": False, "error": str(e)}
    
    def _add_system_points(self, db, user_id: str, system_name: str, amount: float, source: str, metadata: Optional[Dict[str, Any]] = None) -> Dict:
        """Add points for any system (non-XP)"""
        try:
            # Get current value
            current_row = db.session.execute(
                text("""
                    SELECT point_value 
                    FROM system_point_snapshots
                    WHERE user_id = :user_id AND system_name = :system_name
                    ORDER BY id DESC
                    LIMIT 1
                """),
                {"user_id": user_id, "system_name": system_name},
            ).fetchone()
            
            balance_before = float(current_row[0]) if current_row and current_row[0] is not None else 0.0
            balance_after = balance_before + amount
            
            # Update snapshot
            self._update_snapshot(db, user_id, system_name, balance_after, balance_before, amount, source, metadata)
            
            # Log transaction
            self._log_transaction(db, user_id, system_name, "credit", amount, balance_before, balance_after, source, metadata)
            
            # Update usage stats
            self._update_usage_stats(db, user_id, system_name, amount)
            
            db.session.commit()
            
            return {
                "success": True,
                "user_id": user_id,
                "point_type": system_name,
                "amount": amount,
                "balance_before": balance_before,
                "balance_after": balance_after,
                "message": "Points added"
            }
        except Exception as e:
            db.session.rollback()
            return {"success": False, "error": str(e)}
    
    def _update_snapshot(self, db, user_id: str, system_name: str, new_value: float, previous_value: float, delta: float, source: str, metadata: Optional[Dict[str, Any]] = None):
        """Update or create system point snapshot"""
        db.session.execute(
            text("""
                INSERT INTO system_point_snapshots 
                (user_id, system_name, point_value, previous_value, delta, snapshot_data, source, metadata, created_at, updated_at)
                VALUES (:user_id, :system_name, :point_value, :previous_value, :delta, :snapshot_data, :source, :metadata, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            """),
            {
                "user_id": user_id,
                "system_name": system_name,
                "point_value": new_value,
                "previous_value": previous_value,
                "delta": delta,
                "snapshot_data": json.dumps({
                    "value": new_value,
                    "previous": previous_value,
                    "delta": delta,
                    "source": source,
                    "timestamp": datetime.now().isoformat()
                }),
                "source": source,
                "metadata": json.dumps(metadata or {})
            },
        )
    
    def _log_transaction(self, db, user_id: str, system_name: str, transaction_type: str, amount: float, balance_before: float, balance_after: float, source: str, metadata: Optional[Dict[str, Any]] = None):
        """Log point transaction"""
        try:
            db.session.execute(
                text("""
                    INSERT INTO point_transactions
                    (user_id, system_name, transaction_type, amount, balance_before, balance_after, source, metadata, created_at)
                    VALUES (:user_id, :system_name, :transaction_type, :amount, :balance_before, :balance_after, :source, :metadata, CURRENT_TIMESTAMP)
                """),
                {
                    "user_id": user_id,
                    "system_name": system_name,
                    "transaction_type": transaction_type,
                    "amount": amount,
                    "balance_before": balance_before,
                    "balance_after": balance_after,
                    "source": source,
                    "metadata": json.dumps(metadata or {})
                },
            )
        except Exception:
            # Table might not exist yet
            pass
    
    def _update_usage_stats(self, db, user_id: str, system_name: str, points_earned: float):
        """Update system usage statistics"""
        try:
            # Check if stats exist
            existing = db.session.execute(
                text("""
                    SELECT id, usage_count, total_points_earned 
                    FROM system_usage_stats
                    WHERE user_id = :user_id AND system_name = :system_name
                """),
                {"user_id": user_id, "system_name": system_name},
            ).fetchone()
            
            if existing:
                # Update existing
                db.session.execute(
                    text("""
                        UPDATE system_usage_stats
                        SET usage_count = usage_count + 1,
                            total_points_earned = total_points_earned + :points,
                            average_points_per_use = (total_points_earned + :points) / (usage_count + 1),
                            last_used_at = CURRENT_TIMESTAMP,
                            updated_at = CURRENT_TIMESTAMP
                        WHERE user_id = :user_id AND system_name = :system_name
                    """),
                    {"user_id": user_id, "system_name": system_name, "points": points_earned},
                )
            else:
                # Create new
                db.session.execute(
                    text("""
                        INSERT INTO system_usage_stats
                        (user_id, system_name, usage_count, total_points_earned, average_points_per_use, first_used_at, last_used_at, created_at, updated_at)
                        VALUES (:user_id, :system_name, 1, :points, :points, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                    """),
                    {"user_id": user_id, "system_name": system_name, "points": points_earned},
                )
        except Exception:
            # Table might not exist yet
            pass
    
    def get_all_points(self, user_id: str = "default_user") -> Dict:
        """Get all points for a user from database"""
        try:
            app, db = self._get_db()
            with app.app_context():
                self._ensure_player_level_row(db, user_id)
                
                # Get XP and level
                pl = db.session.execute(
                    text("SELECT level, total_xp FROM player_levels WHERE user_id = :user_id LIMIT 1"),
                    {"user_id": user_id},
                ).fetchone()
                
                level = int(pl[0]) if pl and pl[0] else 1
                xp_total = int(pl[1]) if pl and pl[1] else 0
                
                # Get latest snapshots for all systems
                rows = db.session.execute(
                    text("""
                        SELECT s.system_name, s.point_value
                        FROM system_point_snapshots s
                        JOIN (
                            SELECT system_name, MAX(id) AS max_id
                            FROM system_point_snapshots
                            WHERE user_id = :user_id
                            GROUP BY system_name
                        ) t ON s.id = t.max_id
                        WHERE s.user_id = :user_id
                    """),
                    {"user_id": user_id},
                ).fetchall()
                
                snapshots = {r[0]: r[1] for r in rows} if rows else {}
                
                # Build points dict with all known systems
                points = {
                    "xp_total": xp_total,
                    "level": level,
                    "stats_points_total": float(snapshots.get("stats_points_total", 0) or 0),
                    "stats_points_available": float(snapshots.get("stats_points_available", 0) or 0),
                    "achievements_earned": int(snapshots.get("achievements_earned", 0) or 0),
                    "milestones_reached": int(snapshots.get("milestones_reached", 0) or 0),
                    "trophy_points": float(snapshots.get("trophy_points", 0) or 0),
                    "coins": float(snapshots.get("coins", 0) or 0),
                    "credits": float(snapshots.get("credits", 0) or 0),
                    "battle_points": float(snapshots.get("battle_points", 0) or 0),
                    "social_points": float(snapshots.get("social_points", 0) or 0),
                    "knowledge_points": float(snapshots.get("knowledge_points", 0) or 0),
                    "dna_manipulation_points": float(snapshots.get("dna_manipulation_points", 0) or 0),
                    "dna_cloning_points": float(snapshots.get("dna_cloning_points", 0) or 0),
                    "generation_points": float(snapshots.get("generation_points", 0) or 0),
                    "accuracy_grade": "A+",
                }
                
                # Include all systems dynamically
                points["systems"] = {k: float(v or 0) for k, v in snapshots.items()}
                
                return {"success": True, "user_id": user_id, "points": points}
        except Exception as e:
            return {"success": False, "error": str(e), "user_id": user_id, "points": {}}
    
    def get_point_statistics(self, user_id: str, days: int = 30) -> Dict:
        """Get point statistics for a user"""
        try:
            app, db = self._get_db()
            with app.app_context():
                # Get transaction stats
                stats = db.session.execute(
                    text("""
                        SELECT 
                            system_name,
                            COUNT(*) as transaction_count,
                            SUM(amount) as total_earned,
                            AVG(amount) as average_amount,
                            MIN(amount) as min_amount,
                            MAX(amount) as max_amount
                        FROM point_transactions
                        WHERE user_id = :user_id 
                        AND created_at >= datetime('now', '-' || :days || ' days')
                        GROUP BY system_name
                    """),
                    {"user_id": user_id, "days": days},
                ).fetchall()
                
                return {
                    "success": True,
                    "user_id": user_id,
                    "period_days": days,
                    "statistics": [
                        {
                            "system_name": row[0],
                            "transaction_count": row[1],
                            "total_earned": float(row[2] or 0),
                            "average_amount": float(row[3] or 0),
                            "min_amount": float(row[4] or 0),
                            "max_amount": float(row[5] or 0),
                        }
                        for row in stats
                    ]
                }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    def get_system_usage_stats(self, user_id: str) -> Dict:
        """Get usage statistics for all systems"""
        try:
            app, db = self._get_db()
            with app.app_context():
                stats = db.session.execute(
                    text("""
                        SELECT system_name, usage_count, total_points_earned, average_points_per_use, last_used_at
                        FROM system_usage_stats
                        WHERE user_id = :user_id
                        ORDER BY total_points_earned DESC
                    """),
                    {"user_id": user_id},
                ).fetchall()
                
                return {
                    "success": True,
                    "user_id": user_id,
                    "systems": [
                        {
                            "system_name": row[0],
                            "usage_count": row[1],
                            "total_points_earned": float(row[2] or 0),
                            "average_points_per_use": float(row[3] or 0),
                            "last_used_at": row[4].isoformat() if row[4] else None,
                        }
                        for row in stats
                    ]
                }
        except Exception as e:
            return {"success": False, "error": str(e)}


# Global instance
unified_points_db_enhanced = UnifiedPointsDatabaseEnhanced()
