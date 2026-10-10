"""
Battle v3 Ultimate Routes
"""
from flask import Blueprint, request, jsonify
from backend.services.battle_v3_ultimate import battle_v3_ultimate
from src.utils.error_handler import ErrorHandler
from src.utils.rate_limiter import rate_limit
import uuid

battle_v3_bp = Blueprint('battle_v3', __name__)

def get_user_id():
    """Get user ID from session or request"""
    from flask import session
    if 'user_id' not in session:
        session['user_id'] = str(uuid.uuid4())
    return session.get('user_id', request.args.get('user_id', 'anonymous'))


@battle_v3_bp.route('/api/battle-v3/create', methods=['POST'])
@battle_v3_bp.route('/vidgenerator/api/battle-v3/create', methods=['POST'])
@rate_limit()
def create_battle():
    """Create a new battle"""
    try:
        user_id = get_user_id()
        data = request.get_json() or {}
        battle_type = data.get('battle_type', 'pvp_standard')
        opponent_id = data.get('opponent_id')
        strategy = data.get('strategy', 'balanced')
        
        result = battle_v3_ultimate.create_battle(user_id, battle_type, opponent_id, strategy)
        
        # Enhance battle with future tech and calculator
        if result.get('success') and 'battle' in result:
            battle_id = result['battle'].get('battle_id', '')
            try:
                from backend.services.future_tech_integration_service import future_tech_integration_service
                result['battle'] = future_tech_integration_service.enhance_battle_data(
                    battle_id, user_id, result['battle']
                )
            except Exception as e:
                print(f"[BattleV3] Error enhancing battle on create: {e}")
        
        return jsonify(result), 200
    except Exception as e:
        request_id = str(uuid.uuid4())[:8]
        error_response, status_code = ErrorHandler.create_error_response(e, 500, request_id)
        return error_response, status_code


@battle_v3_bp.route('/api/battle-v3/<battle_id>', methods=['GET'])
@battle_v3_bp.route('/vidgenerator/api/battle-v3/<battle_id>', methods=['GET'])
@rate_limit()
def get_battle(battle_id: str):
    """Get battle details"""
    try:
        user_id = request.args.get('user_id', get_user_id())
        result = battle_v3_ultimate.get_battle(battle_id)
        
        # Enhance battle with future tech and calculator
        if result.get('success') and 'battle' in result:
            try:
                from backend.services.future_tech_integration_service import future_tech_integration_service
                result['battle'] = future_tech_integration_service.enhance_battle_data(
                    battle_id, user_id, result['battle']
                )
            except Exception as e:
                print(f"[BattleV3] Error enhancing battle: {e}")
        
        return jsonify(result), 200 if result.get('success') else 404
    except Exception as e:
        request_id = str(uuid.uuid4())[:8]
        error_response, status_code = ErrorHandler.create_error_response(e, 500, request_id)
        return error_response, status_code


@battle_v3_bp.route('/api/battle-v3/<battle_id>/round', methods=['POST'])
@battle_v3_bp.route('/vidgenerator/api/battle-v3/<battle_id>/round', methods=['POST'])
@rate_limit()
def execute_round(battle_id: str):
    """Execute a battle round"""
    try:
        data = request.get_json() or {}
        user_action = data.get('action', 'attack')
        user_id = data.get('user_id', get_user_id())
        
        result = battle_v3_ultimate.execute_battle_round(battle_id, user_action)
        
        # Enhance battle result with future tech and calculator
        if result.get('success') and 'battle' in result:
            try:
                from backend.services.future_tech_integration_service import future_tech_integration_service
                result['battle'] = future_tech_integration_service.enhance_battle_data(
                    battle_id, user_id, result['battle']
                )
            except Exception as e:
                print(f"[BattleV3] Error enhancing battle: {e}")
        
        return jsonify(result), 200
    except Exception as e:
        request_id = str(uuid.uuid4())[:8]
        error_response, status_code = ErrorHandler.create_error_response(e, 500, request_id)
        return error_response, status_code


@battle_v3_bp.route('/api/battle-v3/types')
@battle_v3_bp.route('/vidgenerator/api/battle-v3/types')
@rate_limit()
def get_battle_types():
    """Get all battle types"""
    return jsonify({
        'success': True,
        'battle_types': battle_v3_ultimate.battle_types
    }), 200


@battle_v3_bp.route('/api/battle-v3/strategies')
@battle_v3_bp.route('/vidgenerator/api/battle-v3/strategies')
@rate_limit()
def get_strategies():
    """Get all battle strategies"""
    return jsonify({
        'success': True,
        'strategies': battle_v3_ultimate.strategies
    }), 200
