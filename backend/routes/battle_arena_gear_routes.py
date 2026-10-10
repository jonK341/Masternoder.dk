"""
Battle Arena Gear API Routes
"""
from flask import Blueprint, request, jsonify
from backend.services.battle_arena_gear_system import battle_arena_gear_system
from backend.services.battle_arena_error_handlers import BattleArenaErrorHandler
from backend.services.battle_arena_agents import battle_arena_agent_system
from backend.services.battle_arena_event_handlers import battle_arena_event_handler
from src.utils.input_validator import InputValidator
from src.utils.error_handler import ErrorHandler
from src.utils.rate_limiter import rate_limit
from datetime import datetime
import sys
import uuid

battle_arena_gear_bp = Blueprint('battle_arena_gear', __name__)

@battle_arena_gear_bp.route('/api/battle-arena-gear/definitions', methods=['GET'])
@battle_arena_gear_bp.route('/vidgenerator/api/battle-arena-gear/definitions', methods=['GET'])
@rate_limit()
def get_gear_definitions():
    """Get all gear definitions"""
    try:
        gear_type = request.args.get('type', None)
        rarity = request.args.get('rarity', None)
        
        definitions = battle_arena_gear_system.gear_definitions
        
        # Filter by type if provided
        if gear_type:
            definitions = {
                gid: gdef for gid, gdef in definitions.items()
                if gdef.get('type') == gear_type
            }
        
        # Filter by rarity if provided
        if rarity:
            definitions = {
                gid: gdef for gid, gdef in definitions.items()
                if gdef.get('rarity') == rarity
            }
        
        return jsonify({
            'success': True,
            'definitions': definitions,
            'count': len(definitions)
        }), 200
    except Exception as e:
        error_response = BattleArenaErrorHandler.handle_error(e, 'unknown_error', {})
        return jsonify(error_response), 500


@battle_arena_gear_bp.route('/api/battle-arena-gear/definition/<gear_id>', methods=['GET'])
@battle_arena_gear_bp.route('/vidgenerator/api/battle-arena-gear/definition/<gear_id>', methods=['GET'])
@rate_limit()
def get_gear_definition(gear_id: str):
    """Get specific gear definition"""
    try:
        gear_def = battle_arena_gear_system.get_gear_definition(gear_id)
        
        if not gear_def:
            error_response = BattleArenaErrorHandler.handle_error(
                ValueError('Gear not found'),
                'gear_not_found',
                {'gear_id': gear_id}
            )
            return jsonify(error_response), 404
        
        return jsonify({
            'success': True,
            'gear': gear_def
        }), 200
    except Exception as e:
        error_response = BattleArenaErrorHandler.handle_error(e, 'gear_not_found', {'gear_id': gear_id})
        return jsonify(error_response), 500


@battle_arena_gear_bp.route('/api/battle-arena-gear/user/<user_id>', methods=['GET'])
@battle_arena_gear_bp.route('/vidgenerator/api/battle-arena-gear/user/<user_id>', methods=['GET'])
@rate_limit()
def get_user_gear(user_id: str):
    """Get user's equipped gear with calculated stats"""
    try:
        user_gear = battle_arena_gear_system.get_user_gear(user_id)
        gear_data = {
            'success': True,
            'user_id': user_id,
            'gear': user_gear
        }
        
        # Enhance arena gear data with future tech, calculator, and gear stats
        try:
            from backend.services.future_tech_integration_service import future_tech_integration_service
            battle_id = request.args.get('battle_id', '')
            if battle_id:
                gear_data = future_tech_integration_service.enhance_arena_battle_data(
                    battle_id, user_id, gear_data
                )
            else:
                # Enhance with calculator even without battle_id
                if 'gear' in gear_data and 'total_stats' in gear_data['gear']:
                    gear_data['calculator_enhanced'] = True
        except Exception as e:
            print(f"[BattleArenaGear] Error enhancing gear: {e}")
        
        return jsonify(gear_data), 200
    except Exception as e:
        request_id = str(uuid.uuid4())[:8]
        error_response, status_code = ErrorHandler.create_error_response(e, 500, request_id)
        return error_response, status_code


@battle_arena_gear_bp.route('/api/battle-arena-gear/equip', methods=['POST'])
@battle_arena_gear_bp.route('/vidgenerator/api/battle-arena-gear/equip', methods=['POST'])
@rate_limit()
def equip_gear():
    """Equip gear to user"""
    try:
        data = InputValidator.get_json_safe(default={})
        user_id = InputValidator.sanitize_string(data.get('user_id', ''))
        gear_id = InputValidator.sanitize_string(data.get('gear_id', ''))
        
        if not user_id or not gear_id:
            error_response = BattleArenaErrorHandler.handle_error(
                ValueError('user_id and gear_id required'),
                'validation_error',
                {'field': 'user_id/gear_id', 'value': None}
            )
            return jsonify(error_response), 400
        
        # Use inventory agent
        inventory_agent = battle_arena_agent_system.get_agent('inventory')
        agent_result = inventory_agent.manage_inventory(user_id, 'equip', gear_id=gear_id)
        
        if not agent_result.get('success'):
            error_response = BattleArenaErrorHandler.handle_error(
                Exception(agent_result.get('error', 'Failed to equip gear')),
                'inventory_error',
                {'user_id': user_id, 'gear_id': gear_id, 'operation': 'equip'}
            )
            return jsonify(error_response), 400
        
        result = agent_result.get('result', {})
        
        # Emit event
        battle_arena_event_handler.emit('gear_equipped', {
            'user_id': user_id,
            'gear_id': gear_id,
            'result': result
        })
        
        return jsonify(result), 200 if result.get('success') else 400
    except Exception as e:
        error_response = BattleArenaErrorHandler.handle_error(e, 'inventory_error', {
            'user_id': data.get('user_id', ''),
            'gear_id': data.get('gear_id', ''),
            'operation': 'equip'
        })
        return jsonify(error_response), 500


@battle_arena_gear_bp.route('/api/battle-arena-gear/unequip', methods=['POST'])
@battle_arena_gear_bp.route('/vidgenerator/api/battle-arena-gear/unequip', methods=['POST'])
@rate_limit()
def unequip_gear():
    """Unequip gear from user"""
    try:
        data = InputValidator.get_json_safe(default={})
        user_id = InputValidator.sanitize_string(data.get('user_id', ''))
        slot = InputValidator.sanitize_string(data.get('slot', ''))
        
        if not user_id or not slot:
            error_response = BattleArenaErrorHandler.handle_error(
                ValueError('user_id and slot required'),
                'validation_error',
                {'field': 'user_id/slot', 'value': None}
            )
            return jsonify(error_response), 400
        
        # Use inventory agent
        inventory_agent = battle_arena_agent_system.get_agent('inventory')
        agent_result = inventory_agent.manage_inventory(user_id, 'unequip', slot=slot)
        
        if not agent_result.get('success'):
            error_response = BattleArenaErrorHandler.handle_error(
                Exception(agent_result.get('error', 'Failed to unequip gear')),
                'inventory_error',
                {'user_id': user_id, 'slot': slot, 'operation': 'unequip'}
            )
            return jsonify(error_response), 400
        
        result = agent_result.get('result', {})
        
        # Emit event
        battle_arena_event_handler.emit('gear_unequipped', {
            'user_id': user_id,
            'slot': slot,
            'result': result
        })
        
        return jsonify(result), 200 if result.get('success') else 400
    except Exception as e:
        error_response = BattleArenaErrorHandler.handle_error(e, 'inventory_error', {
            'user_id': data.get('user_id', ''),
            'slot': data.get('slot', ''),
            'operation': 'unequip'
        })
        return jsonify(error_response), 500


@battle_arena_gear_bp.route('/api/battle-arena-gear/inventory/<user_id>', methods=['GET'])
@battle_arena_gear_bp.route('/vidgenerator/api/battle-arena-gear/inventory/<user_id>', methods=['GET'])
@rate_limit()
def get_inventory(user_id: str):
    """Get user gear inventory"""
    try:
        inventory = battle_arena_gear_system.get_inventory(user_id)
        
        return jsonify({
            'success': True,
            'user_id': user_id,
            'inventory': inventory
        }), 200
    except Exception as e:
        request_id = str(uuid.uuid4())[:8]
        error_response, status_code = ErrorHandler.create_error_response(e, 500, request_id)
        return error_response, status_code


@battle_arena_gear_bp.route('/api/battle-arena-gear/add', methods=['POST'])
@battle_arena_gear_bp.route('/vidgenerator/api/battle-arena-gear/add', methods=['POST'])
@rate_limit()
def add_gear():
    """Add gear to user inventory"""
    try:
        data = InputValidator.get_json_safe(default={})
        user_id = InputValidator.sanitize_string(data.get('user_id', ''))
        gear_id = InputValidator.sanitize_string(data.get('gear_id', ''))
        quantity = int(data.get('quantity', 1))
        
        if not user_id or not gear_id:
            error_response = BattleArenaErrorHandler.handle_error(
                ValueError('user_id and gear_id required'),
                'validation_error',
                {'field': 'user_id/gear_id', 'value': None}
            )
            return jsonify(error_response), 400
        
        # Use inventory agent
        inventory_agent = battle_arena_agent_system.get_agent('inventory')
        agent_result = inventory_agent.manage_inventory(user_id, 'add', gear_id=gear_id, quantity=quantity)
        
        if not agent_result.get('success'):
            error_response = BattleArenaErrorHandler.handle_error(
                Exception(agent_result.get('error', 'Failed to add gear')),
                'inventory_error',
                {'user_id': user_id, 'gear_id': gear_id, 'operation': 'add'}
            )
            return jsonify(error_response), 400
        
        result = agent_result.get('result', {})
        
        return jsonify(result), 200 if result.get('success') else 400
    except Exception as e:
        error_response = BattleArenaErrorHandler.handle_error(e, 'inventory_error', {
            'user_id': data.get('user_id', ''),
            'gear_id': data.get('gear_id', ''),
            'operation': 'add'
        })
        return jsonify(error_response), 500


@battle_arena_gear_bp.route('/api/battle-arena-gear/calculate-stats', methods=['POST'])
@battle_arena_gear_bp.route('/vidgenerator/api/battle-arena-gear/calculate-stats', methods=['POST'])
@rate_limit()
def calculate_gear_stats():
    """Calculate gear stats using calculator and divisions"""
    try:
        data = InputValidator.get_json_safe(default={})
        user_id = InputValidator.sanitize_string(data.get('user_id', ''))
        gear_id = InputValidator.sanitize_string(data.get('gear_id', ''))
        
        if not user_id or not gear_id:
            error_response = BattleArenaErrorHandler.handle_error(
                ValueError('user_id and gear_id required'),
                'validation_error',
                {'field': 'user_id/gear_id', 'value': None}
            )
            return jsonify(error_response), 400
        
        # Check if gear exists
        gear_def = battle_arena_gear_system.get_gear_definition(gear_id)
        if not gear_def:
            error_response = BattleArenaErrorHandler.handle_error(
                ValueError('Gear not found'),
                'gear_not_found',
                {'gear_id': gear_id}
            )
            return jsonify(error_response), 404
        
        # Use stats agent for calculation
        stats_agent = battle_arena_agent_system.get_agent('stats')
        agent_result = stats_agent.analyze_gear_stats(user_id, gear_id)
        
        if not agent_result.get('success'):
            # Fallback to direct calculation
            stats = battle_arena_gear_system.calculate_gear_stats(user_id, gear_id)
        else:
            stats = agent_result.get('analysis', {})
        
        if not stats:
            error_response = BattleArenaErrorHandler.handle_error(
                Exception('Failed to calculate stats'),
                'calculator_error',
                {'user_id': user_id, 'gear_id': gear_id}
            )
            return jsonify(error_response), 500
        
        # Emit event
        battle_arena_event_handler.emit('stats_calculated', {
            'user_id': user_id,
            'gear_id': gear_id,
            'stats': stats
        })
        
        return jsonify({
            'success': True,
            'user_id': user_id,
            'gear_id': gear_id,
            'stats': stats,
            'agent_id': agent_result.get('agent_id') if agent_result.get('success') else None
        }), 200
    except Exception as e:
        error_response = BattleArenaErrorHandler.handle_error(e, 'calculator_error', {
            'user_id': data.get('user_id', ''),
            'gear_id': data.get('gear_id', '')
        })
        return jsonify(error_response), 500


@battle_arena_gear_bp.route('/api/battle-arena-gear/divisions/<user_id>', methods=['GET'])
@battle_arena_gear_bp.route('/vidgenerator/api/battle-arena-gear/divisions/<user_id>', methods=['GET'])
@rate_limit()
def get_user_divisions(user_id: str):
    """Get user division data"""
    try:
        divisions = battle_arena_gear_system.get_user_divisions(user_id)
        
        return jsonify({
            'success': True,
            'user_id': user_id,
            'divisions': divisions
        }), 200
    except Exception as e:
        request_id = str(uuid.uuid4())[:8]
        error_response, status_code = ErrorHandler.create_error_response(e, 500, request_id)
        return error_response, status_code


@battle_arena_gear_bp.route('/api/battle-arena-gear/generate', methods=['POST'])
@battle_arena_gear_bp.route('/vidgenerator/api/battle-arena-gear/generate', methods=['POST'])
@rate_limit()
def generate_gear():
    """Generate gear from user divisions using calculator"""
    try:
        data = InputValidator.get_json_safe(default={})
        user_id = InputValidator.sanitize_string(data.get('user_id', ''))
        gear_type = InputValidator.sanitize_string(data.get('gear_type', None))
        
        if not user_id:
            return jsonify({
                'success': False,
                'error': 'user_id required'
            }), 400
        
        result = battle_arena_gear_system.generate_gear_from_divisions(user_id, gear_type)
        
        return jsonify(result), 200 if result.get('success') else 400
    except Exception as e:
        request_id = str(uuid.uuid4())[:8]
        error_response, status_code = ErrorHandler.create_error_response(e, 500, request_id)
        return error_response, status_code


@battle_arena_gear_bp.route('/api/battle-arena-gear/points/<user_id>', methods=['GET'])
@battle_arena_gear_bp.route('/vidgenerator/api/battle-arena-gear/points/<user_id>', methods=['GET'])
@rate_limit()
def get_gear_points(user_id: str):
    """Get saved gear points for user"""
    try:
        points = battle_arena_gear_system.get_gear_points(user_id)
        
        return jsonify({
            'success': True,
            'user_id': user_id,
            'points': points
        }), 200
    except Exception as e:
        error_response = BattleArenaErrorHandler.handle_error(e, 'storage_error', {
            'user_id': user_id,
            'operation': 'get_points',
            'file': 'battle_arena_gear_points.json'
        })
        return jsonify(error_response), 500


@battle_arena_gear_bp.route('/api/battle-arena-gear/agents/status', methods=['GET'])
@battle_arena_gear_bp.route('/vidgenerator/api/battle-arena-gear/agents/status', methods=['GET'])
@rate_limit()
def get_agents_status():
    """Get status of all battle arena agents"""
    try:
        status = battle_arena_agent_system.get_all_agents_status()
        return jsonify({
            'success': True,
            'agents_status': status
        }), 200
    except Exception as e:
        error_response = BattleArenaErrorHandler.handle_error(e, 'unknown_error', {})
        return jsonify(error_response), 500


@battle_arena_gear_bp.route('/api/battle-arena-gear/agents/recommend', methods=['POST'])
@battle_arena_gear_bp.route('/vidgenerator/api/battle-arena-gear/agents/recommend', methods=['POST'])
@rate_limit()
def recommend_gear():
    """Get gear recommendations from gear agent"""
    try:
        data = InputValidator.get_json_safe(default={})
        user_id = InputValidator.sanitize_string(data.get('user_id', ''))
        battle_type = InputValidator.sanitize_string(data.get('battle_type', None))
        
        if not user_id:
            error_response = BattleArenaErrorHandler.handle_error(
                ValueError('user_id required'),
                'validation_error',
                {'field': 'user_id', 'value': None}
            )
            return jsonify(error_response), 400
        
        gear_agent = battle_arena_agent_system.get_agent('gear')
        result = gear_agent.recommend_gear(user_id, battle_type)
        
        return jsonify(result), 200 if result.get('success') else 400
    except Exception as e:
        error_response = BattleArenaErrorHandler.handle_error(e, 'unknown_error', {
            'user_id': data.get('user_id', '')
        })
        return jsonify(error_response), 500


@battle_arena_gear_bp.route('/api/battle-arena-gear/agents/optimize', methods=['POST'])
@battle_arena_gear_bp.route('/vidgenerator/api/battle-arena-gear/agents/optimize', methods=['POST'])
@rate_limit()
def optimize_gear():
    """Optimize gear loadout using gear agent"""
    try:
        data = InputValidator.get_json_safe(default={})
        user_id = InputValidator.sanitize_string(data.get('user_id', ''))
        
        if not user_id:
            error_response = BattleArenaErrorHandler.handle_error(
                ValueError('user_id required'),
                'validation_error',
                {'field': 'user_id', 'value': None}
            )
            return jsonify(error_response), 400
        
        gear_agent = battle_arena_agent_system.get_agent('gear')
        result = gear_agent.optimize_gear_loadout(user_id)
        
        return jsonify(result), 200 if result.get('success') else 400
    except Exception as e:
        error_response = BattleArenaErrorHandler.handle_error(e, 'unknown_error', {
            'user_id': data.get('user_id', '')
        })
        return jsonify(error_response), 500


@battle_arena_gear_bp.route('/api/battle-arena-gear/agents/compare', methods=['POST'])
@battle_arena_gear_bp.route('/vidgenerator/api/battle-arena-gear/agents/compare', methods=['POST'])
@rate_limit()
def compare_gear():
    """Compare two pieces of gear using stats agent"""
    try:
        data = InputValidator.get_json_safe(default={})
        user_id = InputValidator.sanitize_string(data.get('user_id', ''))
        gear_id1 = InputValidator.sanitize_string(data.get('gear_id1', ''))
        gear_id2 = InputValidator.sanitize_string(data.get('gear_id2', ''))
        
        if not user_id or not gear_id1 or not gear_id2:
            error_response = BattleArenaErrorHandler.handle_error(
                ValueError('user_id, gear_id1, and gear_id2 required'),
                'validation_error',
                {'field': 'gear_ids', 'value': None}
            )
            return jsonify(error_response), 400
        
        stats_agent = battle_arena_agent_system.get_agent('stats')
        result = stats_agent.compare_gear(user_id, gear_id1, gear_id2)
        
        return jsonify(result), 200 if result.get('success') else 400
    except Exception as e:
        error_response = BattleArenaErrorHandler.handle_error(e, 'unknown_error', {
            'user_id': data.get('user_id', '')
        })
        return jsonify(error_response), 500


@battle_arena_gear_bp.route('/api/battle-arena-gear/events/history', methods=['GET'])
@battle_arena_gear_bp.route('/vidgenerator/api/battle-arena-gear/events/history', methods=['GET'])
@rate_limit()
def get_event_history():
    """Get event history"""
    try:
        event_type = request.args.get('event_type', None)
        limit = int(request.args.get('limit', 100))
        
        history = battle_arena_event_handler.get_event_history(event_type, limit)
        
        return jsonify({
            'success': True,
            'events': history,
            'count': len(history)
        }), 200
    except Exception as e:
        error_response = BattleArenaErrorHandler.handle_error(e, 'unknown_error', {})
        return jsonify(error_response), 500

