"""
Creative Time Machine 500+ Routes
API routes for time machine projections and technology downloads
"""
from flask import Blueprint, request, jsonify
from backend.services.creative_timemashine_500plus import creative_timemashine_500plus
from backend.services.technology_intelligence_battle import technology_intelligence_battle
from src.utils.input_validator import InputValidator
from src.utils.error_handler import ErrorHandler
from src.utils.rate_limiter import rate_limit
from datetime import datetime
import sys
import uuid

creative_timemashine_bp = Blueprint('creative_timemashine', __name__)

@creative_timemashine_bp.route('/api/timemashine/project', methods=['POST'])
@creative_timemashine_bp.route('/vidgenerator/api/timemashine/project', methods=['POST'])
@rate_limit()
def project_to_future():
    """Project website into the future (500+ years)"""
    try:
        data = InputValidator.get_json_safe(default={})
        user_id = InputValidator.sanitize_string(data.get('user_id', 'default_user'))
        target_years = int(data.get('target_years', 500))
        projection_type = InputValidator.sanitize_string(data.get('projection_type', 'full'))
        
        if target_years < 500:
            target_years = 500  # Enforce minimum 500 years
        
        result = creative_timemashine_500plus.project_to_future(
            user_id, target_years, projection_type
        )
        
        return jsonify(result), 200 if result.get('success') else 400
    except Exception as e:
        request_id = str(uuid.uuid4())[:8]
        error_response, status_code = ErrorHandler.create_error_response(e, 500, request_id)
        return error_response, status_code


@creative_timemashine_bp.route('/api/timemashine/projection/<projection_id>', methods=['GET'])
@creative_timemashine_bp.route('/vidgenerator/api/timemashine/projection/<projection_id>', methods=['GET'])
@rate_limit()
def get_projection(projection_id: str):
    """Get a specific future projection"""
    try:
        result = creative_timemashine_500plus.get_projection(projection_id)
        return jsonify(result), 200 if result.get('success') else 404
    except Exception as e:
        request_id = str(uuid.uuid4())[:8]
        error_response, status_code = ErrorHandler.create_error_response(e, 500, request_id)
        return error_response, status_code


@creative_timemashine_bp.route('/api/timemashine/user/<user_id>/projections', methods=['GET'])
@creative_timemashine_bp.route('/vidgenerator/api/timemashine/user/<user_id>/projections', methods=['GET'])
@rate_limit()
def get_user_projections(user_id: str):
    """Get all projections for a user"""
    try:
        result = creative_timemashine_500plus.get_user_projections(user_id)
        return jsonify(result), 200
    except Exception as e:
        request_id = str(uuid.uuid4())[:8]
        error_response, status_code = ErrorHandler.create_error_response(e, 500, request_id)
        return error_response, status_code


@creative_timemashine_bp.route('/api/timemashine/download-tech', methods=['POST'])
@creative_timemashine_bp.route('/vidgenerator/api/timemashine/download-tech', methods=['POST'])
@rate_limit()
def download_future_tech():
    """Download future technology from projection"""
    try:
        data = InputValidator.get_json_safe(default={})
        user_id = InputValidator.sanitize_string(data.get('user_id', 'default_user'))
        projection_id = InputValidator.sanitize_string(data.get('projection_id', ''))
        tech_id = InputValidator.sanitize_string(data.get('tech_id', ''))
        
        if not projection_id or not tech_id:
            return jsonify({
                'success': False,
                'error': 'projection_id and tech_id required'
            }), 400
        
        result = technology_intelligence_battle.download_tech_intelligence(
            user_id, projection_id, tech_id
        )
        
        return jsonify(result), 200 if result.get('success') else 400
    except Exception as e:
        request_id = str(uuid.uuid4())[:8]
        error_response, status_code = ErrorHandler.create_error_response(e, 500, request_id)
        return error_response, status_code


@creative_timemashine_bp.route('/api/timemashine/integrate-battle', methods=['POST'])
@creative_timemashine_bp.route('/vidgenerator/api/timemashine/integrate-battle', methods=['POST'])
@rate_limit()
def integrate_to_battle():
    """Integrate downloaded technology intelligence into battle logic"""
    try:
        data = InputValidator.get_json_safe(default={})
        user_id = InputValidator.sanitize_string(data.get('user_id', 'default_user'))
        tech_storage_id = InputValidator.sanitize_string(data.get('tech_storage_id', ''))
        battle_id = InputValidator.sanitize_string(data.get('battle_id', ''))
        
        if not tech_storage_id or not battle_id:
            return jsonify({
                'success': False,
                'error': 'tech_storage_id and battle_id required'
            }), 400
        
        # Integrate to battle logic
        result = technology_intelligence_battle.integrate_to_battle_logic(
            user_id, tech_storage_id, battle_id
        )
        
        # Apply logic to battle
        if result.get('success'):
            apply_result = technology_intelligence_battle.apply_logic_to_battle(battle_id, user_id)
            result['applied'] = apply_result
        
        return jsonify(result), 200 if result.get('success') else 400
    except Exception as e:
        request_id = str(uuid.uuid4())[:8]
        error_response, status_code = ErrorHandler.create_error_response(e, 500, request_id)
        return error_response, status_code


@creative_timemashine_bp.route('/api/timemashine/battle-logic/<battle_id>', methods=['GET'])
@creative_timemashine_bp.route('/vidgenerator/api/timemashine/battle-logic/<battle_id>', methods=['GET'])
@rate_limit()
def get_battle_logic(battle_id: str):
    """Get enhanced battle logic for a battle"""
    try:
        result = technology_intelligence_battle.get_battle_logic(battle_id)
        return jsonify(result), 200
    except Exception as e:
        request_id = str(uuid.uuid4())[:8]
        error_response, status_code = ErrorHandler.create_error_response(e, 500, request_id)
        return error_response, status_code


@creative_timemashine_bp.route('/api/timemashine/downloaded-tech/<user_id>', methods=['GET'])
@creative_timemashine_bp.route('/vidgenerator/api/timemashine/downloaded-tech/<user_id>', methods=['GET'])
@rate_limit()
def get_downloaded_tech(user_id: str):
    """Get all downloaded technologies for a user"""
    try:
        result = technology_intelligence_battle.get_downloaded_tech(user_id)
        return jsonify(result), 200
    except Exception as e:
        request_id = str(uuid.uuid4())[:8]
        error_response, status_code = ErrorHandler.create_error_response(e, 500, request_id)
        return error_response, status_code


@creative_timemashine_bp.route('/api/timemashine/future-technologies', methods=['GET'])
@creative_timemashine_bp.route('/vidgenerator/api/timemashine/future-technologies', methods=['GET'])
@rate_limit()
def get_future_technologies():
    """Get list of available future technologies"""
    try:
        target_year = int(request.args.get('target_year', creative_timemashine_500plus.current_year + 500))
        
        tech_list = creative_timemashine_500plus._get_technologies_for_year(target_year)
        battle_systems = creative_timemashine_500plus._get_battle_systems_for_year(target_year)
        
        return jsonify({
            'success': True,
            'target_year': target_year,
            'technologies': tech_list,
            'battle_systems': battle_systems,
            'count': len(tech_list)
        }), 200
    except Exception as e:
        request_id = str(uuid.uuid4())[:8]
        error_response, status_code = ErrorHandler.create_error_response(e, 500, request_id)
        return error_response, status_code

