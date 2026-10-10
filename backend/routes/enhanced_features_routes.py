"""
Enhanced Features Routes
Routes for enhanced click activity, trophies, and new systems
"""
from flask import Blueprint, request, jsonify
import logging
from typing import Dict, Any, List

logger = logging.getLogger(__name__)

enhanced_features_bp = Blueprint('enhanced_features', __name__, url_prefix='/api/enhanced')

@enhanced_features_bp.route('/click/award', methods=['POST'])
def award_enhanced_click():
    """Award enhanced points for click activity"""
    try:
        from backend.services.enhanced_click_activity import enhanced_click_activity
        from backend.services.unified_points_database import unified_points_db
        
        data = request.get_json() or {}
        user_id = data.get('user_id', 'default_user')
        metadata = data.get('metadata', {})
        
        # Calculate enhanced points
        point_calc = enhanced_click_activity.calculate_click_points(user_id, metadata)
        
        # Award points
        unified_points_db.add_points(
            user_id,
            'activity',
            point_calc['total_points'],
            source='enhanced_click'
        )
        
        return jsonify({
            'success': True,
            'points_awarded': point_calc['total_points'],
            'breakdown': {
                'base': point_calc['base_points'],
                'combo_bonus': point_calc['combo_bonus'],
                'streak_bonus': point_calc['streak_bonus'],
                'level_bonus': point_calc['level_bonus'],
                'critical_bonus': point_calc['critical_bonus'],
                'is_critical': point_calc['is_critical']
            },
            'multiplier': point_calc['multiplier']
        })
    except Exception as e:
        logger.error(f"Error awarding enhanced click: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@enhanced_features_bp.route('/trophy/award', methods=['POST'])
def award_trophy():
    """Award a trophy to a user"""
    try:
        from backend.services.trophy_system import trophy_system
        
        data = request.get_json() or {}
        user_id = data.get('user_id', 'default_user')
        trophy_type = data.get('trophy_type')
        metadata = data.get('metadata', {})
        
        if not trophy_type:
            return jsonify({
                'success': False,
                'error': 'Trophy type required'
            }), 400
        
        result = trophy_system.award_trophy(user_id, trophy_type, metadata)
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error awarding trophy: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@enhanced_features_bp.route('/trophy/list', methods=['GET'])
def list_trophies():
    """List all available trophies"""
    try:
        from backend.services.trophy_system import trophy_system
        
        user_id = request.args.get('user_id', '')
        user_trophies = []
        
        if user_id:
            user_trophies = trophy_system.get_user_trophies(user_id)
        
        return jsonify({
            'success': True,
            'available_trophies': list(trophy_system.trophy_definitions.keys()),
            'trophy_definitions': trophy_system.trophy_definitions,
            'user_trophies': user_trophies if user_id else []
        })
    except Exception as e:
        logger.error(f"Error listing trophies: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@enhanced_features_bp.route('/hunter/levels', methods=['GET'])
def get_hunter_levels():
    """Get hunter game level information"""
    try:
        # Hunter levels 1-100
        levels = []
        for level in range(1, 101):
            level_info = {
                'level': level,
                'name': get_hunter_level_name(level),
                'tier': get_hunter_tier(level),
                'required_xp': calculate_required_xp(level),
                'unlocks': get_level_unlocks(level),
                'multiplier': 1.0 + (level * 0.01)  # 1% per level
            }
            levels.append(level_info)
        
        return jsonify({
            'success': True,
            'total_levels': 100,
            'levels': levels
        })
    except Exception as e:
        logger.error(f"Error getting hunter levels: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

def get_hunter_level_name(level: int) -> str:
    """Get name for hunter level"""
    if level <= 10:
        return f'Novice Hunter {level}'
    elif level <= 20:
        return f'Apprentice Hunter {level}'
    elif level <= 30:
        return f'Skilled Hunter {level}'
    elif level <= 40:
        return f'Expert Hunter {level}'
    elif level <= 50:
        return f'Master Hunter {level}'
    elif level <= 60:
        return f'Elite Hunter {level}'
    elif level <= 70:
        return f'Advanced Hunter {level}'
    elif level <= 80:
        return f'Legendary Hunter {level}'
    elif level <= 90:
        return f'Mythic Hunter {level}'
    else:
        return f'Divine Hunter {level}'

def get_hunter_tier(level: int) -> str:
    """Get tier for hunter level"""
    if level <= 50:
        return 'Standard'
    elif level <= 60:
        return 'Elite'
    elif level <= 70:
        return 'Master'
    elif level <= 80:
        return 'Legendary'
    elif level <= 90:
        return 'Mythic'
    else:
        return 'Divine'

def calculate_required_xp(level: int) -> int:
    """Calculate required XP for level"""
    base_xp = 100
    return int(base_xp * (level ** 1.5))

def get_level_unlocks(level: int) -> List[str]:
    """Get unlocks for a specific level"""
    unlocks = []
    
    if level % 10 == 0:
        unlocks.append(f'Level {level} Ability')
    if level >= 51:
        unlocks.append('Elite Hunter Access')
    if level >= 61:
        unlocks.append('Master Hunter Access')
    if level >= 71:
        unlocks.append('Legendary Hunter Access')
    if level >= 81:
        unlocks.append('Mythic Hunter Access')
    if level >= 91:
        unlocks.append('Divine Hunter Access')
    
    return unlocks
