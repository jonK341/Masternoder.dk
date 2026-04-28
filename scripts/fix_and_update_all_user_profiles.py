#!/usr/bin/env python3
"""
Fix and Update All User Profiles
- Fix missing profile data
- Add personalized profile keys for new users
- Update stats and points in profiles
- Ensure all profiles have complete data
"""
import os
import sys
import json
import uuid
from datetime import datetime
from sqlalchemy import text

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

def fix_and_update_profiles():
    """Fix and update all user profiles"""
    print("=" * 70)
    print("FIX AND UPDATE ALL USER PROFILES")
    print("=" * 70)
    
    try:
        from src.app import create_app
        from src.db.models import db
        
        app = create_app()
        with app.app_context():
            updated_count = 0
            created_count = 0
            error_count = 0
            
            # Get all users from user_profiles table
            try:
                users = db.session.execute(
                    text("SELECT DISTINCT user_id FROM user_profiles")
                ).fetchall()
                user_ids = [row[0] for row in users if row[0]]
                print(f"\nFound {len(user_ids)} existing users")
            except Exception as e:
                print(f"Error getting users from user_profiles: {e}")
                user_ids = []
            
            # Also check player_levels for users not in user_profiles
            try:
                level_users = db.session.execute(
                    text("SELECT DISTINCT user_id FROM player_levels WHERE user_id IS NOT NULL")
                ).fetchall()
                level_user_ids = [row[0] for row in level_users if row[0]]
                all_user_ids = list(set(user_ids + level_user_ids))
                print(f"Found {len(all_user_ids)} total users (including from player_levels)")
            except Exception as e:
                print(f"Error getting users from player_levels: {e}")
                all_user_ids = user_ids
            
            # Process each user
            for user_id in all_user_ids:
                try:
                    # Check if profile exists
                    profile_exists = db.session.execute(
                        text("SELECT id FROM user_profiles WHERE user_id = :user_id LIMIT 1"),
                        {"user_id": user_id}
                    ).fetchone()
                    
                    if profile_exists:
                        # Update existing profile
                        updated = update_user_profile(db, user_id)
                        if updated:
                            updated_count += 1
                            print(f"  [UPDATED] {user_id}")
                        else:
                            print(f"  [SKIP] {user_id} (no changes needed)")
                    else:
                        # Create new profile with personalized key
                        created = create_user_profile(db, user_id)
                        if created:
                            created_count += 1
                            print(f"  [CREATED] {user_id}")
                        else:
                            error_count += 1
                            print(f"  [ERROR] {user_id} (creation failed)")
                            
                except Exception as e:
                    error_count += 1
                    print(f"  [ERROR] {user_id}: {e}")
            
            print("\n" + "=" * 70)
            print("SUMMARY")
            print("=" * 70)
            print(f"Updated profiles: {updated_count}")
            print(f"Created profiles: {created_count}")
            print(f"Errors: {error_count}")
            print(f"Total processed: {len(all_user_ids)}")
            
            return {
                'success': True,
                'updated': updated_count,
                'created': created_count,
                'errors': error_count,
                'total': len(all_user_ids)
            }
            
    except Exception as e:
        print(f"\nFATAL ERROR: {e}")
        import traceback
        traceback.print_exc()
        return {'success': False, 'error': str(e)}

def update_user_profile(db, user_id):
    """Update existing user profile with missing data"""
    try:
        # Get current profile
        profile = db.session.execute(
            text("""
                SELECT id, user_id, username, preferences, agent_skillset_id, 
                       onboarding_complete, created_at, updated_at
                FROM user_profiles 
                WHERE user_id = :user_id LIMIT 1
            """),
            {"user_id": user_id}
        ).fetchone()
        
        if not profile:
            return False
        
        # Parse preferences
        preferences = {}
        try:
            prefs_str = profile[3] if profile[3] else '{}'
            preferences = json.loads(prefs_str) if isinstance(prefs_str, str) else prefs_str
        except:
            preferences = {}
        
        # Ensure personalized profile key exists
        if 'profile_key' not in preferences or not preferences.get('profile_key'):
            preferences['profile_key'] = str(uuid.uuid4())[:16]
            updated = True
        else:
            updated = False
        
        # Ensure display_name exists
        if 'display_name' not in preferences or not preferences.get('display_name'):
            preferences['display_name'] = profile[2] or user_id  # Use username or user_id
            updated = True
        
        # Update agent_skillset_id if missing
        skillset_id = profile[4] if len(profile) > 4 else None
        if not skillset_id:
            skillset_id = 'balanced'
            update_skillset = True
        else:
            update_skillset = False
        
        # Update if needed
        if updated or update_skillset:
            if update_skillset:
                db.session.execute(
                    text("""
                        UPDATE user_profiles 
                        SET preferences = :prefs, 
                            agent_skillset_id = :skillset,
                            updated_at = :updated_at
                        WHERE user_id = :user_id
                    """),
                    {
                        "prefs": json.dumps(preferences),
                        "skillset": skillset_id,
                        "updated_at": datetime.now().isoformat(),
                        "user_id": user_id
                    }
                )
            else:
                db.session.execute(
                    text("""
                        UPDATE user_profiles 
                        SET preferences = :prefs,
                            updated_at = :updated_at
                        WHERE user_id = :user_id
                    """),
                    {
                        "prefs": json.dumps(preferences),
                        "updated_at": datetime.now().isoformat(),
                        "user_id": user_id
                    }
                )
            db.session.commit()
            return True
        
        return False
        
    except Exception as e:
        print(f"  Error updating profile for {user_id}: {e}")
        db.session.rollback()
        return False

def create_user_profile(db, user_id):
    """Create new user profile with personalized key"""
    try:
        # Generate personalized profile key
        profile_key = str(uuid.uuid4())[:16]
        
        # Get username from user_id or generate one
        username = user_id if not user_id.startswith('default_') else f"user_{uuid.uuid4().hex[:8]}"
        
        # Create preferences with personalized key
        preferences = {
            'profile_key': profile_key,
            'display_name': username,
            'created_at': datetime.now().isoformat()
        }
        
        # Insert new profile
        db.session.execute(
            text("""
                INSERT OR IGNORE INTO user_profiles 
                (id, user_id, username, preferences, agent_skillset_id, 
                 onboarding_complete, created_at, updated_at)
                VALUES 
                (:id, :user_id, :username, :preferences, :skillset,
                 :onboarding_complete, :created_at, :updated_at)
            """),
            {
                "id": str(uuid.uuid4()),
                "user_id": user_id,
                "username": username,
                "preferences": json.dumps(preferences),
                "skillset": "balanced",
                "onboarding_complete": True,
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat()
            }
        )
        db.session.commit()
        
        # Initialize points for new user
        try:
            from backend.services.unified_points_database import unified_points_db
            if unified_points_db:
                unified_points_db.add_points(user_id, 'xp_points', 100, source='profile_creation')
        except:
            pass
        
        return True
        
    except Exception as e:
        print(f"  Error creating profile for {user_id}: {e}")
        db.session.rollback()
        return False

if __name__ == '__main__':
    result = fix_and_update_profiles()
    if result.get('success'):
        print("\n✓ Profile update completed successfully")
        sys.exit(0)
    else:
        print(f"\n✗ Profile update failed: {result.get('error')}")
        sys.exit(1)
