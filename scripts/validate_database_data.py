#!/usr/bin/env python3
"""
Database Validation Script
Validates that all data is present and correct
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def validate_all_data():
    """Validate all database data"""
    print("="*70)
    print("DATABASE VALIDATION")
    print("="*70)
    print()
    
    validation_results = {
        'unified_points': {'total': 0, 'valid': 0, 'invalid': 0},
        'agents': {'total': 0, 'valid': 0, 'invalid': 0},
        'rewards': {'total': 0, 'valid': 0, 'invalid': 0},
        'skills': {'total': 0, 'valid': 0, 'invalid': 0},
        'activity': {'total': 0, 'valid': 0, 'invalid': 0},
        'tech_tree': {'total': 0, 'valid': 0, 'invalid': 0},
    }
    
    # Get test users
    test_users = [f"test_user_{i+1}" for i in range(50)]
    
    # 1. Validate Unified Points
    print("[1/6] Validating unified points...")
    try:
        from backend.services.unified_point_counter import UnifiedPointCounter
        point_counter = UnifiedPointCounter()
        
        for user_id in test_users:
            try:
                points = point_counter.get_all_points(user_id)
                validation_results['unified_points']['total'] += 1
                if points and isinstance(points, dict):
                    if 'total_points' in points or 'xp_total' in points:
                        validation_results['unified_points']['valid'] += 1
                    else:
                        validation_results['unified_points']['invalid'] += 1
                else:
                    validation_results['unified_points']['invalid'] += 1
            except Exception as e:
                validation_results['unified_points']['invalid'] += 1
        
        print(f"  [OK] Points: {validation_results['unified_points']['valid']}/{validation_results['unified_points']['total']} valid")
    except Exception as e:
        print(f"  [ERROR] Could not validate points: {e}")
    
    # 2. Validate Agents
    print("[2/6] Validating agents...")
    try:
        from backend.services.agent_manager import agent_manager
        
        for user_id in test_users[:20]:
            try:
                if hasattr(agent_manager, 'get_all_agents_for_user'):
                    agents = agent_manager.get_all_agents_for_user(user_id)
                    validation_results['agents']['total'] += 1
                    if agents and len(agents) > 0:
                        validation_results['agents']['valid'] += 1
                    else:
                        validation_results['agents']['invalid'] += 1
            except Exception as e:
                validation_results['agents']['invalid'] += 1
        
        print(f"  [OK] Agents: {validation_results['agents']['valid']}/{validation_results['agents']['total']} valid")
    except Exception as e:
        print(f"  [ERROR] Could not validate agents: {e}")
    
    # 3. Validate Rewards
    print("[3/6] Validating rewards...")
    try:
        from backend.services.rewards_system_v2 import rewards_system_v2
        
        for user_id in test_users[:30]:
            try:
                if hasattr(rewards_system_v2, 'get_user_rewards'):
                    rewards = rewards_system_v2.get_user_rewards(user_id)
                    validation_results['rewards']['total'] += 1
                    if rewards and isinstance(rewards, dict):
                        validation_results['rewards']['valid'] += 1
                    else:
                        validation_results['rewards']['invalid'] += 1
            except Exception as e:
                validation_results['rewards']['invalid'] += 1
        
        print(f"  [OK] Rewards: {validation_results['rewards']['valid']}/{validation_results['rewards']['total']} valid")
    except Exception as e:
        print(f"  [ERROR] Could not validate rewards: {e}")
    
    # 4. Validate Skills
    print("[4/6] Validating skills...")
    try:
        from backend.services.agent_battle_skills import agent_battle_skills
        
        for user_id in test_users[:25]:
            try:
                if hasattr(agent_battle_skills, 'get_user_skills'):
                    skills = agent_battle_skills.get_user_skills(user_id)
                    validation_results['skills']['total'] += 1
                    if skills and isinstance(skills, dict):
                        validation_results['skills']['valid'] += 1
                    else:
                        validation_results['skills']['invalid'] += 1
            except Exception as e:
                validation_results['skills']['invalid'] += 1
        
        print(f"  [OK] Skills: {validation_results['skills']['valid']}/{validation_results['skills']['total']} valid")
    except Exception as e:
        print(f"  [ERROR] Could not validate skills: {e}")
    
    # 5. Validate Activity
    print("[5/6] Validating activity...")
    try:
        from backend.services.activity_points_system import ActivityPointsSystem
        activity_system = ActivityPointsSystem()
        
        for user_id in test_users:
            try:
                if hasattr(activity_system, 'visitor_data'):
                    validation_results['activity']['total'] += 1
                    if user_id in activity_system.visitor_data:
                        validation_results['activity']['valid'] += 1
                    else:
                        validation_results['activity']['invalid'] += 1
            except Exception as e:
                validation_results['activity']['invalid'] += 1
        
        print(f"  [OK] Activity: {validation_results['activity']['valid']}/{validation_results['activity']['total']} valid")
    except Exception as e:
        print(f"  [ERROR] Could not validate activity: {e}")
    
    # 6. Validate Tech Tree
    print("[6/6] Validating tech tree...")
    try:
        from backend.services.enhanced_tech_tree_with_quests import enhanced_tech_tree
        
        for user_id in test_users[:15]:
            try:
                if hasattr(enhanced_tech_tree, 'get_user_tech_tree'):
                    tech_tree = enhanced_tech_tree.get_user_tech_tree(user_id)
                    validation_results['tech_tree']['total'] += 1
                    if tech_tree:
                        validation_results['tech_tree']['valid'] += 1
                    else:
                        validation_results['tech_tree']['invalid'] += 1
            except Exception as e:
                validation_results['tech_tree']['invalid'] += 1
        
        print(f"  [OK] Tech Tree: {validation_results['tech_tree']['valid']}/{validation_results['tech_tree']['total']} valid")
    except Exception as e:
        print(f"  [ERROR] Could not validate tech tree: {e}")
    
    # Summary
    print()
    print("="*70)
    print("VALIDATION SUMMARY")
    print("="*70)
    print()
    
    total_valid = sum(r['valid'] for r in validation_results.values())
    total_total = sum(r['total'] for r in validation_results.values())
    
    for system, results in validation_results.items():
        percentage = (results['valid'] / results['total'] * 100) if results['total'] > 0 else 0
        print(f"{system:20s}: {results['valid']:3d}/{results['total']:3d} ({percentage:5.1f}%)")
    
    print()
    print(f"Overall: {total_valid}/{total_total} ({total_valid/total_total*100 if total_total > 0 else 0:.1f}%)")
    print()
    
    return validation_results

if __name__ == "__main__":
    validate_all_data()
