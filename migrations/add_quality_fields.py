"""
Migration: Add quality fields to Documentary model

This migration adds:
- quality_score (Float)
- quality_level (String)
- quality_meets_a_plus (Boolean)

Run this script to update existing databases.
"""
import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def run_migration():
    """Add quality columns to documentaries table"""
    try:
        from src.app import create_app
        from src.db.models import db, Documentary
        from sqlalchemy import text
        
        app = create_app()
        
        with app.app_context():
            # Check if columns already exist
            from sqlalchemy import inspect
            inspector = inspect(db.engine)
            columns = [col['name'] for col in inspector.get_columns('documentaries')]
            
            print("=" * 70)
            print("Migration: Add Quality Fields to Documentary Model")
            print("=" * 70)
            print()
            
            # Add quality_score if missing
            if 'quality_score' not in columns:
                print("Adding quality_score column...")
                db.session.execute(text("""
                    ALTER TABLE documentaries 
                    ADD COLUMN quality_score REAL DEFAULT 0.0
                """))
                print("[OK] quality_score added")
            else:
                print("[OK] quality_score already exists")
            
            # Add quality_level if missing
            if 'quality_level' not in columns:
                print("Adding quality_level column...")
                db.session.execute(text("""
                    ALTER TABLE documentaries 
                    ADD COLUMN quality_level VARCHAR(20)
                """))
                print("[OK] quality_level added")
            else:
                print("[OK] quality_level already exists")
            
            # Add quality_meets_a_plus if missing
            if 'quality_meets_a_plus' not in columns:
                print("Adding quality_meets_a_plus column...")
                db.session.execute(text("""
                    ALTER TABLE documentaries 
                    ADD COLUMN quality_meets_a_plus BOOLEAN DEFAULT 0
                """))
                print("[OK] quality_meets_a_plus added")
            else:
                print("[OK] quality_meets_a_plus already exists")
            
            # Commit changes
            db.session.commit()
            
            print()
            print("=" * 70)
            print("[OK] Migration completed successfully!")
            print("=" * 70)
            print()
            print("New columns added:")
            print("  - quality_score (REAL)")
            print("  - quality_level (VARCHAR(20))")
            print("  - quality_meets_a_plus (BOOLEAN)")
            print()
            
            # Verify columns exist
            from sqlalchemy import inspect
            inspector = inspect(db.engine)
            columns_after = [col['name'] for col in inspector.get_columns('documentaries')]
            
            if all(col in columns_after for col in ['quality_score', 'quality_level', 'quality_meets_a_plus']):
                print("[OK] All quality columns verified!")
            else:
                print("[WARN] Warning: Some columns may not have been added correctly")
            
            return True
            
    except Exception as e:
        print(f"[ERROR] Migration failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    success = run_migration()
    sys.exit(0 if success else 1)

