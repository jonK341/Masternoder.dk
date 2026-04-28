#!/usr/bin/env python3
"""
Agent Status Check
Comprehensive check of all agents and their status
"""
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def check_agents():
    """Check all agents status"""
    print("=" * 80)
    print("AGENT STATUS CHECK")
    print("=" * 80)
    print()
    
    results = {
        'agents': {},
        'services': {},
        'status': 'unknown',
        'errors': [],
        'warnings': []
    }
    
    # Check Master Fix Agent
    print("1. Master Fix Agent")
    print("-" * 80)
    try:
        from backend.services.master_fix_agent_skills import master_fix_agent_skills
        skills = master_fix_agent_skills.get_all_skills()
        personality = master_fix_agent_skills.personality if hasattr(master_fix_agent_skills, 'personality') else {'name': 'Master Fix Agent', 'experience_level': 0}
        stats = master_fix_agent_skills.get_statistics() if hasattr(master_fix_agent_skills, 'get_statistics') else {'total_skills_used': 0}
        
        results['agents']['master_fix_agent'] = {
            'status': 'active',
            'skills_count': len(skills),
            'personality': personality.get('name', 'Unknown'),
            'experience': personality.get('experience_level', 0),
            'stats': stats
        }
        
        print(f"  ✅ Status: ACTIVE")
        print(f"  📊 Skills: {len(skills)} available")
        print(f"  👤 Personality: {personality.get('name', 'Unknown')}")
        print(f"  ⭐ Experience: {personality.get('experience_level', 0)}")
        print(f"  📈 Stats: {stats.get('total_skills_used', 0)} skills used")
    except Exception as e:
        results['agents']['master_fix_agent'] = {'status': 'error', 'error': str(e)}
        results['errors'].append(f"Master Fix Agent: {e}")
        print(f"  ❌ Error: {e}")
    print()
    
    # Check Agent Automation
    print("2. Agent Automation")
    print("-" * 80)
    try:
        from backend.services.agent_automation import agent_automation
        status = agent_automation.get_status()
        
        results['services']['agent_automation'] = {
            'status': 'active' if status.get('running') else 'stopped',
            'enabled': status.get('enabled', False),
            'autoplay': status.get('autoplay', False),
            'auto_fix': status.get('auto_fix_enabled', False),
            'tasks': len(status.get('tasks', []))
        }
        
        print(f"  ✅ Status: {'ACTIVE' if status.get('running') else 'STOPPED'}")
        print(f"  🔄 Enabled: {status.get('enabled', False)}")
        print(f"  ▶️  Autoplay: {status.get('autoplay', False)}")
        print(f"  🔧 Auto-Fix: {status.get('auto_fix_enabled', False)}")
        print(f"  📋 Tasks: {len(status.get('tasks', []))}")
    except Exception as e:
        results['services']['agent_automation'] = {'status': 'error', 'error': str(e)}
        results['errors'].append(f"Agent Automation: {e}")
        print(f"  ❌ Error: {e}")
    print()
    
    # Check Agent Activation System
    print("3. Agent Activation System")
    print("-" * 80)
    try:
        from backend.services.agent_activation_system import agent_activation_system
        status = agent_activation_system.get_status()
        
        results['services']['agent_activation'] = {
            'status': 'active' if status.get('running') else 'stopped',
            'activations': status.get('total_activations', 0),
            'enabled': status.get('enabled_activations', 0),
            'history': status.get('activation_history_count', 0)
        }
        
        print(f"  ✅ Status: {'ACTIVE' if status.get('running') else 'STOPPED'}")
        print(f"  🔄 Activations: {status.get('total_activations', 0)} total")
        print(f"  ✅ Enabled: {status.get('enabled_activations', 0)}")
        print(f"  📜 History: {status.get('activation_history_count', 0)} records")
    except Exception as e:
        results['services']['agent_activation'] = {'status': 'error', 'error': str(e)}
        results['errors'].append(f"Agent Activation: {e}")
        print(f"  ❌ Error: {e}")
    print()
    
    # Check Agent Research Tracker
    print("4. Agent Research Tracker")
    print("-" * 80)
    try:
        from backend.services.agent_research_tracker import agent_research_tracker
        research_summary = agent_research_tracker.get_research_summary()
        monitoring_summary = agent_research_tracker.get_monitoring_summary()
        
        results['services']['agent_research'] = {
            'status': 'active',
            'research_topics': research_summary.get('topics', 0),
            'active_projects': research_summary.get('active_projects', 0),
            'findings': research_summary.get('total_findings', 0),
            'monitoring_targets': monitoring_summary.get('monitoring_targets', 0),
            'alerts': monitoring_summary.get('active_alerts', 0)
        }
        
        print(f"  ✅ Status: ACTIVE")
        print(f"  🔬 Research Topics: {research_summary.get('topics', 0)}")
        print(f"  📊 Active Projects: {research_summary.get('active_projects', 0)}")
        print(f"  📝 Findings: {research_summary.get('total_findings', 0)}")
        print(f"  📈 Monitoring Targets: {monitoring_summary.get('monitoring_targets', 0)}")
        print(f"  ⚠️  Active Alerts: {monitoring_summary.get('active_alerts', 0)}")
    except Exception as e:
        results['services']['agent_research'] = {'status': 'error', 'error': str(e)}
        results['errors'].append(f"Agent Research: {e}")
        print(f"  ❌ Error: {e}")
    print()
    
    # Check Agent Trigger System
    print("5. Agent Trigger System")
    print("-" * 80)
    try:
        from backend.services.agent_trigger_system import agent_trigger_system
        stats = agent_trigger_system.get_trigger_stats()
        
        results['services']['agent_trigger'] = {
            'status': 'active',
            'total_triggers': stats.get('total_triggers', 0),
            'enabled_triggers': stats.get('enabled_triggers', 0),
            'executions': stats.get('total_executions', 0),
            'points_awarded': stats.get('points_awarded', {})
        }
        
        print(f"  ✅ Status: ACTIVE")
        print(f"  🎯 Total Triggers: {stats.get('total_triggers', 0)}")
        print(f"  ✅ Enabled: {stats.get('enabled_triggers', 0)}")
        print(f"  🔄 Executions: {stats.get('total_executions', 0)}")
        points = stats.get('points_awarded', {})
        print(f"  💰 Points Awarded:")
        print(f"     - XP: {points.get('total_xp', 0)}")
        print(f"     - Gen: {points.get('total_generation_points', 0)}")
        print(f"     - Battle: {points.get('total_battle_points', 0)}")
    except Exception as e:
        results['services']['agent_trigger'] = {'status': 'error', 'error': str(e)}
        results['errors'].append(f"Agent Trigger: {e}")
        print(f"  ❌ Error: {e}")
    print()
    
    # Check Agent Skillset
    print("6. Agent Skillset")
    print("-" * 80)
    try:
        from backend.services.agent_skillset import agent_skillset
        skillsets = agent_skillset.get_all_skillsets()
        
        results['services']['agent_skillset'] = {
            'status': 'active',
            'agents': len(skillsets.get('agents', {})),
            'test_players': len(skillsets.get('test_players', {}))
        }
        
        print(f"  ✅ Status: ACTIVE")
        print(f"  🤖 Agents: {len(skillsets.get('agents', {}))}")
        print(f"  👥 Test Players: {len(skillsets.get('test_players', {}))}")
        
        # Show agent details
        for agent_id, agent_data in skillsets.get('agents', {}).items():
            print(f"     - {agent_data.get('name', agent_id)}: Level {agent_data.get('level', 0)}, {len(agent_data.get('skills', []))} skills")
    except Exception as e:
        results['services']['agent_skillset'] = {'status': 'error', 'error': str(e)}
        results['errors'].append(f"Agent Skillset: {e}")
        print(f"  ❌ Error: {e}")
    print()
    
    # Check Agent Groups
    print("7. Agent Groups")
    print("-" * 80)
    try:
        from backend.services.agent_groups import agent_groups
        groups = agent_groups.get_all_groups()
        
        results['services']['agent_groups'] = {
            'status': 'active',
            'groups': len(groups)
        }
        
        print(f"  ✅ Status: ACTIVE")
        print(f"  👥 Groups: {len(groups)}")
        
        for group_id, group_data in groups.items():
            members = group_data.get('members', {})
            total = sum(len(v) if isinstance(v, list) else 0 for v in members.values())
            print(f"     - {group_data.get('name', group_id)}: {total} members")
    except Exception as e:
        results['services']['agent_groups'] = {'status': 'error', 'error': str(e)}
        results['errors'].append(f"Agent Groups: {e}")
        print(f"  ❌ Error: {e}")
    print()
    
    # Check Agent Support Service
    print("8. Agent Support Service")
    print("-" * 80)
    try:
        from backend.services.agent_support_service import agent_support_service
        services = agent_support_service.get_services()
        tickets = agent_support_service.get_support_tickets()
        
        results['services']['agent_support'] = {
            'status': 'active',
            'services': len(services.get('services', {})),
            'tickets': len(tickets.get('tickets', []))
        }
        
        print(f"  ✅ Status: ACTIVE")
        print(f"  🛠️  Services: {len(services.get('services', {}))}")
        print(f"  🎫 Tickets: {len(tickets.get('tickets', []))}")
    except Exception as e:
        results['services']['agent_support'] = {'status': 'error', 'error': str(e)}
        results['errors'].append(f"Agent Support: {e}")
        print(f"  ❌ Error: {e}")
    print()
    
    # Check Agent Python Executor
    print("9. Agent Python Executor")
    print("-" * 80)
    try:
        from backend.services.agent_python_executor import agent_python_executor
        scripts = agent_python_executor.get_available_scripts() if hasattr(agent_python_executor, 'get_available_scripts') else {'scripts': []}
        
        results['services']['agent_python_executor'] = {
            'status': 'active',
            'scripts': len(scripts.get('scripts', []))
        }
        
        print(f"  ✅ Status: ACTIVE")
        print(f"  🐍 Scripts Available: {len(scripts.get('scripts', []))}")
    except Exception as e:
        results['services']['agent_python_executor'] = {'status': 'error', 'error': str(e)}
        results['errors'].append(f"Agent Python Executor: {e}")
        print(f"  ❌ Error: {e}")
    print()
    
    # Check API Monitoring Agent
    print("10. API Monitoring Agent")
    print("-" * 80)
    try:
        from backend.services.api_monitoring_agent import api_monitoring_agent
        status = api_monitoring_agent.get_status()
        
        results['services']['api_monitoring'] = {
            'status': 'active' if status.get('enabled') else 'disabled',
            'enabled': status.get('enabled', False),
            'auto_generate': status.get('auto_generate_enabled', False),
            'scans': status.get('scan_count', 0),
            'alerts': status.get('alerts_count', 0)
        }
        
        print(f"  ✅ Status: {'ACTIVE' if status.get('enabled') else 'DISABLED'}")
        print(f"  🔄 Enabled: {status.get('enabled', False)}")
        print(f"  🤖 Auto-Generate: {status.get('auto_generate_enabled', False)}")
        print(f"  📊 Scans: {status.get('scan_count', 0)}")
        print(f"  ⚠️  Alerts: {status.get('alerts_count', 0)}")
    except Exception as e:
        results['services']['api_monitoring'] = {'status': 'error', 'error': str(e)}
        results['errors'].append(f"API Monitoring: {e}")
        print(f"  ❌ Error: {e}")
    print()
    
    # Check New Agents
    print("11. New Agents (8 Specialized Agents)")
    print("-" * 80)
    new_agents_status = {}
    try:
        from backend.services.agent_content_generator import agent_content_generator
        from backend.services.agent_battle_strategy import agent_battle_strategy
        from backend.services.agent_social_engagement import agent_social_engagement
        from backend.services.agent_analytics import agent_analytics
        from backend.services.agent_security import agent_security
        from backend.services.agent_performance_optimizer import agent_performance_optimizer
        from backend.services.agent_user_experience import agent_user_experience
        from backend.services.agent_integration import agent_integration
        
        agents_list = [
            ('Content Generator', agent_content_generator),
            ('Battle Strategy', agent_battle_strategy),
            ('Social Engagement', agent_social_engagement),
            ('Analytics', agent_analytics),
            ('Security', agent_security),
            ('Performance Optimizer', agent_performance_optimizer),
            ('User Experience', agent_user_experience),
            ('Integration', agent_integration)
        ]
        
        active_count = 0
        for name, agent in agents_list:
            try:
                status = agent.get_status()
                new_agents_status[name.lower().replace(' ', '_')] = {
                    'status': 'active',
                    'level': status.get('level', 1),
                    'skills': len(status.get('skills', []))
                }
                active_count += 1
                print(f"  ✅ {name}: Level {status.get('level', 1)}, {len(status.get('skills', []))} skills")
            except Exception as e:
                new_agents_status[name.lower().replace(' ', '_')] = {'status': 'error', 'error': str(e)}
                print(f"  ❌ {name}: {e}")
        
        results['agents']['new_agents'] = {
            'status': 'active',
            'total': len(agents_list),
            'active': active_count,
            'agents': new_agents_status
        }
        
        print(f"\n  📊 Total: {active_count}/{len(agents_list)} active")
    except Exception as e:
        results['agents']['new_agents'] = {'status': 'error', 'error': str(e)}
        results['errors'].append(f"New Agents: {e}")
        print(f"  ❌ Error: {e}")
    print()
    
    # Summary
    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)
    
    total_agents = len(results['agents'])
    total_services = len(results['services'])
    active_agents = sum(1 for a in results['agents'].values() if a.get('status') == 'active')
    active_services = sum(1 for s in results['services'].values() if s.get('status') == 'active')
    
    # Count new agents
    new_agents_count = results['agents'].get('new_agents', {}).get('active', 0)
    
    print(f"📊 Agents: {active_agents}/{total_agents} active")
    print(f"📊 New Agents: {new_agents_count} specialized agents")
    print(f"📊 Services: {active_services}/{total_services} active")
    print(f"❌ Errors: {len(results['errors'])}")
    print(f"⚠️  Warnings: {len(results['warnings'])}")
    
    if results['errors']:
        print("\n❌ Errors Found:")
        for error in results['errors']:
            print(f"   - {error}")
    
    if active_agents == total_agents and active_services == total_services and not results['errors']:
        results['status'] = 'healthy'
        print("\n✅ All agents are healthy and operational!")
    elif active_agents > 0 or active_services > 0:
        results['status'] = 'partial'
        print("\n⚠️  Some agents/services have issues")
    else:
        results['status'] = 'error'
        print("\n❌ Critical issues detected")
    
    print("=" * 80)
    
    return results

if __name__ == '__main__':
    try:
        results = check_agents()
        sys.exit(0 if results['status'] == 'healthy' else 1)
    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
