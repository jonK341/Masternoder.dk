#!/usr/bin/env python3
"""
Check and Fix Functions and Loading Tables
Comprehensive check of database tables, data loading functions, and table population
"""
import os
import sys
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def check_database_tables():
    """Check if required database tables exist"""
    print("=" * 70)
    print("DATABASE TABLES CHECK")
    print("=" * 70)
    
    try:
        from src.app import create_app
        from src.db.models import db
        from sqlalchemy import inspect
        
        app = create_app()
        with app.app_context():
            inspector = inspect(db.engine)
            existing_tables = inspector.get_table_names()
            
            # Required tables
            required_tables = [
                'user_profiles',
                'user_scraped_info',
                'user_agent_skills',
                'onboarding_progress',
                'calculation_history',
                'point_loss_detection',
                'repair_log',
                'predictions',
                'pattern_analysis',
                'anomaly_detection',
                'system_point_snapshots',
                'player_levels',
                'xp_history',
                'daily_activities',
                'rewards',
                'user_rewards'
            ]
            
            print(f"\nExisting tables: {len(existing_tables)}")
            print(f"Required tables: {len(required_tables)}")
            print()
            
            missing_tables = []
            existing_required = []
            
            for table in required_tables:
                if table in existing_tables:
                    existing_required.append(table)
                    print(f"  ✓ {table}")
                else:
                    missing_tables.append(table)
                    print(f"  ✗ {table} - MISSING")
            
            print()
            print(f"Summary: {len(existing_required)}/{len(required_tables)} tables exist")
            
            if missing_tables:
                print(f"\nMissing tables ({len(missing_tables)}):")
                for table in missing_tables:
                    print(f"  - {table}")
                return False, missing_tables
            else:
                print("\n✓ All required tables exist!")
                return True, []
                
    except Exception as e:
        print(f"\n✗ Error checking tables: {e}")
        import traceback
        traceback.print_exc()
        return False, []

def check_data_loading_functions():
    """Check data loading functions in services"""
    print("\n" + "=" * 70)
    print("DATA LOADING FUNCTIONS CHECK")
    print("=" * 70)
    
    services_to_check = [
        'agent_secretary',
        'agent_integration',
        'agent_user_experience',
        'agent_performance_optimizer',
        'agent_security',
        'agent_analytics',
        'agent_judge',
        'agent_social_engagement',
        'master_fix_agent_skills'
    ]
    
    working_services = []
    missing_services = []
    
    for service_name in services_to_check:
        try:
            module = __import__(f'backend.services.{service_name}', fromlist=[service_name])
            if hasattr(module, service_name):
                service_class = getattr(module, service_name)
                if hasattr(service_class, 'load_data'):
                    working_services.append(service_name)
                    print(f"  ✓ {service_name} - has load_data()")
                else:
                    missing_services.append(service_name)
                    print(f"  ✗ {service_name} - missing load_data()")
            else:
                missing_services.append(service_name)
                print(f"  ✗ {service_name} - service class not found")
        except ImportError as e:
            missing_services.append(service_name)
            print(f"  ✗ {service_name} - import error: {e}")
        except Exception as e:
            missing_services.append(service_name)
            print(f"  ✗ {service_name} - error: {e}")
    
    print()
    print(f"Summary: {len(working_services)}/{len(services_to_check)} services have load_data()")
    
    return len(working_services) == len(services_to_check), missing_services

def check_table_data_population():
    """Check if tables have data"""
    print("\n" + "=" * 70)
    print("TABLE DATA POPULATION CHECK")
    print("=" * 70)
    
    try:
        from src.app import create_app
        from src.db.models import db
        from sqlalchemy import text
        
        app = create_app()
        with app.app_context():
            tables_to_check = [
                'user_profiles',
                'calculation_history',
                'point_loss_detection',
                'player_levels',
                'xp_history',
                'rewards'
            ]
            
            results = {}
            
            for table in tables_to_check:
                try:
                    result = db.session.execute(text(f"SELECT COUNT(*) FROM {table}"))
                    count = result.scalar()
                    results[table] = count
                    status = "✓" if count > 0 else "⚠"
                    print(f"  {status} {table}: {count} records")
                except Exception as e:
                    results[table] = -1
                    print(f"  ✗ {table}: Error - {e}")
            
            print()
            empty_tables = [t for t, c in results.items() if c == 0]
            if empty_tables:
                print(f"⚠ Empty tables ({len(empty_tables)}):")
                for table in empty_tables:
                    print(f"  - {table}")
                return False, empty_tables
            else:
                print("✓ All checked tables have data!")
                return True, []
                
    except Exception as e:
        print(f"\n✗ Error checking table data: {e}")
        import traceback
        traceback.print_exc()
        return False, []

def generate_fix_report(missing_tables, missing_services, empty_tables):
    """Generate a report of what needs to be fixed"""
    print("\n" + "=" * 70)
    print("FIX REPORT")
    print("=" * 70)
    
    if not missing_tables and not missing_services and not empty_tables:
        print("\n✓ Everything looks good! No fixes needed.")
        return
    
    print("\nActions needed:")
    
    if missing_tables:
        print(f"\n1. CREATE MISSING TABLES ({len(missing_tables)}):")
        print("   Run migration scripts:")
        for table in missing_tables:
            if 'calculation' in table or 'point_loss' in table or 'repair' in table:
                print(f"   - python scripts/migrate_advanced_calculator.py")
                break
            elif 'player_levels' in table or 'xp_history' in table:
                print(f"   - python scripts/migrate_hunters_game_complete.py")
                break
            elif 'rewards' in table:
                print(f"   - python scripts/migrate_hunters_game_complete.py")
                break
    
    if empty_tables:
        print(f"\n2. POPULATE EMPTY TABLES ({len(empty_tables)}):")
        for table in empty_tables:
            if 'calculation' in table:
                print(f"   - python scripts/populate_advanced_calculator_data.py")
                break
            elif 'rewards' in table:
                print(f"   - python scripts/populate_initial_rewards.py")
                break
    
    if missing_services:
        print(f"\n3. FIX MISSING SERVICES ({len(missing_services)}):")
        for service in missing_services:
            print(f"   - Check backend/services/{service}.py")

def main():
    """Main function"""
    print("=" * 70)
    print("FUNCTIONS AND TABLES COMPREHENSIVE CHECK")
    print("=" * 70)
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Check database tables
    tables_ok, missing_tables = check_database_tables()
    
    # Check data loading functions
    functions_ok, missing_services = check_data_loading_functions()
    
    # Check table data
    data_ok, empty_tables = check_table_data_population()
    
    # Generate report
    generate_fix_report(missing_tables, missing_services, empty_tables)
    
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"Database Tables: {'✓ OK' if tables_ok else '✗ Issues found'}")
    print(f"Loading Functions: {'✓ OK' if functions_ok else '✗ Issues found'}")
    print(f"Table Data: {'✓ OK' if data_ok else '✗ Issues found'}")
    
    overall_ok = tables_ok and functions_ok and data_ok
    print(f"\nOverall Status: {'✓ ALL GOOD' if overall_ok else '⚠ NEEDS ATTENTION'}")
    
    return overall_ok

if __name__ == '__main__':
    success = main()
    exit(0 if success else 1)
