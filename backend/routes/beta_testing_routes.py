"""
Beta Testing Routes
API endpoints for beta testing system
"""
from flask import Blueprint, request, jsonify
from backend.services.beta_testing_system import beta_testing_system
from src.utils.error_handler import ErrorHandler
from src.utils.rate_limiter import rate_limit
import uuid

beta_testing_bp = Blueprint('beta_testing', __name__)


def get_user_id():
    """Get user ID from session or request"""
    from flask import session
    if 'user_id' not in session:
        import uuid
        session['user_id'] = str(uuid.uuid4())
    return session.get('user_id', request.args.get('user_id', 'anonymous'))


@beta_testing_bp.route('/api/beta-testing/create', methods=['POST'])
@beta_testing_bp.route('/vidgenerator/api/beta-testing/create', methods=['POST'])
@rate_limit()
def create_beta_test():
    """Create a new beta test"""
    try:
        data = request.get_json() or {}
        test_name = data.get('test_name', '')
        description = data.get('description', '')
        features = data.get('features', [])
        duration_days = int(data.get('duration_days', 30))
        max_testers = int(data.get('max_testers', 100))
        
        result = beta_testing_system.create_beta_test(
            test_name, description, features, duration_days, max_testers
        )
        return jsonify(result), 200
    except Exception as e:
        request_id = str(uuid.uuid4())[:8]
        error_response, status_code = ErrorHandler.create_error_response(e, 500, request_id)
        return error_response, status_code


@beta_testing_bp.route('/api/beta-testing/register/<test_id>', methods=['POST'])
@beta_testing_bp.route('/vidgenerator/api/beta-testing/register/<test_id>', methods=['POST'])
@rate_limit()
def register_tester(test_id: str):
    """Register as a beta tester"""
    try:
        user_id = get_user_id()
        result = beta_testing_system.register_tester(test_id, user_id)
        return jsonify(result), 200
    except Exception as e:
        request_id = str(uuid.uuid4())[:8]
        error_response, status_code = ErrorHandler.create_error_response(e, 500, request_id)
        return error_response, status_code


@beta_testing_bp.route('/api/beta-testing/feedback/<test_id>', methods=['POST'])
@beta_testing_bp.route('/vidgenerator/api/beta-testing/feedback/<test_id>', methods=['POST'])
@rate_limit()
def submit_feedback(test_id: str):
    """Submit feedback for a beta test"""
    try:
        user_id = get_user_id()
        data = request.get_json() or {}
        feedback_type = data.get('feedback_type', 'general')
        content = data.get('content', '')
        rating = data.get('rating')
        
        result = beta_testing_system.submit_feedback(
            test_id, user_id, feedback_type, content, rating
        )
        return jsonify(result), 200
    except Exception as e:
        request_id = str(uuid.uuid4())[:8]
        error_response, status_code = ErrorHandler.create_error_response(e, 500, request_id)
        return error_response, status_code


@beta_testing_bp.route('/api/beta-testing/results/<test_id>', methods=['POST'])
@beta_testing_bp.route('/vidgenerator/api/beta-testing/results/<test_id>', methods=['POST'])
@rate_limit()
def submit_test_result(test_id: str):
    """Submit test results"""
    try:
        user_id = get_user_id()
        data = request.get_json() or {}
        result_data = data.get('result_data', {})
        
        result = beta_testing_system.submit_test_result(test_id, user_id, result_data)
        return jsonify(result), 200
    except Exception as e:
        request_id = str(uuid.uuid4())[:8]
        error_response, status_code = ErrorHandler.create_error_response(e, 500, request_id)
        return error_response, status_code


@beta_testing_bp.route('/api/beta-testing/tests')
@beta_testing_bp.route('/vidgenerator/api/beta-testing/tests')
@rate_limit()
def get_all_tests():
    """Get all beta tests"""
    try:
        result = beta_testing_system.get_all_beta_tests()
        return jsonify(result), 200
    except Exception as e:
        request_id = str(uuid.uuid4())[:8]
        error_response, status_code = ErrorHandler.create_error_response(e, 500, request_id)
        return error_response, status_code


@beta_testing_bp.route('/api/beta-testing/test/<test_id>')
@beta_testing_bp.route('/vidgenerator/api/beta-testing/test/<test_id>')
@rate_limit()
def get_test(test_id: str):
    """Get beta test details"""
    try:
        result = beta_testing_system.get_beta_test(test_id)
        return jsonify(result), 200
    except Exception as e:
        request_id = str(uuid.uuid4())[:8]
        error_response, status_code = ErrorHandler.create_error_response(e, 500, request_id)
        return error_response, status_code


@beta_testing_bp.route('/api/beta-testing/my-tests')
@beta_testing_bp.route('/vidgenerator/api/beta-testing/my-tests')
@rate_limit()
def get_my_tests():
    """Get tests for current user"""
    try:
        user_id = get_user_id()
        result = beta_testing_system.get_tester_tests(user_id)
        return jsonify(result), 200
    except Exception as e:
        request_id = str(uuid.uuid4())[:8]
        error_response, status_code = ErrorHandler.create_error_response(e, 500, request_id)
        return error_response, status_code


@beta_testing_bp.route('/api/beta-testing/feedback/<test_id>')
@beta_testing_bp.route('/vidgenerator/api/beta-testing/feedback/<test_id>')
@rate_limit()
def get_test_feedback(test_id: str):
    """Get feedback for a test"""
    try:
        result = beta_testing_system.get_test_feedback(test_id)
        return jsonify(result), 200
    except Exception as e:
        request_id = str(uuid.uuid4())[:8]
        error_response, status_code = ErrorHandler.create_error_response(e, 500, request_id)
        return error_response, status_code

