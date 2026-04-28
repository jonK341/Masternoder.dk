#!/usr/bin/env python3
"""
Generate test users with points in different subsystems
Tests leaderboard aggregation and data loading
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flask import Flask
from src.app import create_app
from src.db.models import db, UserProfile
import json
import random
import uuid

# Point distributions per subsystem
SUBSYSTEM_POINTS = {
    'xp': {'min': 100, 'max': 10000, 'field': 'xp_total'},
    'battle': {'min': 50, 'max': 5000, 'field': 'battle_points'},
    'activity': {'min': 20, 'max': 3000, 'field': 'activity_points'},
    'chat': {'min': 10, 'max': 2000, 'field': 'chat_points'},
    'theme': {'min': 30, 'max': 2500, 'field': 'theme_points_total'},
    'trophy': {'min': 5, 'max': 1500, 'field': 'trophy_points'},
    'generation': {'min': 0, 'max': 4000, 'field': 'generations_total'},
    'reward': {'min': 15, 'max': 2000, 'field': 'reward_points'},
}

def generate_test_users(count=50):
    """Generate test users with points in different subsystems"""
    app = create_app()
    
    with app.app_context():
        created = 0
        skipped = 0
        
        print(f"Generating {count} test users with subsystem points...")
        print("="*70)
        
        for i in range(count):
            user_id = f'test_subsystem_user_{i}'
            username = f'TestSub{i}'
            
            # Check if user exists
            existing = UserProfile.query.filter_by(user_id=user_id).first()
            if existing:
                print(f"[{i+1}/{count}] Skipping {user_id} (already exists)")
                skipped += 1
                continue
            
            try:
                # Create user profile
                user = UserProfile(
                    id=str(uuid.uuid4()),
                    user_id=user_id,
                    username=username,
                    preferences=json.dumps({
                        'test_user': True,
                        'subsystem_test': True,
                        'created_for': 'subsystem_leaderboard_testing'
                    })
                )
                db.session.add(user)
                
                # Add points via unified_points_database
                try:
                    from backend.services.unified_points_database import unified_points_db
                    
                    # Randomly assign points to 2-4 subsystems per user
                    subsystems = random.sample(list(SUBSYSTEM_POINTS.keys()), random.randint(2, 4))
                    
                    user_points = {}
                    for subsystem in subsystems:
                        config = SUBSYSTEM_POINTS[subsystem]
                        points_value = random.randint(config['min'], config['max'])
                        field_name = config['field']
                        user_points[field_name] = points_value
                    
                    # Save points
                    if unified_points_db:
                        unified_points_db.save_user_points(user_id, user_points)
                    
                    print(f"[{i+1}/{count}] Created {username} with points in: {', '.join(subsystems)}")
                    created += 1
                except Exception as e:
                    print(f"[{i+1}/{count}] Error adding points for {user_id}: {e}")
                    # Still commit the user
                    created += 1
                
                # Commit every 10 users
                if (i + 1) % 10 == 0:
                    db.session.commit()
                    print(f"Committed {i+1} users...")
                    
            except Exception as e:
                print(f"[{i+1}/{count}] Error creating user {user_id}: {e}")
                import traceback
                traceback.print_exc()
                db.session.rollback()
                continue
        
        # Final commit
        db.session.commit()
        
        print("="*70)
        print(f"✅ Created {created} test users")
        print(f"⏭️  Skipped {skipped} existing users")
        print(f"📊 Total: {created + skipped} users processed")
        print("="*70)
        
        return created

if __name__ == '__main__':
    count = int(sys.argv[1]) if len(sys.argv) > 1 else 50
    generate_test_users(count)
