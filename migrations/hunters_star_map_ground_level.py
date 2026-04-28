#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
A++ Database Migration: Hunters + Star Map Ground Level
Standard tables and functions for Trophy Hunters, star map, Electric Magnet specials.
Run from project root: python migrations/hunters_star_map_ground_level.py

Creates/ensures:
- player_levels (hunters-compatible)
- rewards, user_rewards
- xp_history
- star_map_visits, hunters_game_sessions, hunters_profiles, hunters_spells, agent_geo_refs
- knowledge_base
"""
import os
import sys
from pathlib import Path

project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))


def _get_app_and_db():
    """Minimal Flask+SQLAlchemy bootstrap. Uses same DB as app (env or instance)."""
    from flask import Flask
    from flask_sqlalchemy import SQLAlchemy
    uri = os.getenv("DATABASE_URL") or os.getenv("SQLALCHEMY_DATABASE_URI")
    if not uri:
        instance = project_root / "instance"
        instance.mkdir(exist_ok=True)
        uri = f"sqlite:///{instance / 'database.db'}"
    app = Flask(__name__)
    app.config["SQLALCHEMY_DATABASE_URI"] = uri
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    db = SQLAlchemy()
    db.init_app(app)
    return app, db


def run_migration():
    try:
        from sqlalchemy import text, inspect

        app, db = _get_app_and_db()
        applied = []

        with app.app_context():
            inspector = inspect(db.engine)
            tables = inspector.get_table_names()

            # ----- player_levels (hunters_game compatible) -----
            if "player_levels" not in tables:
                db.session.execute(text("""
                    CREATE TABLE player_levels (
                        user_id VARCHAR(100) PRIMARY KEY,
                        current_level INTEGER DEFAULT 1,
                        current_xp INTEGER DEFAULT 0,
                        total_xp INTEGER DEFAULT 0,
                        xp_to_next_level INTEGER DEFAULT 1000,
                        level_progress REAL DEFAULT 0.0,
                        title VARCHAR(80) DEFAULT 'Novice Hunter',
                        prestige_level INTEGER DEFAULT 0,
                        stat_creativity INTEGER DEFAULT 0,
                        stat_efficiency INTEGER DEFAULT 0,
                        stat_quality INTEGER DEFAULT 0,
                        stat_social INTEGER DEFAULT 0,
                        stat_knowledge INTEGER DEFAULT 0,
                        available_stat_points INTEGER DEFAULT 0,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """))
                db.session.commit()
                applied.append("player_levels")
            else:
                applied.append("player_levels (exists)")

            # ----- rewards -----
            if "rewards" not in tables:
                db.session.execute(text("""
                    CREATE TABLE rewards (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        reward_type VARCHAR(50) NOT NULL,
                        reward_name VARCHAR(200) NOT NULL,
                        reward_description TEXT,
                        level_required INTEGER,
                        points_required INTEGER,
                        point_type VARCHAR(50),
                        reward_data TEXT,
                        icon VARCHAR(20) DEFAULT '🎁',
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """))
                db.session.commit()
                applied.append("rewards")
            else:
                applied.append("rewards (exists)")

            # ----- user_rewards -----
            if "user_rewards" not in tables:
                db.session.execute(text("""
                    CREATE TABLE user_rewards (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id VARCHAR(100) NOT NULL,
                        reward_id INTEGER NOT NULL,
                        claimed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (reward_id) REFERENCES rewards(id)
                    )
                """))
                db.session.commit()
                applied.append("user_rewards")
            else:
                applied.append("user_rewards (exists)")

            # ----- xp_history -----
            if "xp_history" not in tables:
                db.session.execute(text("""
                    CREATE TABLE xp_history (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id VARCHAR(100) NOT NULL,
                        xp_amount INTEGER NOT NULL,
                        source VARCHAR(80) NOT NULL,
                        action_type VARCHAR(80),
                        metadata TEXT,
                        level_before INTEGER,
                        level_after INTEGER,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """))
                db.session.commit()
                applied.append("xp_history")
            else:
                applied.append("xp_history (exists)")

            # ----- star_map_visits, hunters_* -----
            for name, ddl in [
                ("star_map_visits", """
                    CREATE TABLE IF NOT EXISTS star_map_visits (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id VARCHAR(100) NOT NULL,
                        star_id VARCHAR(80) NOT NULL,
                        visited_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        metadata TEXT
                    )
                """),
                ("hunters_game_sessions", """
                    CREATE TABLE IF NOT EXISTS hunters_game_sessions (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id VARCHAR(100) NOT NULL,
                        session_start TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        session_end TIMESTAMP,
                        duration_seconds INTEGER DEFAULT 0,
                        game_points_earned DECIMAL(15,2) DEFAULT 0,
                        clickthrough_count INTEGER DEFAULT 0,
                        checkpoint_on BOOLEAN DEFAULT 0,
                        metadata TEXT
                    )
                """),
                ("hunters_profiles", """
                    CREATE TABLE IF NOT EXISTS hunters_profiles (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id VARCHAR(100) UNIQUE NOT NULL,
                        profile_data TEXT,
                        agent_tech_enabled BOOLEAN DEFAULT 1,
                        specials TEXT,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """),
                ("hunters_spells", """
                    CREATE TABLE IF NOT EXISTS hunters_spells (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id VARCHAR(100) NOT NULL,
                        spell_id VARCHAR(80) NOT NULL,
                        used_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        cost_paid INTEGER DEFAULT 0,
                        effect_data TEXT
                    )
                """),
                ("agent_geo_refs", """
                    CREATE TABLE IF NOT EXISTS agent_geo_refs (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id VARCHAR(100) NOT NULL,
                        latitude DECIMAL(10,7),
                        longitude DECIMAL(10,7),
                        geo_ref TEXT,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """),
                ("knowledge_base", """
                    CREATE TABLE IF NOT EXISTS knowledge_base (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        kb_key VARCHAR(120) NOT NULL,
                        kb_type VARCHAR(50) DEFAULT 'fact',
                        content TEXT,
                        source VARCHAR(80),
                        metadata TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """),
            ]:
                if name not in inspector.get_table_names():
                    db.session.execute(text(ddl))
                    db.session.commit()
                    applied.append(name)
                else:
                    applied.append(f"{name} (exists)")

            # Indexes
            for table, idx, col in [
                ("star_map_visits", "idx_star_visits_user", "user_id"),
                ("hunters_game_sessions", "idx_hunters_sessions_user", "user_id"),
                ("hunters_profiles", "idx_hunters_profiles_user", "user_id"),
                ("hunters_spells", "idx_hunters_spells_user", "user_id"),
                ("agent_geo_refs", "idx_agent_geo_user", "user_id"),
                ("xp_history", "idx_xp_history_user", "user_id"),
                ("user_rewards", "idx_user_rewards_user", "user_id"),
                ("knowledge_base", "idx_knowledge_base_key", "kb_key"),
            ]:
                if table in inspector.get_table_names():
                    try:
                        db.session.execute(text(f"CREATE INDEX IF NOT EXISTS {idx} ON {table}({col})"))
                        db.session.commit()
                    except Exception:
                        pass

        print("=" * 70)
        print("A++ Hunters / Star Map ground-level migration")
        print("=" * 70)
        for a in applied:
            print(f"  [OK] {a}")
        print("=" * 70)
        return True

    except Exception as e:
        print(f"[ERROR] Migration failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    ok = run_migration()
    sys.exit(0 if ok else 1)
