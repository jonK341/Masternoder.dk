#!/usr/bin/env python3
"""
Resurrect Default User
Fixes default_user profile, creates proper user identification, and awards unified points
"""
import os
import sys
import json
import uuid
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def resurrect_default_user():
    """Resurrect default_user with proper profile and unified points"""
    print("=" * 70)
    print("RESURRECTING DEFAULT_USER")
    print("=" * 70)
    print()
    
    user_id = 'default_user'
    
    # Step 1: Create/Update user profile
    print("[1/4] Creating/Updating user profile...")
    try:
        from src.db.models import db
        from src.app import create_app
        from sqlalchemy import text
        
        app = create_app()
        with app.app_context():
            # Check if profile exists
            result = db.session.execute(
                text("SELECT 1 FROM user_profiles WHERE user_id = :user_id LIMIT 1"),
                {'user_id': user_id}
            ).fetchone()
            
            profile_key = str(uuid.uuid4())[:16]
            preferences = {
                'profile_key': profile_key,
                'display_name': 'Resurrected Player',
                'resurrected_at': datetime.now().isoformat(),
                'resurrection_bonus': True
            }
            
            if result:
                # Update existing profile
                db.session.execute(
                    text("""
                        UPDATE user_profiles 
                        SET preferences = :preferences,
                            updated_at = :updated_at,
                            onboarding_complete = 1
                        WHERE user_id = :user_id
                    """),
                    {
                        'user_id': user_id,
                        'preferences': json.dumps(preferences),
                        'updated_at': datetime.now().isoformat()
                    }
                )
                print(f"  [OK] Updated profile for {user_id}")
            else:
                # Create new profile
                db.session.execute(
                    text("""
                        INSERT INTO user_profiles 
                        (id, user_id, username, preferences, agent_skillset_id, 
                         onboarding_complete, created_at, updated_at)
                        VALUES 
                        (:id, :user_id, :username, :preferences, :skillset,
                         :onboarding_complete, :created_at, :updated_at)
                    """),
                    {
                        'id': str(uuid.uuid4()),
                        'user_id': user_id,
                        'username': 'ResurrectedPlayer',
                        'preferences': json.dumps(preferences),
                        'skillset': 'balanced',
                        'onboarding_complete': True,
                        'created_at': datetime.now().isoformat(),
                        'updated_at': datetime.now().isoformat()
                    }
                )
                print(f"  [OK] Created profile for {user_id}")
            
            db.session.commit()
    except Exception as e:
        print(f"  [WARN] Profile update failed: {e}")
        # Fallback to file
        try:
            profiles_dir = os.path.join(BASE_DIR, 'logs', 'user_profiles')
            os.makedirs(profiles_dir, exist_ok=True)
            profile_file = os.path.join(profiles_dir, f"{user_id}.json")
            profile_data = {
                'user_id': user_id,
                'username': 'ResurrectedPlayer',
                'preferences': preferences,
                'onboarding_complete': True,
                'created_at': datetime.now().isoformat(),
                'updated_at': datetime.now().isoformat()
            }
            with open(profile_file, 'w') as f:
                json.dump(profile_data, f, indent=2)
            print(f"  [OK] Saved profile to file")
        except Exception as e2:
            print(f"  [FAIL] File fallback failed: {e2}")
    
    print()
    
    # Step 2: Award unified points (resurrection bonus)
    print("[2/4] Awarding unified points (resurrection bonus)...")
    try:
        from backend.services.unified_points_database import unified_points_db
        if unified_points_db:
            # Award resurrection bonuses
            bonuses = {
                'xp_points': 1000,
                'battle_points': 500,
                'social_points': 300,
                'achievement_points': 200,
                'milestone_points': 150,
                'trophy_points': 100,
                'activity_points': 400,
                'coins': 1000,
                'credits': 500,
                'knowledge_points': 300,
                'dna_manipulation_points': 50,
                'dna_cloning_points': 50
            }
            
            awarded = {}
            for point_type, amount in bonuses.items():
                try:
                    result = unified_points_db.add_points(
                        user_id, 
                        point_type, 
                        amount, 
                        source='resurrection_bonus',
                        metadata={'resurrection_date': datetime.now().isoformat()}
                    )
                    if result.get('success'):
                        awarded[point_type] = amount
                except Exception as e:
                    print(f"  [WARN] Failed to award {point_type}: {e}")
            
            print(f"  [OK] Awarded {len(awarded)} point types")
            for pt, amt in awarded.items():
                print(f"    - {pt}: +{amt}")
        else:
            print("  [WARN] Unified points database not available")
    except Exception as e:
        print(f"  [WARN] Points award failed: {e}")
    
    print()
    
    # Step 3: Verify points
    print("[3/4] Verifying points...")
    try:
        from backend.services.unified_points_database import unified_points_db
        if unified_points_db:
            points = unified_points_db.get_all_points(user_id)
            print(f"  [OK] XP Total: {points.get('xp_total', 0)}")
            print(f"  [OK] Level: {points.get('level', 1)}")
            print(f"  [OK] Systems: {len(points.get('systems', {}))} point types")
    except Exception as e:
        print(f"  [WARN] Verification failed: {e}")
    
    print()
    
    # Step 4: Create identifier mapping
    print("[4/4] Creating identifier mapping...")
    try:
        identifiers_dir = os.path.join(BASE_DIR, 'logs', 'user_identifiers')
        os.makedirs(identifiers_dir, exist_ok=True)
        
        identifier_file = os.path.join(identifiers_dir, f"{user_id}.json")
        identifier_data = {
            'user_id': user_id,
            'identifiers': {
                'ip_address': 'default',
                'user_agent': 'resurrected',
                'composite_fingerprint': 'default_user_resurrected',
                'timestamp': datetime.now().isoformat()
            },
            'created_at': datetime.now().isoformat(),
            'resurrected': True
        }
        with open(identifier_file, 'w') as f:
            json.dump(identifier_data, f, indent=2)
        print(f"  [OK] Created identifier mapping")
    except Exception as e:
        print(f"  [WARN] Identifier mapping failed: {e}")
    
    print()
    print("=" * 70)
    print("RESURRECTION COMPLETE")
    print("=" * 70)
    print(f"User ID: {user_id}")
    print(f"Status: Resurrected with unified points and profile")
    print()

if __name__ == '__main__':
    resurrect_default_user()
