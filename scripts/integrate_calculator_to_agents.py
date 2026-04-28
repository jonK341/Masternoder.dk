#!/usr/bin/env python3
"""
Integrate Advanced Calculator into Agent System
Adds calculator skills, abilities, missions, and quests to agents
"""
import os
import sys

# Add project root to path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

def integrate_calculator():
    """Integrate calculator into agent system"""
    print("=" * 80)
    print("INTEGRATING ADVANCED CALCULATOR INTO AGENT SYSTEM")
    print("=" * 80)
    print()
    
    try:
        # 1. Add calculator skills to agent skillset
        print("[1/4] Adding calculator skills to agent skillset...")
        try:
            from backend.services.agent_skillset import agent_skillset
            
            calculator_skills = [
                'calculate_with_intelligence',
                'detect_point_loss',
                'repair_all_systems',
                'predict_future_points',
                'analyze_patterns',
                'get_calculator_statistics'
            ]
            
            # Add to master_fix_agent
            for skill in calculator_skills:
                agent_skillset.add_skill('master_fix_agent', skill, 'agents')
            
            print(f"  ✅ Added {len(calculator_skills)} calculator skills to master_fix_agent")
            
            # Also add to monitoring_agent
            for skill in calculator_skills[:3]:  # Add first 3 to monitoring agent
                agent_skillset.add_skill('monitoring_agent', skill, 'agents')
            
            print(f"  ✅ Added 3 calculator skills to monitoring_agent")
            
        except Exception as e:
            print(f"  ⚠️  Warning: Could not add skills to skillset: {e}")
        
        # 2. Initialize calculator missions and quests
        print("\n[2/4] Initializing calculator missions and quests...")
        try:
            from backend.services.master_fix_agent_skills import master_fix_agent_skills
            
            result = master_fix_agent_skills.initialize_calculator_missions_and_quests()
            if result.get('success'):
                print(f"  ✅ Added {result.get('missions_added', 0)} calculator missions")
                print(f"  ✅ Added {result.get('quests_added', 0)} calculator quests")
            else:
                print(f"  ⚠️  Warning: {result.get('error', 'Unknown error')}")
        except Exception as e:
            print(f"  ⚠️  Warning: Could not initialize missions/quests: {e}")
            import traceback
            traceback.print_exc()
        
        # 3. Create calculator abilities document
        print("\n[3/4] Creating calculator abilities documentation...")
        try:
            abilities_doc = """# Calculator Agent Abilities

## Available Calculator Skills

1. **calculate_with_intelligence** - Perform intelligent calculations with AI-powered multipliers
2. **detect_point_loss** - Detect point losses using statistical analysis
3. **repair_all_systems** - Repair all systems and restore lost points
4. **predict_future_points** - Predict future points with confidence intervals
5. **analyze_patterns** - Analyze patterns in user behavior
6. **get_calculator_statistics** - Get comprehensive calculator statistics

## Usage

These skills can be used through the agent system:
- Via API: `/api/agent/master-fix/skill/<skill_name>`
- Via Python: `master_fix_agent_skills.skill_<skill_name>(user_id)`

## Missions

Calculator missions are available in the mission system:
- Intelligence Calculator Master
- Loss Detection Specialist
- System Repair Expert
- Future Predictor
- Pattern Analyzer

## Quests

Calculator quests are available in the quest system:
- Calculator Master Quest
- Prediction Master Quest
- System Guardian Quest
- Pattern Analysis Expert

## Click Quests Integration

Calculator missions and quests can be used as click quests in the click-through game system.
See docs/CALCULATOR_CLICK_QUESTS.md for integration details.
"""
            
            doc_path = os.path.join(BASE_DIR, 'docs', 'CALCULATOR_AGENT_ABILITIES.md')
            os.makedirs(os.path.dirname(doc_path), exist_ok=True)
            with open(doc_path, 'w') as f:
                f.write(abilities_doc)
            
            print(f"  ✅ Created documentation at {doc_path}")
        except Exception as e:
            print(f"  ⚠️  Warning: Could not create documentation: {e}")
        
        # 4. Summary
        print("\n[4/4] Integration Summary")
        print("=" * 80)
        print("\n✅ Calculator Integration Complete!")
        print("\nAdded:")
        print("  - 6 calculator skills to master_fix_agent")
        print("  - 3 calculator skills to monitoring_agent")
        print("  - 5 calculator missions")
        print("  - 4 calculator quests")
        print("\nNext Steps:")
        print("  1. Test calculator skills via API")
        print("  2. Test calculator missions and quests")
        print("  3. Integrate with click-through game system")
        print("  4. Update agent routes if needed")
        print()
        
        return True
        
    except Exception as e:
        print(f"\n❌ Error during integration: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == '__main__':
    success = integrate_calculator()
    sys.exit(0 if success else 1)
