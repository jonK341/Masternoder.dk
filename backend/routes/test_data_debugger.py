"""
Test Data Generation Debugger Tools
Provides UI and API for generating test users and agents one at a time
"""
from flask import Blueprint, jsonify, request, Response
from src.app import create_app
from src.db.models import db, UserProfile
from src.db.models_agent import Agent
from backend.services.unified_points_database import unified_points_db
import json
import uuid
import random

test_data_debugger_bp = Blueprint('test_data_debugger', __name__)

# Create app instance for context
app = create_app()

@test_data_debugger_bp.route('/api/debugger/test-data/generate-user', methods=['POST'])
@test_data_debugger_bp.route('/vidgenerator/api/debugger/test-data/generate-user', methods=['POST'])
def generate_single_user():
    """Generate a single test user"""
    try:
        data = request.get_json() or {}
        username = data.get('username', f'TestUser_{random.randint(1000, 9999)}')
        user_id = data.get('user_id', f'test_user_{random.randint(1000, 9999)}')
        
        with app.app_context():
            # Check if user already exists
            existing = UserProfile.query.filter_by(user_id=user_id).first()
            if existing:
                return jsonify({
                    'success': False,
                    'error': f'User with ID {user_id} already exists',
                    'user_id': user_id
                }), 400
            
            # Create user profile
            user = UserProfile(
                id=str(uuid.uuid4()),
                user_id=user_id,
                username=username,
                preferences=json.dumps({
                    'test_user': True,
                    'created_for_testing': True,
                    'created_via': 'debugger_tool'
                })
            )
            
            db.session.add(user)
            
            # Add random points
            points_data = {
                'xp_points': random.randint(0, 10000),
                'battle_points': random.randint(0, 5000),
                'activity_points': random.randint(0, 3000),
                'trophy_points': random.randint(0, 2000),
                'generation_points': random.randint(0, 4000),
                'chat_points': random.randint(0, 1500),
            }
            
            # Update unified points
            for point_type, value in points_data.items():
                unified_points_db.add_points(user_id, point_type, value, source='debugger_tool')
            
            db.session.commit()
            
            return jsonify({
                'success': True,
                'user': {
                    'id': user.id,
                    'user_id': user.user_id,
                    'username': user.username,
                    'points': points_data
                },
                'message': f'Test user {username} created successfully'
            }), 200
            
    except Exception as e:
        import traceback
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500

@test_data_debugger_bp.route('/api/debugger/test-data/generate-agent', methods=['POST'])
@test_data_debugger_bp.route('/vidgenerator/api/debugger/test-data/generate-agent', methods=['POST'])
def generate_single_agent():
    """Generate a single test agent"""
    try:
        data = request.get_json() or {}
        agent_name = data.get('agent_name', f'TestAgent_{random.randint(1000, 9999)}')
        user_id = data.get('user_id', f'test_user_{random.randint(0, 99)}')
        agent_type = data.get('agent_type', random.choice(['personal_assistant', 'creative_partner', 'strategist']))
        
        with app.app_context():
            # Check if agent already exists
            existing = Agent.query.filter_by(agent_name=agent_name, user_id=user_id).first()
            if existing:
                return jsonify({
                    'success': False,
                    'error': f'Agent {agent_name} for user {user_id} already exists'
                }), 400
            
            personality_traits = {
                'curiosity': round(random.uniform(0.5, 1.0), 2),
                'creativity': round(random.uniform(0.5, 1.0), 2),
                'efficiency': round(random.uniform(0.5, 1.0), 2)
            }
            
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
                personality_traits=json.dumps(personality_traits),
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
                    'created_via': 'debugger_tool'
                })
            )
            
            db.session.add(agent)
            db.session.commit()
            
            return jsonify({
                'success': True,
                'agent': {
                    'id': agent.id,
                    'user_id': agent.user_id,
                    'agent_name': agent.agent_name,
                    'agent_type': agent.agent_type,
                    'levels': {
                        'system_1': agent.level_system_1,
                        'system_2': agent.level_system_2,
                        'system_3': agent.level_system_3
                    },
                    'personality': personality_traits
                },
                'message': f'Test agent {agent_name} created successfully'
            }), 200
            
    except Exception as e:
        import traceback
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500

@test_data_debugger_bp.route('/api/debugger/test-data/stats', methods=['GET'])
@test_data_debugger_bp.route('/vidgenerator/api/debugger/test-data/stats', methods=['GET'])
def get_test_data_stats():
    """Get statistics about test data"""
    try:
        with app.app_context():
            test_users = UserProfile.query.filter(UserProfile.user_id.like('test_user%')).count()
            test_agents = Agent.query.filter(Agent.agent_name.like('TestAgent%')).count()
            
            return jsonify({
                'success': True,
                'stats': {
                    'test_users': test_users,
                    'test_agents': test_agents,
                    'total_test_data': test_users + test_agents
                }
            }), 200
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@test_data_debugger_bp.route('/api/debugger/test-data/list-users', methods=['GET'])
@test_data_debugger_bp.route('/vidgenerator/api/debugger/test-data/list-users', methods=['GET'])
def list_test_users():
    """List test users"""
    try:
        limit = int(request.args.get('limit', 50))
        with app.app_context():
            users = UserProfile.query.filter(UserProfile.user_id.like('test_user%')).limit(limit).all()
            
            return jsonify({
                'success': True,
                'users': [{
                    'id': u.id,
                    'user_id': u.user_id,
                    'username': u.username,
                    'created_at': u.created_at.isoformat() if u.created_at else None
                } for u in users],
                'count': len(users)
            }), 200
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@test_data_debugger_bp.route('/api/debugger/test-data/list-agents', methods=['GET'])
@test_data_debugger_bp.route('/vidgenerator/api/debugger/test-data/list-agents', methods=['GET'])
def list_test_agents():
    """List test agents"""
    try:
        limit = int(request.args.get('limit', 50))
        with app.app_context():
            agents = Agent.query.filter(Agent.agent_name.like('TestAgent%')).limit(limit).all()
            
            return jsonify({
                'success': True,
                'agents': [{
                    'id': a.id,
                    'user_id': a.user_id,
                    'agent_name': a.agent_name,
                    'agent_type': a.agent_type,
                    'created_at': a.created_at.isoformat() if a.created_at else None
                } for a in agents],
                'count': len(agents)
            }), 200
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
