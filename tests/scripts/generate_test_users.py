"""
Script to generate test users for performance testing
"""
import sys
import os
from pathlib import Path
import json
import random
import uuid

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

def generate_test_users(count=1000):
    """Generate test users with random points"""
    print(f"Generating {count} test users...")
    
    try:
        from src.app import create_app
        from backend.services.unified_points_database import unified_points_db
        from src.db.models import db, UserProfile
        
        # Create Flask app and use application context
        app = create_app()
        
        with app.app_context():
            created = 0
            for i in range(count):
                user_id = f'test_user_{i}'
                
                # Check if user already exists
                existing = UserProfile.query.filter_by(user_id=user_id).first()
                if existing:
                    continue
                
                # Create user profile
                user = UserProfile(
                    id=str(uuid.uuid4()),
                    user_id=user_id,
                    username=f'TestUser{i}',
                    preferences=json.dumps({
                        'test_user': True,
                        'created_for_testing': True
                    })
                )
                
                db.session.add(user)
                
                # Add random points
                points_data = {
                    'xp_points': random.randint(0, 10000),
                    'battle_points': random.randint(0, 5000),
                    'activity_points': random.randint(0, 3000),
                    'trophy_points': random.randint(0, 2000),
                    'generation_points': random.randint(0, 4000),
                    'chat_points': random.randint(0, 1500),
                }
                
                # Update unified points
                for point_type, value in points_data.items():
                    unified_points_db.add_points(user_id, point_type, value, source='test_user_generation')
                
                created += 1
                
                if (i + 1) % 100 == 0:
                    print(f"Created {i + 1}/{count} users...")
                    db.session.commit()
            
            db.session.commit()
            print(f"\n✅ Created {created} test users")
            return created
        
    except Exception as e:
        print(f"❌ Error generating test users: {e}")
        import traceback
        traceback.print_exc()
        return 0


if __name__ == '__main__':
    count = int(sys.argv[1]) if len(sys.argv) > 1 else 1000
    generate_test_users(count)
