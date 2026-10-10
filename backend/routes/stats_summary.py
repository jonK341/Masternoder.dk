"""Stats summary API for landing page"""
from flask import Blueprint, jsonify, request
from src.db.models import db, Documentary, UserProfile

stats_summary_bp = Blueprint('stats_summary', __name__)

@stats_summary_bp.route('/stats/summary')
@stats_summary_bp.route('/stats/summary/')
def stats_summary_page():
    """Stats summary page"""
    from flask import Response
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Stats Summary - masternoder.dk</title>
        <meta charset="UTF-8">
    </head>
    <body>
        <h1>Statistics Summary</h1>
        <p>Stats summary page</p>
        <p><a href="/vidgenerator/stats">Back to stats</a></p>
    </body>
    </html>
    """, 200

# Note: Middleware strips /vidgenerator, so /vidgenerator/api/* becomes /api/* before matching
# Only need /api/* route - middleware handles the prefix
@stats_summary_bp.route('/api/stats/summary', methods=['GET'])
def get_stats_summary():
    """Get summary stats for landing page with enhanced data"""
    try:
        # Get user_id from query params (for profile page)
        user_id = request.args.get('user_id', None)
        
        # If user_id is provided, return user-specific summary
        if user_id:
            return _get_user_summary(user_id)
        
        # Otherwise return global stats
        stats = {
            'total_videos': 0,
            'completed_videos': 0,
            'total_users': 0,
            'success_rate': 95,
            'total_achievements': 0,
            'total_battles': 0,
            'total_xp': 0,
            'active_users': 0
        }
        
        # Count total videos
        try:
            stats['total_videos'] = Documentary.query.count()
            stats['completed_videos'] = Documentary.query.filter_by(status='completed').count()
            stats['success_rate'] = int((stats['completed_videos'] / stats['total_videos'] * 100)) if stats['total_videos'] > 0 else 0
        except Exception as e:
            print(f"[StatsSummary] Error getting videos: {e}")
        
        # Count users (if UserProfile exists)
        try:
            stats['total_users'] = UserProfile.query.count()
        except:
            pass
        
        # Get enhanced stats from other systems
        try:
            from backend.services.quick_battle_system import quick_battle
            battle_stats = quick_battle.get_user_battle_stats('default_user')
            if battle_stats and 'total_battles' in battle_stats:
                stats['total_battles'] = battle_stats.get('total_battles', 0)
        except:
            pass
        
        try:
            from backend.services.xp_system import XPSystem
            xp_system = XPSystem()
            profile = xp_system.get_user_profile('default_user')
            if profile and 'total_xp' in profile:
                stats['total_xp'] = profile.get('total_xp', 0)
        except:
            pass
        
        try:
            from backend.services.game_achievements import game_achievement_system
            if game_achievement_system:
                achievements = game_achievement_system.get_user_achievements('default_user')
                if achievements:
                    stats['total_achievements'] = len(achievements) if isinstance(achievements, list) else 0
        except:
            pass
        
        return jsonify({
            'success': True,
            'stats': stats
        }), 200
    except Exception as e:
        # Always return 200 with default stats
        return jsonify({
            'success': True,
            'stats': {
                'total_videos': 0,
                'completed_videos': 0,
                'total_users': 0,
                'success_rate': 95,
                'total_achievements': 0,
                'total_battles': 0,
                'total_xp': 0,
                'active_users': 0
            }
        }), 200


def _get_user_summary(user_id: str):
    """Get user-specific summary with video/clip counts as 2 points each"""
    try:
        # Initialize summary structure
        summary = {
            'level': 1,
            'xp': 0,
            'videos_created': 0,
            'clips_created': 0,
            'total_points': 0,
            'total_battles': 0,
            'achievements': 0
        }
        
        # Count videos created by user (from Documentary table)
        # Videos count as 2 points each
        try:
            video_count = 0
            # Try to get documentaries filtered by user_id if that field exists
            try:
                # Check if Documentary has user_id field
                if hasattr(Documentary, 'user_id'):
                    video_count = Documentary.query.filter_by(
                        user_id=user_id,
                        status='completed'
                    ).count()
                else:
                    # If no user_id field, count all completed documentaries
                    # (In a multi-user system, you'd filter by user_id)
                    video_count = Documentary.query.filter_by(
                        status='completed'
                    ).count()
            except Exception as e:
                print(f"[StatsSummary] Error counting videos: {e}")
                video_count = 0
            
            # Count clips (from MovieClip table or similar)
            clip_count = 0
            try:
                from src.db.models import MovieClip
                if hasattr(MovieClip, 'user_id'):
                    clip_count = MovieClip.query.filter_by(user_id=user_id).count()
                else:
                    # Count all clips if no user_id field
                    clip_count = MovieClip.query.count()
            except Exception as e:
                print(f"[StatsSummary] Error counting clips: {e}")
                clip_count = 0
            
            # Each video and clip counts as 2 points
            summary['videos_created'] = video_count * 2
            summary['clips_created'] = clip_count * 2
            
        except Exception as e:
            print(f"[StatsSummary] Error getting video/clip counts: {e}")
        
        # Get XP and level from XP system
        try:
            from backend.services.xp_system import XPSystem
            xp_system = XPSystem()
            profile = xp_system.get_user_profile(user_id)
            if profile:
                summary['level'] = profile.get('level', 1)
                summary['xp'] = profile.get('total_xp', 0)
        except Exception as e:
            print(f"[StatsSummary] Error getting XP: {e}")
        
        # Get battle stats
        try:
            from backend.services.quick_battle_system import quick_battle
            battle_stats = quick_battle.get_user_battle_stats(user_id)
            if battle_stats and 'total_battles' in battle_stats:
                summary['total_battles'] = battle_stats.get('total_battles', 0)
        except Exception as e:
            print(f"[StatsSummary] Error getting battle stats: {e}")
        
        # Get achievements
        try:
            from backend.services.game_achievements import game_achievement_system
            if game_achievement_system:
                achievements = game_achievement_system.get_user_achievements(user_id)
                if achievements:
                    summary['achievements'] = len(achievements) if isinstance(achievements, list) else 0
        except Exception as e:
            print(f"[StatsSummary] Error getting achievements: {e}")
        
        # Calculate total points (videos and clips already multiplied by 2)
        summary['total_points'] = summary['videos_created'] + summary['clips_created']
        
        return jsonify({
            'success': True,
            'summary': summary
        }), 200
    except Exception as e:
        print(f"[StatsSummary] Error in _get_user_summary: {e}")
        # Return default summary structure
        return jsonify({
            'success': True,
            'summary': {
                'level': 1,
                'xp': 0,
                'videos_created': 0,
                'clips_created': 0,
                'total_points': 0,
                'total_battles': 0,
                'achievements': 0
            }
        }), 200

