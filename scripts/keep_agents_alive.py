#!/usr/bin/env python3
"""
Keep Agents Alive
Continuously run agents with real player behavior
"""
import os
import sys
import time
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def run_agents():
    """Run agents continuously"""
    print("=" * 70)
    print("KEEPING AGENTS ALIVE")
    print("=" * 70)
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    try:
        from src.app import create_app
        from src.db.models import db
        from backend.services.agent_behavior_executor import agent_behavior_executor
        from backend.services.agent_player_behavior import agent_player_behavior
        
        app = create_app()
        
        agent_ids = [f"agent_{i:03d}" for i in range(1, 21)]
        iteration = 0
        
        while True:
            iteration += 1
            print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Iteration {iteration}")
            print("-" * 70)
            
            with app.app_context():
                active_count = 0
                total_actions = 0
                total_xp = 0
                
                for agent_id in agent_ids:
                    behavior_type = agent_player_behavior.get_behavior_type(agent_id)
                    
                    if agent_player_behavior.should_be_active_now(behavior_type):
                        try:
                            result = agent_behavior_executor.execute_and_save_session(agent_id, db)
                            if result.get('success'):
                                active_count += 1
                                total_actions += result['actions_executed']
                                total_xp += result['total_xp']
                                print(f"  ✓ {agent_id}: {result['actions_executed']} actions, {result['total_xp']} XP")
                        except Exception as e:
                            print(f"  ✗ {agent_id}: {e}")
                
                print(f"\nSummary: {active_count} active, {total_actions} actions, {total_xp} XP")
            
            # Wait 10 minutes before next iteration
            print(f"\nWaiting 10 minutes...")
            time.sleep(600)
            
    except KeyboardInterrupt:
        print("\n\nStopped by user")
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    run_agents()
