"""
Game Stats Save Routes
Ensure all game stats are saved and connected to unified points
"""
from flask import Blueprint, request, jsonify
from backend.services.point_connection_system import PointConnectionSystem
from backend.services.enhanced_game_mechanics import enhanced_game_mechanics
from backend.services.unified_point_system_reconstructed import unified_point_system
from backend.services.unified_points_database import unified_points_database
from src.utils.rate_limiter import rate_limit
import sys

game_stats_save_bp = Blueprint('game_stats_save', __name__)


@game_stats_save_bp.route('/api/game/save-all-stats', methods=['POST'])
@game_stats_save_bp.route('/vidgenerator/api/game/save-all-stats', methods=['POST'])
@rate_limit()
def save_all_game_stats():
    """Save all game stats and ensure they're connected to unified points"""
    try:
        data = request.get_json() or {}
        user_id = data.get('user_id', 'default_user')
        stats = data.get('stats', {})
        
        # Initialize services
        point_connection = PointConnectionSystem()
        enhanced_game_mechanics.set_unified_points(unified_point_system)
        
        # Save all stats to database
        stats_to_save = {
            'level': stats.get('level', 1),
            'xp': stats.get('xp', 0),
            'total_xp': stats.get('total_xp', 0),
            'videos_created': stats.get('videos_created', 0),
            'videos_watched': stats.get('videos_watched', 0),
            'battles_won': stats.get('battles_won', 0),
            'battles_lost': stats.get('battles_lost', 0),
            'achievements': stats.get('achievements', 0),
            'milestones': stats.get('milestones', 0),
            'credits': stats.get('credits', 0),
            'points': stats.get('points', 0),
            'stats_points': stats.get('stats_points', 0),
            'clicks': stats.get('clicks', 0),
            'missions_completed': stats.get('missions_completed', 0),
            'quests_completed': stats.get('quests_completed', 0),
            'trophies_earned': stats.get('trophies_earned', 0),
            'online_time': stats.get('online_time', 0),
            'engagement_score': stats.get('engagement_score', 0),
        }
        
        # Save to unified points database
        unified_points_database.save_user_points(user_id, stats_to_save)
        
        # Connect points via point connection system
        if stats_to_save.get('points', 0) > 0:
            point_connection.ensure_point_counting(user_id, 'game_points', stats_to_save['points'], 'game_stats')
        
        if stats_to_save.get('xp', 0) > 0:
            point_connection.ensure_point_counting(user_id, 'xp', stats_to_save['xp'], 'game_stats')
        
        if stats_to_save.get('credits', 0) > 0:
            point_connection.ensure_point_counting(user_id, 'coins', stats_to_save['credits'], 'game_stats')
        
        if stats_to_save.get('clicks', 0) > 0:
            point_connection.ensure_point_counting(user_id, 'activity_points', stats_to_save['clicks'] * 2, 'game_stats')
        
        return jsonify({
            'success': True,
            'message': 'All stats saved and connected',
            'user_id': user_id,
            'stats_saved': stats_to_save
        }), 200
    except Exception as e:
        print(f"[GameStatsSave] Error: {e}", file=sys.stderr, flush=True)
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
