"""
Monetization & Top 50 Routes
Cash generation, top 50 leaderboard, top 6 trophies, and resources
"""
from flask import Blueprint, jsonify, request
import logging

logger = logging.getLogger(__name__)

try:
    from backend.services.monetization_cash_generator import monetization_cash_generator
except ImportError:
    monetization_cash_generator = None
    logger.warning("monetization_cash_generator not available")

try:
    from backend.services.victory_trophy_generator import victory_trophy_generator
except ImportError:
    victory_trophy_generator = None
    logger.warning("victory_trophy_generator not available")

try:
    from backend.services.tech_tree_knowledge import tech_tree_knowledge
except ImportError:
    tech_tree_knowledge = None
    logger.warning("tech_tree_knowledge not available")

try:
    from backend.services.insane_battle_system import insane_battle_system
except ImportError:
    insane_battle_system = None
    logger.warning("insane_battle_system not available")

monetization_top50_bp = Blueprint('monetization_top50', __name__)


@monetization_top50_bp.route('/api/monetization/generate-cash', methods=['POST'])
@monetization_top50_bp.route('/vidgenerator/api/monetization/generate-cash', methods=['POST'])
def generate_cash():
    """Generate cash from source"""
    try:
        data = request.get_json() or {}
        user_id = data.get('user_id', 'default_user')
        source = data.get('source', 'content_creation')
        amount = data.get('amount')
        metadata = data.get('metadata', {})
        
        result = monetization_cash_generator.generate_cash(user_id, source, amount, metadata)
        return jsonify(result), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@monetization_top50_bp.route('/api/monetization/top50', methods=['GET'])
@monetization_top50_bp.route('/api/monetization/top-50', methods=['GET'])
@monetization_top50_bp.route('/vidgenerator/api/monetization/top50', methods=['GET'])
@monetization_top50_bp.route('/vidgenerator/api/monetization/top-50', methods=['GET'])
def get_top_50():
    """Get top 50 earners"""
    try:
        if monetization_cash_generator is None:
            return jsonify({
                'success': False,
                'error': 'Monetization service not available',
                'top50': [],
                'top_50': []
            }), 200
        
        limit = int(request.args.get('limit', 50))
        # Try with limit parameter first, fallback to no parameters
        try:
            top_50 = monetization_cash_generator.get_top_50(limit=limit)
        except TypeError:
            top_50 = monetization_cash_generator.get_top_50()
        # Handle both list and dict returns
        if isinstance(top_50, dict):
            result = top_50
            if 'top50' not in result:
                result['top50'] = result.get('top_50', [])
        else:
            result = {
                'success': True,
                'top50': top_50,
                'top_50': top_50,
                'count': len(top_50) if isinstance(top_50, list) else 0
            }
        return jsonify(result), 200
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Error getting top50: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e),
            'top50': [],
            'top_50': []
        }), 200  # Return 200 with empty data instead of 500


@monetization_top50_bp.route('/api/monetization/top-6', methods=['GET'])
@monetization_top50_bp.route('/vidgenerator/api/monetization/top-6', methods=['GET'])
def get_top_6():
    """Get top 6 earners with trophies and resources"""
    try:
        top_6 = monetization_cash_generator.get_top_6()
        
        # Generate trophies and resources for top 6
        trophies_result = victory_trophy_generator.get_top_6_trophies(top_6)
        
        return jsonify({
            'success': True,
            'top_6': top_6,
            'trophies': trophies_result,
            'count': len(top_6)
        }), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@monetization_top50_bp.route('/api/monetization/cash', methods=['GET'])
@monetization_top50_bp.route('/api/monetization/user-cash', methods=['GET'])
@monetization_top50_bp.route('/vidgenerator/api/monetization/cash', methods=['GET'])
@monetization_top50_bp.route('/vidgenerator/api/monetization/user-cash', methods=['GET'])
def get_user_cash():
    """Get user cash status"""
    try:
        if monetization_cash_generator is None:
            return jsonify({
                'success': False,
                'error': 'Monetization service not available',
                'total_cash': 0,
                'cash_sources': {}
            }), 200
        
        user_id = request.args.get('user_id', 'default_user')
        result = monetization_cash_generator.get_user_cash(user_id)
        # Ensure response has success and total_cash
        if 'success' not in result:
            result['success'] = True
        if 'total_cash' not in result:
            result['total_cash'] = 0
        return jsonify(result), 200
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Error getting user cash: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e),
            'total_cash': 0,
            'cash_sources': {}
        }), 200  # Return 200 with empty data instead of 500


@monetization_top50_bp.route('/api/trophies/generate', methods=['POST'])
@monetization_top50_bp.route('/vidgenerator/api/trophies/generate', methods=['POST'])
def generate_trophies():
    """Generate trophies and resources"""
    try:
        data = request.get_json() or {}
        user_id = data.get('user_id', 'default_user')
        rank = data.get('rank', 1)
        
        result = victory_trophy_generator.generate_trophy_for_rank(user_id, rank)
        return jsonify(result), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@monetization_top50_bp.route('/api/trophies/user', methods=['GET'])
@monetization_top50_bp.route('/vidgenerator/api/trophies/user', methods=['GET'])
def get_user_trophies():
    """Get user trophies"""
    try:
        user_id = request.args.get('user_id', 'default_user')
        result = victory_trophy_generator.get_user_trophies(user_id)
        return jsonify(result), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@monetization_top50_bp.route('/api/knowledge/unlock', methods=['POST'])
@monetization_top50_bp.route('/vidgenerator/api/knowledge/unlock', methods=['POST'])
def unlock_knowledge():
    """Unlock knowledge node"""
    try:
        data = request.get_json() or {}
        user_id = data.get('user_id', 'default_user')
        knowledge_id = data.get('knowledge_id')
        
        if not knowledge_id:
            return jsonify({'success': False, 'error': 'knowledge_id required'}), 400
        
        result = tech_tree_knowledge.unlock_knowledge(user_id, knowledge_id)
        return jsonify(result), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@monetization_top50_bp.route('/api/tech-tree/knowledge', methods=['GET'])
@monetization_top50_bp.route('/api/knowledge/user', methods=['GET'])
@monetization_top50_bp.route('/vidgenerator/api/tech-tree/knowledge', methods=['GET'])
@monetization_top50_bp.route('/vidgenerator/api/knowledge/user', methods=['GET'])
def get_user_knowledge():
    """Get user knowledge"""
    try:
        if tech_tree_knowledge is None:
            return jsonify({
                'success': False,
                'error': 'Tech tree knowledge service not available',
                'knowledge_nodes': []
            }), 200
        
        user_id = request.args.get('user_id', 'default_user')
        result = tech_tree_knowledge.get_user_knowledge(user_id)
        # Ensure response has knowledge_nodes array
        if 'knowledge_nodes' not in result:
            result['knowledge_nodes'] = []
        return jsonify(result), 200
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Error getting user knowledge: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e),
            'knowledge_nodes': []
        }), 200  # Return 200 with empty data instead of 500


@monetization_top50_bp.route('/api/battles/insane/create', methods=['POST'])
@monetization_top50_bp.route('/vidgenerator/api/battles/insane/create', methods=['POST'])
def create_insane_battle():
    """Create insane battle"""
    try:
        data = request.get_json() or {}
        user_id = data.get('user_id', 'default_user')
        battle_type = data.get('battle_type', 'insane_lock')
        
        result = insane_battle_system.create_insane_battle(user_id, battle_type)
        return jsonify(result), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@monetization_top50_bp.route('/api/battles/insane/complete', methods=['POST'])
@monetization_top50_bp.route('/vidgenerator/api/battles/insane/complete', methods=['POST'])
def complete_insane_battle():
    """Complete insane battle"""
    try:
        data = request.get_json() or {}
        battle_id = data.get('battle_id')
        victory = data.get('victory', False)
        
        if not battle_id:
            return jsonify({'success': False, 'error': 'battle_id required'}), 400
        
        result = insane_battle_system.complete_battle(battle_id, victory)
        return jsonify(result), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@monetization_top50_bp.route('/api/battles/insane/user', methods=['GET'])
@monetization_top50_bp.route('/vidgenerator/api/battles/insane/user', methods=['GET'])
def get_user_insane_battles():
    """Get user insane battles"""
    try:
        user_id = request.args.get('user_id', 'default_user')
        result = insane_battle_system.get_user_battles(user_id)
        return jsonify(result), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

