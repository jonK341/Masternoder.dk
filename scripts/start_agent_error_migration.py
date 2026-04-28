#!/usr/bin/env python3
"""
Start Agent Error Migration
Automates error handler migration with agents
"""
import os
import sys
import requests
import json
import codecs
from datetime import datetime

# Fix Windows encoding
if sys.platform == 'win32':
    if sys.stdout.encoding != 'utf-8':
        sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Configuration
BASE_URL = "https://masternoder.dk"
API_BASE = f"{BASE_URL}/vidgenerator/api"

def assign_migration_tasks_to_agents(max_tasks=10):
    """Assign migration tasks to agents automatically"""
    print("=" * 80)
    print("AGENT ERROR MIGRATION - AUTOMATED ASSIGNMENT")
    print("=" * 80)
    print()
    
    try:
        # Generate tasks
        url = f"{API_BASE}/errors/tasks/generate"
        response = requests.post(url, json={
            'priority': 'all',
            'max_tasks': max_tasks
        }, timeout=10, verify=False)
        
        if response.status_code != 200:
            print(f"[FAIL] Failed to generate tasks: {response.status_code}")
            return []
        
        data = response.json()
        tasks = data.get('tasks', [])
        
        if not tasks:
            print("[WARN] No tasks generated")
            return []
        
        print(f"[OK] Generated {len(tasks)} migration tasks")
        print()
        
        # Assign to agents
        assigned_count = 0
        failed_count = 0
        
        # Prioritize high priority tasks
        high_priority = [t for t in tasks if t.get('priority') == 'high']
        medium_priority = [t for t in tasks if t.get('priority') == 'medium']
        low_priority = [t for t in tasks if t.get('priority') == 'low']
        
        prioritized_tasks = high_priority + medium_priority + low_priority
        
        for task in prioritized_tasks[:max_tasks]:
            task_id = task.get('task_id')
            file_name = task.get('file_name', 'Unknown')
            handlers_count = task.get('handlers_count', 0)
            
            print(f"[ASSIGN] Assigning: {file_name} ({handlers_count} handlers)...")
            
            try:
                assign_url = f"{API_BASE}/errors/tasks/assign"
                assign_response = requests.post(assign_url, json={
                    'task_id': task_id,
                    'agent_id': 'error_migration_agent',  # Use dedicated migration agent
                    'priority': task.get('priority', 'medium')
                }, timeout=10, verify=False)
                
                if assign_response.status_code == 200:
                    assign_data = assign_response.json()
                    if assign_data.get('success'):
                        assigned_count += 1
                        print(f"   [OK] Assigned to error_migration_agent")
                        if assign_data.get('points_awarded'):
                            points = assign_data.get('points', {})
                            print(f"   [POINTS] XP: {points.get('xp', 0)}, Activity: {points.get('activity_points', 0)}, Generation: {points.get('generation_points', 0)}")
                    else:
                        failed_count += 1
                        print(f"   [WARN] Assignment returned success=False")
                else:
                    failed_count += 1
                    print(f"   [FAIL] HTTP {assign_response.status_code}")
            except Exception as e:
                failed_count += 1
                print(f"   [FAIL] Error: {e}")
            
            print()
        
        print("=" * 80)
        print("ASSIGNMENT SUMMARY")
        print("=" * 80)
        print(f"[OK] Successfully assigned: {assigned_count} tasks")
        print(f"[FAIL] Failed assignments: {failed_count} tasks")
        print()
        
        return assigned_count, failed_count
    except Exception as e:
        print(f"[FAIL] Error in assignment: {e}")
        import traceback
        traceback.print_exc()
        return 0, 0


def main():
    """Main function"""
    print()
    print("=" * 80)
    print("AGENT ERROR MIGRATION - STARTING")
    print("=" * 80)
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Disable SSL warnings
    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    
    # Assign tasks to agents
    print("[1/1] Assigning migration tasks to agents...")
    assigned, failed = assign_migration_tasks_to_agents(max_tasks=15)
    print()
    
    # Final summary
    print("=" * 80)
    print("MIGRATION STARTED WITH AGENTS")
    print("=" * 80)
    print()
    print(f"[OK] Tasks assigned: {assigned}")
    print(f"[FAIL] Tasks failed: {failed}")
    print()
    print("Agents are now working on error handler migration!")
    print("Monitor progress at /vidgenerator/debugger -> Error Dashboard")
    print()


if __name__ == "__main__":
    main()
