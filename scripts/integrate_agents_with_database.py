#!/usr/bin/env python3
"""
Integrate Agents with Database
Make agents execute behaviors and save to database
"""
import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def integrate_agents():
    """Integrate agent behaviors with database"""
    print("=" * 70)
    print("INTEGRATING AGENTS WITH DATABASE")
    print("=" * 70)
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    try:
        from src.app import create_app
        from src.db.models import db
        from backend.services.agent_behavior_executor import agent_behavior_executor
        
        app = create_app()
        with app.app_context():
            # Create test agents as users if they don't exist
            agent_ids = [f"agent_{i:03d}" for i in range(1, 11)]
            
            print(f"Creating/updating {len(agent_ids)} agents in database...")
            print()
            
            for agent_id in agent_ids:
                try:
                    # Check if user profile exists
                    result = db.session.execute("""
                        SELECT COUNT(*) FROM user_profiles WHERE user_id = :user_id
                    """, {'user_id': agent_id})
                    exists = result.scalar() > 0
                    
                    if not exists:
                        # Create user profile
                        db.session.execute("""
                            INSERT INTO user_profiles
                            (user_id, username, preferences, created_at, updated_at)
                            VALUES (:user_id, :username, :prefs, :created, :updated)
                        """, {
                            'user_id': agent_id,
                            'username': agent_id.replace('_', ' ').title(),
                            'prefs': '{"type": "agent"}',
                            'created': datetime.now(),
                            'updated': datetime.now()
                        })
                        print(f"  ✓ Created profile for {agent_id}")
                    else:
                        print(f"  - Profile exists for {agent_id}")
                    
                    # Execute agent behavior session
                    result = agent_behavior_executor.execute_and_save_session(agent_id, db)
                    if result.get('success'):
                        print(f"  ✓ {agent_id}: {result['actions_executed']} actions, {result['total_xp']} XP")
                    else:
                        print(f"  ✗ {agent_id}: {result.get('error', 'Unknown error')}")
                    
                except Exception as e:
                    print(f"  ✗ {agent_id}: {e}")
            
            db.session.commit()
            
            print()
            print("=" * 70)
            print("INTEGRATION COMPLETE")
            print("=" * 70)
            print()
            print("Agents are now integrated with database!")
            print("They will behave like real players and save all actions.")
            print()
            
            return True
            
    except Exception as e:
        print(f"\n✗ Integration failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    from sqlalchemy import text
    import json
    success = integrate_agents()
    sys.exit(0 if success else 1)
