#!/usr/bin/env python3
"""
Start Agent Behavior Engine
Continuously run agents with realistic player behavior
"""
import os
import sys
import time
import threading
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

class AgentBehaviorEngine:
    """Engine to continuously run agent behaviors"""
    
    def __init__(self):
        self.running = False
        self.agents = []
        self.threads = []
    
    def start(self, num_agents=10):
        """Start the behavior engine"""
        print("=" * 70)
        print("STARTING AGENT BEHAVIOR ENGINE")
        print("=" * 70)
        print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Agents: {num_agents}")
        print()
        
        try:
            from backend.services.agent_player_behavior import agent_player_behavior
            
            # Create agents
            self.agents = [f"agent_{i:03d}" for i in range(1, num_agents + 1)]
            self.running = True
            
            # Start agent threads
            for agent_id in self.agents:
                thread = threading.Thread(
                    target=self._agent_loop,
                    args=(agent_id, agent_player_behavior),
                    daemon=True
                )
                thread.start()
                self.threads.append(thread)
            
            print(f"Started {len(self.threads)} agent threads")
            print("Engine running... Press Ctrl+C to stop")
            print()
            
            # Keep main thread alive
            try:
                while self.running:
                    time.sleep(60)  # Report every minute
                    active_count = sum(1 for t in self.threads if t.is_alive())
                    print(f"[{datetime.now().strftime('%H:%M:%S')}] {active_count} agents active")
            except KeyboardInterrupt:
                print("\nStopping engine...")
                self.running = False
                
        except Exception as e:
            print(f"Error starting engine: {e}")
            import traceback
            traceback.print_exc()
    
    def _agent_loop(self, agent_id, behavior_system):
        """Main loop for a single agent"""
        behavior_type = behavior_system.get_behavior_type(agent_id)
        
        while self.running:
            try:
                # Check if agent should be active
                if behavior_system.should_be_active_now(behavior_type):
                    # Generate and execute session
                    session_plan = behavior_system.generate_session_plan(agent_id, behavior_type)
                    
                    # Execute actions (simplified - just log for now)
                    for action in session_plan['actions']:
                        if not self.running:
                            break
                        
                        result = behavior_system.execute_action(agent_id, action)
                        # Here you would save to database or send to API
                        
                        # Wait between actions
                        time.sleep(random.uniform(1, 5))
                
                # Wait before next check (5-15 minutes)
                time.sleep(random.uniform(300, 900))
                
            except Exception as e:
                print(f"Error in agent {agent_id}: {e}")
                time.sleep(60)  # Wait before retry

import random

if __name__ == '__main__':
    engine = AgentBehaviorEngine()
    engine.start(num_agents=20)
