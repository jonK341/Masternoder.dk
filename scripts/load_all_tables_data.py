#!/usr/bin/env python3
"""
Load All Tables Data
Comprehensive data loading functions for all newly created tables
"""
import os
import sys
import json
import random
from datetime import datetime, timedelta
from sqlalchemy import text

# Add project root to path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

def load_user_profiles(db, num_users=50):
    """Load user profiles data"""
    print(f"Loading {num_users} user profiles...")
    
    users = []
    for i in range(1, num_users + 1):
        user_id = f"user_{i:03d}" if i < 1000 else f"user_{i}"
        username = f"Player{i}"
        
        preferences = {
            'display_name': username,
            'theme': random.choice(['dark', 'light', 'auto']),
            'notifications': random.choice([True, False])
        }
        
        scraped_info = {
            'browser': random.choice(['Chrome', 'Firefox', 'Safari', 'Edge']),
            'device': random.choice(['desktop', 'mobile', 'tablet']),
            'location': random.choice(['US', 'UK', 'DK', 'DE', 'FR'])
        }
        
        db.session.execute(text("""
            INSERT OR IGNORE INTO user_profiles 
            (user_id, username, preferences, scraped_info, agent_skillset_id, 
             onboarding_complete, created_at, updated_at)
            VALUES (:user_id, :username, :preferences, :scraped_info, :skillset, 
                    :onboarding, :created, :updated)
        """, {
            'user_id': user_id,
            'username': username,
            'preferences': json.dumps(preferences),
            'scraped_info': json.dumps(scraped_info),
            'skillset': random.choice(['balanced', 'creator', 'battle', 'social', 'analytics']),
            'onboarding': random.choice([True, False]),
            'created': datetime.now() - timedelta(days=random.randint(0, 180)),
            'updated': datetime.now()
        }))
        users.append(user_id)
    
    db.session.commit()
    print(f"  ✓ Loaded {len(users)} user profiles")
    return users

def load_onboarding_progress(db, users):
    """Load onboarding progress data"""
    print(f"Loading onboarding progress for {len(users)} users...")
    
    steps = ['welcome', 'profile_setup', 'skill_selection', 'first_action', 'tutorial', 'completed']
    
    loaded = 0
    for user_id in users[:30]:  # Load for first 30 users
        if random.random() > 0.3:  # 70% have started onboarding
            current_step = random.choice(steps)
            completed_steps = steps[:steps.index(current_step)] if current_step in steps else []
            
            progress = len(completed_steps) * 100 // len(steps)
            
            db.session.execute(text("""
                INSERT OR IGNORE INTO onboarding_progress
                (user_id, onboarding_started, current_step, completed_steps, 
                 progress_percentage, skill_path, created_at, updated_at)
                VALUES (:user_id, :started, :step, :completed, :progress, :path, :created, :updated)
            """), {
                'user_id': user_id,
                'started': datetime.now() - timedelta(days=random.randint(0, 30)),
                'step': current_step,
                'completed': json.dumps(completed_steps),
                'progress': progress,
                'path': random.choice(['balanced', 'creator', 'battle']),
                'created': datetime.now() - timedelta(days=random.randint(0, 30)),
                'updated': datetime.now()
            })
            loaded += 1
    
    db.session.commit()
    print(f"  ✓ Loaded onboarding progress for {loaded} users")
    return loaded

def load_player_levels(db, users):
    """Load player levels data"""
    print(f"Loading player levels for {len(users)} users...")
    
    loaded = 0
    for user_id in users:
        level = random.randint(1, 50)
        total_xp = random.randint(100, 50000)
        current_level_xp = total_xp % (level * 100)
        xp_to_next = (level * 100) - current_level_xp
        
        db.session.execute(text("""
            INSERT OR IGNORE INTO player_levels
            (user_id, level, total_xp, current_level_xp, xp_to_next_level, created_at, updated_at)
            VALUES (:user_id, :level, :total_xp, :current_xp, :next_xp, :created, :updated)
        """), {
            'user_id': user_id,
            'level': level,
            'total_xp': total_xp,
            'current_xp': current_level_xp,
            'next_xp': xp_to_next,
            'created': datetime.now() - timedelta(days=random.randint(0, 180)),
            'updated': datetime.now()
        })
        loaded += 1
    
    db.session.commit()
    print(f"  ✓ Loaded player levels for {loaded} users")
    return loaded

def load_xp_history(db, users):
    """Load XP history data"""
    print(f"Loading XP history...")
    
    sources = ['login', 'battle', 'generation', 'social', 'achievement', 'daily_quest']
    loaded = 0
    
    for user_id in users[:40]:  # Load for first 40 users
        # Create 5-20 XP history entries per user
        num_entries = random.randint(5, 20)
        for _ in range(num_entries):
            xp_amount = random.randint(10, 500)
            source = random.choice(sources)
            
            db.session.execute(text("""
                INSERT INTO xp_history
                (user_id, xp_amount, xp_source, source_details, created_at)
                VALUES (:user_id, :amount, :source, :details, :created)
            """), {
                'user_id': user_id,
                'amount': xp_amount,
                'source': source,
                'details': json.dumps({'action': f"{source}_action_{random.randint(1, 10)}"}),
                'created': datetime.now() - timedelta(days=random.randint(0, 90))
            })
            loaded += 1
    
    db.session.commit()
    print(f"  ✓ Loaded {loaded} XP history records")
    return loaded

def load_daily_activities(db, users):
    """Load daily activities data"""
    print(f"Loading daily activities...")
    
    loaded = 0
    for user_id in users[:30]:  # Load for first 30 users
        # Create activities for last 30 days
        for day_offset in range(30):
            activity_date = datetime.now().date() - timedelta(days=day_offset)
            
            if random.random() > 0.3:  # 70% chance of activity on that day
                login_xp = random.randint(10, 50) if random.random() > 0.2 else 0
                activity_xp = random.randint(20, 200)
                total_xp = login_xp + activity_xp
                activities_completed = random.randint(1, 10)
                
                db.session.execute(text("""
                    INSERT OR IGNORE INTO daily_activities
                    (user_id, activity_date, login_xp, activity_xp, total_xp, activities_completed, created_at)
                    VALUES (:user_id, :date, :login_xp, :activity_xp, :total_xp, :completed, :created)
                """), {
                    'user_id': user_id,
                    'date': activity_date,
                    'login_xp': login_xp,
                    'activity_xp': activity_xp,
                    'total_xp': total_xp,
                    'completed': activities_completed,
                    'created': datetime.combine(activity_date, datetime.min.time())
                })
                loaded += 1
    
    db.session.commit()
    print(f"  ✓ Loaded {loaded} daily activity records")
    return loaded

def load_user_agent_skills(db, users):
    """Load user agent skills data"""
    print(f"Loading user agent skills...")
    
    skill_names = ['battle_strategy', 'content_creation', 'social_engagement', 
                   'analytics', 'automation', 'optimization', 'security', 'judge']
    
    loaded = 0
    for user_id in users[:25]:  # Load for first 25 users
        num_skills = random.randint(2, 6)
        selected_skills = random.sample(skill_names, num_skills)
        
        for skill_name in selected_skills:
            db.session.execute(text("""
                INSERT OR IGNORE INTO user_agent_skills
                (user_id, skill_name, skill_level, experience, assigned_at, updated_at)
                VALUES (:user_id, :skill, :level, :exp, :assigned, :updated)
            """), {
                'user_id': user_id,
                'skill': skill_name,
                'level': random.randint(1, 10),
                'exp': random.randint(100, 5000),
                'assigned': datetime.now() - timedelta(days=random.randint(0, 60)),
                'updated': datetime.now()
            })
            loaded += 1
    
    db.session.commit()
    print(f"  ✓ Loaded {loaded} user agent skills")
    return loaded

def load_user_scraped_info(db, users):
    """Load user scraped info data"""
    print(f"Loading user scraped info...")
    
    info_types = ['browser', 'device', 'location', 'behavior']
    
    loaded = 0
    for user_id in users[:20]:  # Load for first 20 users
        for info_type in info_types:
            if random.random() > 0.3:  # 70% chance
                info_data = {
                    'browser': {'name': 'Chrome', 'version': '120.0'},
                    'device': {'type': 'desktop', 'os': 'Windows'},
                    'location': {'country': 'US', 'timezone': 'America/New_York'},
                    'behavior': {'sessions': random.randint(1, 100), 'avg_duration': random.randint(100, 3600)}
                }.get(info_type, {})
                
                db.session.execute(text("""
                    INSERT INTO user_scraped_info
                    (user_id, info_type, info_data, scraped_at)
                    VALUES (:user_id, :type, :data, :scraped)
                """), {
                    'user_id': user_id,
                    'type': info_type,
                    'data': json.dumps(info_data),
                    'scraped': datetime.now() - timedelta(days=random.randint(0, 30))
                })
                loaded += 1
    
    db.session.commit()
    print(f"  ✓ Loaded {loaded} scraped info records")
    return loaded

def main():
    """Main function to load all table data"""
    print("=" * 70)
    print("LOAD ALL TABLES DATA")
    print("=" * 70)
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    try:
        from src.app import create_app
        from src.db.models import db
        
        app = create_app()
        with app.app_context():
            print("Loading data into all tables...")
            print()
            
            # Load user profiles first (other tables depend on it)
            users = load_user_profiles(db, num_users=50)
            print()
            
            # Load dependent tables
            load_onboarding_progress(db, users)
            print()
            
            load_player_levels(db, users)
            print()
            
            load_xp_history(db, users)
            print()
            
            load_daily_activities(db, users)
            print()
            
            load_user_agent_skills(db, users)
            print()
            
            load_user_scraped_info(db, users)
            print()
            
            # Summary
            print("=" * 70)
            print("DATA LOADING COMPLETE")
            print("=" * 70)
            print()
            print("✓ All tables loaded with data!")
            print()
            print("Tables populated:")
            print("  - user_profiles: 50 users")
            print("  - onboarding_progress: ~30 users")
            print("  - player_levels: 50 users")
            print("  - xp_history: ~40 users with multiple entries")
            print("  - daily_activities: ~30 users with 30 days of data")
            print("  - user_agent_skills: ~25 users with multiple skills")
            print("  - user_scraped_info: ~20 users with multiple info types")
            print()
            
    except Exception as e:
        print(f"\n✗ Data loading failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == '__main__':
    main()
