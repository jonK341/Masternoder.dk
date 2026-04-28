"""
Create Error Logging Database Tables
Creates the error_logs and error_summaries tables
"""
import os
import sys

# Add project root to path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from src.app import create_app
from src.db.models import db
from src.db.models_error_logging import ErrorLog, ErrorSummary


def create_error_logging_tables():
    """Create error logging tables"""
    print("=" * 70)
    print("CREATE ERROR LOGGING TABLES")
    print("=" * 70)
    print()
    
    app = create_app()
    
    with app.app_context():
        try:
            print("Creating error logging tables...")
            db.create_all()
            
            # Verify tables exist
            from sqlalchemy import inspect
            inspector = inspect(db.engine)
            tables = inspector.get_table_names()
            
            required_tables = ['error_logs', 'error_summaries']
            missing_tables = [t for t in required_tables if t not in tables]
            
            if missing_tables:
                print(f"[ERROR] Missing tables: {', '.join(missing_tables)}")
                return False
            
            print("[OK] All error logging tables created successfully!")
            print()
            print("Created tables:")
            for table in required_tables:
                if table in tables:
                    print(f"  [OK] {table}")
            
            # Get table info
            print()
            print("Table Information:")
            for table_name in required_tables:
                if table_name in tables:
                    columns = inspector.get_columns(table_name)
                    print(f"  {table_name}: {len(columns)} columns")
            
            print()
            print("=" * 70)
            print("SUCCESS")
            print("=" * 70)
            return True
            
        except Exception as e:
            print(f"\n[ERROR] Failed to create tables: {e}")
            import traceback
            traceback.print_exc()
            return False


if __name__ == '__main__':
    success = create_error_logging_tables()
    sys.exit(0 if success else 1)
