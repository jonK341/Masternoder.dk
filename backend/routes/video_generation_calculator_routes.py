"""
API Routes for Video Generation Calculator
"""
from flask import Blueprint, request, jsonify
from backend.services.video_generation_calculator import video_generation_calculator
from src.utils.input_validator import InputValidator
from src.utils.error_handler import ErrorHandler

calculator_bp = Blueprint('video_generation_calculator', __name__)


@calculator_bp.route('/api/video-generation/calculate', methods=['POST'])
@calculator_bp.route('/vidgenerator/api/video-generation/calculate', methods=['POST'])
def calculate_process():
    """Calculate and validate video generation process"""
    try:
        data = InputValidator.get_json_safe(request)
        
        prompt = InputValidator.sanitize_string(data.get('prompt', ''))
        user_id = InputValidator.sanitize_string(data.get('user_id', 'default_user'))
        duration = int(data.get('duration', 5))
        resolution = InputValidator.sanitize_string(data.get('resolution', '1280x768'))
        video_type = InputValidator.sanitize_string(data.get('video_type', 'video'))
        
        result = video_generation_calculator.calculate_process(
            prompt=prompt,
            user_id=user_id,
            duration=duration,
            resolution=resolution,
            video_type=video_type
        )
        
        return jsonify(result), 200
    except Exception as e:
        return ErrorHandler.create_error_response(str(e), 500)


@calculator_bp.route('/api/video-generation/solve-problems', methods=['POST'])
def solve_problems():
    """Solve identified problems automatically"""
    try:
        data = InputValidator.get_json_safe(request)
        problems = data.get('problems', [])
        
        if not problems:
            return jsonify({
                'success': False,
                'error': 'No problems provided'
            }), 400
        
        result = video_generation_calculator.solve_problems(problems)
        
        return jsonify({
            'success': True,
            'result': result
        }), 200
    except Exception as e:
        return ErrorHandler.create_error_response(str(e), 500)

