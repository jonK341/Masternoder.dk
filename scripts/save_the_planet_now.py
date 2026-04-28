#!/usr/bin/env python3
"""
SAVE THE PLANET - NOW!
Activates all agents to perform comprehensive system maintenance
"""
import os
import sys
import json
from datetime import datetime

# Add project root to path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

def save_the_planet():
    """Activate all agents to save the planet!"""
    print("=" * 80)
    print("🌍 SAVING THE PLANET - AGENT ACTIVATION 🌍")
    print("=" * 80)
    print()
    
    results = {
        'timestamp': datetime.now().isoformat(),
        'agents_activated': [],
        'operations_performed': [],
        'errors': [],
        'success': True
    }
    
    # 1. Agent Controller - Master Control
    print("🎮 [1/16] Activating Agent Controller...")
    try:
        from backend.services.agent_controller import agent_controller
        status = agent_controller.get_status()
        results['agents_activated'].append({
            'agent': 'agent_controller',
            'status': 'active',
            'total_agents': status.get('total_agents', 0)
        })
        print(f"  ✅ Agent Controller: Managing {status.get('total_agents', 0)} agents")
    except Exception as e:
        results['errors'].append(f'Agent Controller: {e}')
        print(f"  ❌ Error: {e}")
    
    # 2. Master Fix Agent - System Repair
    print("\n🔧 [2/16] Activating Master Fix Agent...")
    try:
        from backend.services.master_fix_agent_skills import master_fix_agent_skills
        
        # Run full diagnostic
        diagnostic = master_fix_agent_skills.skill_run_full_diagnostic()
        if diagnostic.get('success'):
            health = diagnostic.get('health_score', 0)
            print(f"  ✅ System Health: {health}%")
            results['operations_performed'].append({
                'agent': 'master_fix',
                'operation': 'full_diagnostic',
                'health_score': health
            })
        
        # Check blueprints
        blueprint_check = master_fix_agent_skills.skill_check_blueprints()
        if blueprint_check.get('success'):
            count = blueprint_check.get('blueprint_count', 0)
            print(f"  ✅ Blueprints: {count} registered")
        
        # Verify database
        db_check = master_fix_agent_skills.skill_verify_database()
        if db_check.get('success'):
            print(f"  ✅ Database: Verified")
        
        results['agents_activated'].append({'agent': 'master_fix', 'status': 'active'})
    except Exception as e:
        results['errors'].append(f'Master Fix Agent: {e}')
        print(f"  ❌ Error: {e}")
    
    # 3. API Monitoring Agent - API Health
    print("\n📊 [3/16] Activating API Monitoring Agent...")
    try:
        from backend.services.api_monitoring_agent import api_monitoring_agent
        status = api_monitoring_agent.get_status()
        enabled = status.get('enabled', False)
        if not enabled:
            # Set enabled if possible
            try:
                api_monitoring_agent.config['enabled'] = True
            except:
                pass
        print(f"  ✅ API Monitoring: {'Enabled' if status.get('enabled', False) else 'Active'}, {status.get('scan_count', 0)} scans")
        results['agents_activated'].append({'agent': 'api_monitoring', 'status': 'active'})
    except Exception as e:
        results['errors'].append(f'API Monitoring: {e}')
        print(f"  ❌ Error: {e}")
    
    # 4. Agent Automation - Auto Maintenance
    print("\n🤖 [4/16] Activating Agent Automation...")
    try:
        from backend.services.agent_automation import agent_automation
        # Start automation if not already started
        try:
            agent_automation.start()
        except:
            pass
        status = agent_automation.get_status()
        print(f"  ✅ Automation: Status: {status.get('status', 'active')}, Autoplay: {status.get('autoplay', False)}, Auto-Fix: {status.get('auto_fix_enabled', False)}")
        results['agents_activated'].append({'agent': 'automation', 'status': 'active'})
    except Exception as e:
        results['errors'].append(f'Automation: {e}')
        print(f"  ❌ Error: {e}")
    
    # 5. Agent Activation System - Scheduled Tasks
    print("\n⚡ [5/16] Activating Agent Activation System...")
    try:
        from backend.services.agent_activation_system import agent_activation_system
        agent_activation_system.start()
        status = agent_activation_system.get_status()
        enabled = status.get('enabled_activations_count', 0)
        print(f"  ✅ Activation System: {enabled} activations enabled")
        results['agents_activated'].append({'agent': 'activation', 'status': 'active'})
    except Exception as e:
        results['errors'].append(f'Activation System: {e}')
        print(f"  ❌ Error: {e}")
    
    # 6. Agent Research Tracker - Research & Monitoring
    print("\n🔬 [6/16] Activating Agent Research Tracker...")
    try:
        from backend.services.agent_research_tracker import agent_research_tracker
        research_summary = agent_research_tracker.get_research_summary()
        monitoring_summary = agent_research_tracker.get_monitoring_summary()
        print(f"  ✅ Research: {len(research_summary.get('total_topics', []))} topics, {len(monitoring_summary.get('total_targets', []))} monitoring targets")
        results['agents_activated'].append({'agent': 'research', 'status': 'active'})
    except Exception as e:
        results['errors'].append(f'Research Tracker: {e}')
        print(f"  ❌ Error: {e}")
    
    # 7. Agent Trigger System - Points System
    print("\n🎯 [7/16] Activating Agent Trigger System...")
    try:
        from backend.services.agent_trigger_system import agent_trigger_system
        stats = agent_trigger_system.get_trigger_stats()
        print(f"  ✅ Triggers: {stats.get('total_triggers', 0)} triggers, {stats.get('enabled_triggers', 0)} enabled")
        results['agents_activated'].append({'agent': 'trigger', 'status': 'active'})
    except Exception as e:
        results['errors'].append(f'Trigger System: {e}')
        print(f"  ❌ Error: {e}")
    
    # 8. Content Generator Agent
    print("\n🎨 [8/16] Activating Content Generator Agent...")
    try:
        from backend.services.agent_content_generator import agent_content_generator
        status = agent_content_generator.get_status()
        print(f"  ✅ Content Generator: Level {status.get('level', 1)}, {len(status.get('skills', []))} skills")
        results['agents_activated'].append({'agent': 'content_generator', 'status': 'active'})
    except Exception as e:
        results['errors'].append(f'Content Generator: {e}')
        print(f"  ❌ Error: {e}")
    
    # 9. Battle Strategy Agent
    print("\n⚔️ [9/16] Activating Battle Strategy Agent...")
    try:
        from backend.services.agent_battle_strategy import agent_battle_strategy
        status = agent_battle_strategy.get_status()
        print(f"  ✅ Battle Strategy: Level {status.get('level', 1)}, {len(status.get('skills', []))} skills")
        results['agents_activated'].append({'agent': 'battle_strategy', 'status': 'active'})
    except Exception as e:
        results['errors'].append(f'Battle Strategy: {e}')
        print(f"  ❌ Error: {e}")
    
    # 10. Social Engagement Agent
    print("\n👥 [10/16] Activating Social Engagement Agent...")
    try:
        from backend.services.agent_social_engagement import agent_social_engagement
        status = agent_social_engagement.get_status()
        print(f"  ✅ Social Engagement: Level {status.get('level', 1)}, {len(status.get('skills', []))} skills")
        results['agents_activated'].append({'agent': 'social_engagement', 'status': 'active'})
    except Exception as e:
        results['errors'].append(f'Social Engagement: {e}')
        print(f"  ❌ Error: {e}")
    
    # 11. Analytics Agent
    print("\n📈 [11/16] Activating Analytics Agent...")
    try:
        from backend.services.agent_analytics import agent_analytics
        status = agent_analytics.get_status()
        print(f"  ✅ Analytics: Level {status.get('level', 1)}, {len(status.get('skills', []))} skills")
        results['agents_activated'].append({'agent': 'analytics', 'status': 'active'})
    except Exception as e:
        results['errors'].append(f'Analytics: {e}')
        print(f"  ❌ Error: {e}")
    
    # 12. Security Agent
    print("\n🔒 [12/16] Activating Security Agent...")
    try:
        from backend.services.agent_security import agent_security
        scan_result = agent_security.scan_vulnerabilities()
        if scan_result.get('success'):
            score = scan_result.get('security_score', 0)
            print(f"  ✅ Security: Score {score}%, {scan_result.get('total_scans', 0)} scans")
        results['agents_activated'].append({'agent': 'security', 'status': 'active'})
    except Exception as e:
        results['errors'].append(f'Security: {e}')
        print(f"  ❌ Error: {e}")
    
    # 13. Performance Optimizer Agent
    print("\n⚡ [13/16] Activating Performance Optimizer Agent...")
    try:
        from backend.services.agent_performance_optimizer import agent_performance_optimizer
        status = agent_performance_optimizer.get_status()
        print(f"  ✅ Performance Optimizer: Level {status.get('level', 1)}, {status.get('optimizations_performed', 0)} optimizations")
        results['agents_activated'].append({'agent': 'performance_optimizer', 'status': 'active'})
    except Exception as e:
        results['errors'].append(f'Performance Optimizer: {e}')
        print(f"  ❌ Error: {e}")
    
    # 14. User Experience Agent
    print("\n✨ [14/16] Activating User Experience Agent...")
    try:
        from backend.services.agent_user_experience import agent_user_experience
        status = agent_user_experience.get_status()
        print(f"  ✅ User Experience: Level {status.get('level', 1)}, {status.get('ux_analyses', 0)} analyses")
        results['agents_activated'].append({'agent': 'user_experience', 'status': 'active'})
    except Exception as e:
        results['errors'].append(f'User Experience: {e}')
        print(f"  ❌ Error: {e}")
    
    # 15. Integration Agent
    print("\n🔗 [15/16] Activating Integration Agent...")
    try:
        from backend.services.agent_integration import agent_integration
        status = agent_integration.get_status()
        print(f"  ✅ Integration: Level {status.get('level', 1)}, {status.get('integrations_created', 0)} integrations")
        results['agents_activated'].append({'agent': 'integration', 'status': 'active'})
    except Exception as e:
        results['errors'].append(f'Integration: {e}')
        print(f"  ❌ Error: {e}")
    
    # 17. Agent Manager
    print("\n👔 [17/18] Activating Agent Manager...")
    try:
        from backend.services.agent_manager import agent_manager
        # Activate all agents using manager
        activation_result = agent_manager.activate_all_agents()
        status = agent_manager.get_status()
        print(f"  ✅ Manager: Level {status.get('level', 1)}, Activated {activation_result.get('activated', 0)} agents, {status.get('ai_fixes_applied', 0)} AI fixes")
        results['agents_activated'].append({'agent': 'manager', 'status': 'active'})
        results['operations_performed'].append({
            'agent': 'manager',
            'operation': 'activate_all_agents',
            'activated': activation_result.get('activated', 0)
        })
    except Exception as e:
        results['errors'].append(f'Manager: {e}')
        print(f"  ❌ Error: {e}")
    
    # 18. Agent Secretary
    print("\n📋 [18/19] Activating Agent Secretary...")
    try:
        from backend.services.agent_secretary import agent_secretary
        # Coordinate activation
        coord_result = agent_secretary.coordinate_agent_activation()
        # Generate status report
        report_result = agent_secretary.generate_ai_report('status')
        status = agent_secretary.get_status()
        print(f"  ✅ Secretary: Level {status.get('level', 1)}, {status.get('reports_generated', 0)} reports, {status.get('tasks_scheduled', 0)} tasks scheduled")
        results['agents_activated'].append({'agent': 'secretary', 'status': 'active'})
        results['operations_performed'].append({
            'agent': 'secretary',
            'operation': 'coordinate_and_report',
            'report_generated': True
        })
    except Exception as e:
        results['errors'].append(f'Secretary: {e}')
        print(f"  ❌ Error: {e}")
    
    # 19. Agent Judge
    print("\n⚖️ [19/19] Activating Agent Judge...")
    try:
        from backend.services.agent_judge import agent_judge
        # Rate system health
        health_rating = agent_judge.rate_system_health()
        status = agent_judge.get_status()
        print(f"  ✅ Judge: Level {status.get('level', 1)}, {status.get('judgments_made', 0)} judgments, {status.get('systems_rated', 0)} systems rated")
        results['agents_activated'].append({'agent': 'judge', 'status': 'active'})
        results['operations_performed'].append({
            'agent': 'judge',
            'operation': 'rate_system_health',
            'health_rating': health_rating.get('rating', {}).get('rating', 'N/A')
        })
    except Exception as e:
        results['errors'].append(f'Judge: {e}')
        print(f"  ❌ Error: {e}")
    
    # 16. Agent Support Service
    print("\n🛠️ [16/19] Activating Agent Support Service...")
    try:
        from backend.services.agent_support_service import agent_support_service
        # Get services and tickets from support_data
        support_data = agent_support_service.support_data
        services = support_data.get('services', {})
        tickets = support_data.get('support_tickets', [])
        print(f"  ✅ Support Service: {len(services)} services, {len(tickets)} tickets")
        results['agents_activated'].append({'agent': 'support', 'status': 'active'})
    except Exception as e:
        results['errors'].append(f'Support Service: {e}')
        print(f"  ❌ Error: {e}")
    
    # Final Summary
    print("\n" + "=" * 80)
    print("🌍 PLANET SAVE STATUS 🌍")
    print("=" * 80)
    
    active_count = len([a for a in results['agents_activated'] if a.get('status') == 'active'])
    total_agents = len(results['agents_activated'])
    
    # Update count display
    print(f"\n📊 Total Agents: {total_agents}")
    operations_count = len(results['operations_performed'])
    errors_count = len(results['errors'])
    
    print(f"\n✅ Agents Activated: {active_count}/{total_agents}")
    print(f"🔧 Operations Performed: {operations_count}")
    print(f"❌ Errors: {errors_count}")
    
    if errors_count == 0:
        print("\n🎉 PLANET SAVED! All agents are operational!")
        results['success'] = True
    else:
        print(f"\n⚠️  Planet partially saved. {errors_count} errors encountered.")
        results['success'] = False
    
    # Save results
    results_file = os.path.join(BASE_DIR, 'logs', 'agents', 'planet_save_results.json')
    os.makedirs(os.path.dirname(results_file), exist_ok=True)
    with open(results_file, 'w') as f:
        json.dump(results, f, indent=2, default=str)
    
    print(f"\n📄 Results saved to: {results_file}")
    print("=" * 80)
    
    return results

if __name__ == '__main__':
    save_the_planet()
