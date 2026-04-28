#!/usr/bin/env python3
"""
Hunters Game + Star Map Database Migration
Creates: star_map_visits, hunters_game_sessions, hunters_profiles, hunters_spells, agent_geo_refs
"""
import os
import sys
from sqlalchemy import text, inspect

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.app import create_app
from src.db.models import db


def run():
    app = create_app()
    with app.app_context():
        inspector = inspect(db.engine)
        applied = []

        tables = [
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
        ]

        for name, ddl in tables:
            if name not in inspector.get_table_names():
                db.session.execute(text(ddl))
                db.session.commit()
                applied.append(f"Created {name}")
            else:
                applied.append(f"Exists {name}")

        indexes = [
            ("star_map_visits", "idx_star_visits_user", "user_id"),
            ("hunters_game_sessions", "idx_hunters_sessions_user", "user_id"),
            ("hunters_profiles", "idx_hunters_profiles_user", "user_id"),
            ("hunters_spells", "idx_hunters_spells_user", "user_id"),
            ("agent_geo_refs", "idx_agent_geo_user", "user_id"),
        ]
        for table, idx, col in indexes:
            try:
                db.session.execute(text(f"CREATE INDEX IF NOT EXISTS {idx} ON {table}({col})"))
                db.session.commit()
            except Exception:
                pass

        print("Hunters/Star Map migration done:", applied)


if __name__ == "__main__":
    run()
