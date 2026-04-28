"""
Database Migration Script for Hunters Game
Creates all necessary tables for the leveling system
"""
import os
import sys

# Add project root to path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from src.app import create_app
from src.db.models import db, PlayerLevel, XPHistory, DailyActivity
from src.db.init_db import init_db_on_first_run


def migrate_hunters_game():
    """Create Hunters Game database tables"""
    print("=" * 60)
    print("Hunters Game Database Migration")
    print("=" * 60)
    print()
    
    app = create_app()
    
    with app.app_context():
        try:
            # Initialize database (creates all tables)
            print("Initializing database...")
            success = init_db_on_first_run(app, db)
            
            if not success:
                print("[WARN] Database initialization had issues")
                print("Attempting to create tables directly...")
            
            # Create tables explicitly
            print("Creating Hunters Game tables...")
            db.create_all()
            
            # Verify tables exist
            from sqlalchemy import inspect
            inspector = inspect(db.engine)
            tables = inspector.get_table_names()
            
            required_tables = ['player_levels', 'xp_history', 'daily_activities']
            missing_tables = [t for t in required_tables if t not in tables]
            
            if missing_tables:
                print(f"[ERROR] Missing tables: {', '.join(missing_tables)}")
                return False
            
            print("[OK] All tables created successfully!")
            print()
            print("Created tables:")
            for table in required_tables:
                if table in tables:
                    print(f"  [OK] {table}")
            
            # Get table info
            print()
            print("Table Information:")
            for table_name in required_tables:
                try:
                    result = db.session.execute(
                        f"SELECT COUNT(*) FROM {table_name}"
                    )
                    count = result.scalar()
                    print(f"  {table_name}: {count} rows")
                except Exception as e:
                    print(f"  {table_name}: Error - {e}")
            
            print()
            print("=" * 60)
            print("[OK] Migration Complete!")
            print("=" * 60)
            
            return True
            
        except Exception as e:
            print(f"[ERROR] Migration failed: {e}")
            import traceback
            traceback.print_exc()
            return False


if __name__ == '__main__':
    success = migrate_hunters_game()
    sys.exit(0 if success else 1)

