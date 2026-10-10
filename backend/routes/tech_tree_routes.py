"""
Technology Tree Routes
API endpoints for tech tree research system
"""
from flask import Blueprint, request, jsonify
import logging

logger = logging.getLogger(__name__)

try:
    try:
        from backend.services.tech_tree_system import tech_tree_system
    except ImportError:
        tech_tree_system = None
except ImportError:
    tech_tree_system = None
    logger.warning("tech_tree_system not available")

# Import utils - optional
try:
    from src.utils.input_validator import InputValidator
except ImportError:
    InputValidator = None
try:
    from src.utils.error_handler import ErrorHandler
except ImportError:
    ErrorHandler = None
# Import rate limiter - optional
try:
    from src.utils.rate_limiter import rate_limit
except ImportError:
    def rate_limit():
        def decorator(f):
            return f
        return decorator
import uuid

tech_tree_bp = Blueprint('tech_tree', __name__)

@tech_tree_bp.route('/api/tech-tree', methods=['GET'])
@tech_tree_bp.route('/vidgenerator/api/tech-tree', methods=['GET'])
@rate_limit()
def get_tech_tree():
    """Get technology tree with user progress"""
    try:
        if tech_tree_system is None:
            return jsonify({
                'success': True,
                'tech_tree': {
                    'technologies': {},
                    'total_researched': 0,
                    'total_available': 0
                }
            }), 200
        
        user_id = request.args.get('user_id', 'default_user')
        result = tech_tree_system.get_tech_tree(user_id)
        # Ensure result has success and tech_tree keys
        if not isinstance(result, dict):
            result = {'success': True, 'tech_tree': {}}
        if 'success' not in result:
            result['success'] = True
        if 'tech_tree' not in result:
            result['tech_tree'] = result if isinstance(result, dict) else {}
        return jsonify(result), 200
    except Exception as e:
        logger.error(f"Error getting tech tree: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e),
            'tech_tree': {
                'technologies': {},
                'total_researched': 0,
                'total_available': 0
            }
        }), 200  # Return 200 with empty data instead of 500

@tech_tree_bp.route('/api/tech-tree/research/start', methods=['POST'])
@tech_tree_bp.route('/vidgenerator/api/tech-tree/research/start', methods=['POST'])
@rate_limit()
def start_research():
    """Start researching a technology"""
    try:
        data = InputValidator.get_json_safe(default={})
        user_id = InputValidator.sanitize_string(data.get('user_id', 'default_user'), max_length=50).strip()
        tech_id = InputValidator.sanitize_string(data.get('tech_id', ''), max_length=50).strip()
        
        if not tech_id:
            return jsonify({'success': False, 'error': 'tech_id is required'}), 400
        
        result = tech_tree_system.start_research(user_id, tech_id)
        return jsonify(result), 200 if result.get('success') else 400
    except Exception as e:
        request_id = str(uuid.uuid4())[:8]
        error_response, status_code = ErrorHandler.create_error_response(e, 500, request_id)
        return error_response, status_code

@tech_tree_bp.route('/api/tech-tree/research/complete', methods=['POST'])
@tech_tree_bp.route('/vidgenerator/api/tech-tree/research/complete', methods=['POST'])
@rate_limit()
def complete_research():
    """Complete a research"""
    try:
        data = InputValidator.get_json_safe(default={})
        user_id = InputValidator.sanitize_string(data.get('user_id', 'default_user'), max_length=50).strip()
        tech_id = InputValidator.sanitize_string(data.get('tech_id', ''), max_length=50).strip()
        
        if not tech_id:
            return jsonify({'success': False, 'error': 'tech_id is required'}), 400
        
        result = tech_tree_system.complete_research(user_id, tech_id)
        return jsonify(result), 200 if result.get('success') else 400
    except Exception as e:
        request_id = str(uuid.uuid4())[:8]
        error_response, status_code = ErrorHandler.create_error_response(e, 500, request_id)
        return error_response, status_code

@tech_tree_bp.route('/api/tech-tree/research/progress', methods=['POST'])
@tech_tree_bp.route('/vidgenerator/api/tech-tree/research/progress', methods=['POST'])
@rate_limit()
def update_research_progress():
    """Update research progress"""
    try:
        data = InputValidator.get_json_safe(default={})
        user_id = InputValidator.sanitize_string(data.get('user_id', 'default_user'), max_length=50).strip()
        tech_id = InputValidator.sanitize_string(data.get('tech_id', ''), max_length=50).strip()
        progress = float(data.get('progress', 0))
        
        if not tech_id:
            return jsonify({'success': False, 'error': 'tech_id is required'}), 400
        
        result = tech_tree_system.update_research_progress(user_id, tech_id, progress)
        return jsonify(result), 200 if result.get('success') else 400
    except Exception as e:
        request_id = str(uuid.uuid4())[:8]
        error_response, status_code = ErrorHandler.create_error_response(e, 500, request_id)
        return error_response, status_code

@tech_tree_bp.route('/api/tech-tree/user/<user_id>', methods=['GET'])
@tech_tree_bp.route('/vidgenerator/api/tech-tree/user/<user_id>', methods=['GET'])
@rate_limit()
def get_user_research(user_id: str):
    """Get user's research progress"""
    try:
        result = tech_tree_system.get_user_research(user_id)
        return jsonify(result), 200
    except Exception as e:
        request_id = str(uuid.uuid4())[:8]
        error_response, status_code = ErrorHandler.create_error_response(e, 500, request_id)
        return error_response, status_code

@tech_tree_bp.route('/api/tech-tree/bonuses/<user_id>', methods=['GET'])
@tech_tree_bp.route('/vidgenerator/api/tech-tree/bonuses/<user_id>', methods=['GET'])
@rate_limit()
def get_research_bonuses(user_id: str):
    """Get user's research bonuses"""
    try:
        result = tech_tree_system.get_research_bonuses(user_id)
        return jsonify(result), 200
    except Exception as e:
        request_id = str(uuid.uuid4())[:8]
        error_response, status_code = ErrorHandler.create_error_response(e, 500, request_id)
        return error_response, status_code

@tech_tree_bp.route('/api/tech-tree/learn', methods=['POST'])
@tech_tree_bp.route('/vidgenerator/api/tech-tree/learn', methods=['POST'])
@rate_limit()
def learn_from_tech_research():
    """Learn from tech research - process visual memories"""
    try:
        data = InputValidator.get_json_safe(default={})
        user_id = InputValidator.sanitize_string(data.get('user_id', 'default_user'), max_length=50).strip()
        agent_id = InputValidator.sanitize_string(data.get('agent_id', ''), max_length=50).strip()
        
        result = tech_tree_system.learn_from_tech_research(user_id, agent_id if agent_id else None)
        return jsonify(result), 200 if result.get('success') else 400
    except Exception as e:
        request_id = str(uuid.uuid4())[:8]
        error_response, status_code = ErrorHandler.create_error_response(e, 500, request_id)
        return error_response, status_code

@tech_tree_bp.route('/api/tech-tree/knowledge', methods=['GET'])
@tech_tree_bp.route('/vidgenerator/api/tech-tree/knowledge', methods=['GET'])
@rate_limit()
def get_knowledge():
    """Get knowledge tree data"""
    try:
        user_id = request.args.get('user_id', 'default_user')
        
        if tech_tree_system is None:
            return jsonify({
                'success': True,
                'knowledge': {
                    'nodes': [],
                    'total_unlocked': 0,
                    'total_available': 0
                }
            }), 200
        
        # Try to get knowledge data
        try:
            result = tech_tree_system.get_knowledge(user_id)
        except AttributeError:
            # Method doesn't exist, return empty data
            result = {
                'success': True,
                'knowledge': {
                    'nodes': [],
                    'total_unlocked': 0,
                    'total_available': 0
                }
            }
        
        # Ensure result has success and knowledge keys
        if not isinstance(result, dict):
            result = {'success': True, 'knowledge': {}}
        if 'success' not in result:
            result['success'] = True
        if 'knowledge' not in result:
            result['knowledge'] = result if isinstance(result, dict) else {}
        
        return jsonify(result), 200
    except Exception as e:
        logger.error(f"Error getting knowledge: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e),
            'knowledge': {
                'nodes': [],
                'total_unlocked': 0,
                'total_available': 0
            }
        }), 200  # Return 200 with empty data instead of 500

@tech_tree_bp.route('/api/tech-tree/agent-learning', methods=['GET'])
@tech_tree_bp.route('/vidgenerator/api/tech-tree/agent-learning', methods=['GET'])
@rate_limit()
def get_agent_tech_learning():
    """Get agent's tech learning progress"""
    try:
        user_id = request.args.get('user_id', 'default_user')
        agent_id = request.args.get('agent_id')
        
        if not agent_id:
            return jsonify({'success': False, 'error': 'agent_id is required'}), 400
        
        result = tech_tree_system.get_agent_tech_learning(user_id, agent_id)
        return jsonify(result), 200 if result.get('success') else 400
    except Exception as e:
        request_id = str(uuid.uuid4())[:8]
        error_response, status_code = ErrorHandler.create_error_response(e, 500, request_id)
        return error_response, status_code

@tech_tree_bp.route('/api/tech-tree/skills', methods=['GET'])
@tech_tree_bp.route('/vidgenerator/api/tech-tree/skills', methods=['GET'])
@rate_limit()
def get_tech_skills():
    """Get skills unlocked from tech research"""
    try:
        user_id = request.args.get('user_id', 'default_user')
        tech_id = request.args.get('tech_id')
        
        result = tech_tree_system.get_tech_skills(user_id, tech_id)
        return jsonify(result), 200
    except Exception as e:
        request_id = str(uuid.uuid4())[:8]
        error_response, status_code = ErrorHandler.create_error_response(e, 500, request_id)
        return error_response, status_code

@tech_tree_bp.route('/api/tech-tree/learning-data', methods=['GET'])
@tech_tree_bp.route('/vidgenerator/api/tech-tree/learning-data', methods=['GET'])
@rate_limit()
def get_progressive_learning_data():
    """Get progressive learning data for user"""
    try:
        user_id = request.args.get('user_id', 'default_user')
        
        result = tech_tree_system.get_progressive_learning_data(user_id)
        return jsonify(result), 200
    except Exception as e:
        request_id = str(uuid.uuid4())[:8]
        error_response, status_code = ErrorHandler.create_error_response(e, 500, request_id)
        return error_response, status_code
