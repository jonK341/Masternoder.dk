#!/usr/bin/env python3
"""
Production Agent Runner
Runs agents directly in production environment with real database
"""
import os
import sys
import time
import signal
from datetime import datetime
from threading import Thread, Lock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

class ProductionAgentRunner:
    """Production-ready agent runner"""
    
    def __init__(self, num_agents=20):
        self.num_agents = num_agents
        self.running = True
        self.lock = Lock()
        self.stats = {
            'start_time': datetime.now(),
            'total_sessions': 0,
            'total_actions': 0,
            'total_xp': 0,
            'errors': 0
        }
        
        # Setup signal handlers
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        print("\n\nReceived shutdown signal, stopping agents...")
        self.running = False
    
    def run_agent_loop(self, agent_id):
        """Main loop for a single agent"""
        try:
            from src.app import create_app
            from src.db.models import db
            from backend.services.agent_behavior_executor import agent_behavior_executor
            from backend.services.agent_player_behavior import agent_player_behavior
            
            app = create_app()
            
            while self.running:
                try:
                    with app.app_context():
                        behavior_type = agent_player_behavior.get_behavior_type(agent_id)
                        
                        # Check if agent should be active
                        if agent_player_behavior.should_be_active_now(behavior_type):
                            # Execute session and save to database
                            result = agent_behavior_executor.execute_and_save_session(agent_id, db)
                            
                            if result.get('success'):
                                with self.lock:
                                    self.stats['total_sessions'] += 1
                                    self.stats['total_actions'] += result['actions_executed']
                                    self.stats['total_xp'] += result['total_xp']
                                
                                print(f"[{datetime.now().strftime('%H:%M:%S')}] {agent_id}: "
                                      f"{result['actions_executed']} actions, {result['total_xp']} XP")
                            else:
                                with self.lock:
                                    self.stats['errors'] += 1
                                print(f"[{datetime.now().strftime('%H:%M:%S')}] {agent_id}: Error - {result.get('error')}")
                        
                        # Wait before next check (5-15 minutes based on behavior type)
                        wait_time = {
                            'casual': 600,      # 10 minutes
                            'active': 300,      # 5 minutes
                            'hardcore': 180,    # 3 minutes
                            'social': 600       # 10 minutes
                        }.get(behavior_type, 600)
                        
                        # Add some randomness
                        wait_time += (hash(agent_id) % 300)
                        
                        time.sleep(wait_time)
                        
                except Exception as e:
                    with self.lock:
                        self.stats['errors'] += 1
                    print(f"Error in {agent_id}: {e}")
                    time.sleep(60)  # Wait before retry
                    
        except Exception as e:
            print(f"Fatal error in agent {agent_id}: {e}")
    
    def start(self):
        """Start all agents in production"""
        print("=" * 70)
        print("PRODUCTION AGENT RUNNER")
        print("=" * 70)
        print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Agents: {self.num_agents}")
        print(f"Environment: PRODUCTION")
        print()
        print("⚠️  WARNING: Running directly in production!")
        print("   Agents will create real database entries.")
        print("   Press Ctrl+C to stop.")
        print()
        
        # Create agent IDs
        agent_ids = [f"agent_{i:03d}" for i in range(1, self.num_agents + 1)]
        
        # Start agent threads
        threads = []
        for agent_id in agent_ids:
            thread = Thread(target=self.run_agent_loop, args=(agent_id,), daemon=True)
            thread.start()
            threads.append(thread)
        
        print(f"Started {len(threads)} agent threads")
        print("Agents running in production...")
        print()
        
        # Report stats periodically
        try:
            while self.running:
                time.sleep(300)  # Every 5 minutes
                elapsed = (datetime.now() - self.stats['start_time']).total_seconds() / 60
                
                with self.lock:
                    print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Stats (running {elapsed:.1f} min):")
                    print(f"  Sessions: {self.stats['total_sessions']}")
                    print(f"  Actions: {self.stats['total_actions']}")
                    print(f"  Total XP: {self.stats['total_xp']}")
                    print(f"  Errors: {self.stats['errors']}")
                    print()
                    
        except KeyboardInterrupt:
            print("\nStopping agents...")
            self.running = False
        
        # Wait for threads to finish
        print("Waiting for agents to finish...")
        for thread in threads:
            thread.join(timeout=10)
        
        print()
        print("=" * 70)
        print("FINAL STATS")
        print("=" * 70)
        elapsed = (datetime.now() - self.stats['start_time']).total_seconds() / 60
        print(f"Runtime: {elapsed:.1f} minutes")
        print(f"Total Sessions: {self.stats['total_sessions']}")
        print(f"Total Actions: {self.stats['total_actions']}")
        print(f"Total XP: {self.stats['total_xp']}")
        print(f"Errors: {self.stats['errors']}")
        print()
        print("Agents stopped.")

if __name__ == '__main__':
    runner = ProductionAgentRunner(num_agents=20)
    runner.start()
