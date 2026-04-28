"""
Complete Database Migration for Hunters Game
Creates all tables including rewards system
"""
import os
import sys

# Add project root to path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from src.app import create_app
from src.db.models import db

# Try to import init_db, but make it optional
try:
    from src.db.init_db import init_db_on_first_run
    HAS_INIT_DB = True
except ImportError:
    HAS_INIT_DB = False
    print("[WARN] src.db.init_db not found, using db.create_all() instead")


def create_rewards_tables(db):
    """Create rewards tables using raw SQL"""
    try:
        # Create rewards table
        db.session.execute("""
            CREATE TABLE IF NOT EXISTS rewards (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                reward_type VARCHAR(50) NOT NULL,
                reward_name VARCHAR(100) NOT NULL,
                reward_description TEXT,
                level_required INTEGER,
                points_required INTEGER,
                point_type VARCHAR(50),
                reward_data TEXT,
                icon VARCHAR(10) DEFAULT '🎁',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Create indexes for rewards
        try:
            db.session.execute("CREATE INDEX IF NOT EXISTS idx_rewards_type ON rewards(reward_type)")
        except:
            pass  # Index might already exist
        
        try:
            db.session.execute("CREATE INDEX IF NOT EXISTS idx_rewards_level ON rewards(level_required)")
        except:
            pass
        
        try:
            db.session.execute("CREATE INDEX IF NOT EXISTS idx_rewards_points ON rewards(points_required)")
        except:
            pass
        
        # Create user_rewards table
        db.session.execute("""
            CREATE TABLE IF NOT EXISTS user_rewards (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id VARCHAR(100) NOT NULL,
                reward_id INTEGER NOT NULL,
                claimed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user_id, reward_id)
            )
        """)
        
        # Create indexes for user_rewards
        try:
            db.session.execute("CREATE INDEX IF NOT EXISTS idx_user_rewards_user_id ON user_rewards(user_id)")
        except:
            pass
        
        try:
            db.session.execute("CREATE INDEX IF NOT EXISTS idx_user_rewards_reward_id ON user_rewards(reward_id)")
        except:
            pass
        
        db.session.commit()
        return True
    except Exception as e:
        print(f"[ERROR] Failed to create rewards tables: {e}")
        db.session.rollback()
        return False


def migrate_complete():
    """Create all Hunters Game tables including rewards"""
    print("=" * 70)
    print("Complete Hunters Game Database Migration")
    print("=" * 70)
    print()
    
    app = create_app()
    
    with app.app_context():
        from src.db.models import db
        
        try:
            # Initialize database (creates all tables from models)
            print("Step 1: Initializing database...")
            if HAS_INIT_DB:
                success = init_db_on_first_run(app, db)
                if not success:
                    print("[WARN] Database initialization had issues")
                    print("Attempting to create tables directly...")
            else:
                print("[INFO] Using db.create_all() directly")
            
            # Create tables explicitly from models
            print("Step 2: Creating tables from models...")
            db.create_all()
            
            # Create rewards tables (not in models yet)
            print("Step 3: Creating rewards tables...")
            rewards_success = create_rewards_tables(db)
            
            if not rewards_success:
                print("[WARN] Rewards tables creation had issues")
            
            # Verify tables exist
            print("Step 4: Verifying tables...")
            from sqlalchemy import inspect
            inspector = inspect(db.engine)
            tables = inspector.get_table_names()
            
            required_tables = [
                'player_levels',
                'xp_history', 
                'daily_activities',
                'rewards',
                'user_rewards'
            ]
            
            missing = [t for t in required_tables if t not in tables]
            if missing:
                print(f"[ERROR] Missing tables: {', '.join(missing)}")
                print()
                print("Attempting to create missing tables with SQL...")
                
                # Try to create missing tables with raw SQL
                for table_name in missing:
                    if table_name == 'rewards':
                        create_rewards_tables(db)
                    elif table_name == 'user_rewards':
                        create_rewards_tables(db)
                    else:
                        print(f"[WARN] Cannot auto-create {table_name} - check models")
                
                # Re-check
                inspector = inspect(db.engine)
                tables = inspector.get_table_names()
                missing = [t for t in required_tables if t not in tables]
                
                if missing:
                    print(f"[ERROR] Still missing tables: {', '.join(missing)}")
                    return False
            
            print("[OK] All tables created successfully!")
            print()
            print("Created tables:")
            for table in required_tables:
                if table in tables:
                    print(f"  ✅ {table}")
                else:
                    print(f"  ❌ {table} - MISSING")
            
            # Get table info
            print()
            print("Table Information:")
            for table_name in required_tables:
                if table_name in tables:
                    try:
                        result = db.session.execute(
                            f"SELECT COUNT(*) FROM {table_name}"
                        )
                        count = result.scalar()
                        print(f"  {table_name}: {count} rows")
                    except Exception as e:
                        print(f"  {table_name}: Error querying - {e}")
                else:
                    print(f"  {table_name}: Table does not exist")
            
            # Check table structures
            print()
            print("Table Structures:")
            for table_name in required_tables:
                if table_name in tables:
                    try:
                        result = db.session.execute(f"PRAGMA table_info({table_name})")
                        columns = result.fetchall()
                        print(f"  {table_name}: {len(columns)} columns")
                    except Exception as e:
                        print(f"  {table_name}: Error - {e}")
            
            print()
            print("=" * 70)
            print("[OK] Migration Complete!")
            print("=" * 70)
            print()
            print("Next Steps:")
            print("  1. Populate initial rewards data")
            print("  2. Test API endpoints")
            print("  3. Verify point counters linking")
            
            return True
            
        except Exception as e:
            print(f"[ERROR] Migration failed: {e}")
            import traceback
            traceback.print_exc()
            return False


if __name__ == '__main__':
    success = migrate_complete()
    sys.exit(0 if success else 1)
