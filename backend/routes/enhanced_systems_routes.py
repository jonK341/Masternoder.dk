"""
Routes for Enhanced Systems
- Enhanced Tech Tree with Quests
- Enhanced Skills System
- Enhanced User Profile JSON
- Unified Point System JSON Storage
"""
from flask import Blueprint, jsonify, request
from backend.services.enhanced_tech_tree_with_quests import enhanced_tech_tree_quests
from backend.services.enhanced_skills_system import enhanced_skills_system
from backend.services.enhanced_user_profile_json import enhanced_user_profile_json
from backend.services.unified_point_system_json_storage import unified_point_json_storage

enhanced_systems_bp = Blueprint('enhanced_systems', __name__)


# Enhanced Tech Tree Routes
@enhanced_systems_bp.route('/api/tech-tree/quests/add', methods=['POST'])
@enhanced_systems_bp.route('/vidgenerator/api/tech-tree/quests/add', methods=['POST'])
def add_quest_to_tech():
    """Add quest to tech tree node"""
    try:
        data = request.get_json() or {}
        tech_id = data.get('tech_id')
        quest_id = data.get('quest_id')
        quest_data = data.get('quest_data', {})
        
        if not tech_id or not quest_id:
            return jsonify({
                'success': False,
                'error': 'tech_id and quest_id required'
            }), 400
        
        result = enhanced_tech_tree_quests.add_quest_to_tech(tech_id, quest_id, quest_data)
        return jsonify(result), 200
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@enhanced_systems_bp.route('/api/tech-tree/conclusion/add', methods=['POST'])
@enhanced_systems_bp.route('/vidgenerator/api/tech-tree/conclusion/add', methods=['POST'])
def add_research_conclusion():
    """Add research conclusion to tech tree node"""
    try:
        data = request.get_json() or {}
        tech_id = data.get('tech_id')
        conclusion_data = data.get('conclusion_data', {})
        
        if not tech_id:
            return jsonify({
                'success': False,
                'error': 'tech_id required'
            }), 400
        
        result = enhanced_tech_tree_quests.add_research_conclusion(tech_id, conclusion_data)
        return jsonify(result), 200
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@enhanced_systems_bp.route('/api/tech-tree/with-quests', methods=['GET'])
@enhanced_systems_bp.route('/vidgenerator/api/tech-tree/with-quests', methods=['GET'])
def get_tech_with_quests():
    """Get tech tree with quests and conclusions"""
    try:
        user_id = request.args.get('user_id', 'default_user')
        tech_id = request.args.get('tech_id')
        
        if tech_id:
            result = enhanced_tech_tree_quests.get_tech_with_quests(user_id, tech_id)
        else:
            result = enhanced_tech_tree_quests.get_all_tech_with_quests(user_id)
        
        return jsonify(result), 200
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# Enhanced Skills Routes
# Note: Middleware strips /vidgenerator, so /vidgenerator/api/* becomes /api/* before matching
# Only need /api/* route - middleware handles the prefix
@enhanced_systems_bp.route('/api/skills/abilities', methods=['GET'])
def get_all_abilities():
    """Get all available abilities"""
    try:
        result = enhanced_skills_system.get_all_abilities()
        return jsonify(result), 200
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'abilities': []
        }), 200  # Return 200 with empty data

@enhanced_systems_bp.route('/api/skills/list', methods=['GET'])
def get_all_skills():
    """Get all available skills"""
    try:
        user_id = request.args.get('user_id', 'default_user')
        try:
            from backend.services.skills_abilities_tracker import skills_abilities_tracker
            result = skills_abilities_tracker.get_all_skills_abilities(user_id)
            return jsonify({
                'success': True,
                'skills': result.get('skills', {}),
                'user_id': user_id
            }), 200
        except ImportError:
            return jsonify({
                'success': True,
                'skills': {},
                'user_id': user_id
            }), 200
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'skills': {}
        }), 200

@enhanced_systems_bp.route('/api/abilities/list', methods=['GET'])
def get_all_abilities_list():
    """Get all available abilities list"""
    try:
        user_id = request.args.get('user_id', 'default_user')
        try:
            from backend.services.skills_abilities_tracker import skills_abilities_tracker
            result = skills_abilities_tracker.get_all_skills_abilities(user_id)
            return jsonify({
                'success': True,
                'abilities': result.get('abilities', {}),
                'user_id': user_id
            }), 200
        except ImportError:
            try:
                from backend.services.enhanced_skills_system import enhanced_skills_system
                result = enhanced_skills_system.get_all_abilities()
                return jsonify({
                    'success': True,
                    'abilities': result.get('abilities', []),
                    'user_id': user_id
                }), 200
            except:
                return jsonify({
                    'success': True,
                    'abilities': [],
                    'user_id': user_id
                }), 200
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'abilities': []
        }), 200


@enhanced_systems_bp.route('/api/skills/unlock', methods=['POST'])
@enhanced_systems_bp.route('/vidgenerator/api/skills/unlock', methods=['POST'])
def unlock_ability():
    """Unlock an ability"""
    try:
        data = request.get_json() or {}
        user_id = data.get('user_id', 'default_user')
        ability_id = data.get('ability_id')
        quest_id = data.get('quest_id')
        
        if not ability_id:
            return jsonify({
                'success': False,
                'error': 'ability_id required'
            }), 400
        
        result = enhanced_skills_system.unlock_ability(user_id, ability_id, quest_id)
        return jsonify(result), 200 if result.get('success') else 400
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@enhanced_systems_bp.route('/api/skills/user', methods=['GET'])
@enhanced_systems_bp.route('/vidgenerator/api/skills/user', methods=['GET'])
def get_user_abilities():
    """Get user's abilities"""
    try:
        user_id = request.args.get('user_id', 'default_user')
        result = enhanced_skills_system.get_user_abilities(user_id)
        return jsonify(result), 200
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# Enhanced User Profile Routes
@enhanced_systems_bp.route('/api/profile/get', methods=['GET'])
@enhanced_systems_bp.route('/vidgenerator/api/profile/get', methods=['GET'])
def get_user_profile():
    """Get user profile"""
    try:
        user_id = request.args.get('user_id', 'default_user')
        result = enhanced_user_profile_json.get_profile(user_id)
        return jsonify({
            'success': True,
            'profile': result
        }), 200
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@enhanced_systems_bp.route('/api/profile/update', methods=['POST'])
@enhanced_systems_bp.route('/vidgenerator/api/profile/update', methods=['POST'])
def update_user_profile():
    """Update user profile"""
    try:
        data = request.get_json() or {}
        user_id = data.get('user_id', 'default_user')
        updates = data.get('updates', {})
        
        result = enhanced_user_profile_json.update_profile(user_id, updates)
        return jsonify({
            'success': True,
            'profile': result
        }), 200
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# Unified Point System JSON Storage Routes
@enhanced_systems_bp.route('/api/points/json/get', methods=['GET'])
@enhanced_systems_bp.route('/vidgenerator/api/points/json/get', methods=['GET'])
def get_points_json():
    """Get points from JSON storage (fast refresh)"""
    try:
        user_id = request.args.get('user_id', 'default_user')
        force_refresh = request.args.get('force_refresh', 'false').lower() == 'true'
        
        result = unified_point_json_storage.get_all_points(user_id, force_refresh=force_refresh)
        return jsonify({
            'success': True,
            'points': result
        }), 200
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@enhanced_systems_bp.route('/api/points/json/increment', methods=['POST'])
@enhanced_systems_bp.route('/vidgenerator/api/points/json/increment', methods=['POST'])
def increment_point():
    """Increment a point type (fast refresh)"""
    try:
        data = request.get_json() or {}
        user_id = data.get('user_id', 'default_user')
        point_type = data.get('point_type')
        amount = data.get('amount', 1)
        
        if not point_type:
            return jsonify({
                'success': False,
                'error': 'point_type required'
            }), 400
        
        result = unified_point_json_storage.increment_point(user_id, point_type, amount)
        return jsonify(result), 200
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

