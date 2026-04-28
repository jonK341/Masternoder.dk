"""
Start Agent Automation System
Initializes and starts all agent automation, groups, and skillsets
"""
import os
import sys
from pathlib import Path

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

def start_automation():
    """Start agent automation system"""
    print("=" * 80)
    print("STARTING AGENT AUTOMATION SYSTEM")
    print("=" * 80)
    print()
    
    try:
        from backend.services.agent_automation import agent_automation
        from backend.services.agent_skillset import agent_skillset
        from backend.services.agent_groups import agent_groups
        
        # Enable automation
        agent_automation.config['enabled'] = True
        agent_automation.config['autoplay'] = True
        agent_automation.save_config()
        print("✅ Automation enabled and autoplay activated")
        
        # Start automation
        agent_automation.start()
        print("✅ Agent automation started")
        
        # Verify skillsets
        skillsets = agent_skillset.get_all_skillsets()
        print(f"✅ Loaded {len(skillsets.get('agents', {}))} agent skillsets")
        print(f"✅ Loaded {len(skillsets.get('test_players', {}))} test player skillsets")
        
        # Verify groups
        groups = agent_groups.get_all_groups()
        print(f"✅ Loaded {len(groups)} groups")
        
        for group_id, group in groups.items():
            stats = agent_groups.get_group_stats(group_id)
            print(f"   - {group['name']}: {stats['total_members']} members")
        
        # Get status
        status = agent_automation.get_status()
        print()
        print("=" * 80)
        print("AUTOMATION STATUS")
        print("=" * 80)
        print(f"Running: {status['running']}")
        print(f"Enabled: {status['enabled']}")
        print(f"Autoplay: {status['autoplay']}")
        print(f"Tasks: {status['tasks_count']}")
        print(f"Active Threads: {status['active_threads']}")
        print()
        print("=" * 80)
        print("✅ AGENT AUTOMATION SYSTEM ACTIVE!")
        print("=" * 80)
        
        return True
        
    except Exception as e:
        print(f"❌ Error starting automation: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    success = start_automation()
    sys.exit(0 if success else 1)
