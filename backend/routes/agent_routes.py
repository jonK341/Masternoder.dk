"""
Agent Routes - Agent system API endpoints
"""
from flask import Blueprint, request, jsonify
# Import agent system - optional, fallback to agent_manager
try:
    from backend.services.agent_system import agent_system
except ImportError:
    agent_system = None
    try:
        from backend.services.agent_manager import agent_manager
    except ImportError:
        agent_manager = None

# Import rate limiter - optional
try:
    from src.utils.rate_limiter import rate_limit
except ImportError:
    # Fallback decorator that does nothing
    def rate_limit():
        def decorator(f):
            return f
        return decorator

import sys
import uuid

agent_bp = Blueprint('agent', __name__)

@agent_bp.route('/api/agent/create', methods=['POST'])
@agent_bp.route('/vidgenerator/api/agent/create', methods=['POST'])
@rate_limit()
def create_agent():
    """Create a new agent"""
    try:
        data = request.get_json() or {}
        user_id = data.get('user_id', 'default_user')
        agent_name = data.get('agent_name', 'My Agent')
        agent_type = data.get('agent_type', 'personal_assistant')
        
        agent = agent_system.create_agent(user_id, agent_name, agent_type)
        return jsonify({
            'success': True,
            'agent': agent
        }), 200
    except Exception as e:
        print(f"[Agent] Error creating agent: {e}", file=sys.stderr, flush=True)
        import traceback
        traceback.print_exc(file=sys.stderr)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@agent_bp.route('/api/agent/get', methods=['GET'])
@agent_bp.route('/vidgenerator/api/agent/get', methods=['GET'])
@rate_limit()
def get_agent():
    """Get agent data"""
    try:
        agent_id = request.args.get('agent_id')
        user_id = request.args.get('user_id')
        
        if agent_id:
            agent = agent_system.get_agent(agent_id)
            if agent:
                return jsonify({
                    'success': True,
                    'agent': agent
                }), 200
            else:
                return jsonify({
                    'success': False,
                    'error': 'Agent not found'
                }), 404
        elif user_id:
            agents = agent_system.get_user_agents(user_id)
            return jsonify({
                'success': True,
                'agents': agents
            }), 200
        else:
            return jsonify({
                'success': False,
                'error': 'agent_id or user_id required'
            }), 400
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@agent_bp.route('/api/agent/get-all', methods=['GET'])
@agent_bp.route('/api/agent/get_all', methods=['GET'])
@agent_bp.route('/api/agent/all', methods=['GET'])
@agent_bp.route('/vidgenerator/api/agent/get-all', methods=['GET'])
@agent_bp.route('/vidgenerator/api/agent/get_all', methods=['GET'])
@agent_bp.route('/vidgenerator/api/agent/all', methods=['GET'])
@rate_limit()
def get_all_agents():
    """Get all agents for a user"""
    try:
        user_id = request.args.get('user_id', 'default_user')
        
        # Try agent_system first, fallback to agent_manager
        if agent_system:
            agents = agent_system.get_user_agents(user_id)
        elif agent_manager and hasattr(agent_manager, 'get_all_agents_for_user'):
            agents = agent_manager.get_all_agents_for_user(user_id)
        else:
            return jsonify({
                'success': False,
                'error': 'Agent system not available',
                'agents': []
            }), 200
        
        agents = agents if agents else []
        # Ensure response has success and agents array
        if isinstance(agents, dict):
            result = agents
            if 'agents' not in result:
                result['agents'] = []
        else:
            result = {
                'success': True,
                'agents': agents if isinstance(agents, list) else []
            }
        return jsonify(result), 200
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Error getting all agents: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e),
            'agents': []
        }), 200  # Return 200 with empty data instead of 500

@agent_bp.route('/api/agent/copy-behavior', methods=['POST'])
@agent_bp.route('/vidgenerator/api/agent/copy-behavior', methods=['POST'])
@rate_limit()
def copy_user_behavior():
    """Copy user behavior to agent"""
    try:
        data = request.get_json() or {}
        agent_id = data.get('agent_id')
        user_id = data.get('user_id', 'default_user')
        
        if not agent_id:
            return jsonify({
                'success': False,
                'error': 'agent_id required'
            }), 400
        
        behavior = agent_system.copy_user_behavior(agent_id, user_id)
        return jsonify({
            'success': True,
            'behavior_pattern': behavior
        }), 200
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@agent_bp.route('/api/agent/calendar', methods=['GET'])
@agent_bp.route('/vidgenerator/api/agent/calendar', methods=['GET'])
@rate_limit()
def get_calendar():
    """Get giga calendar for agent"""
    try:
        agent_id = request.args.get('agent_id')
        days = int(request.args.get('days', 30))
        
        if not agent_id:
            return jsonify({
                'success': False,
                'error': 'agent_id required'
            }), 400
        
        calendar = agent_system.get_giga_calendar(agent_id, days=days)
        return jsonify({
            'success': True,
            'calendar': calendar
        }), 200
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@agent_bp.route('/api/agent/video-opinion', methods=['POST'])
@agent_bp.route('/vidgenerator/api/agent/video-opinion', methods=['POST'])
@rate_limit()
def get_video_opinion():
    """Get agent opinion on video generation"""
    try:
        data = request.get_json() or {}
        agent_id = data.get('agent_id')
        video_id = data.get('video_id')
        video_data = data.get('video_data', {})
        
        if not agent_id or not video_id:
            return jsonify({
                'success': False,
                'error': 'agent_id and video_id required'
            }), 400
        
        # Generate agent opinion
        opinion = agent_system.generate_video_opinion(agent_id, video_id, video_data)
        return jsonify({
            'success': True,
            'opinion': opinion
        }), 200
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@agent_bp.route('/api/agent/top-lists', methods=['GET'])
@agent_bp.route('/vidgenerator/api/agent/top-lists', methods=['GET'])
@rate_limit()
def get_top_lists():
    """Get Top100/Top50/Top25/Top10 lists"""
    try:
        agent_id = request.args.get('agent_id')
        
        if not agent_id:
            return jsonify({
                'success': False,
                'error': 'agent_id required'
            }), 400
        
        agent = agent_system.get_agent(agent_id)
        if not agent:
            return jsonify({
                'success': False,
                'error': 'Agent not found'
            }), 404
        
        return jsonify({
            'success': True,
            'top100_tasks': agent.get('top100_tasks', []),
            'top50_skills': agent.get('top50_skills', []),
            'top25_missions': agent.get('top25_missions', []),
            'top10_achievements': agent.get('top10_achievements', [])
        }), 200
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@agent_bp.route('/api/agent/gps', methods=['POST'])
@agent_bp.route('/vidgenerator/api/agent/gps', methods=['POST'])
@rate_limit()
def update_gps_location():
    """Update agent GPS location"""
    try:
        data = request.get_json() or {}
        agent_id = data.get('agent_id')
        location = data.get('location')  # GPS coordinates or location name
        
        if not agent_id or not location:
            return jsonify({
                'success': False,
                'error': 'agent_id and location required'
            }), 400
        
        result = agent_system.update_gps_location(agent_id, location)
        return jsonify({
            'success': True,
            'location': result
        }), 200
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@agent_bp.route('/api/agent/coordinate', methods=['POST'])
@agent_bp.route('/vidgenerator/api/agent/coordinate', methods=['POST'])
@rate_limit()
def coordinate_agent():
    """Coordinate agent with service worker for production"""
    try:
        data = request.get_json() or {}
        agent_id = data.get('agent_id')
        video_id = data.get('video_id')
        production_data = data.get('production_data', {})
        
        if not agent_id or not video_id:
            return jsonify({
                'success': False,
                'error': 'agent_id and video_id required'
            }), 400
        
        coordination = agent_system.coordinate_with_service_worker(agent_id, video_id, production_data)
        return jsonify({
            'success': True,
            'coordination': coordination
        }), 200
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@agent_bp.route('/api/agent/award-xp', methods=['POST'])
@agent_bp.route('/vidgenerator/api/agent/award-xp', methods=['POST'])
@rate_limit()
def award_agent_xp():
    """Award XP to agent"""
    try:
        data = request.get_json() or {}
        agent_id = data.get('agent_id')
        system = data.get('system', 'system_1')
        xp_amount = int(data.get('xp_amount', 0))
        
        if not agent_id:
            return jsonify({
                'success': False,
                'error': 'agent_id required'
            }), 400
        
        result = agent_system.award_xp(agent_id, system, xp_amount)
        return jsonify(result), 200 if result.get('success') else 400
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@agent_bp.route('/api/agent/save-memory', methods=['POST'])
@agent_bp.route('/vidgenerator/api/agent/save-memory', methods=['POST'])
@rate_limit()
def save_visual_memory():
    """Save visual memory for agent"""
    try:
        data = request.get_json() or {}
        agent_id = data.get('agent_id')
        memory_type = data.get('memory_type', 'general')
        memory_data = data.get('memory_data', {})
        
        if not agent_id:
            return jsonify({
                'success': False,
                'error': 'agent_id required'
            }), 400
        
        result = agent_system.save_visual_memory(agent_id, memory_type, memory_data)
        return jsonify(result), 200 if result.get('success') else 400
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@agent_bp.route('/api/agent/learn-from-memory', methods=['POST'])
@agent_bp.route('/vidgenerator/api/agent/learn-from-memory', methods=['POST'])
@rate_limit()
def learn_from_memory():
    """Agent learns from visual memory"""
    try:
        data = request.get_json() or {}
        agent_id = data.get('agent_id')
        memory_id = data.get('memory_id')
        
        if not agent_id:
            return jsonify({
                'success': False,
                'error': 'agent_id required'
            }), 400
        
        result = agent_system.learn_from_memory(agent_id, memory_id)
        return jsonify(result), 200 if result.get('success') else 400
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@agent_bp.route('/api/agent/predict-behavior', methods=['GET', 'POST'])
@agent_bp.route('/vidgenerator/api/agent/predict-behavior', methods=['GET', 'POST'])
@rate_limit()
def predict_behavior():
    """Predict user behavior based on agent analysis"""
    try:
        if request.method == 'GET':
            agent_id = request.args.get('agent_id')
            time_horizon = request.args.get('time_horizon', '24h')
        else:
            data = request.get_json() or {}
            agent_id = data.get('agent_id')
            time_horizon = data.get('time_horizon', '24h')
        
        if not agent_id:
            return jsonify({
                'success': False,
                'error': 'agent_id required'
            }), 400
        
        result = agent_system.predict_user_behavior(agent_id, time_horizon)
        return jsonify(result), 200 if result.get('success') else 400
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@agent_bp.route('/api/agent/generate-tasks', methods=['POST'])
@agent_bp.route('/vidgenerator/api/agent/generate-tasks', methods=['POST'])
@rate_limit()
def generate_smart_tasks():
    """Auto-generate smart tasks"""
    try:
        data = request.get_json() or {}
        agent_id = data.get('agent_id')
        count = int(data.get('count', 10))
        
        if not agent_id:
            return jsonify({
                'success': False,
                'error': 'agent_id required'
            }), 400
        
        result = agent_system.generate_smart_tasks(agent_id, count)
        return jsonify(result), 200 if result.get('success') else 400
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@agent_bp.route('/api/agent/recommendations', methods=['GET', 'POST'])
@agent_bp.route('/vidgenerator/api/agent/recommendations', methods=['GET', 'POST'])
@rate_limit()
def get_recommendations():
    """Get smart recommendations"""
    try:
        if request.method == 'GET':
            agent_id = request.args.get('agent_id')
            user_id = request.args.get('user_id', 'default_user')
            context = request.args.get('context', 'general')
        else:
            data = request.get_json() or {}
            agent_id = data.get('agent_id')
            user_id = data.get('user_id', 'default_user')
            context = data.get('context', 'general')
        
        # If no agent_id provided, try to get user's agents and use first one
        if not agent_id:
            try:
                user_agents = agent_system.get_user_agents(user_id)
                if user_agents and len(user_agents) > 0:
                    # Use first agent if available
                    if isinstance(user_agents, list) and len(user_agents) > 0:
                        agent_id = user_agents[0].get('agent_id') if isinstance(user_agents[0], dict) else None
                    elif isinstance(user_agents, dict) and 'agents' in user_agents and len(user_agents['agents']) > 0:
                        agent_id = user_agents['agents'][0].get('agent_id') if isinstance(user_agents['agents'][0], dict) else None
            except:
                pass
        
        if not agent_id:
            # Return empty recommendations if no agent found
            return jsonify({
                'success': True,
                'recommendations': [],
                'message': 'No agent found for user'
            }), 200
        
        result = agent_system.get_smart_recommendations(agent_id, context)
        # Ensure response has success and recommendations array
        if isinstance(result, dict):
            if 'recommendations' not in result:
                result['recommendations'] = []
        else:
            result = {
                'success': True,
                'recommendations': result if isinstance(result, list) else []
            }
        return jsonify(result), 200 if result.get('success', True) else 200
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Error getting recommendations: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e),
            'recommendations': []
        }), 200  # Return 200 with empty data instead of 500
    """Get smart recommendations"""
    try:
        if request.method == 'GET':
            agent_id = request.args.get('agent_id')
            context = request.args.get('context', 'general')
        else:
            data = request.get_json() or {}
            agent_id = data.get('agent_id')
            context = data.get('context', 'general')
        
        if not agent_id:
            return jsonify({
                'success': False,
                'error': 'agent_id required'
            }), 400
        
        result = agent_system.get_smart_recommendations(agent_id, context)
        return jsonify(result), 200 if result.get('success') else 400
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@agent_bp.route('/api/agent/unified-points', methods=['GET'])
@agent_bp.route('/vidgenerator/api/agent/unified-points', methods=['GET'])
@rate_limit()
def get_agent_with_points():
    """Get agent data with unified points integration"""
    try:
        agent_id = request.args.get('agent_id')
        
        if not agent_id:
            return jsonify({
                'success': False,
                'error': 'agent_id required'
            }), 400
        
        result = agent_system.get_agent_with_unified_points(agent_id)
        return jsonify(result), 200 if 'error' not in result else 404
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@agent_bp.route('/api/agent/recall-memory', methods=['GET', 'POST'])
@agent_bp.route('/vidgenerator/api/agent/recall-memory', methods=['GET', 'POST'])
@rate_limit()
def recall_memory():
    """Recall visual memory by ID or category"""
    try:
        if request.method == 'GET':
            agent_id = request.args.get('agent_id')
            memory_id = request.args.get('memory_id')
            category = request.args.get('category')
        else:
            data = request.get_json() or {}
            agent_id = data.get('agent_id')
            memory_id = data.get('memory_id')
            category = data.get('category')
        
        if not agent_id:
            return jsonify({
                'success': False,
                'error': 'agent_id required'
            }), 400
        
        result = agent_system.recall_memory(agent_id, memory_id, category)
        return jsonify(result), 200 if result.get('success') else 400
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@agent_bp.route('/api/agent/apply-memory-decay', methods=['POST'])
@agent_bp.route('/vidgenerator/api/agent/apply-memory-decay', methods=['POST'])
@rate_limit()
def apply_memory_decay():
    """Apply memory decay to agent memories"""
    try:
        data = request.get_json() or {}
        agent_id = data.get('agent_id')
        
        if not agent_id:
            return jsonify({
                'success': False,
                'error': 'agent_id required'
            }), 400
        
        result = agent_system.apply_memory_decay(agent_id)
        return jsonify(result), 200
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
