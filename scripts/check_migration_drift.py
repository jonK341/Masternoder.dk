#!/usr/bin/env python3
"""
Check migration drift between expected canonical tables and current DB.
Also prints missing ledger entries for canonical migration scripts.
"""
import os
from sqlalchemy import create_engine, inspect, text


CANONICAL_TABLES = {
    "battle_matches",
    "trophy_definitions",
    "user_trophy_unlocks",
    "shop_items",
    "shop_purchases",
    "user_inventory",
    "chat_sessions",
    "chat_messages",
    "gallery_items",
    "user_gallery_state",
    "gallery_downloads",
    "point_aggregates_daily",
    "video_generation_jobs",
    "job_artifacts",
    "player_levels",
    "xp_history",
    "daily_activities",
    "point_transactions",
    "point_history",
    "point_aggregates",
    "point_analytics",
    "system_usage_stats",
    "system_point_snapshots",
    "agent_missions",
    "agent_quests",
    "agent_personality",
    "agent_skill_history",
    "agent_ai_intelligence",
    "agent_errors",
    "agent_use_cases",
    "dna_manipulation",
    "agent_technologies",
    "agent_technology_improvements",
    "agent_technology_metrics",
    "agent_technology_usage",
    "agent_technology_relationships",
    "agent_technology_events",
    "rewards",
    "user_rewards",
    "comm_psych_theory_unlocks",
    "comm_psych_activity_log",
    "star_map_visits",
    "hunters_game_sessions",
    "hunters_profiles",
    "hunters_spells",
    "agent_geo_refs",
    "schema_migrations",
}

EXPECTED_CANONICAL_SCRIPTS = {
    "scripts/unified_points_database_migration.py",
    "scripts/missing_tables_migration.py",
    "scripts/agent_technologies_database_migration.py",
    "scripts/migrate_hunters_game_complete.py",
    "scripts/communication_psychology_migration.py",
    "scripts/hunters_star_map_migration.py",
}


def main() -> int:
    db_url = os.getenv("DATABASE_URL") or os.getenv("SQLALCHEMY_DATABASE_URI") or "sqlite:///instance/database.db"
    engine = create_engine(db_url)
    insp = inspect(engine)
    current = set(insp.get_table_names())

    missing_tables = sorted(CANONICAL_TABLES - current)
    extra_tables = sorted(current - CANONICAL_TABLES)

    print(f"DB: {db_url}")
    print(f"Current tables: {len(current)}")
    print(f"Expected canonical tables: {len(CANONICAL_TABLES)}")
    print(f"Missing canonical tables: {len(missing_tables)}")
    for name in missing_tables:
        print(f"  MISSING_TABLE: {name}")

    print(f"Extra tables (not in canonical set): {len(extra_tables)}")
    for name in extra_tables:
        print(f"  EXTRA_TABLE: {name}")

    missing_script_records = []
    with engine.connect() as conn:
        if "schema_migrations" in current:
            rows = conn.execute(text("SELECT DISTINCT script_name FROM schema_migrations")).fetchall()
            present_scripts = {r[0] for r in rows}
            missing_script_records = sorted(EXPECTED_CANONICAL_SCRIPTS - present_scripts)
        else:
            missing_script_records = sorted(EXPECTED_CANONICAL_SCRIPTS)

    print(f"Missing canonical script ledger entries: {len(missing_script_records)}")
    for name in missing_script_records:
        print(f"  MISSING_LEDGER: {name}")

    if missing_tables or missing_script_records:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
