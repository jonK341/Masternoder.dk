"""
Enhanced Game Agent API Routes
3 Agent Abilities with Gaming Experience Tracking
"""
from flask import Blueprint, request, jsonify
from backend.services.enhanced_game_agent import EnhancedGameAgent, active_enhanced_agents
from src.utils.rate_limiter import rate_limit
import sys

enhanced_agent_bp = Blueprint('enhanced_agent', __name__)


@enhanced_agent_bp.route('/api/agent/enhanced/create', methods=['POST'])
@enhanced_agent_bp.route('/vidgenerator/api/agent/enhanced/create', methods=['POST'])
@rate_limit()
def create_enhanced_agent():
    """Create an enhanced game agent"""
    try:
        data = request.get_json() or {}
        agent_id = data.get('agent_id')
        user_id = data.get('user_id')
        base_url = data.get('base_url', 'https://masternoder.dk/vidgenerator')
        
        agent = EnhancedGameAgent(agent_id=agent_id, base_url=base_url, user_id=user_id)
        active_enhanced_agents[agent.agent_id] = agent
        
        return jsonify({
            'success': True,
            'agent_id': agent.agent_id,
            'user_id': agent.user_id,
            'message': f'Enhanced agent {agent.agent_id} created'
        }), 200
    except Exception as e:
        print(f"[Enhanced Agent Create] Error: {e}", file=sys.stderr, flush=True)
        return jsonify({'success': False, 'error': str(e)}), 200


@enhanced_agent_bp.route('/api/agent/enhanced/<agent_id>/automated-gameplay', methods=['POST'])
@enhanced_agent_bp.route('/vidgenerator/api/agent/enhanced/<agent_id>/automated-gameplay', methods=['POST'])
@rate_limit()
def automated_gameplay(agent_id: str):
    """Ability 1: Automated Gameplay"""
    try:
        agent = active_enhanced_agents.get(agent_id)
        if not agent:
            return jsonify({'success': False, 'error': 'Agent not found'}), 200
        
        data = request.get_json() or {}
        duration_minutes = int(data.get('duration_minutes', 10))
        action_interval = int(data.get('action_interval', 30))
        
        result = agent.automated_gameplay(duration_minutes, action_interval)
        return jsonify(result), 200
    except Exception as e:
        print(f"[Enhanced Agent Automated Gameplay] Error: {e}", file=sys.stderr, flush=True)
        return jsonify({'success': False, 'error': str(e)}), 200


@enhanced_agent_bp.route('/api/agent/enhanced/<agent_id>/battle-automation', methods=['POST'])
@enhanced_agent_bp.route('/vidgenerator/api/agent/enhanced/<agent_id>/battle-automation', methods=['POST'])
@rate_limit()
def battle_automation(agent_id: str):
    """Ability 2: Battle Automation"""
    try:
        agent = active_enhanced_agents.get(agent_id)
        if not agent:
            return jsonify({'success': False, 'error': 'Agent not found'}), 200
        
        data = request.get_json() or {}
        num_battles = int(data.get('num_battles', 10))
        battle_type = data.get('battle_type', 'quick')
        difficulty = data.get('difficulty', 'balanced')
        
        result = agent.battle_automation(num_battles, battle_type, difficulty)
        return jsonify(result), 200
    except Exception as e:
        print(f"[Enhanced Agent Battle Automation] Error: {e}", file=sys.stderr, flush=True)
        return jsonify({'success': False, 'error': str(e)}), 200


@enhanced_agent_bp.route('/api/agent/enhanced/<agent_id>/content-generation', methods=['POST'])
@enhanced_agent_bp.route('/vidgenerator/api/agent/enhanced/<agent_id>/content-generation', methods=['POST'])
@rate_limit()
def content_generation(agent_id: str):
    """Ability 3: Content Generation"""
    try:
        agent = active_enhanced_agents.get(agent_id)
        if not agent:
            return jsonify({'success': False, 'error': 'Agent not found'}), 200
        
        data = request.get_json() or {}
        num_generations = int(data.get('num_generations', 5))
        generation_type = data.get('generation_type', 'clip')
        
        result = agent.content_generation(num_generations, generation_type)
        return jsonify(result), 200
    except Exception as e:
        print(f"[Enhanced Agent Content Generation] Error: {e}", file=sys.stderr, flush=True)
        return jsonify({'success': False, 'error': str(e)}), 200


@enhanced_agent_bp.route('/api/agent/enhanced/<agent_id>/stats', methods=['GET'])
@enhanced_agent_bp.route('/vidgenerator/api/agent/enhanced/<agent_id>/stats', methods=['GET'])
@rate_limit()
def get_agent_stats(agent_id: str):
    """Get enhanced agent stats"""
    try:
        agent = active_enhanced_agents.get(agent_id)
        if not agent:
            return jsonify({'success': False, 'error': 'Agent not found'}), 200
        
        stats = agent.get_stats()
        return jsonify({'success': True, 'stats': stats}), 200
    except Exception as e:
        print(f"[Enhanced Agent Stats] Error: {e}", file=sys.stderr, flush=True)
        return jsonify({'success': False, 'error': str(e)}), 200


@enhanced_agent_bp.route('/api/agent/enhanced/<agent_id>/reset', methods=['POST'])
@enhanced_agent_bp.route('/vidgenerator/api/agent/enhanced/<agent_id>/reset', methods=['POST'])
@rate_limit()
def reset_agent_stats(agent_id: str):
    """Reset enhanced agent stats"""
    try:
        agent = active_enhanced_agents.get(agent_id)
        if not agent:
            return jsonify({'success': False, 'error': 'Agent not found'}), 200
        
        agent.reset_stats()
        return jsonify({'success': True, 'message': f'Agent {agent_id} stats reset'}), 200
    except Exception as e:
        print(f"[Enhanced Agent Reset] Error: {e}", file=sys.stderr, flush=True)
        return jsonify({'success': False, 'error': str(e)}), 200
