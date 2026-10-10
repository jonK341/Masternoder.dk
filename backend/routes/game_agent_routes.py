"""
Game Agent API Routes
API endpoints for automated game agent
"""
from flask import Blueprint, request, jsonify
from backend.services.game_agent import get_game_agent, GameAgent
from src.utils.rate_limiter import rate_limit
import sys
import uuid

game_agent_bp = Blueprint('game_agent', __name__, url_prefix='')

@game_agent_bp.route('/api/agent/create', methods=['POST'])
@game_agent_bp.route('/vidgenerator/api/agent/create', methods=['POST'])
@rate_limit()
def create_agent():
    """Create a new game agent instance"""
    try:
        data = request.get_json() or {}
        agent_id = data.get('agent_id') or f"agent_{uuid.uuid4().hex[:12]}"
        base_url = data.get('base_url', 'https://masternoder.dk/vidgenerator')
        
        agent = GameAgent(agent_id=agent_id, base_url=base_url)
        
        return jsonify({
            'success': True,
            'agent_id': agent.agent_id,
            'stats': agent.get_stats()
        }), 200
    except Exception as e:
        print(f"[GameAgent] Error creating agent: {e}", file=sys.stderr, flush=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 200

@game_agent_bp.route('/api/agent/play', methods=['POST'])
@game_agent_bp.route('/vidgenerator/api/agent/play', methods=['POST'])
@rate_limit()
def play_game():
    """Start automated game session"""
    try:
        data = request.get_json() or {}
        agent_id = data.get('agent_id')
        user_id = data.get('user_id', 'anonymous')
        duration_minutes = int(data.get('duration_minutes', 5))
        actions_per_minute = int(data.get('actions_per_minute', 3))
        
        agent = get_game_agent(agent_id)
        
        # Run session in background (for long sessions, consider using threading/tasks)
        session_result = agent.play_game_session(
            user_id=user_id,
            duration_minutes=duration_minutes,
            actions_per_minute=actions_per_minute
        )
        
        return jsonify(session_result), 200
    except Exception as e:
        print(f"[GameAgent] Error playing game: {e}", file=sys.stderr, flush=True)
        import traceback
        traceback.print_exc(file=sys.stderr)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 200

@game_agent_bp.route('/api/agent/battle', methods=['POST'])
@game_agent_bp.route('/vidgenerator/api/agent/battle', methods=['POST'])
@rate_limit()
def create_battle():
    """Create and execute a battle"""
    try:
        data = request.get_json() or {}
        agent_id = data.get('agent_id')
        user_id = data.get('user_id', 'anonymous')
        battle_type = data.get('battle_type', 'quick')
        opponent_type = data.get('opponent_type', 'ai')
        difficulty = data.get('difficulty', 'balanced')
        
        agent = get_game_agent(agent_id)
        
        # Create battle
        battle_result = agent.create_battle(user_id, battle_type, opponent_type, difficulty)
        
        if battle_result.get('success'):
            battle_id = battle_result['battle_id']
            # Execute battle
            import time
            time.sleep(1)  # Short delay
            execute_result = agent.execute_battle(battle_id, user_id, won=None)
            
            return jsonify({
                'success': True,
                'battle_created': battle_result,
                'battle_executed': execute_result
            }), 200
        else:
            return jsonify(battle_result), 200
            
    except Exception as e:
        print(f"[GameAgent] Error creating battle: {e}", file=sys.stderr, flush=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 200

@game_agent_bp.route('/api/agent/test-url', methods=['POST'])
@game_agent_bp.route('/vidgenerator/api/agent/test-url', methods=['POST'])
@rate_limit()
def test_url():
    """Test a URL/endpoint"""
    try:
        data = request.get_json() or {}
        agent_id = data.get('agent_id')
        url = data.get('url')
        method = data.get('method', 'GET')
        test_data = data.get('data')
        timeout = int(data.get('timeout', 10))
        
        if not url:
            return jsonify({
                'success': False,
                'error': 'url is required'
            }), 200
        
        agent = get_game_agent(agent_id)
        result = agent.test_url(url, method=method, data=test_data, timeout=timeout)
        
        return jsonify(result), 200
    except Exception as e:
        print(f"[GameAgent] Error testing URL: {e}", file=sys.stderr, flush=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 200

@game_agent_bp.route('/api/agent/test-urls', methods=['POST'])
@game_agent_bp.route('/vidgenerator/api/agent/test-urls', methods=['POST'])
@rate_limit()
def test_urls():
    """Test multiple URLs"""
    try:
        data = request.get_json() or {}
        agent_id = data.get('agent_id')
        urls = data.get('urls', [])
        method = data.get('method', 'GET')
        
        if not urls:
            return jsonify({
                'success': False,
                'error': 'urls array is required'
            }), 200
        
        agent = get_game_agent(agent_id)
        result = agent.test_multiple_urls(urls, method=method)
        
        return jsonify(result), 200
    except Exception as e:
        print(f"[GameAgent] Error testing URLs: {e}", file=sys.stderr, flush=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 200

@game_agent_bp.route('/api/agent/earn-points', methods=['POST'])
@game_agent_bp.route('/vidgenerator/api/agent/earn-points', methods=['POST'])
@rate_limit()
def earn_points():
    """Earn points in a category"""
    try:
        data = request.get_json() or {}
        agent_id = data.get('agent_id')
        user_id = data.get('user_id', 'anonymous')
        category = data.get('category', 'CORE')
        point_type = data.get('point_type', 'xp')
        amount = int(data.get('amount', 10))
        source = data.get('source', 'agent')
        
        agent = get_game_agent(agent_id)
        result = agent.earn_points(user_id, category, point_type, amount, source)
        
        return jsonify(result), 200
    except Exception as e:
        print(f"[GameAgent] Error earning points: {e}", file=sys.stderr, flush=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 200

@game_agent_bp.route('/api/agent/stats', methods=['GET'])
@game_agent_bp.route('/vidgenerator/api/agent/stats', methods=['GET'])
def get_agent_stats():
    """Get agent statistics"""
    try:
        agent_id = request.args.get('agent_id')
        agent = get_game_agent(agent_id)
        stats = agent.get_stats()
        
        return jsonify({
            'success': True,
            'stats': stats
        }), 200
    except Exception as e:
        print(f"[GameAgent] Error getting stats: {e}", file=sys.stderr, flush=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 200

@game_agent_bp.route('/api/agent/reset', methods=['POST'])
@game_agent_bp.route('/vidgenerator/api/agent/reset', methods=['POST'])
@rate_limit()
def reset_agent():
    """Reset agent statistics"""
    try:
        data = request.get_json() or {}
        agent_id = data.get('agent_id')
        agent = get_game_agent(agent_id)
        agent.reset_stats()
        
        return jsonify({
            'success': True,
            'message': 'Agent stats reset',
            'stats': agent.get_stats()
        }), 200
    except Exception as e:
        print(f"[GameAgent] Error resetting agent: {e}", file=sys.stderr, flush=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 200
