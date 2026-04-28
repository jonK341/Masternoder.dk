#!/usr/bin/env python3
"""Seed trophy_definitions for Communication Psychology walkthrough trophies. Safe to run multiple times (INSERT OR IGNORE)."""
import os
import sys
_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _root)
os.chdir(_root)
try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(_root, '.env'))
except Exception:
    pass

# Communication Psychology walkthrough trophies (25 theories, points, starmap, DNA integration)
COMM_PSYCH_TROPHIES = [
    ('comm_psych_first', 'First Theory', 'Unlock your first Communication Psychology theory', 'communication_psychology', '📋', 'common'),
    ('comm_psych_five', 'Five Theories', 'Unlock 5 Communication Psychology theories', 'communication_psychology', '📚', 'common'),
    ('comm_psych_ten', 'Ten Theories', 'Unlock 10 Communication Psychology theories', 'communication_psychology', '🎭', 'rare'),
    ('comm_psych_master_25', 'Master of 25', 'Unlock all 25 Communication Psychology theories', 'communication_psychology', '👑', 'legendary'),
    ('comm_psych_points_500', 'Comm-Psych 500', 'Earn 500 Communication Psychology points', 'communication_psychology', '⭐', 'common'),
    ('comm_psych_points_1k', 'Comm-Psych 1K', 'Earn 1000 Communication Psychology points', 'communication_psychology', '💎', 'rare'),
    ('comm_psych_points_5k', 'Comm-Psych 5K', 'Earn 5000 Communication Psychology points', 'communication_psychology', '🌟', 'legendary'),
]


def run_seed():
    from sqlalchemy import text, inspect
    try:
        from src.app import create_app
        from src.db.models import db
        create_app().app_context().push()
        inspector = inspect(db.engine)
    except Exception as e:
        print("App context failed:", e)
        return []

    if 'trophy_definitions' not in inspector.get_table_names():
        print("Table trophy_definitions not found. Run trophies_migration.py first.")
        return []

    applied = []
    with db.engine.begin() as conn:
        for tid, name, desc, cat, icon, rarity in COMM_PSYCH_TROPHIES:
            try:
                conn.execute(
                    text("""
                        INSERT OR IGNORE INTO trophy_definitions (id, name, description, category, icon, rarity)
                        VALUES (:id, :name, :desc, :cat, :icon, :rarity)
                    """),
                    {"id": tid, "name": name, "desc": desc, "cat": cat, "icon": icon, "rarity": rarity}
                )
                applied.append(tid)
            except Exception as e:
                print(f"Skip {tid}: {e}")
    print("Communication Psychology trophies seeded:", applied)
    return applied


if __name__ == '__main__':
    run_seed()
