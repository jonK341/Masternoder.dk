"""
Quick Battle API Routes
Enhanced quick battle with intelligence, counters, and points
"""
from flask import Blueprint, request, jsonify
from backend.services.quick_battle_system import quick_battle
import sys

quick_battle_bp = Blueprint('quick_battle', __name__, url_prefix='')


@quick_battle_bp.route('/api/quick-battle/create', methods=['POST'], strict_slashes=False)
def create_quick_battle():
    """Create a new quick battle"""
    try:
        data = request.get_json() or {}
        user_id = data.get('user_id', 'anonymous')
        difficulty = data.get('difficulty', 'balanced')
        opponent_type = data.get('opponent_type', 'ai')
        
        result = quick_battle.create_quick_battle(user_id, difficulty, opponent_type)
        
        return jsonify({
            'success': True,
            'result': result
        }), 200
    except Exception as e:
        print(f"[QuickBattle] Error: {e}", file=sys.stderr, flush=True)
        import traceback
        traceback.print_exc(file=sys.stderr)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@quick_battle_bp.route('/api/quick-battle/complete', methods=['GET', 'POST'], strict_slashes=False)
@quick_battle_bp.route('/vidgenerator/api/quick-battle/complete', methods=['GET', 'POST'])
def complete_quick_battle():
    """Complete a quick battle and award points with detailed action counting"""
    try:
        # Handle GET requests gracefully
        if request.method == 'GET':
            return jsonify({
                'success': False,
                'error': 'POST request required. Send JSON with: battle_id, user_id, won, duration (optional), moves (optional), action_counts (optional)'
            }), 200
        
        data = request.get_json() or {}
        battle_id = data.get('battle_id')
        user_id = data.get('user_id', 'anonymous')
        won = data.get('won', False)
        duration = data.get('duration', 0.0)
        moves = data.get('moves', 0)
        action_counts = data.get('action_counts', {})  # {click: 10, attack: 5, defense: 3, ability: 2}
        
        if not battle_id:
            return jsonify({'success': False, 'error': 'battle_id required'}), 200
        
        # If action_counts not provided but moves is, create action_counts from moves
        if not action_counts and moves > 0:
            action_counts = {
                'click': moves,
                'attack': moves // 2,
                'defense': moves // 3,
                'ability': moves // 4
            }
        
        # Update battle with action counts before completion
        if battle_id in quick_battle.battles:
            quick_battle.battles[battle_id]['action_counts'] = action_counts
        
        result = quick_battle.complete_battle(battle_id, user_id, won, duration, moves)
        
        return jsonify({
            'success': True,
            'result': result
        }), 200
    except Exception as e:
        print(f"[QuickBattle] Error: {e}", file=sys.stderr, flush=True)
        import traceback
        traceback.print_exc(file=sys.stderr)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@quick_battle_bp.route('/api/quick-battle/track-action', methods=['POST'], strict_slashes=False)
@quick_battle_bp.route('/vidgenerator/api/quick-battle/track-action', methods=['POST'])
def track_battle_action():
    """Track a single action during battle (click, attack, defense, ability)"""
    try:
        data = request.get_json() or {}
        battle_id = data.get('battle_id')
        user_id = data.get('user_id', 'anonymous')
        action_type = data.get('action_type', 'click')  # click, attack, defense, ability, special
        
        if not battle_id:
            return jsonify({'success': False, 'error': 'battle_id required'}), 200
        
        # Find battle and update action counts
        if battle_id in quick_battle.battles:
            battle = quick_battle.battles[battle_id]
            if 'action_counts' not in battle:
                battle['action_counts'] = {}
            battle['action_counts'][action_type] = battle['action_counts'].get(action_type, 0) + 1
            
            return jsonify({
                'success': True,
                'action_type': action_type,
                'action_count': battle['action_counts'][action_type],
                'total_actions': sum(battle['action_counts'].values())
            }), 200
        else:
            return jsonify({
                'success': False,
                'error': 'Battle not found'
            }), 200
    except Exception as e:
        print(f"[QuickBattle] Error tracking action: {e}", file=sys.stderr, flush=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@quick_battle_bp.route('/api/quick-battle/counter', methods=['GET'], strict_slashes=False)
def get_battle_counter():
    """Get battle counter for user"""
    try:
        user_id = request.args.get('user_id', 'anonymous')
        counter = quick_battle.get_battle_counter(user_id)
        
        return jsonify({
            'success': True,
            'counter': counter
        }), 200
    except Exception as e:
        print(f"[QuickBattle] Error: {e}", file=sys.stderr, flush=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@quick_battle_bp.route('/api/quick-battle/streak', methods=['GET'], strict_slashes=False)
def get_battle_streak():
    """Get battle streak for user"""
    try:
        user_id = request.args.get('user_id', 'anonymous')
        streak = quick_battle.get_user_streak(user_id)
        
        return jsonify({
            'success': True,
            'streak': streak
        }), 200
    except Exception as e:
        print(f"[QuickBattle] Error: {e}", file=sys.stderr, flush=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@quick_battle_bp.route('/api/quick-battle/stats', methods=['GET'], strict_slashes=False)
def get_battle_stats():
    """Get comprehensive battle stats"""
    try:
        user_id = request.args.get('user_id', 'anonymous')
        stats = quick_battle.get_user_battle_stats(user_id)
        
        return jsonify({
            'success': True,
            'stats': stats
        }), 200
    except Exception as e:
        print(f"[QuickBattle] Error: {e}", file=sys.stderr, flush=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@quick_battle_bp.route('/api/quick-battle/intelligence', methods=['GET'], strict_slashes=False)
def get_intelligence():
    """Get quick battle intelligence"""
    try:
        user_id = request.args.get('user_id', 'anonymous')
        intelligence = quick_battle.get_quick_battle_intelligence(user_id)
        
        return jsonify({
            'success': True,
            'intelligence': intelligence
        }), 200
    except Exception as e:
        print(f"[QuickBattle] Error: {e}", file=sys.stderr, flush=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@quick_battle_bp.route('/api/quick-battle/join-queue', methods=['POST'], strict_slashes=False)
@quick_battle_bp.route('/vidgenerator/api/quick-battle/join-queue', methods=['POST'])
def join_matchmaking_queue():
    """Join matchmaking queue to find opponent"""
    try:
        data = request.get_json() or {}
        user_id = data.get('user_id', 'anonymous')
        difficulty = data.get('difficulty', 'balanced')
        opponent_type = data.get('opponent_type', 'player')
        
        result = quick_battle.join_matchmaking_queue(user_id, difficulty, opponent_type)
        return jsonify(result), 200
    except Exception as e:
        print(f"[QuickBattle] Error joining queue: {e}", file=sys.stderr, flush=True)
        import traceback
        traceback.print_exc(file=sys.stderr)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@quick_battle_bp.route('/api/quick-battle/leave-queue', methods=['POST'], strict_slashes=False)
@quick_battle_bp.route('/vidgenerator/api/quick-battle/leave-queue', methods=['POST'])
def leave_matchmaking_queue():
    """Leave matchmaking queue"""
    try:
        data = request.get_json() or {}
        user_id = data.get('user_id', 'anonymous')
        
        result = quick_battle.leave_queue(user_id)
        return jsonify(result), 200
    except Exception as e:
        print(f"[QuickBattle] Error leaving queue: {e}", file=sys.stderr, flush=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@quick_battle_bp.route('/api/quick-battle/queue-status', methods=['GET'], strict_slashes=False)
@quick_battle_bp.route('/vidgenerator/api/quick-battle/queue-status', methods=['GET'])
def get_queue_status():
    """Get queue status for user"""
    try:
        user_id = request.args.get('user_id', 'anonymous')
        result = quick_battle.get_queue_status(user_id)
        return jsonify(result), 200
    except Exception as e:
        print(f"[QuickBattle] Error getting queue status: {e}", file=sys.stderr, flush=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@quick_battle_bp.route('/api/quick-battle/test', methods=['GET'], strict_slashes=False)
def test_endpoint():
    """Test endpoint"""
    return jsonify({
        'success': True,
        'message': 'Quick Battle API is working',
        'endpoints': {
            'create': '/api/quick-battle/create (POST)',
            'join_queue': '/api/quick-battle/join-queue (POST)',
            'leave_queue': '/api/quick-battle/leave-queue (POST)',
            'queue_status': '/api/quick-battle/queue-status?user_id=USER_ID',
            'complete': '/api/quick-battle/complete (POST)',
            'counter': '/api/quick-battle/counter?user_id=USER_ID',
            'streak': '/api/quick-battle/streak?user_id=USER_ID',
            'stats': '/api/quick-battle/stats?user_id=USER_ID',
            'intelligence': '/api/quick-battle/intelligence?user_id=USER_ID'
        }
    }), 200

