#!/usr/bin/env python3
"""
Run Database Operations
Execute various database operations to validate functionality
"""
import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_database_queries():
    """Test database queries"""
    print("=" * 70)
    print("DATABASE OPERATIONS TEST")
    print("=" * 70)
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    try:
        from src.app import create_app
        from src.db.models import db
        from sqlalchemy import text
        
        app = create_app()
        with app.app_context():
            print("Testing database queries...")
            print()
            
            # Test user_profiles
            try:
                result = db.session.execute(text("SELECT COUNT(*) FROM user_profiles"))
                count = result.scalar()
                print(f"  ✓ user_profiles: {count} records")
            except Exception as e:
                print(f"  ✗ user_profiles: {e}")
            
            # Test onboarding_progress
            try:
                result = db.session.execute(text("SELECT COUNT(*) FROM onboarding_progress"))
                count = result.scalar()
                print(f"  ✓ onboarding_progress: {count} records")
            except Exception as e:
                print(f"  ✗ onboarding_progress: {e}")
            
            # Test player_levels
            try:
                result = db.session.execute(text("SELECT COUNT(*) FROM player_levels"))
                count = result.scalar()
                print(f"  ✓ player_levels: {count} records")
            except Exception as e:
                print(f"  ✗ player_levels: {e}")
            
            # Test xp_history
            try:
                result = db.session.execute(text("SELECT COUNT(*) FROM xp_history"))
                count = result.scalar()
                print(f"  ✓ xp_history: {count} records")
            except Exception as e:
                print(f"  ✗ xp_history: {e}")
            
            # Test daily_activities
            try:
                result = db.session.execute(text("SELECT COUNT(*) FROM daily_activities"))
                count = result.scalar()
                print(f"  ✓ daily_activities: {count} records")
            except Exception as e:
                print(f"  ✗ daily_activities: {e}")
            
            # Test user_agent_skills
            try:
                result = db.session.execute(text("SELECT COUNT(*) FROM user_agent_skills"))
                count = result.scalar()
                print(f"  ✓ user_agent_skills: {count} records")
            except Exception as e:
                print(f"  ✗ user_agent_skills: {e}")
            
            # Test calculation_history
            try:
                result = db.session.execute(text("SELECT COUNT(*) FROM calculation_history"))
                count = result.scalar()
                print(f"  ✓ calculation_history: {count} records")
            except Exception as e:
                print(f"  ✗ calculation_history: {e}")
            
            # Test rewards
            try:
                result = db.session.execute(text("SELECT COUNT(*) FROM rewards"))
                count = result.scalar()
                print(f"  ✓ rewards: {count} records")
            except Exception as e:
                print(f"  ✗ rewards: {e}")
            
            print()
            print("=" * 70)
            print("DATABASE OPERATIONS COMPLETE")
            print("=" * 70)
            print()
            
            return True
            
    except Exception as e:
        print(f"\n✗ Database operations failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_data_integrity():
    """Test data integrity"""
    print("Testing data integrity...")
    print()
    
    try:
        from src.app import create_app
        from src.db.models import db
        from sqlalchemy import text
        
        app = create_app()
        with app.app_context():
            # Test user profile with onboarding
            result = db.session.execute(text("""
                SELECT COUNT(*) FROM user_profiles up
                LEFT JOIN onboarding_progress op ON up.user_id = op.user_id
                WHERE up.user_id IS NOT NULL
            """))
            count = result.scalar()
            print(f"  ✓ Users with profiles: {count}")
            
            # Test user with level
            result = db.session.execute(text("""
                SELECT COUNT(*) FROM user_profiles up
                LEFT JOIN player_levels pl ON up.user_id = pl.user_id
                WHERE pl.user_id IS NOT NULL
            """))
            count = result.scalar()
            print(f"  ✓ Users with levels: {count}")
            
            # Test user with XP history
            result = db.session.execute(text("""
                SELECT COUNT(DISTINCT user_id) FROM xp_history
            """))
            count = result.scalar()
            print(f"  ✓ Users with XP history: {count}")
            
            print()
            return True
            
    except Exception as e:
        print(f"  ✗ Data integrity test failed: {e}")
        return False

if __name__ == '__main__':
    print()
    test_database_queries()
    test_data_integrity()
    print("All database operations completed!")
