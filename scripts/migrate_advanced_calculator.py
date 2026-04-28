"""
Database Migration Script for Advanced Intelligent Calculator
Creates all necessary tables for the advanced calculator system
"""
import os
import sys

# Add project root to path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

try:
    from src.app import create_app
    from src.db.models_advanced_calculator import (
        Base, CalculationHistory, PointLossDetection, RepairLog,
        Prediction, PatternAnalysis, AnomalyDetection, SystemPointSnapshot
    )
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    
    def migrate_advanced_calculator():
        """Create Advanced Calculator database tables"""
        print("=" * 60)
        print("Advanced Intelligent Calculator Database Migration")
        print("=" * 60)
        print()
        
        app = create_app()
        
        with app.app_context():
            try:
                # Get database URI from app config
                db_uri = app.config.get('SQLALCHEMY_DATABASE_URI')
                if not db_uri:
                    # Try to get from environment or use default
                    db_uri = os.getenv('DATABASE_URL', 'sqlite:///vidgenerator.db')
                
                print(f"Database URI: {db_uri}")
                print()
                
                # Create engine
                engine = create_engine(db_uri)
                
                # Create all tables
                print("Creating Advanced Calculator tables...")
                Base.metadata.create_all(engine)
                
                # Verify tables exist
                from sqlalchemy import inspect
                inspector = inspect(engine)
                tables = inspector.get_table_names()
                
                required_tables = [
                    'calculation_history',
                    'point_loss_detection',
                    'repair_log',
                    'predictions',
                    'pattern_analysis',
                    'anomaly_detection',
                    'system_point_snapshots'
                ]
                
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
                    if table_name in tables:
                        columns = inspector.get_columns(table_name)
                        print(f"\n  {table_name}:")
                        for col in columns[:5]:  # Show first 5 columns
                            print(f"    - {col['name']} ({col['type']})")
                        if len(columns) > 5:
                            print(f"    ... and {len(columns) - 5} more columns")
                
                print()
                print("=" * 60)
                print("Migration completed successfully!")
                print("=" * 60)
                
                return True
                
            except Exception as e:
                print(f"[ERROR] Migration failed: {e}")
                import traceback
                traceback.print_exc()
                return False
    
    if __name__ == '__main__':
        success = migrate_advanced_calculator()
        sys.exit(0 if success else 1)
        
except ImportError as e:
    print(f"[ERROR] Import error: {e}")
    print("Make sure you're running this from the correct directory")
    print("and that all dependencies are installed.")
    sys.exit(1)
