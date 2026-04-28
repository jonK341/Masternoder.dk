#!/usr/bin/env python3
"""
Start Error Handler Migration
Generates migration tasks and assigns them to agents
"""
import os
import sys
import requests
import json
import codecs
from datetime import datetime

# Fix Windows encoding for emojis
if sys.platform == 'win32':
    if sys.stdout.encoding != 'utf-8':
        sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    if sys.stderr.encoding != 'utf-8':
        sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Configuration
BASE_URL = "https://masternoder.dk"
API_BASE = f"{BASE_URL}/vidgenerator/api"

def generate_migration_tasks():
    """Generate migration tasks from error handler analysis"""
    print("=" * 80)
    print("ERROR HANDLER MIGRATION - TASK GENERATION")
    print("=" * 80)
    print()
    
    try:
        url = f"{API_BASE}/errors/tasks/generate"
        response = requests.post(url, json={
            'priority': 'all',
            'max_tasks': 20
        }, timeout=10, verify=False)
        
        if response.status_code == 200:
            data = response.json()
            tasks = data.get('tasks', [])
            print(f"✅ Generated {len(tasks)} migration tasks")
            print()
            
            # Group by priority
            high_priority = [t for t in tasks if t.get('priority') == 'high']
            medium_priority = [t for t in tasks if t.get('priority') == 'medium']
            low_priority = [t for t in tasks if t.get('priority') == 'low']
            
            print(f"📊 Task Breakdown:")
            print(f"   🔴 High Priority: {len(high_priority)} tasks")
            print(f"   🟠 Medium Priority: {len(medium_priority)} tasks")
            print(f"   🟡 Low Priority: {len(low_priority)} tasks")
            print()
            
            # Show top 5 tasks
            print("📋 Top 5 Tasks:")
            for i, task in enumerate(tasks[:5], 1):
                print(f"   {i}. {task.get('file_name', 'Unknown')}")
                print(f"      Handlers: {task.get('handlers_count', 0)}")
                print(f"      Priority: {task.get('priority', 'unknown')}")
                print(f"      Task ID: {task.get('task_id', 'unknown')}")
                print()
            
            return tasks
        else:
            print(f"[FAIL] Failed to generate tasks: {response.status_code}")
            print(f"   Response: {response.text}")
            return []
    except Exception as e:
        print(f"[FAIL] Error generating tasks: {e}")
        import traceback
        traceback.print_exc()
        return []


def assign_tasks_to_agents(tasks, agent_id='agent_manager', max_assignments=5):
    """Assign tasks to agents"""
    print("=" * 80)
    print("ERROR HANDLER MIGRATION - TASK ASSIGNMENT")
    print("=" * 80)
    print()
    
    assigned_count = 0
    failed_count = 0
    
    # Prioritize high priority tasks
    high_priority = [t for t in tasks if t.get('priority') == 'high']
    medium_priority = [t for t in tasks if t.get('priority') == 'medium']
    low_priority = [t for t in tasks if t.get('priority') == 'low']
    
    # Combine in priority order
    prioritized_tasks = high_priority + medium_priority + low_priority
    
    for task in prioritized_tasks[:max_assignments]:
        task_id = task.get('task_id')
        file_name = task.get('file_name', 'Unknown')
        handlers_count = task.get('handlers_count', 0)
        
        print(f"[ASSIGN] Assigning task: {file_name} ({handlers_count} handlers)...")
        
        try:
            url = f"{API_BASE}/errors/tasks/assign"
            response = requests.post(url, json={
                'task_id': task_id,
                'agent_id': agent_id,
                'priority': task.get('priority', 'medium')
            }, timeout=10, verify=False)
            
            if response.status_code == 200:
                data = response.json()
                if data.get('success'):
                    assigned_count += 1
                    print(f"   [OK] Assigned to {agent_id}")
                    if data.get('points_awarded'):
                        print(f"   [POINTS] Points awarded: {data.get('points', {})}")
                else:
                    failed_count += 1
                    print(f"   [WARN] Assignment returned success=False")
            else:
                failed_count += 1
                print(f"   [FAIL] Failed: {response.status_code}")
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


def get_migration_stats():
    """Get migration statistics"""
    print("=" * 80)
    print("ERROR HANDLER MIGRATION - STATISTICS")
    print("=" * 80)
    print()
    
    try:
        url = f"{API_BASE}/errors/tasks/stats"
        response = requests.get(url, timeout=10, verify=False)
        
        if response.status_code == 200:
            data = response.json()
            stats = data.get('stats', {})
            
            print(f"📊 Migration Statistics:")
            print(f"   Total Files: {stats.get('total_files', 0)}")
            print(f"   Files Migrated: {stats.get('files_migrated', 0)}")
            print(f"   Files Remaining: {stats.get('files_remaining', 0)}")
            print(f"   Migration Progress: {stats.get('migration_percent', 0)}%")
            print()
            
            tasks_available = stats.get('tasks_available', {})
            print(f"📋 Tasks Available:")
            print(f"   High Priority: {tasks_available.get('high_priority', 0)}")
            print(f"   Medium Priority: {tasks_available.get('medium_priority', 0)}")
            print(f"   Low Priority: {tasks_available.get('low_priority', 0)}")
            print(f"   Total: {tasks_available.get('total', 0)}")
            print()
            
            return stats
        else:
            print(f"❌ Failed to get stats: {response.status_code}")
            return None
    except Exception as e:
        print(f"❌ Error getting stats: {e}")
        return None


def main():
    """Main migration starter"""
    print()
    print("=" * 80)
    print("ERROR HANDLER MIGRATION - STARTING")
    print("=" * 80)
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Disable SSL warnings
    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    
    # Step 1: Get current stats
    print("[1/3] Getting current migration statistics...")
    stats = get_migration_stats()
    print()
    
    # Step 2: Generate tasks
    print("[2/3] Generating migration tasks...")
    tasks = generate_migration_tasks()
    print()
    
    if not tasks:
        print("❌ No tasks generated. Exiting.")
        return
    
    # Step 3: Assign tasks
    print("[3/3] Assigning tasks to agents...")
    assigned, failed = assign_tasks_to_agents(tasks, max_assignments=10)
    print()
    
    # Final summary
    print("=" * 80)
    print("MIGRATION STARTED")
    print("=" * 80)
    print()
    print(f"✅ Tasks generated: {len(tasks)}")
    print(f"✅ Tasks assigned: {assigned}")
    print(f"❌ Tasks failed: {failed}")
    print()
    print("Next steps:")
    print("1. Agents will start working on assigned tasks")
    print("2. Monitor progress at /vidgenerator/debugger → Error Dashboard")
    print("3. Check task completion via /api/errors/tasks/stats")
    print()
    print("Migration started successfully! 🚀")
    print()


if __name__ == "__main__":
    main()
