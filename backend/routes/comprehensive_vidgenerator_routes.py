"""
Comprehensive Vidgenerator Routes
All missing routes, battle system re-engineering, and unified integrations
"""
from flask import Blueprint, jsonify, request, Response
from backend.services.trigger_based_generator import trigger_based_generator
from backend.services.vidgenerator_comprehensive_audit import VidgeneratorAuditor
from backend.services.unified_point_system_json_storage import unified_point_json_storage
from backend.services.ultra_resource_controller import ultra_resource_controller
import os

comprehensive_vidgenerator_bp = Blueprint('comprehensive_vidgenerator', __name__)


# ============================================================================
# AUDIT & DISCOVERY ROUTES
# ============================================================================

@comprehensive_vidgenerator_bp.route('/audit/run', methods=['GET'])
@comprehensive_vidgenerator_bp.route('/vidgenerator/api/vidgenerator/audit/run', methods=['GET'])
def run_comprehensive_audit():
    """Run comprehensive audit of all vidgenerator pages"""
    try:
        auditor = VidgeneratorAuditor()
        findings = auditor.audit_all()
        
        return jsonify({
            'success': True,
            'findings': findings,
            'summary': {
                'missing_routes': len(findings['missing_routes']),
                'missing_links': len(findings['missing_links']),
                'disabled_features': len(findings['disabled_features']),
                'missing_integrations': len(findings['missing_integrations']),
                'broken_references': len(findings['broken_references'])
            }
        }), 200
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# ============================================================================
# TRIGGER-BASED GENERATOR ROUTES
# ============================================================================

@comprehensive_vidgenerator_bp.route('/trigger/register', methods=['POST'])
@comprehensive_vidgenerator_bp.route('/vidgenerator/api/vidgenerator/trigger/register', methods=['POST'])
def register_trigger():
    """Register a trigger that waits for expected pointers"""
    try:
        data = request.get_json() or {}
        trigger_type = data.get('trigger_type')
        trigger_data = data.get('trigger_data', {})
        expected_pointers = data.get('expected_pointers', [])
        
        if not trigger_type:
            return jsonify({
                'success': False,
                'error': 'trigger_type required'
            }), 400
        
        trigger_id = trigger_based_generator.register_trigger(
            trigger_type, trigger_data, expected_pointers
        )
        
        return jsonify({
            'success': True,
            'trigger_id': trigger_id,
            'status': 'pending',
            'expected_pointers': expected_pointers
        }), 200
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@comprehensive_vidgenerator_bp.route('/trigger/pointer', methods=['POST'])
@comprehensive_vidgenerator_bp.route('/vidgenerator/api/vidgenerator/trigger/pointer', methods=['POST'])
def catch_pointer():
    """Catch a pointer and check for matching triggers"""
    try:
        data = request.get_json() or {}
        pointer_id = data.get('pointer_id')
        pointer_data = data.get('pointer_data', {})
        
        if not pointer_id:
            return jsonify({
                'success': False,
                'error': 'pointer_id required'
            }), 400
        
        triggered = trigger_based_generator.catch_pointer(pointer_id, pointer_data)
        
        return jsonify({
            'success': True,
            'pointer_id': pointer_id,
            'triggers_activated': triggered
        }), 200
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@comprehensive_vidgenerator_bp.route('/trigger/status/<trigger_id>', methods=['GET'])
@comprehensive_vidgenerator_bp.route('/vidgenerator/api/vidgenerator/trigger/status/<trigger_id>', methods=['GET'])
def get_trigger_status(trigger_id: str):
    """Get status of a trigger"""
    try:
        status = trigger_based_generator.get_trigger_status(trigger_id)
        
        if not status:
            return jsonify({
                'success': False,
                'error': 'Trigger not found'
            }), 404
        
        return jsonify({
            'success': True,
            'trigger': status
        }), 200
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@comprehensive_vidgenerator_bp.route('/trigger/pending', methods=['GET'])
@comprehensive_vidgenerator_bp.route('/vidgenerator/api/vidgenerator/trigger/pending', methods=['GET'])
def list_pending_triggers():
    """List all pending triggers"""
    try:
        user_id = request.args.get('user_id')
        triggers = trigger_based_generator.list_pending_triggers(user_id)
        
        return jsonify({
            'success': True,
            'triggers': triggers,
            'count': len(triggers)
        }), 200
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# ============================================================================
# UNIFIED POINTS & ENERGY ROUTES
# ============================================================================

@comprehensive_vidgenerator_bp.route('/points/energy/award', methods=['POST'])
@comprehensive_vidgenerator_bp.route('/vidgenerator/api/vidgenerator/points/energy/award', methods=['POST'])
def award_energy_points():
    """Award energy points through unified system"""
    try:
        data = request.get_json() or {}
        user_id = data.get('user_id', 'default_user')
        energy_type = data.get('energy_type', 'mind')  # mind, power, time, place
        amount = data.get('amount', 1)
        source = data.get('source', 'general')
        
        # Award through unified point system
        point_result = unified_point_json_storage.increment_point(
            user_id, f'energy_{energy_type}', amount
        )
        
        # Also update ultra resource controller
        energy_result = ultra_resource_controller.add_energy(
            user_id, energy_type, amount
        )
        
        return jsonify({
            'success': True,
            'energy_type': energy_type,
            'amount': amount,
            'source': source,
            'point_system': point_result,
            'energy_system': energy_result
        }), 200
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@comprehensive_vidgenerator_bp.route('/points/function/award', methods=['POST'])
@comprehensive_vidgenerator_bp.route('/vidgenerator/api/vidgenerator/points/function/award', methods=['POST'])
def award_function_points():
    """Award function points through unified system"""
    try:
        data = request.get_json() or {}
        user_id = data.get('user_id', 'default_user')
        function_type = data.get('function_type')
        amount = data.get('amount', 1)
        
        if not function_type:
            return jsonify({
                'success': False,
                'error': 'function_type required'
            }), 400
        
        result = unified_point_json_storage.increment_point(
            user_id, f'function_{function_type}', amount
        )
        
        return jsonify({
            'success': True,
            'function_type': function_type,
            'amount': amount,
            'result': result
        }), 200
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@comprehensive_vidgenerator_bp.route('/points/unified/get', methods=['GET'])
@comprehensive_vidgenerator_bp.route('/vidgenerator/api/vidgenerator/points/unified/get', methods=['GET'])
def get_unified_points():
    """Get all points including energy and functions"""
    try:
        user_id = request.args.get('user_id', 'default_user')
        
        # Get from unified point system
        all_points = unified_point_json_storage.get_all_points(user_id)
        
        # Get energy status
        energy_status = ultra_resource_controller.get_energy_status(user_id)
        
        return jsonify({
            'success': True,
            'points': all_points,
            'energy': energy_status.get('energy', {}),
            'total_energy': energy_status.get('total_energy', 0)
        }), 200
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# ============================================================================
# BATTLE SYSTEM RE-ENGINEERING ROUTES
# ============================================================================

@comprehensive_vidgenerator_bp.route('/battle/trigger', methods=['POST'])
@comprehensive_vidgenerator_bp.route('/vidgenerator/api/vidgenerator/battle/trigger', methods=['POST'])
def trigger_battle():
    """Trigger-based battle instead of instant"""
    try:
        data = request.get_json() or {}
        user_id = data.get('user_id', 'default_user')
        battle_type = data.get('battle_type', 'quick')
        
        # Register trigger for battle
        expected_pointers = [
            'energy_check',
            'points_available',
            'battle_ready'
        ]
        
        trigger_id = trigger_based_generator.register_trigger(
            'quick_battle',
            {
                'user_id': user_id,
                'battle_type': battle_type,
                'data': data
            },
            expected_pointers
        )
        
        return jsonify({
            'success': True,
            'trigger_id': trigger_id,
            'message': 'Battle trigger registered. Waiting for expected pointers.',
            'expected_pointers': expected_pointers
        }), 200
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@comprehensive_vidgenerator_bp.route('/battle/agent/strategy', methods=['GET', 'POST'])
@comprehensive_vidgenerator_bp.route('/vidgenerator/api/vidgenerator/battle/agent/strategy', methods=['GET', 'POST'])
def get_agent_battle_strategy():
    """Get battle strategy recommendations from agent"""
    try:
        from backend.services.battle_intelligence_system import BattleIntelligenceSystem
        battle_intelligence = BattleIntelligenceSystem()
        
        if request.method == 'GET':
            user_id = request.args.get('user_id', 'default_user')
            agent_id = request.args.get('agent_id')
            battle_type = request.args.get('battle_type', 'quick')
            opponent_data = request.args.get('opponent_data')
        else:
            data = request.get_json() or {}
            user_id = data.get('user_id', 'default_user')
            agent_id = data.get('agent_id')
            battle_type = data.get('battle_type', 'quick')
            opponent_data = data.get('opponent_data')
        
        if not agent_id:
            return jsonify({
                'success': False,
                'error': 'agent_id is required'
            }), 400
        
        result = battle_intelligence.get_agent_battle_strategy(
            user_id, agent_id, battle_type, opponent_data
        )
        return jsonify(result), 200 if result.get('success') else 400
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@comprehensive_vidgenerator_bp.route('/battle/agent/recommendations', methods=['GET', 'POST'])
@comprehensive_vidgenerator_bp.route('/vidgenerator/api/vidgenerator/battle/agent/recommendations', methods=['GET', 'POST'])
def get_agent_battle_recommendations():
    """Get comprehensive battle recommendations from agent"""
    try:
        from backend.services.battle_intelligence_system import BattleIntelligenceSystem
        battle_intelligence = BattleIntelligenceSystem()
        
        if request.method == 'GET':
            user_id = request.args.get('user_id', 'default_user')
            agent_id = request.args.get('agent_id')
        else:
            data = request.get_json() or {}
            user_id = data.get('user_id', 'default_user')
            agent_id = data.get('agent_id')
        
        if not agent_id:
            return jsonify({
                'success': False,
                'error': 'agent_id is required'
            }), 400
        
        result = battle_intelligence.get_agent_battle_recommendations(user_id, agent_id)
        return jsonify(result), 200 if result.get('success') else 400
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@comprehensive_vidgenerator_bp.route('/battle/agent/analyze', methods=['POST'])
@comprehensive_vidgenerator_bp.route('/vidgenerator/api/vidgenerator/battle/agent/analyze', methods=['POST'])
def analyze_battle_with_agent():
    """Analyze a battle using agent intelligence"""
    try:
        from backend.services.battle_intelligence_system import BattleIntelligenceSystem
        battle_intelligence = BattleIntelligenceSystem()
        
        data = request.get_json() or {}
        user_id = data.get('user_id', 'default_user')
        agent_id = data.get('agent_id')
        battle_id = data.get('battle_id')
        
        if not agent_id or not battle_id:
            return jsonify({
                'success': False,
                'error': 'agent_id and battle_id are required'
            }), 400
        
        result = battle_intelligence.analyze_battle_with_agent(user_id, agent_id, battle_id)
        return jsonify(result), 200 if result.get('success') else 400
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@comprehensive_vidgenerator_bp.route('/hunter/agent/track-xp', methods=['POST'])
@comprehensive_vidgenerator_bp.route('/vidgenerator/api/vidgenerator/hunter/agent/track-xp', methods=['POST'])
def track_hunter_agent_xp():
    """Track XP for hunter game activities with agent integration"""
    try:
        from backend.services.hunters_leveling_system import hunters_leveling_system
        
        data = request.get_json() or {}
        user_id = data.get('user_id', 'default_user')
        agent_id = data.get('agent_id')
        xp_amount = int(data.get('xp_amount', 0))
        activity_type = data.get('activity_type', 'hunter_activity')
        metadata = data.get('metadata', {})
        
        if not agent_id:
            return jsonify({
                'success': False,
                'error': 'agent_id is required'
            }), 400
        
        result = hunters_leveling_system.track_agent_xp(
            user_id, agent_id, xp_amount, activity_type, metadata
        )
        return jsonify(result), 200 if result.get('success') else 400
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@comprehensive_vidgenerator_bp.route('/hunter/agent/recommendations', methods=['GET', 'POST'])
@comprehensive_vidgenerator_bp.route('/vidgenerator/api/vidgenerator/hunter/agent/recommendations', methods=['GET', 'POST'])
def get_hunter_agent_recommendations():
    """Get agent recommendations for hunter game activities"""
    try:
        from backend.services.hunters_leveling_system import hunters_leveling_system
        
        if request.method == 'GET':
            user_id = request.args.get('user_id', 'default_user')
            agent_id = request.args.get('agent_id')
        else:
            data = request.get_json() or {}
            user_id = data.get('user_id', 'default_user')
            agent_id = data.get('agent_id')
        
        if not agent_id:
            return jsonify({
                'success': False,
                'error': 'agent_id is required'
            }), 400
        
        result = hunters_leveling_system.get_agent_recommendations(user_id, agent_id)
        return jsonify(result), 200 if result.get('success') else 400
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@comprehensive_vidgenerator_bp.route('/hunter/agent/apply-bonuses', methods=['POST'])
@comprehensive_vidgenerator_bp.route('/vidgenerator/api/vidgenerator/hunter/agent/apply-bonuses', methods=['POST'])
def apply_hunter_agent_bonuses():
    """Apply agent skill bonuses to XP calculation"""
    try:
        from backend.services.hunters_leveling_system import hunters_leveling_system
        
        data = request.get_json() or {}
        user_id = data.get('user_id', 'default_user')
        agent_id = data.get('agent_id')
        base_xp = int(data.get('base_xp', 0))
        
        if not agent_id:
            return jsonify({
                'success': False,
                'error': 'agent_id is required'
            }), 400
        
        result = hunters_leveling_system.apply_agent_skill_bonuses(user_id, agent_id, base_xp)
        return jsonify(result), 200 if result.get('success') else 400
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@comprehensive_vidgenerator_bp.route('/hunter/calculator/xp-requirements', methods=['GET', 'POST'])
@comprehensive_vidgenerator_bp.route('/vidgenerator/api/vidgenerator/hunter/calculator/xp-requirements', methods=['GET', 'POST'])
def calculate_hunter_xp_requirements():
    """Calculate XP requirements to reach a target level"""
    try:
        from backend.services.hunters_leveling_system import hunters_leveling_system
        
        if request.method == 'GET':
            target_level = int(request.args.get('target_level', 10))
            current_level = int(request.args.get('current_level', 1))
            current_xp = int(request.args.get('current_xp', 0))
        else:
            data = request.get_json() or {}
            target_level = int(data.get('target_level', 10))
            current_level = int(data.get('current_level', 1))
            current_xp = int(data.get('current_xp', 0))
        
        result = hunters_leveling_system.calculate_xp_requirements(
            target_level, current_level, current_xp
        )
        return jsonify(result), 200 if result.get('success') else 400
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@comprehensive_vidgenerator_bp.route('/hunter/calculator/level-progression', methods=['GET', 'POST'])
@comprehensive_vidgenerator_bp.route('/vidgenerator/api/vidgenerator/hunter/calculator/level-progression', methods=['GET', 'POST'])
def calculate_hunter_level_progression():
    """Calculate level progression predictions"""
    try:
        from backend.services.hunters_leveling_system import hunters_leveling_system
        
        if request.method == 'GET':
            user_id = request.args.get('user_id', 'default_user')
            days = int(request.args.get('days', 7))
            daily_xp = request.args.get('daily_xp')
            daily_xp = int(daily_xp) if daily_xp else None
        else:
            data = request.get_json() or {}
            user_id = data.get('user_id', 'default_user')
            days = int(data.get('days', 7))
            daily_xp = data.get('daily_xp')
            daily_xp = int(daily_xp) if daily_xp else None
        
        result = hunters_leveling_system.calculate_level_progression(user_id, days, daily_xp)
        return jsonify(result), 200 if result.get('success') else 400
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@comprehensive_vidgenerator_bp.route('/hunter/calculator/rewards', methods=['GET', 'POST'])
@comprehensive_vidgenerator_bp.route('/vidgenerator/api/vidgenerator/hunter/calculator/rewards', methods=['GET', 'POST'])
def calculate_hunter_rewards():
    """Calculate rewards for a level or range of levels"""
    try:
        from backend.services.hunters_leveling_system import hunters_leveling_system
        
        if request.method == 'GET':
            level = int(request.args.get('level', 1))
            include_future = request.args.get('include_future', 'false').lower() == 'true'
            future_levels = int(request.args.get('future_levels', 10))
        else:
            data = request.get_json() or {}
            level = int(data.get('level', 1))
            include_future = data.get('include_future', False)
            future_levels = int(data.get('future_levels', 10))
        
        result = hunters_leveling_system.calculate_rewards(level, include_future, future_levels)
        return jsonify(result), 200 if result.get('success') else 400
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@comprehensive_vidgenerator_bp.route('/hunter/calculator/optimal-plan', methods=['POST'])
@comprehensive_vidgenerator_bp.route('/vidgenerator/api/vidgenerator/hunter/calculator/optimal-plan', methods=['POST'])
def calculate_hunter_optimal_plan():
    """Calculate optimal activity plan to reach target level"""
    try:
        from backend.services.hunters_leveling_system import hunters_leveling_system
        
        data = request.get_json() or {}
        user_id = data.get('user_id', 'default_user')
        target_level = int(data.get('target_level', 10))
        available_activities = data.get('available_activities', [])
        
        result = hunters_leveling_system.calculate_optimal_activity_plan(
            user_id, target_level, available_activities
        )
        return jsonify(result), 200 if result.get('success') else 400
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@comprehensive_vidgenerator_bp.route('/generator/trigger', methods=['POST'])
@comprehensive_vidgenerator_bp.route('/vidgenerator/api/vidgenerator/generator/trigger', methods=['POST'])
def trigger_generation():
    """Trigger-based generation instead of instant"""
    try:
        data = request.get_json() or {}
        user_id = data.get('user_id', 'default_user')
        prompt = data.get('prompt')
        
        if not prompt:
            return jsonify({
                'success': False,
                'error': 'prompt required'
            }), 400
        
        # Register trigger for generation
        expected_pointers = [
            'energy_sufficient',
            'points_available',
            'generation_ready'
        ]
        
        trigger_id = trigger_based_generator.register_trigger(
            'video_generation',
            {
                'user_id': user_id,
                'prompt': prompt,
                'data': data
            },
            expected_pointers
        )
        
        return jsonify({
            'success': True,
            'trigger_id': trigger_id,
            'message': 'Generation trigger registered. Waiting for expected pointers.',
            'expected_pointers': expected_pointers
        }), 200
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# ============================================================================
# PAGE ROUTES DISCOVERY
# ============================================================================

@comprehensive_vidgenerator_bp.route('/pages/list', methods=['GET'])
@comprehensive_vidgenerator_bp.route('/vidgenerator/api/vidgenerator/pages/list', methods=['GET'])
def list_all_pages():
    """List all pages in vidgenerator"""
    try:
        auditor = VidgeneratorAuditor()
        pages = auditor._find_all_pages()
        
        return jsonify({
            'success': True,
            'pages': pages,
            'count': len(pages)
        }), 200
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

