#!/usr/bin/env python3
"""
Run Agent Behavior Simulation
Execute realistic agent player behavior
"""
import os
import sys
import time
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def simulate_agents():
    """Simulate multiple agents with realistic behavior"""
    print("=" * 70)
    print("AGENT BEHAVIOR SIMULATION")
    print("=" * 70)
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    try:
        from backend.services.agent_player_behavior import agent_player_behavior
        
        # Create multiple agents with different behaviors
        agent_ids = [f"agent_{i:03d}" for i in range(1, 21)]  # 20 agents
        
        print(f"Simulating {len(agent_ids)} agents...")
        print()
        
        total_xp = 0
        total_points = 0
        total_actions = 0
        
        for agent_id in agent_ids:
            behavior_type = agent_player_behavior.get_behavior_type(agent_id)
            should_activate = agent_player_behavior.should_be_active_now(behavior_type)
            
            if should_activate:
                # Generate session plan
                session_plan = agent_player_behavior.generate_session_plan(agent_id, behavior_type)
                
                print(f"  {agent_id} ({behavior_type}): {len(session_plan['actions'])} actions, "
                      f"{session_plan['total_xp']} XP, {session_plan['total_points']} points")
                
                total_xp += session_plan['total_xp']
                total_points += session_plan['total_points']
                total_actions += len(session_plan['actions'])
            else:
                print(f"  {agent_id} ({behavior_type}): Inactive (outside active hours)")
        
        print()
        print("=" * 70)
        print("SIMULATION SUMMARY")
        print("=" * 70)
        print(f"Active Agents: {sum(1 for aid in agent_ids if agent_player_behavior.should_be_active_now(agent_player_behavior.get_behavior_type(aid)))}")
        print(f"Total Actions: {total_actions}")
        print(f"Total XP: {total_xp}")
        print(f"Total Points: {total_points}")
        print()
        
        # Simulate daily activity for a few agents
        print("Simulating daily activity for sample agents...")
        print()
        
        for agent_id in agent_ids[:5]:  # First 5 agents
            daily_activity = agent_player_behavior.simulate_daily_activity(agent_id)
            print(f"  {agent_id}: {daily_activity['total_sessions']} sessions, "
                  f"{daily_activity['total_actions']} actions, "
                  f"{daily_activity['total_xp']} XP")
        
        print()
        print("=" * 70)
        print("SIMULATION COMPLETE")
        print("=" * 70)
        
        return True
        
    except Exception as e:
        print(f"\n✗ Simulation failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    success = simulate_agents()
    sys.exit(0 if success else 1)
