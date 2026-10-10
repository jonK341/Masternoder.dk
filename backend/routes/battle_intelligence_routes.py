"""
Battle Intelligence API Routes
"""
from flask import Blueprint, request, jsonify

# Import services with error handling
try:
    from backend.services.battle_intelligence_system import battle_intelligence_system
except ImportError as e:
    print(f"WARNING: Could not import battle_intelligence_system: {e}")
    battle_intelligence_system = None

# Import utilities with error handling
try:
    from src.utils.input_validator import InputValidator
except ImportError:
    InputValidator = None

try:
    from src.utils.error_handler import ErrorHandler
except ImportError:
    ErrorHandler = None

try:
    from src.utils.rate_limiter import rate_limit
except ImportError:
    def rate_limit():
        def decorator(func):
            return func
        return decorator

battle_intelligence_bp = Blueprint('battle_intelligence_bp', __name__)

# Debug: Print when module is loaded
print(f"[BattleIntelligenceRoutes] Module loaded, blueprint created: {battle_intelligence_bp.name}", flush=True)

@battle_intelligence_bp.route('/api/battle/intelligence/test', methods=['GET'], strict_slashes=False)
@battle_intelligence_bp.route('/vidgenerator/api/battle/intelligence/test', methods=['GET'], strict_slashes=False)
def test_endpoint():
    """Simple test endpoint"""
    print("[BattleIntelligenceRoutes] test_endpoint called", flush=True)
    return jsonify({
        'success': True, 
        'message': 'Battle intelligence blueprint is working',
        'endpoints': {
            'win_probability': '/api/battle/calculator/win-probability',
            'rewards': '/api/battle/calculator/rewards',
            'optimize_strategy': '/api/battle/calculator/optimize-strategy'
        }
    }), 200

@battle_intelligence_bp.route('/api/battle/calculator/win-probability', methods=['GET', 'POST'])
@battle_intelligence_bp.route('/vidgenerator/api/battle/calculator/win-probability', methods=['GET', 'POST'])
@rate_limit()
def calculate_win_probability():
    """Calculate win probability for a battle"""
    try:
        if not battle_intelligence_system:
            return jsonify({'success': False, 'error': 'Battle intelligence system not available'}), 500
        
        if request.method == 'GET':
            user_id = request.args.get('user_id', 'default_user')
            opponent_id = request.args.get('opponent_id')
            battle_type = request.args.get('battle_type', 'quick')
            user_stats = request.args.get('user_stats')
            opponent_stats = request.args.get('opponent_stats')
        else:
            data = request.get_json() or {}
            user_id = data.get('user_id', 'default_user')
            opponent_id = data.get('opponent_id')
            battle_type = data.get('battle_type', 'quick')
            user_stats = data.get('user_stats')
            opponent_stats = data.get('opponent_stats')
        
        # Parse stats if provided as strings
        if isinstance(user_stats, str):
            import json
            user_stats = json.loads(user_stats)
        if isinstance(opponent_stats, str):
            import json
            opponent_stats = json.loads(opponent_stats)
        
        result = battle_intelligence_system.calculate_win_probability(
            user_id, opponent_id, battle_type, user_stats, opponent_stats
        )
        return jsonify(result), 200 if result.get('success') else 400
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@battle_intelligence_bp.route('/api/battle/calculator/rewards', methods=['GET', 'POST'])
@battle_intelligence_bp.route('/vidgenerator/api/battle/calculator/rewards', methods=['GET', 'POST'])
@rate_limit()
def calculate_battle_rewards():
    """Calculate point rewards for a battle"""
    try:
        if not battle_intelligence_system:
            return jsonify({'success': False, 'error': 'Battle intelligence system not available'}), 500
        
        if request.method == 'GET':
            battle_type = request.args.get('battle_type', 'quick')
            victory = request.args.get('victory', 'true').lower() == 'true'
            user_level = int(request.args.get('user_level', 1))
            streak = int(request.args.get('streak', 0))
            difficulty = request.args.get('difficulty', 'normal')
            multipliers = request.args.get('multipliers')
        else:
            data = request.get_json() or {}
            battle_type = data.get('battle_type', 'quick')
            victory = data.get('victory', True)
            user_level = int(data.get('user_level', 1))
            streak = int(data.get('streak', 0))
            difficulty = data.get('difficulty', 'normal')
            multipliers = data.get('multipliers')
        
        # Parse multipliers if provided as string
        if isinstance(multipliers, str):
            import json
            multipliers = json.loads(multipliers)
        
        result = battle_intelligence_system.calculate_battle_rewards(
            battle_type, victory, user_level, streak, difficulty, multipliers
        )
        return jsonify(result), 200 if result.get('success') else 400
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@battle_intelligence_bp.route('/api/battle/calculator/optimize-strategy', methods=['GET', 'POST'])
@battle_intelligence_bp.route('/vidgenerator/api/battle/calculator/optimize-strategy', methods=['GET', 'POST'])
@rate_limit()
def optimize_battle_strategy():
    """Optimize battle strategy based on user history"""
    try:
        if not battle_intelligence_system:
            return jsonify({'success': False, 'error': 'Battle intelligence system not available'}), 500
        
        if request.method == 'GET':
            user_id = request.args.get('user_id', 'default_user')
            battle_type = request.args.get('battle_type', 'quick')
            opponent_data = request.args.get('opponent_data')
            constraints = request.args.get('constraints')
        else:
            data = request.get_json() or {}
            user_id = data.get('user_id', 'default_user')
            battle_type = data.get('battle_type', 'quick')
            opponent_data = data.get('opponent_data')
            constraints = data.get('constraints')
        
        # Parse JSON strings if provided
        if isinstance(opponent_data, str):
            import json
            opponent_data = json.loads(opponent_data)
        if isinstance(constraints, str):
            import json
            constraints = json.loads(constraints)
        
        result = battle_intelligence_system.optimize_battle_strategy(
            user_id, battle_type, opponent_data, constraints
        )
        return jsonify(result), 200 if result.get('success') else 400
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@battle_intelligence_bp.route('/api/battle/intelligence/opponent/<opponent_id>', methods=['GET'])
@battle_intelligence_bp.route('/vidgenerator/api/battle/intelligence/opponent/<opponent_id>', methods=['GET'])
@rate_limit()
def analyze_opponent(opponent_id):
    """Analyze opponent and provide intelligence"""
    try:
        opponent_id = InputValidator.sanitize_string(opponent_id, max_length=100)
        user_id = InputValidator.sanitize_string(request.args.get('user_id', 'default_user'), max_length=100)
        
        result = battle_intelligence_system.analyze_opponent(opponent_id, user_id)
        return jsonify(result), 200
    except Exception as e:
        return ErrorHandler.create_error_response(str(e), 500)


@battle_intelligence_bp.route('/api/battle/intelligence/mode/<mode>', methods=['GET'], strict_slashes=False)
@battle_intelligence_bp.route('/vidgenerator/api/battle/intelligence/mode/<mode>', methods=['GET'], strict_slashes=False)
def get_mode_intelligence(mode):
    """Get intelligence for specific battle mode"""
    try:
        print(f"get_mode_intelligence called with mode: {mode}", flush=True)
        mode = InputValidator.sanitize_string(mode, max_length=50)
        user_id = InputValidator.sanitize_string(request.args.get('user_id', 'default_user'), max_length=100)
        print(f"Mode: {mode}, User ID: {user_id}", flush=True)
        
        result = battle_intelligence_system.get_mode_intelligence(mode, user_id)
        print(f"Result: {result}", flush=True)
        return jsonify(result), 200
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        print(f"Error in get_mode_intelligence: {e}\n{error_trace}", flush=True)
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': error_trace
        }), 500


@battle_intelligence_bp.route('/api/battle/intelligence/strategy', methods=['POST'])
@battle_intelligence_bp.route('/vidgenerator/api/battle/intelligence/strategy', methods=['POST'])
@rate_limit()
def recommend_strategy():
    """Recommend optimal strategy"""
    try:
        data = InputValidator.get_json_safe(default={})
        user_id = InputValidator.sanitize_string(data.get('user_id', 'default_user'), max_length=100)
        battle_type = InputValidator.sanitize_string(data.get('battle_type', 'quick'), max_length=50)
        opponent_data = data.get('opponent_data', {})
        
        result = battle_intelligence_system.recommend_strategy(user_id, battle_type, opponent_data)
        return jsonify(result), 200
    except Exception as e:
        return ErrorHandler.create_error_response(str(e), 500)

@battle_intelligence_bp.route('/api/battle/intelligence/leaderboard', methods=['GET'])
@battle_intelligence_bp.route('/vidgenerator/api/battle/intelligence/leaderboard', methods=['GET'])
@rate_limit()
def get_battle_leaderboard():
    """Get battle leaderboard"""
    try:
        if not battle_intelligence_system:
            return jsonify({'success': False, 'error': 'Battle intelligence system not available'}), 500
        
        limit = int(request.args.get('limit', 10))
        category = request.args.get('category', 'wins')
        
        result = battle_intelligence_system.get_battle_leaderboard(limit, category)
        return jsonify(result), 200 if result.get('success') else 400
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@battle_intelligence_bp.route('/api/battle/intelligence/recent-battles', methods=['GET'])
@battle_intelligence_bp.route('/vidgenerator/api/battle/intelligence/recent-battles', methods=['GET'])
@rate_limit()
def get_recent_battles():
    """Get recent battles"""
    try:
        if not battle_intelligence_system:
            return jsonify({'success': False, 'error': 'Battle intelligence system not available'}), 500
        
        limit = int(request.args.get('limit', 10))
        
        result = battle_intelligence_system.get_recent_battles(limit)
        return jsonify(result), 200 if result.get('success') else 400
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@battle_intelligence_bp.route('/api/battle/intelligence/statistics', methods=['GET'])
@battle_intelligence_bp.route('/vidgenerator/api/battle/intelligence/statistics', methods=['GET'])
@rate_limit()
def get_battle_statistics():
    """Get battle statistics"""
    try:
        if not battle_intelligence_system:
            return jsonify({'success': False, 'error': 'Battle intelligence system not available'}), 500
        
        result = battle_intelligence_system.get_battle_statistics()
        return jsonify(result), 200 if result.get('success') else 400
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
