"""
Intelligent Points Routes
API endpoints for intelligent point middleware system
"""
from flask import Blueprint, request, jsonify
from backend.middleware.intelligent_point_middleware import intelligent_point_middleware
from backend.services.enhanced_178_systems_sync import enhanced_178_systems_sync
from backend.services.skills_abilities_tracker import skills_abilities_tracker
import logging

logger = logging.getLogger(__name__)

intelligent_points_bp = Blueprint('intelligent_points', __name__)

@intelligent_points_bp.route('/api/points/intelligent-update', methods=['POST'])
def intelligent_point_update():
    """Process point update through intelligent middleware"""
    try:
        data = request.get_json()
        user_id = data.get('user_id', 'default')
        point_type = data.get('point_type', 'unknown')
        amount = float(data.get('amount', 0))
        metadata = data.get('metadata', {})
        layers = data.get('layers', {})
        
        # Process through middleware
        result = intelligent_point_middleware.process_point_update(
            user_id, point_type, amount, metadata
        )
        
        return jsonify({
            'success': result['success'],
            'result': result,
            'layers_processed': len(layers)
        }), 200
    except Exception as e:
        logger.error(f"Error in intelligent point update: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@intelligent_points_bp.route('/api/points/sync-all', methods=['GET'])
def sync_all_points():
    """Sync all 178 systems plus special systems"""
    try:
        user_id = request.args.get('user_id', 'default')
        
        # Sync all systems
        sync_result = enhanced_178_systems_sync.sync_all_systems(user_id)
        
        # Get skills and abilities
        skills_abilities = skills_abilities_tracker.get_all_skills_abilities(user_id)
        
        # Get all points from middleware
        all_points = intelligent_point_middleware.get_all_points(user_id)
        
        return jsonify({
            'success': True,
            'points': all_points,
            'sync_result': sync_result,
            'skills_abilities': skills_abilities
        }), 200
    except Exception as e:
        logger.error(f"Error syncing all points: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# Note: Middleware strips /vidgenerator, so /vidgenerator/api/* becomes /api/* before matching
# Adding both variants to ensure route matching
@intelligent_points_bp.route('/api/points/skills-abilities', methods=['GET', 'POST'])
@intelligent_points_bp.route('/vidgenerator/api/points/skills-abilities', methods=['GET', 'POST'])
def skills_abilities_endpoint():
    """Get or update skills and abilities"""
    if request.method == 'GET':
        # GET: Return all skills and abilities for user
        try:
            user_id = request.args.get('user_id', 'default_user')
            result = skills_abilities_tracker.get_all_skills_abilities(user_id)
            return jsonify({
                'success': True,
                'skills_abilities': result,
                'user_id': user_id
            }), 200
        except Exception as e:
            logger.error(f"Error getting skills/abilities: {e}", exc_info=True)
            return jsonify({
                'success': False,
                'error': str(e),
                'skills_abilities': {}
            }), 200  # Return 200 with empty data
    else:
        # POST: Update skills and abilities
        try:
            data = request.get_json() or {}
            user_id = data.get('user_id', 'default_user')
            skill_category = data.get('skill_category')
            skill_name = data.get('skill_name')
            ability_name = data.get('ability_name')
            value = float(data.get('value', 0))
            source = data.get('source', 'default')
            
            if skill_category and skill_name:
                skills_abilities_tracker.update_skill(
                    user_id, skill_category, skill_name, value, source
                )
            elif ability_name:
                skills_abilities_tracker.update_ability(
                    user_id, ability_name, value, source
                )
            else:
                return jsonify({
                    'success': False,
                    'error': 'Missing skill_category/skill_name or ability_name'
                }), 400
            
            return jsonify({
                'success': True,
                'message': 'Skills/abilities updated'
            }), 200
        except Exception as e:
            logger.error(f"Error updating skills/abilities: {e}", exc_info=True)
            return jsonify({
                'success': False,
                'error': str(e)
            }), 200  # Return 200 to avoid breaking frontend

@intelligent_points_bp.route('/api/points/special-systems', methods=['POST'])
def update_special_systems():
    """Update special point systems"""
    try:
        data = request.get_json()
        user_id = data.get('user_id', 'default')
        system_type = data.get('system_type')  # pussyhul_32, birthday_rewards, tech_power, shadows_power, secret_resources
        amount = float(data.get('amount', 0))
        metadata = data.get('metadata', {})
        
        if system_type == 'tech_power':
            enhanced_178_systems_sync.update_tech_power(user_id, amount, metadata.get('source', 'default'))
        elif system_type == 'shadows_power':
            enhanced_178_systems_sync.update_shadows_power(user_id, amount, metadata.get('source', 'default'))
        elif system_type == 'secret_resources':
            resource_type = metadata.get('resource_type', 'default')
            enhanced_178_systems_sync.update_secret_resources(user_id, resource_type, amount)
        else:
            return jsonify({
                'success': False,
                'error': f'Unknown system type: {system_type}'
            }), 400
        
        return jsonify({
            'success': True,
            'message': f'{system_type} updated'
        }), 200
    except Exception as e:
        logger.error(f"Error updating special system: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

