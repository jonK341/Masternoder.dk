"""
Comprehensive Skills and Abilities Routes
Complete system for understanding and managing all skills and abilities
"""
from flask import Blueprint, request, jsonify
from src.utils.rate_limiter import rate_limit
from src.utils.error_handler import ErrorHandler
import uuid

comprehensive_skills_abilities_bp = Blueprint('comprehensive_skills_abilities', __name__)

# Note: Middleware strips /vidgenerator, so /vidgenerator/api/* becomes /api/* before matching
# Only need /api/* route - middleware handles the prefix

@comprehensive_skills_abilities_bp.route('/api/skills/list', methods=['GET'])
@rate_limit()
def get_all_skills():
    """Get comprehensive list of all skills with details"""
    try:
        user_id = request.args.get('user_id', 'default_user')
        
        # Try to get from skills tracker
        try:
            from backend.services.skills_abilities_tracker import skills_abilities_tracker
            result = skills_abilities_tracker.get_all_skills_abilities(user_id)
            skills = result.get('skills', {})
            
            # Format skills by category
            formatted_skills = {}
            for category, skill_list in skills.items():
                formatted_skills[category] = [
                    {
                        'name': skill_name,
                        'value': skill_data.get('value', 0),
                        'level': skill_data.get('level', 1),
                        'max_level': skill_data.get('max_level', 100),
                        'description': skill_data.get('description', ''),
                        'category': category
                    }
                    for skill_name, skill_data in skill_list.items()
                ] if isinstance(skill_list, dict) else skill_list
            
            return jsonify({
                'success': True,
                'skills': formatted_skills,
                'total_skills': sum(len(v) if isinstance(v, (list, dict)) else 1 for v in formatted_skills.values()),
                'user_id': user_id
            }), 200
        except ImportError:
            # Fallback: return skill categories structure
            return jsonify({
                'success': True,
                'skills': {
                    'combat': [],
                    'magic': [],
                    'tech': [],
                    'social': [],
                    'creative': [],
                    'physical': []
                },
                'total_skills': 0,
                'user_id': user_id
            }), 200
    except Exception as e:
        request_id = str(uuid.uuid4())[:8]
        error_response, status_code = ErrorHandler.create_error_response(e, 500, request_id)
        return error_response, status_code

@comprehensive_skills_abilities_bp.route('/api/abilities/list', methods=['GET'])
@rate_limit()
def get_all_abilities_list():
    """Get comprehensive list of all abilities with details"""
    try:
        user_id = request.args.get('user_id', 'default_user')
        
        # Try multiple sources
        abilities_list = []
        
        # Try enhanced skills system
        try:
            from backend.services.enhanced_skills_system import enhanced_skills_system
            result = enhanced_skills_system.get_all_abilities()
            if result.get('success') and result.get('abilities'):
                abilities_list = result['abilities']
        except:
            pass
        
        # Try skills tracker
        if not abilities_list:
            try:
                from backend.services.skills_abilities_tracker import skills_abilities_tracker
                result = skills_abilities_tracker.get_all_skills_abilities(user_id)
                abilities = result.get('abilities', {})
                abilities_list = [
                    {
                        'id': ability_id,
                        'name': ability_data.get('name', ability_id),
                        'description': ability_data.get('description', ''),
                        'unlocked': ability_data.get('unlocked', False),
                        'level': ability_data.get('level', 0),
                        'category': ability_data.get('category', 'general')
                    }
                    for ability_id, ability_data in abilities.items()
                ] if isinstance(abilities, dict) else abilities
            except:
                pass
        
        return jsonify({
            'success': True,
            'abilities': abilities_list,
            'total_abilities': len(abilities_list),
            'unlocked_count': sum(1 for a in abilities_list if a.get('unlocked', False)),
            'user_id': user_id
        }), 200
    except Exception as e:
        request_id = str(uuid.uuid4())[:8]
        error_response, status_code = ErrorHandler.create_error_response(e, 500, request_id)
        return error_response, status_code


# Alias: points -> skills/abilities (fixes /api/points/skills-abilities 404)
@comprehensive_skills_abilities_bp.route('/api/points/skills-abilities', methods=['GET'])
@comprehensive_skills_abilities_bp.route('/vidgenerator/api/points/skills-abilities', methods=['GET'])
@rate_limit()
def get_points_skills_abilities_alias():
    """Return skills & abilities in a points-oriented wrapper"""
    try:
        user_id = request.args.get('user_id', 'default_user')
        # Reuse comprehensive endpoint if possible
        try:
            from backend.services.skills_abilities_tracker import skills_abilities_tracker
            data = skills_abilities_tracker.get_all_skills_abilities(user_id)
        except Exception:
            data = {'skills': {}, 'abilities': {}}
        return jsonify({
            'success': True,
            'user_id': user_id,
            'skills_abilities': data
        }), 200
    except Exception as e:
        # Return 200 with empty payload to avoid breaking frontend
        return jsonify({
            'success': True,
            'user_id': request.args.get('user_id', 'default_user'),
            'skills_abilities': {},
            'error': str(e)
        }), 200

@comprehensive_skills_abilities_bp.route('/api/skills/abilities/comprehensive', methods=['GET'])
@rate_limit()
def get_comprehensive_skills_abilities():
    """Get comprehensive skills and abilities data with full details"""
    try:
        user_id = request.args.get('user_id', 'default_user')
        
        result = {
            'success': True,
            'user_id': user_id,
            'skills': {},
            'abilities': [],
            'aggregator_resources': {},
            'total_skill_points': 0,
            'total_ability_points': 0,
            'unlocked_abilities': 0
        }
        
        # Get from skills tracker
        try:
            from backend.services.skills_abilities_tracker import skills_abilities_tracker
            data = skills_abilities_tracker.get_all_skills_abilities(user_id)
            result['skills'] = data.get('skills', {})
            result['abilities'] = data.get('abilities', {})
            result['aggregator_resources'] = data.get('aggregator_resources', {})
            
            # Calculate totals
            for category_skills in result['skills'].values():
                if isinstance(category_skills, dict):
                    for skill_data in category_skills.values():
                        result['total_skill_points'] += skill_data.get('value', 0)
                elif isinstance(category_skills, list):
                    for skill_data in category_skills:
                        result['total_skill_points'] += skill_data.get('value', 0)
            
            if isinstance(result['abilities'], dict):
                result['unlocked_abilities'] = sum(1 for a in result['abilities'].values() if a.get('unlocked', False))
            elif isinstance(result['abilities'], list):
                result['unlocked_abilities'] = sum(1 for a in result['abilities'] if a.get('unlocked', False))
        except:
            pass
        
        return jsonify(result), 200
    except Exception as e:
        request_id = str(uuid.uuid4())[:8]
        error_response, status_code = ErrorHandler.create_error_response(e, 500, request_id)
        return error_response, status_code

@comprehensive_skills_abilities_bp.route('/api/skills/<skill_name>/details', methods=['GET'])
@rate_limit()
def get_skill_details(skill_name):
    """Get detailed information about a specific skill"""
    try:
        user_id = request.args.get('user_id', 'default_user')
        
        try:
            from backend.services.skills_abilities_tracker import skills_abilities_tracker
            data = skills_abilities_tracker.get_all_skills_abilities(user_id)
            skills = data.get('skills', {})
            
            # Find skill across all categories
            for category, category_skills in skills.items():
                if isinstance(category_skills, dict) and skill_name in category_skills:
                    skill_data = category_skills[skill_name]
                    return jsonify({
                        'success': True,
                        'skill': {
                            'name': skill_name,
                            'category': category,
                            'value': skill_data.get('value', 0),
                            'level': skill_data.get('level', 1),
                            'max_level': skill_data.get('max_level', 100),
                            'description': skill_data.get('description', ''),
                            'source': skill_data.get('source', 'default')
                        }
                    }), 200
        except:
            pass
        
        return jsonify({
            'success': False,
            'error': 'Skill not found'
        }), 404
    except Exception as e:
        request_id = str(uuid.uuid4())[:8]
        error_response, status_code = ErrorHandler.create_error_response(e, 500, request_id)
        return error_response, status_code

@comprehensive_skills_abilities_bp.route('/api/abilities/<ability_id>/details', methods=['GET'])
@rate_limit()
def get_ability_details(ability_id):
    """Get detailed information about a specific ability"""
    try:
        user_id = request.args.get('user_id', 'default_user')
        
        # Try enhanced skills system
        try:
            from backend.services.enhanced_skills_system import enhanced_skills_system
            result = enhanced_skills_system.get_user_abilities(user_id)
            if result.get('success') and result.get('abilities'):
                for ability in result['abilities']:
                    if ability.get('id') == ability_id:
                        return jsonify({
                            'success': True,
                            'ability': ability
                        }), 200
        except:
            pass
        
        # Try skills tracker
        try:
            from backend.services.skills_abilities_tracker import skills_abilities_tracker
            data = skills_abilities_tracker.get_all_skills_abilities(user_id)
            abilities = data.get('abilities', {})
            if isinstance(abilities, dict) and ability_id in abilities:
                ability_data = abilities[ability_id]
                return jsonify({
                    'success': True,
                    'ability': {
                        'id': ability_id,
                        'name': ability_data.get('name', ability_id),
                        'description': ability_data.get('description', ''),
                        'unlocked': ability_data.get('unlocked', False),
                        'level': ability_data.get('level', 0),
                        'category': ability_data.get('category', 'general')
                    }
                }), 200
        except:
            pass
        
        return jsonify({
            'success': False,
            'error': 'Ability not found'
        }), 404
    except Exception as e:
        request_id = str(uuid.uuid4())[:8]
        error_response, status_code = ErrorHandler.create_error_response(e, 500, request_id)
        return error_response, status_code
