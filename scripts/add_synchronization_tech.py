#!/usr/bin/env python3
"""
Add Synchronization technology to agent_technologies and recap knowledge db.
Run after migrations to ensure agent_synchronization exists.
"""
import os
import sys
import json
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

SYNC_TECH = {
    'tech_id': 'agent_synchronization',
    'tech_name': 'Synchronization',
    'category': 'core',
    'icon': '🔄',
    'description': 'Platform-wide sync device, domain sync, status API. Rulebook V16.',
}

IMPROVEMENT_FUNCTIONS = [
    'optimize_performance', 'enhance_security', 'improve_reliability',
    'scale_capacity', 'reduce_latency', 'increase_throughput',
    'add_monitoring', 'enable_auto_recovery', 'improve_caching',
    'enhance_logging', 'add_analytics', 'upgrade_algorithm',
]


def add_to_agent_technologies():
    """Insert or ignore agent_synchronization in agent_technologies table."""
    try:
        from src.app import create_app
        from src.db.models import db
        from sqlalchemy import text, inspect

        app = create_app()
        with app.app_context():
            inspector = inspect(db.engine)
            if 'agent_technologies' not in inspector.get_table_names():
                print("   [WARN] agent_technologies table does not exist. Run migration first.")
                return False

            db.session.execute(
                text("""
                    INSERT OR IGNORE INTO agent_technologies
                    (tech_id, tech_name, category, icon, description, version, status, enabled, created_at, updated_at)
                    VALUES (:tech_id, :tech_name, :category, :icon, :description, '1.0.0', 'active', 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                """),
                {
                    "tech_id": SYNC_TECH['tech_id'],
                    "tech_name": SYNC_TECH['tech_name'],
                    "category": SYNC_TECH['category'],
                    "icon": SYNC_TECH['icon'],
                    "description": SYNC_TECH['description'],
                }
            )

            if 'agent_technology_improvements' in inspector.get_table_names():
                for imp in IMPROVEMENT_FUNCTIONS:
                    try:
                        db.session.execute(
                            text("""
                                INSERT OR IGNORE INTO agent_technology_improvements
                                (tech_id, improvement_function, improvement_name, status, level, max_level, created_at, updated_at)
                                VALUES (:tech_id, :improvement_function, :improvement_name, 'available', 0, 10, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                            """),
                            {
                                "tech_id": SYNC_TECH['tech_id'],
                                "improvement_function": imp,
                                "improvement_name": imp.replace('_', ' ').title(),
                            }
                        )
                    except Exception:
                        pass

            db.session.commit()
            print("   [OK] agent_synchronization added to agent_technologies")
            return True
    except Exception as e:
        print(f"   [ERROR] agent_technologies: {e}")
        try:
            db.session.rollback()
        except Exception:
            pass
        return False


def ensure_knowledge_entry():
    """Ensure Synchronization entry exists in agent_learning_knowledge.json."""
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    path = os.path.join(base, 'data', 'agent_learning_knowledge.json')
    if not os.path.exists(path):
        print("   [WARN] agent_learning_knowledge.json not found")
        return False
    try:
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        entries = data.get('entries') or []
        if not any(e.get('id') == 'synchronization' for e in entries):
            entries.append({
                "id": "synchronization",
                "source": "system",
                "title": "Synchronization",
                "text": "Platform-wide sync mechanisms. unified_points_sync_device.record_domain_sync(domain) after writes. Domains: unified_points, users, profiles, aggregator, trophies, achievements, battle, shop, quests, leaderboards, analytics, compendium, generator, gallery, social, agent_skillsets, agent_knowledge, game, paypal, login, onboarding. GET /api/sync/status, POST /api/sync/now. Rulebook V16.",
                "rulebook_ref": ["v16", "v7"],
                "created_at": datetime.utcnow().strftime("%Y-%m-%d"),
            })
            data['entries'] = entries
            data['updated_at'] = datetime.utcnow().strftime("%Y-%m-%d")
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            print("   [OK] Synchronization entry added to agent_learning_knowledge.json")
        else:
            print("   [OK] Synchronization entry already in agent_learning_knowledge.json")
        return True
    except Exception as e:
        print(f"   [ERROR] agent_learning_knowledge: {e}")
        return False


def main():
    print("=" * 60)
    print("ADD SYNCHRONIZATION TECHNOLOGY")
    print("=" * 60)
    print()
    add_to_agent_technologies()
    ensure_knowledge_entry()
    print()
    print("Done.")


if __name__ == '__main__':
    main()
