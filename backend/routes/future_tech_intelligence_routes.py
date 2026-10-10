"""
Future Technology Intelligence Routes
API routes for upgraded future tech intelligence system
"""
from flask import Blueprint, request, jsonify
from backend.services.future_tech_intelligence_upgrade import future_tech_intelligence_upgrade
from src.utils.input_validator import InputValidator
from src.utils.error_handler import ErrorHandler
from src.utils.rate_limiter import rate_limit
import uuid

future_tech_intel_bp = Blueprint('future_tech_intelligence', __name__)

@future_tech_intel_bp.route('/api/future-tech-intel/upgrade', methods=['POST'])
@future_tech_intel_bp.route('/vidgenerator/api/future-tech-intel/upgrade', methods=['POST'])
@rate_limit()
def upgrade_intelligence():
    """Upgrade intelligence level"""
    try:
        data = InputValidator.get_json_safe(default={})
        target_level = float(data.get('target_level', 5.0))
        
        result = future_tech_intelligence_upgrade.upgrade_intelligence(target_level)
        return jsonify(result), 200 if result.get('success') else 400
    except Exception as e:
        request_id = str(uuid.uuid4())[:8]
        error_response, status_code = ErrorHandler.create_error_response(e, 500, request_id)
        return error_response, status_code


@future_tech_intel_bp.route('/api/future-tech-intel/technologies', methods=['GET'])
@future_tech_intel_bp.route('/vidgenerator/api/future-tech-intel/technologies', methods=['GET'])
@rate_limit()
def get_enhanced_technologies():
    """Get enhanced future technologies"""
    try:
        years_ahead = int(request.args.get('years_ahead', 500))
        
        result = future_tech_intelligence_upgrade.get_future_technologies_enhanced(years_ahead)
        return jsonify(result), 200 if result.get('success') else 400
    except Exception as e:
        request_id = str(uuid.uuid4())[:8]
        error_response, status_code = ErrorHandler.create_error_response(e, 500, request_id)
        return error_response, status_code


@future_tech_intel_bp.route('/api/future-tech-intel/install', methods=['POST'])
@future_tech_intel_bp.route('/vidgenerator/api/future-tech-intel/install', methods=['POST'])
@rate_limit()
def install_technology():
    """Install a future technology"""
    try:
        data = InputValidator.get_json_safe(default={})
        tech_id = InputValidator.sanitize_string(data.get('tech_id', ''))
        user_id = InputValidator.sanitize_string(data.get('user_id', 'default_user'))
        force_reinstall = bool(data.get('force_reinstall', False))
        
        if not tech_id:
            return jsonify({
                'success': False,
                'error': 'tech_id required'
            }), 400
        
        result = future_tech_intelligence_upgrade.install_future_technology(
            tech_id, user_id, force_reinstall
        )
        return jsonify(result), 200 if result.get('success') else 400
    except Exception as e:
        request_id = str(uuid.uuid4())[:8]
        error_response, status_code = ErrorHandler.create_error_response(e, 500, request_id)
        return error_response, status_code


@future_tech_intel_bp.route('/api/future-tech-intel/re-entomb', methods=['POST'])
@future_tech_intel_bp.route('/vidgenerator/api/future-tech-intel/re-entomb', methods=['POST'])
@rate_limit()
def re_entomb_technologies():
    """Re-entomb (reinitialize) all future technologies"""
    try:
        data = InputValidator.get_json_safe(default={})
        user_id = InputValidator.sanitize_string(data.get('user_id', 'system'))
        
        result = future_tech_intelligence_upgrade.re_entomb_technologies(user_id)
        return jsonify(result), 200 if result.get('success') else 400
    except Exception as e:
        request_id = str(uuid.uuid4())[:8]
        error_response, status_code = ErrorHandler.create_error_response(e, 500, request_id)
        return error_response, status_code


@future_tech_intel_bp.route('/api/future-tech-intel/guides', methods=['GET'])
@future_tech_intel_bp.route('/vidgenerator/api/future-tech-intel/guides', methods=['GET'])
@rate_limit()
def get_installation_guides():
    """Get all installation guides"""
    try:
        result = future_tech_intelligence_upgrade.get_installation_guides()
        return jsonify(result), 200
    except Exception as e:
        request_id = str(uuid.uuid4())[:8]
        error_response, status_code = ErrorHandler.create_error_response(e, 500, request_id)
        return error_response, status_code


@future_tech_intel_bp.route('/api/future-tech-intel/features', methods=['GET'])
@future_tech_intel_bp.route('/vidgenerator/api/future-tech-intel/features', methods=['GET'])
@rate_limit()
def get_all_features():
    """Get all available features"""
    try:
        result = future_tech_intelligence_upgrade.get_all_features()
        return jsonify(result), 200
    except Exception as e:
        request_id = str(uuid.uuid4())[:8]
        error_response, status_code = ErrorHandler.create_error_response(e, 500, request_id)
        return error_response, status_code


@future_tech_intel_bp.route('/api/future-tech-intel/status', methods=['GET'])
@future_tech_intel_bp.route('/vidgenerator/api/future-tech-intel/status', methods=['GET'])
@rate_limit()
def get_status():
    """Get system status"""
    try:
        result = future_tech_intelligence_upgrade.get_all_features()
        result['installed_count'] = len(future_tech_intelligence_upgrade.installed_technologies)
        result['installation_history_count'] = len(future_tech_intelligence_upgrade.installation_history)
        return jsonify({
            'success': True,
            'intelligence_level': future_tech_intelligence_upgrade.intelligence_level,
            'installed_technologies': result['installed_count'],
            'installation_history': result['installation_history_count'],
            'features': result
        }), 200
    except Exception as e:
        request_id = str(uuid.uuid4())[:8]
        error_response, status_code = ErrorHandler.create_error_response(e, 500, request_id)
        return error_response, status_code

