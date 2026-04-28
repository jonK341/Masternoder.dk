#!/usr/bin/env python3
"""
Run Agents Continuously
Keep agents running with realistic behavior
"""
import os
import sys
import time
import requests
from datetime import datetime
from threading import Thread

BASE_URL = "https://masternoder.dk"
API_BASE = f"{BASE_URL}/vidgenerator/api"

class ContinuousAgentRunner:
    """Runs agents continuously with realistic behavior"""
    
    def __init__(self, num_agents=10):
        self.num_agents = num_agents
        self.agents = [f"agent_{i:03d}" for i in range(1, num_agents + 1)]
        self.running = True
        self.stats = {
            'total_sessions': 0,
            'total_actions': 0,
            'total_xp': 0,
            'start_time': datetime.now()
        }
    
    def run_agent(self, agent_id):
        """Run a single agent"""
        while self.running:
            try:
                # Check if should be active
                r = requests.get(f"{API_BASE}/agents/behavior/should-be-active?agent_id={agent_id}", timeout=5)
                if r.status_code == 200:
                    data = r.json()
                    if data.get('should_be_active'):
                        # Simulate session with execution
                        r2 = requests.post(f"{API_BASE}/agents/behavior/simulate-session",
                                         json={'agent_id': agent_id, 'execute': True}, timeout=30)
                        if r2.status_code == 200:
                            result = r2.json()
                            if result.get('success'):
                                plan = result.get('session_plan', {})
                                self.stats['total_sessions'] += 1
                                self.stats['total_actions'] += len(plan.get('actions', []))
                                self.stats['total_xp'] += plan.get('total_xp', 0)
                                print(f"[{datetime.now().strftime('%H:%M:%S')}] {agent_id}: {len(plan.get('actions', []))} actions, {plan.get('total_xp', 0)} XP")
                
                # Wait before next check (5-15 minutes)
                time.sleep(300 + (hash(agent_id) % 600))
                
            except Exception as e:
                print(f"Error in {agent_id}: {e}")
                time.sleep(60)
    
    def start(self):
        """Start all agents"""
        print("=" * 70)
        print("STARTING CONTINUOUS AGENT RUNNER")
        print("=" * 70)
        print(f"Agents: {self.num_agents}")
        print(f"Started: {self.stats['start_time'].strftime('%Y-%m-%d %H:%M:%S')}")
        print()
        
        # Start agent threads
        threads = []
        for agent_id in self.agents:
            thread = Thread(target=self.run_agent, args=(agent_id,), daemon=True)
            thread.start()
            threads.append(thread)
        
        print(f"Started {len(threads)} agent threads")
        print("Agents running... Press Ctrl+C to stop")
        print()
        
        # Report stats periodically
        try:
            while self.running:
                time.sleep(300)  # Every 5 minutes
                elapsed = (datetime.now() - self.stats['start_time']).total_seconds() / 60
                print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Stats after {elapsed:.1f} minutes:")
                print(f"  Sessions: {self.stats['total_sessions']}")
                print(f"  Actions: {self.stats['total_actions']}")
                print(f"  Total XP: {self.stats['total_xp']}")
                print()
        except KeyboardInterrupt:
            print("\nStopping agents...")
            self.running = False

if __name__ == '__main__':
    runner = ContinuousAgentRunner(num_agents=20)
    runner.start()
