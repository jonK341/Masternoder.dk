"""
Script to generate test agents for performance testing
"""
import sys
import os
from pathlib import Path
import json
import random
import uuid

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

def generate_test_agents(count=100, user_id_prefix='test_user'):
    """Generate test agents with random stats"""
    print(f"Generating {count} test agents...")
    
    agent_types = ['personal_assistant', 'creative_partner', 'strategist', 'team_manager', 'secretary']
    personality_traits_list = [
        {'curiosity': 0.8, 'creativity': 0.7, 'efficiency': 0.6},
        {'analytical': 0.9, 'organized': 0.8, 'detail_oriented': 0.7},
        {'innovative': 0.8, 'collaborative': 0.7, 'adaptive': 0.6},
        {'leadership': 0.9, 'strategic': 0.8, 'decisive': 0.7},
        {'supportive': 0.8, 'reliable': 0.9, 'proactive': 0.7}
    ]
    
    try:
        from src.app import create_app
        from src.db.models_agent import Agent
        
        # Create Flask app and use application context
        app = create_app()
        
        with app.app_context():
            from src.db.models import db
            
            created = 0
            for i in range(count):
                agent_name = f'TestAgent{i}'
                user_id = f'{user_id_prefix}_{i % 100}'  # Distribute across first 100 users
                
                # Check if agent already exists (by name and user_id)
                existing = Agent.query.filter_by(agent_name=agent_name, user_id=user_id).first()
                if existing:
                    continue
                
                # Random agent type
                agent_type = random.choice(agent_types)
                personality = random.choice(personality_traits_list)
                
                # Create agent
                agent = Agent(
                    id=str(uuid.uuid4()),
                    user_id=user_id,
                    agent_name=agent_name,
                    agent_type=agent_type,
                    level_system_1=random.randint(1, 10),
                    level_system_2=random.randint(1, 10),
                    level_system_3=random.randint(1, 10),
                    total_tasks_completed=random.randint(0, 500),
                    total_skills_learned=random.randint(0, 50),
                    total_missions_accomplished=random.randint(0, 25),
                    total_points_earned=random.randint(0, 10000),
                    behavior_pattern=json.dumps({}),
                    learning_rate=round(random.uniform(0.1, 0.5), 2),
                    personality_traits=json.dumps(personality),
                    current_location=None,
                    location_history=json.dumps([]),
                    navigation_enabled=True,
                    calendar_level=random.randint(1, 10),
                    calendar_data=json.dumps({}),
                    top100_tasks=json.dumps([]),
                    top50_skills=json.dumps([]),
                    top25_missions=json.dumps([]),
                    top10_achievements=json.dumps([]),
                    unified_points=json.dumps({}),
                    effects=json.dumps({}),
                    active_effects=json.dumps([]),
                    video_generation_count=random.randint(0, 100),
                    video_generation_opinions=json.dumps([]),
                    service_worker_coordination=json.dumps({}),
                    metadata=json.dumps({
                        'test_agent': True,
                        'created_for_testing': True,
                        'batch_number': i // 100
                    })
                )
                
                db.session.add(agent)
                created += 1
                
                if (i + 1) % 100 == 0:
                    print(f"Created {i + 1}/{count} agents...")
                    db.session.commit()
            
            db.session.commit()
            print(f"\n✅ Created {created} test agents")
            return created
            
    except Exception as e:
        print(f"❌ Error generating test agents: {e}")
        import traceback
        traceback.print_exc()
        return 0


if __name__ == '__main__':
    count = int(sys.argv[1]) if len(sys.argv) > 1 else 100
    user_id_prefix = sys.argv[2] if len(sys.argv) > 2 else 'test_user'
    generate_test_agents(count, user_id_prefix)
