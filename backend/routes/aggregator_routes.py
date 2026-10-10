"""
Aggregator API Routes - Content aggregation endpoints
"""
from flask import Blueprint, request, jsonify
from backend.services.aggregators.video_aggregator import video_aggregator
from backend.services.aggregators.social_aggregator import social_aggregator
from backend.services.aggregators.stats_aggregator import stats_aggregator
from backend.services.aggregators.intelligence_aggregator import IntelligenceAggregator

intelligence_aggregator = IntelligenceAggregator()
from src.utils.input_validator import InputValidator
from src.utils.error_handler import ErrorHandler
from src.utils.rate_limiter import rate_limit
from datetime import datetime
import sys
import uuid

aggregator_bp = Blueprint('aggregator', __name__)

# Video Aggregator Routes
@aggregator_bp.route('/api/aggregators/videos/all', methods=['GET'])
@aggregator_bp.route('/vidgenerator/api/aggregators/videos/all', methods=['GET'])
@rate_limit()
def aggregate_all_videos():
    """Aggregate all videos and clips"""
    try:
        filters = {
            'page': int(request.args.get('page', 1)),
            'limit': int(request.args.get('limit', 20)),
            'search': request.args.get('search', ''),
            'category': request.args.get('category', ''),
            'start_date': request.args.get('start_date'),
            'end_date': request.args.get('end_date')
        }
        
        result = video_aggregator.aggregate(filters)
        return jsonify(result), 200
    except Exception as e:
        request_id = str(uuid.uuid4())[:8]
        error_response, status_code = ErrorHandler.create_error_response(e, 500, request_id)
        return error_response, status_code

@aggregator_bp.route('/api/aggregators/videos/user/<user_id>', methods=['GET'])
@aggregator_bp.route('/vidgenerator/api/aggregators/videos/user/<user_id>', methods=['GET'])
@rate_limit()
def aggregate_user_videos(user_id):
    """Aggregate videos by user"""
    try:
        user_id = InputValidator.sanitize_string(user_id, max_length=50).strip()
        filters = {
            'page': int(request.args.get('page', 1)),
            'limit': int(request.args.get('limit', 20))
        }
        
        result = video_aggregator.aggregate_by_user(user_id, filters)
        return jsonify(result), 200
    except Exception as e:
        request_id = str(uuid.uuid4())[:8]
        error_response, status_code = ErrorHandler.create_error_response(e, 500, request_id)
        return error_response, status_code

@aggregator_bp.route('/api/aggregators/videos/theme/<theme>', methods=['GET'])
@aggregator_bp.route('/vidgenerator/api/aggregators/videos/theme/<theme>', methods=['GET'])
@rate_limit()
def aggregate_theme_videos(theme):
    """Aggregate videos by theme"""
    try:
        theme = InputValidator.sanitize_string(theme, max_length=50).strip()
        filters = {
            'page': int(request.args.get('page', 1)),
            'limit': int(request.args.get('limit', 20))
        }
        
        result = video_aggregator.aggregate_by_theme(theme, filters)
        return jsonify(result), 200
    except Exception as e:
        request_id = str(uuid.uuid4())[:8]
        error_response, status_code = ErrorHandler.create_error_response(e, 500, request_id)
        return error_response, status_code

@aggregator_bp.route('/api/aggregators/videos/provider/<provider>', methods=['GET'])
@aggregator_bp.route('/vidgenerator/api/aggregators/videos/provider/<provider>', methods=['GET'])
@rate_limit()
def aggregate_provider_videos(provider):
    """Aggregate videos by provider"""
    try:
        provider = InputValidator.sanitize_string(provider, max_length=50).strip()
        filters = {
            'page': int(request.args.get('page', 1)),
            'limit': int(request.args.get('limit', 20))
        }
        
        result = video_aggregator.aggregate_by_provider(provider, filters)
        return jsonify(result), 200
    except Exception as e:
        request_id = str(uuid.uuid4())[:8]
        error_response, status_code = ErrorHandler.create_error_response(e, 500, request_id)
        return error_response, status_code

@aggregator_bp.route('/api/aggregators/videos/stats', methods=['GET'])
@aggregator_bp.route('/vidgenerator/api/aggregators/videos/stats', methods=['GET'])
@rate_limit()
def get_video_statistics():
    """Get aggregated video statistics"""
    try:
        result = video_aggregator.get_statistics()
        return jsonify(result), 200
    except Exception as e:
        request_id = str(uuid.uuid4())[:8]
        error_response, status_code = ErrorHandler.create_error_response(e, 500, request_id)
        return error_response, status_code

@aggregator_bp.route('/api/aggregators/videos/search', methods=['GET'])
@aggregator_bp.route('/vidgenerator/api/aggregators/videos/search', methods=['GET'])
@rate_limit()
def search_videos():
    """Search videos"""
    try:
        query = request.args.get('q', '')
        filters = {
            'search': query,
            'page': int(request.args.get('page', 1)),
            'limit': int(request.args.get('limit', 20))
        }
        
        result = video_aggregator.aggregate(filters)
        return jsonify(result), 200
    except Exception as e:
        request_id = str(uuid.uuid4())[:8]
        error_response, status_code = ErrorHandler.create_error_response(e, 500, request_id)
        return error_response, status_code

# Social Aggregator Routes
@aggregator_bp.route('/api/aggregators/social/feed/<user_id>', methods=['GET'])
@aggregator_bp.route('/vidgenerator/api/aggregators/social/feed/<user_id>', methods=['GET'])
@rate_limit()
def aggregate_social_feed(user_id):
    """Aggregate social feed for user"""
    try:
        user_id = InputValidator.sanitize_string(user_id, max_length=50).strip()
        limit = int(request.args.get('limit', 20))
        
        result = social_aggregator.aggregate_feed(user_id, limit)
        return jsonify(result), 200
    except Exception as e:
        request_id = str(uuid.uuid4())[:8]
        error_response, status_code = ErrorHandler.create_error_response(e, 500, request_id)
        return error_response, status_code

@aggregator_bp.route('/api/aggregators/social/activity/<user_id>', methods=['GET'])
@aggregator_bp.route('/vidgenerator/api/aggregators/social/activity/<user_id>', methods=['GET'])
@rate_limit()
def aggregate_social_activity(user_id):
    """Aggregate user activity"""
    try:
        user_id = InputValidator.sanitize_string(user_id, max_length=50).strip()
        
        result = social_aggregator.aggregate_activity(user_id)
        return jsonify(result), 200
    except Exception as e:
        request_id = str(uuid.uuid4())[:8]
        error_response, status_code = ErrorHandler.create_error_response(e, 500, request_id)
        return error_response, status_code

@aggregator_bp.route('/api/aggregators/social/trending', methods=['GET'])
@aggregator_bp.route('/vidgenerator/api/aggregators/social/trending', methods=['GET'])
@rate_limit()
def aggregate_trending():
    """Get trending posts"""
    try:
        limit = int(request.args.get('limit', 10))
        
        result = social_aggregator.aggregate_trending(limit)
        return jsonify(result), 200
    except Exception as e:
        request_id = str(uuid.uuid4())[:8]
        error_response, status_code = ErrorHandler.create_error_response(e, 500, request_id)
        return error_response, status_code

@aggregator_bp.route('/api/aggregators/social/popular', methods=['GET'])
@aggregator_bp.route('/vidgenerator/api/aggregators/social/popular', methods=['GET'])
@rate_limit()
def aggregate_popular():
    """Get popular posts"""
    try:
        limit = int(request.args.get('limit', 10))
        
        result = social_aggregator.aggregate_popular(limit)
        return jsonify(result), 200
    except Exception as e:
        request_id = str(uuid.uuid4())[:8]
        error_response, status_code = ErrorHandler.create_error_response(e, 500, request_id)
        return error_response, status_code

@aggregator_bp.route('/api/aggregators/social/engagement/<post_id>', methods=['GET'])
@aggregator_bp.route('/vidgenerator/api/aggregators/social/engagement/<post_id>', methods=['GET'])
@rate_limit()
def aggregate_engagement(post_id):
    """Get post engagement metrics"""
    try:
        post_id = InputValidator.sanitize_string(post_id, max_length=50).strip()
        
        result = social_aggregator.aggregate_engagement(post_id)
        return jsonify(result), 200
    except Exception as e:
        request_id = str(uuid.uuid4())[:8]
        error_response, status_code = ErrorHandler.create_error_response(e, 500, request_id)
        return error_response, status_code

# Stats Aggregator Routes
@aggregator_bp.route('/api/aggregators/stats/user/<user_id>', methods=['GET'])
@aggregator_bp.route('/vidgenerator/api/aggregators/stats/user/<user_id>', methods=['GET'])
@rate_limit()
def aggregate_user_stats(user_id):
    """Aggregate all user stats"""
    try:
        user_id = InputValidator.sanitize_string(user_id, max_length=50).strip()
        
        result = stats_aggregator.aggregate_user_stats(user_id)
        return jsonify(result), 200
    except Exception as e:
        request_id = str(uuid.uuid4())[:8]
        error_response, status_code = ErrorHandler.create_error_response(e, 500, request_id)
        return error_response, status_code

@aggregator_bp.route('/api/aggregators/stats/progress/<user_id>', methods=['GET'])
@aggregator_bp.route('/vidgenerator/api/aggregators/stats/progress/<user_id>', methods=['GET'])
@rate_limit()
def aggregate_progress(user_id):
    """Aggregate user progress"""
    try:
        user_id = InputValidator.sanitize_string(user_id, max_length=50).strip()
        
        result = stats_aggregator.aggregate_progress(user_id)
        return jsonify(result), 200
    except Exception as e:
        request_id = str(uuid.uuid4())[:8]
        error_response, status_code = ErrorHandler.create_error_response(e, 500, request_id)
        return error_response, status_code

@aggregator_bp.route('/api/aggregators/stats/achievements/<user_id>', methods=['GET'])
@aggregator_bp.route('/vidgenerator/api/aggregators/stats/achievements/<user_id>', methods=['GET'])
@rate_limit()
def aggregate_achievements(user_id):
    """Aggregate user achievements"""
    try:
        user_id = InputValidator.sanitize_string(user_id, max_length=50).strip()
        
        result = stats_aggregator.aggregate_achievements(user_id)
        return jsonify(result), 200
    except Exception as e:
        request_id = str(uuid.uuid4())[:8]
        error_response, status_code = ErrorHandler.create_error_response(e, 500, request_id)
        return error_response, status_code

@aggregator_bp.route('/api/aggregators/stats/performance/<user_id>', methods=['GET'])
@aggregator_bp.route('/vidgenerator/api/aggregators/stats/performance/<user_id>', methods=['GET'])
@rate_limit()
def aggregate_performance(user_id):
    """Aggregate user performance"""
    try:
        user_id = InputValidator.sanitize_string(user_id, max_length=50).strip()
        
        result = stats_aggregator.aggregate_performance(user_id)
        return jsonify(result), 200
    except Exception as e:
        request_id = str(uuid.uuid4())[:8]
        error_response, status_code = ErrorHandler.create_error_response(e, 500, request_id)
        return error_response, status_code

@aggregator_bp.route('/api/aggregators/stats/history/<user_id>', methods=['GET'])
@aggregator_bp.route('/vidgenerator/api/aggregators/stats/history/<user_id>', methods=['GET'])
@rate_limit()
def aggregate_history(user_id):
    """Aggregate user history"""
    try:
        user_id = InputValidator.sanitize_string(user_id, max_length=50).strip()
        period = request.args.get('period', 'week')
        
        result = stats_aggregator.aggregate_history(user_id, period)
        return jsonify(result), 200
    except Exception as e:
        request_id = str(uuid.uuid4())[:8]
        error_response, status_code = ErrorHandler.create_error_response(e, 500, request_id)
        return error_response, status_code

# Unified Aggregator Routes
@aggregator_bp.route('/api/aggregators/unified/dashboard/<user_id>', methods=['GET'])
@aggregator_bp.route('/vidgenerator/api/aggregators/unified/dashboard/<user_id>', methods=['GET'])
@rate_limit()
def unified_dashboard(user_id):
    """Unified dashboard with all aggregated data"""
    try:
        user_id = InputValidator.sanitize_string(user_id, max_length=50).strip()
        
        # Aggregate all data
        video_data = video_aggregator.aggregate_by_user(user_id, {'limit': 10})
        social_data = social_aggregator.aggregate_activity(user_id)
        stats_data = stats_aggregator.aggregate_user_stats(user_id)
        
        dashboard = {
            'success': True,
            'user_id': user_id,
            'videos': video_data.get('data', []),
            'video_total': video_data.get('total', 0),
            'social_activities': social_data.get('activities', []),
            'social_total': social_data.get('total', 0),
            'stats': stats_data.get('stats', {}),
            'aggregated_at': datetime.utcnow().isoformat()
        }
        
        # Enhance dashboard with future tech and calculator
        try:
            from backend.services.future_tech_integration_service import future_tech_integration_service
            dashboard = future_tech_integration_service.enhance_aggregator_data(user_id, dashboard)
        except Exception as e:
            print(f"[AggregatorRoutes] Error enhancing dashboard: {e}")
        
        return jsonify(dashboard), 200
    except Exception as e:
        request_id = str(uuid.uuid4())[:8]
        error_response, status_code = ErrorHandler.create_error_response(e, 500, request_id)
        return error_response, status_code

