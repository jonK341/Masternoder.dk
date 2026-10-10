"""
Game routes for game mechanics functionality
"""
from flask import Blueprint, render_template, request, jsonify
from datetime import datetime, timedelta

# Import models with error handling (import inside functions if needed)
try:
    from src.db.models import db, Documentary
    MODELS_AVAILABLE = True
except ImportError:
    MODELS_AVAILABLE = False
    db = None
    Documentary = None

game_bp = Blueprint('game', __name__)


@game_bp.route('/static/<path:filename>')
@game_bp.route('/vidgenerator/static/<path:filename>')
def serve_static(filename):
    """Serve static files for game pages"""
    from flask import send_from_directory, current_app
    import os
    
    try:
        # Try multiple possible static file locations
        base_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        static_paths = [
            os.path.join(base_path, 'vidgenerator', 'static'),
            os.path.join(base_path, 'src', 'web', 'static'),
            os.path.join(base_path, 'backend', 'static'),
        ]
        
        # Also try Flask's configured static folder
        if hasattr(current_app, 'static_folder') and current_app.static_folder:
            static_paths.insert(0, current_app.static_folder)
        
        for static_path in static_paths:
            if os.path.exists(static_path):
                file_path = os.path.join(static_path, filename)
                if os.path.exists(file_path) and os.path.isfile(file_path):
                    return send_from_directory(static_path, filename)
        
        return f"Static file not found: {filename}", 404
    except Exception as e:
        import traceback
        error_msg = f"Error serving static file: {str(e)}\n{traceback.format_exc()}"
        print(f"[Game Static] {error_msg}")
        return f"Error serving static file: {str(e)}", 500


@game_bp.route('/battle')
@game_bp.route('/battle/')
def battle_index():
    """Battle page"""
    from flask import Response
    import os
    
    try:
        base_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        battle_path = os.path.join(base_path, 'vidgenerator', 'battle')
        index_file = os.path.join(battle_path, 'index.html')
        
        if os.path.exists(index_file):
            with open(index_file, 'r', encoding='utf-8') as f:
                content = f.read()
            return Response(content, mimetype='text/html; charset=utf-8')
        
        return "Battle page not found", 404
    except Exception as e:
        return f"Error loading battle page: {str(e)}", 500


@game_bp.route('/social')
@game_bp.route('/social/')
def social_index():
    """Social page"""
    from flask import Response
    import os
    
    try:
        base_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        social_path = os.path.join(base_path, 'vidgenerator', 'social')
        index_file = os.path.join(social_path, 'index.html')
        
        if os.path.exists(index_file):
            with open(index_file, 'r', encoding='utf-8') as f:
                content = f.read()
            return Response(content, mimetype='text/html; charset=utf-8')
        
        return "Social page not found", 404
    except Exception as e:
        return f"Error loading social page: {str(e)}", 500


@game_bp.route('/shop')
@game_bp.route('/shop/')
def shop_index():
    """Shop page"""
    from flask import Response
    import os
    
    try:
        base_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        shop_path = os.path.join(base_path, 'vidgenerator', 'shop')
        index_file = os.path.join(shop_path, 'index.html')
        
        if os.path.exists(index_file):
            with open(index_file, 'r', encoding='utf-8') as f:
                content = f.read()
            return Response(content, mimetype='text/html; charset=utf-8')
        
        return "Shop page not found", 404
    except Exception as e:
        return f"Error loading shop page: {str(e)}", 500

# Import caching utility for performance optimization
try:
    from src.utils.query_cache import cached_query
    CACHE_AVAILABLE = True
except ImportError:
    CACHE_AVAILABLE = False
    def cached_query(ttl=None):
        """Dummy decorator if cache not available"""
        def decorator(func):
            return func
        return decorator

# Import game achievement system
try:
    from backend.services.game_achievements import game_achievement_system
except ImportError:
    game_achievement_system = None


# Profile route removed - handled by direct route in app.py to avoid conflicts

@game_bp.route('/game')
@game_bp.route('/game/')
def game_index():
    """Game main page - deployed and fully functional"""
    from flask import Response
    import os
    
    try:
        # Priority 1: Serve from vidgenerator/game directory (production files)
        base_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        vidgen_path = os.path.join(base_path, 'vidgenerator', 'game')
        index_file = os.path.join(vidgen_path, 'index.html')
        
        if os.path.exists(index_file):
            with open(index_file, 'r', encoding='utf-8') as f:
                content = f.read()
            response = Response(content, mimetype='text/html; charset=utf-8')
            # Cache headers will be added by app.after_request middleware
            return response
        
        # Priority 2: Try template rendering
        try:
            return render_template('game/index.html')
        except Exception:
            pass
        
        # Fallback: Basic HTML
        return """
        <!DOCTYPE html>
        <html lang="da">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Hunters Game - MasterNoder</title>
            <style>
                body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                       background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                       min-height: 100vh; padding: 20px; margin: 0; }
                .container { max-width: 1200px; margin: 0 auto; background: white;
                            border-radius: 20px; overflow: hidden; box-shadow: 0 20px 60px rgba(0,0,0,0.3); }
                .header { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                         color: white; padding: 30px; text-align: center; }
                .header h1 { font-size: 2.5em; margin-bottom: 10px; }
                .content { padding: 30px; }
                a { color: #667eea; text-decoration: none; }
                a:hover { text-decoration: underline; }
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>Hunters Game</h1>
                    <p>Game mechanics and XP system</p>
                </div>
                <div class="content">
                    <p>Game interface loading...</p>
                    <p><a href="/vidgenerator">← Back to main page</a></p>
                </div>
            </div>
        </body>
        </html>
        """, 200
        
    except Exception as e:
        return f"Error loading game page: {str(e)}", 500


@game_bp.route('/api/game/xp', methods=['POST'])
def update_xp():
    """API endpoint for updating XP - integrated with hunters leveling system"""
    try:
        from backend.services.hunters_leveling_system import hunters_leveling_system
        
        data = request.get_json() or {}
        user_id = data.get('user_id', 'default_user')
        xp_amount = data.get('xp_amount', 0)
        source = data.get('source', 'unknown')
        action_type = data.get('action_type', 'manual')
        metadata = data.get('metadata', {})
        
        if xp_amount <= 0:
            return jsonify({
                'status': 'error',
                'message': 'XP amount must be positive'
            }), 400
        
        result = hunters_leveling_system.award_xp(
            user_id=user_id,
            xp_amount=xp_amount,
            source=source,
            action_type=action_type,
            metadata=metadata
        )
        
        return jsonify({
            'status': 'success',
            'message': 'XP updated successfully',
            'result': result
        }), 200
    except Exception as e:
        import traceback
        return jsonify({
            'status': 'error',
            'message': str(e),
            'traceback': traceback.format_exc()
        }), 500


@game_bp.route('/api/game/state')
def get_game_state():
    """Get current game state - enhanced with full leveling system"""
    try:
        from backend.services.hunters_leveling_system import hunters_leveling_system
        
        user_id = request.args.get('user_id', 'default_user')
        
        # Get leveling profile
        level_profile = hunters_leveling_system.get_player_profile(user_id)
        
        # Get categories for game
        categories_data = {}
        try:
            from src.services.content_categories import content_category_service
            categories = content_category_service.get_all_categories()
            for category in categories:
                cat_id = category.get('id')
                cat_stats = content_category_service.get_category_stats(cat_id)
                categories_data[cat_id] = {
                    'name': category.get('name_da', category.get('name')),
                    'documentaries': cat_stats.get('documentaries_completed', 0),
                    'views': cat_stats.get('total_views', 0)
                }
        except Exception as cat_err:
            print(f"[Game] Error loading categories: {cat_err}")
        
        # Get stats points
        stats_points = 0
        if game_achievement_system:
            stats = _calculate_user_stats(user_id)
            result = game_achievement_system.update_user_stats(user_id, stats)
            stats_points = result['total_stats_points']
        
        return jsonify({
            'status': 'success',
            'game_state': {
                'categories': categories_data,
                'stats_points': stats_points,
                'level': level_profile.get('current_level', 1),
                'xp': level_profile.get('current_xp', 0),
                'total_xp': level_profile.get('total_xp', 0),
                'level_progress': level_profile.get('level_progress', 0),
                'title': level_profile.get('title', 'Novice Hunter'),
                'prestige_level': level_profile.get('prestige_level', 0),
                'stats': level_profile.get('stats', {}),
                'available_stat_points': level_profile.get('available_stat_points', 0)
            },
            'message': 'Game state loaded'
        }), 200
    except Exception as e:
        import traceback
        return jsonify({
            'status': 'error',
            'message': str(e),
            'traceback': traceback.format_exc()
        }), 500


@game_bp.route('/api/game/categories')
def get_game_categories():
    """Get categories for game mode"""
    try:
        from src.services.content_categories import content_category_service
        categories = content_category_service.get_all_categories()
        
        # Add game-specific data for each category
        game_categories = []
        for category in categories:
            cat_id = category.get('id')
            stats = content_category_service.get_category_stats(cat_id)
            
            game_categories.append({
                'id': cat_id,
                'name': category.get('name_da', category.get('name')),
                'description': category.get('description_da', category.get('description')),
                'documentaries_count': stats.get('documentaries_completed', 0),
                'total_views': stats.get('total_views', 0),
                'xp_multiplier': 1.0,  # Can be customized per category
                'difficulty': 'Normal'  # Can be customized per category
            })
        
        return jsonify({
            'success': True,
            'categories': game_categories
        }), 200
    except Exception as e:
        import traceback
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500


@game_bp.route('/api/game/achievements')
@game_bp.route('/vidgenerator/api/game/achievements')
def get_achievements():
    """Get all achievements for current user"""
    try:
        # Get user ID (simplified - in production would use session/auth)
        user_id = request.args.get('user_id', 'default_user')
        
        if not game_achievement_system:
            return jsonify({
                'success': False,
                'error': 'Achievement system not available'
            }), 500
        
        achievements = game_achievement_system.get_user_achievements(user_id)
        
        return jsonify({
            'success': True,
            'achievements': achievements,
            'total_count': len(achievements),
            'earned_count': sum(1 for ach in achievements if ach.get('earned', False))
        }), 200
    except Exception as e:
        import traceback
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500


@game_bp.route('/api/game/milestones')
def get_milestones():
    """Get all milestones for current user"""
    try:
        user_id = request.args.get('user_id', 'default_user')
        
        if not game_achievement_system:
            return jsonify({
                'success': False,
                'error': 'Achievement system not available'
            }), 500
        
        milestones = game_achievement_system.get_user_milestones(user_id)
        
        return jsonify({
            'success': True,
            'milestones': milestones,
            'total_count': len(milestones),
            'reached_count': sum(1 for mil in milestones if mil.get('reached', False))
        }), 200
    except Exception as e:
        import traceback
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500


@game_bp.route('/api/game/stats')
@game_bp.route('/vidgenerator/api/game/stats')
def get_game_stats():
    """Get comprehensive game statistics for a user"""
    try:
        user_id = request.args.get('user_id', 'default_user')
        
        # Calculate current stats
        stats = _calculate_user_stats(user_id)
        
        # Get stats points if achievement system is available
        stats_points = 0
        if game_achievement_system:
            result = game_achievement_system.update_user_stats(user_id, stats)
            stats_points = result.get('total_stats_points', 0)
        
        return jsonify({
            'success': True,
            'user_id': user_id,
            'stats': stats,
            'stats_points': stats_points,
            'total_videos': stats.get('total_videos', 0),
            'total_xp': stats.get('total_xp', 0),
            'level': stats.get('level', 1)
        }), 200
    except Exception as e:
        import traceback
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500


@game_bp.route('/api/game/stats-points')
def get_stats_points():
    """Get user's total statistics points"""
    try:
        user_id = request.args.get('user_id', 'default_user')
        
        if not game_achievement_system:
            return jsonify({
                'success': False,
                'error': 'Achievement system not available'
            }), 500
        
        # Calculate current stats
        stats = _calculate_user_stats(user_id)
        
        # Update and check for new achievements/milestones
        result = game_achievement_system.update_user_stats(user_id, stats)
        
        return jsonify({
            'success': True,
            'total_stats_points': result['total_stats_points'],
            'new_achievements': result['new_achievements'],
            'new_milestones': result['new_milestones'],
            'total_earned_points': result['total_earned_points']
        }), 200
    except Exception as e:
        import traceback
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500


@game_bp.route('/api/game/update-stats', methods=['POST'])
def update_stats():
    """Update user stats and check for new achievements/milestones"""
    try:
        data = request.get_json() or {}
        user_id = data.get('user_id', 'default_user')
        
        if not game_achievement_system:
            return jsonify({
                'success': False,
                'error': 'Achievement system not available'
            }), 500
        
        # Calculate current stats from database
        stats = _calculate_user_stats(user_id)
        
        # Update and check for new achievements/milestones
        result = game_achievement_system.update_user_stats(user_id, stats)
        
        return jsonify({
            'success': True,
            'stats': stats,
            'total_stats_points': result['total_stats_points'],
            'new_achievements': result['new_achievements'],
            'new_milestones': result['new_milestones'],
            'total_earned_points': result['total_earned_points']
        }), 200
    except Exception as e:
        import traceback
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500


# ============================================================================
# HUNTERS GAME - Full Leveling System Routes
# ============================================================================

@game_bp.route('/api/game/hunters/profile', methods=['GET'])
def get_player_profile():
    """Get complete player profile with level, stats, and progress"""
    try:
        from backend.services.hunters_leveling_system import hunters_leveling_system
        from backend.services.xp_system import xp_system
        
        user_id = request.args.get('user_id', 'default_user')
        
        # Get leveling profile
        level_profile = hunters_leveling_system.get_player_profile(user_id)
        
        # Get achievements
        achievements = []
        if game_achievement_system:
            achievements = game_achievement_system.get_user_achievements(user_id)
        
        # Get milestones
        milestones = []
        if game_achievement_system:
            milestones = game_achievement_system.get_user_milestones(user_id)
        
        # Get XP system profile
        xp_profile = xp_system.get_user_profile(user_id)
        
        # Get stats points
        stats_points = 0
        if game_achievement_system:
            stats_points = game_achievement_system.get_user_stats_points(user_id)
        
        return jsonify({
            'success': True,
            'profile': {
                'user_id': user_id,
                'leveling': level_profile,
                'achievements': achievements,
                'milestones': milestones,
                'xp_system': xp_profile,
                'stats_points': stats_points
            }
        }), 200
        
    except Exception as e:
        import traceback
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500


@game_bp.route('/api/game/hunters/level', methods=['GET'])
def get_level_info():
    """Get player level information"""
    try:
        from backend.services.hunters_leveling_system import hunters_leveling_system
        
        user_id = request.args.get('user_id', 'default_user')
        profile = hunters_leveling_system.get_player_profile(user_id)
        
        return jsonify({
            'success': True,
            'level_info': {
                'current_level': profile['current_level'],
                'current_xp': profile['current_xp'],
                'total_xp': profile['total_xp'],
                'xp_to_next_level': profile['xp_to_next_level'],
                'level_progress': profile['level_progress'],
                'title': profile['title'],
                'prestige_level': profile['prestige_level'],
                'next_level_info': profile['next_level_info']
            }
        }), 200
        
    except Exception as e:
        import traceback
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500


@game_bp.route('/api/game/hunters/award-xp', methods=['POST'])
def award_xp_hunters():
    """Award XP to a player"""
    try:
        from backend.services.hunters_leveling_system import hunters_leveling_system
        
        data = request.get_json() or {}
        user_id = data.get('user_id', 'default_user')
        xp_amount = data.get('xp_amount', 0)
        source = data.get('source', 'unknown')
        action_type = data.get('action_type')
        metadata = data.get('metadata', {})
        
        if xp_amount <= 0:
            return jsonify({
                'success': False,
                'error': 'XP amount must be positive'
            }), 400
        
        result = hunters_leveling_system.award_xp(
            user_id, xp_amount, source, action_type, metadata
        )
        
        return jsonify({
            'success': True,
            'result': result
        }), 200
        
    except Exception as e:
        import traceback
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500


@game_bp.route('/api/game/hunters/stats', methods=['GET'])
def get_hunters_stats():
    """Get player stats"""
    try:
        from backend.services.hunters_leveling_system import hunters_leveling_system
        
        user_id = request.args.get('user_id', 'default_user')
        profile = hunters_leveling_system.get_player_profile(user_id)
        
        return jsonify({
            'success': True,
            'stats': profile['stats'],
            'available_stat_points': profile['available_stat_points']
        }), 200
        
    except Exception as e:
        import traceback
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500


@game_bp.route('/api/game/hunters/allocate-stats', methods=['POST'])
def allocate_stats_hunters():
    """Allocate stat points"""
    try:
        from backend.services.hunters_leveling_system import hunters_leveling_system
        
        data = request.get_json() or {}
        user_id = data.get('user_id', 'default_user')
        
        # Support both formats: individual stat_name/points or stat_allocations dict
        stat_name = data.get('stat_name')
        points = data.get('points', 0)
        stat_allocations = data.get('stat_allocations', {})
        
        # If individual stat_name provided, convert to stat_allocations format
        if stat_name and points != 0:
            stat_allocations = {stat_name: points}
        
        if not stat_allocations:
            return jsonify({
                'success': False,
                'error': 'stat_allocations or stat_name/points required'
            }), 400
        
        result = hunters_leveling_system.allocate_stat_points(user_id, stat_allocations)
        
        return jsonify({
            'success': result.get('success', False),
            'result': result,
            'message': result.get('message', '')
        }), 200 if result.get('success') else 400
        
    except Exception as e:
        import traceback
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500


@game_bp.route('/api/game/hunters/leaderboard', methods=['GET'])
def get_leaderboard():
    """Get leaderboard"""
    try:
        from backend.services.hunters_leveling_system import hunters_leveling_system
        
        limit = int(request.args.get('limit', 100))
        category = request.args.get('category', 'level')
        
        leaderboard = hunters_leveling_system.get_leaderboard(limit, category)
        
        return jsonify({
            'success': True,
            'leaderboard': leaderboard,
            'category': category,
            'limit': limit
        }), 200
        
    except Exception as e:
        import traceback
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500


@game_bp.route('/api/game/hunters/xp-history', methods=['GET'])
def get_xp_history():
    """Get XP history for a player"""
    try:
        from backend.services.hunters_leveling_system import hunters_leveling_system
        
        user_id = request.args.get('user_id', 'default_user')
        limit = int(request.args.get('limit', 50))
        
        history = hunters_leveling_system.xp_history.get(user_id, [])
        history = history[-limit:]  # Get last N entries
        
        return jsonify({
            'success': True,
            'history': history,
            'total_events': len(hunters_leveling_system.xp_history.get(user_id, []))
        }), 200
        
    except Exception as e:
        import traceback
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500


@game_bp.route('/api/game/rewards/claim', methods=['POST'])
@game_bp.route('/vidgenerator/api/game/rewards/claim', methods=['POST'])
def claim_game_reward():
    """Claim a game reward"""
    try:
        from backend.services.rewards_system import rewards_system
        
        data = request.get_json() or {}
        user_id = data.get('user_id', 'default_user')
        reward_id = data.get('reward_id')
        
        if not reward_id:
            return jsonify({
                'success': False,
                'error': 'reward_id is required'
            }), 400
        
        result = rewards_system.claim_reward(user_id, reward_id)
        
        return jsonify(result), 200 if result.get('success') else 400
    except Exception as e:
        import traceback
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500


@game_bp.route('/api/game/hunters/rewards', methods=['GET'])
def get_level_rewards():
    """Get rewards for a specific level or all levels"""
    try:
        from backend.services.hunters_leveling_system import hunters_leveling_system
        
        level = request.args.get('level')
        
        if level:
            level = int(level)
            reward = hunters_leveling_system.level_rewards.get(level, {})
            return jsonify({
                'success': True,
                'level': level,
                'rewards': reward
            }), 200
        else:
            # Return all rewards
            return jsonify({
                'success': True,
                'rewards': hunters_leveling_system.level_rewards
            }), 200
            
    except Exception as e:
        import traceback
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500


@game_bp.route('/api/game/hunters/titles', methods=['GET'])
def get_titles():
    """Get available titles"""
    try:
        from backend.services.hunters_leveling_system import hunters_leveling_system
        
        return jsonify({
            'success': True,
            'titles': hunters_leveling_system.titles,
            'title_levels': list(hunters_leveling_system.titles.keys())
        }), 200
        
    except Exception as e:
        import traceback
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500


@game_bp.route('/api/game/hunters/prestige', methods=['POST'])
def prestige():
    """Prestige: Reset to level 1 with permanent bonuses"""
    try:
        from backend.services.hunters_leveling_system import hunters_leveling_system
        
        data = request.get_json() or {}
        user_id = data.get('user_id', 'default_user')
        
        result = hunters_leveling_system.prestige(user_id)
        
        return jsonify({
            'success': result.get('success', False),
            'result': result
        }), 200 if result.get('success') else 400
        
    except Exception as e:
        import traceback
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500


@game_bp.route('/api/game/hunters/calculate-level', methods=['POST'])
def calculate_level():
    """Calculate level from XP (utility endpoint)"""
    try:
        from backend.services.hunters_leveling_system import hunters_leveling_system
        
        data = request.get_json() or {}
        total_xp = int(data.get('total_xp', 0))
        
        level = hunters_leveling_system.calculate_level(total_xp)
        xp_for_level = hunters_leveling_system.xp_for_level(level)
        xp_for_next = hunters_leveling_system.xp_for_level(level + 1)
        
        return jsonify({
            'success': True,
            'total_xp': total_xp,
            'level': level,
            'xp_for_current_level': xp_for_level,
            'xp_for_next_level': xp_for_next,
            'xp_in_current_level': total_xp - xp_for_level,
            'xp_to_next_level': xp_for_next - total_xp,
            'title': hunters_leveling_system.get_title_for_level(level)
        }), 200
        
    except Exception as e:
        import traceback
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500


@game_bp.route('/api/game/challenges/daily')
def get_daily_challenges():
    """Get daily challenges for user"""
    try:
        from backend.services.daily_challenges import daily_challenge_system
        user_id = request.args.get('user_id', 'default_user')
        challenges = daily_challenge_system.get_daily_challenges(user_id)
        return jsonify({
            'success': True,
            'challenges': challenges
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'challenges': []
        }), 500


@game_bp.route('/api/game/challenges/weekly')
def get_weekly_challenges():
    """Get weekly challenges for user"""
    try:
        from backend.services.daily_challenges import daily_challenge_system
        user_id = request.args.get('user_id', 'default_user')
        challenges = daily_challenge_system.get_weekly_challenges(user_id)
        return jsonify({
            'success': True,
            'challenges': challenges
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'challenges': []
        }), 500


@game_bp.route('/api/game/challenges/update', methods=['POST'])
def update_challenge():
    """Update challenge progress"""
    try:
        from backend.services.daily_challenges import daily_challenge_system
        data = request.get_json() or {}
        user_id = data.get('user_id', 'default_user')
        challenge_id = data.get('challenge_id')
        progress = data.get('progress', 1)
        
        if not challenge_id:
            return jsonify({
                'success': False,
                'error': 'challenge_id required'
            }), 400
        
        result = daily_challenge_system.update_challenge_progress(user_id, challenge_id, progress)
        return jsonify(result)
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@game_bp.route('/api/game/challenges/summary')
def get_challenges_summary():
    """Get challenges summary"""
    try:
        from backend.services.daily_challenges import daily_challenge_system
        user_id = request.args.get('user_id', 'default_user')
        summary = daily_challenge_system.get_user_challenges_summary(user_id)
        return jsonify({
            'success': True,
            'summary': summary
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'summary': {}
        }), 500


# Note: Middleware strips /vidgenerator, so /vidgenerator/api/* becomes /api/* before matching
# Only need /api/* route - middleware handles the prefix
@game_bp.route('/api/game/battle/create', methods=['POST'])
def create_battle():
    """Create a new battle"""
    try:
        from backend.services.battle_system import battle_system
        data = request.get_json() or {}
        player1_id = data.get('user_id', 'default_user')
        player2_id = data.get('opponent_id')
        battle_type = data.get('battle_type', 'ranked')
        bet_amount = data.get('bet_amount', 0)
        
        result = battle_system.create_battle(player1_id, player2_id, battle_type, bet_amount)
        return jsonify(result)
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# Note: Middleware strips /vidgenerator, so /vidgenerator/api/* becomes /api/* before matching
# Only need /api/* route - middleware handles the prefix
@game_bp.route('/api/game/battle/execute', methods=['POST'])
def execute_battle():
    """Execute a battle"""
    try:
        from backend.services.battle_system import battle_system
        data = request.get_json() or {}
        battle_id = data.get('battle_id')
        
        if not battle_id:
            return jsonify({
                'success': False,
                'error': 'battle_id required'
            }), 400
        
        result = battle_system.execute_battle(battle_id)
        return jsonify(result)
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# Note: Middleware strips /vidgenerator, so /vidgenerator/api/* becomes /api/* before matching
# Only need /api/* route - middleware handles the prefix
@game_bp.route('/api/game/battle/stats')
def get_battle_stats():
    """Get comprehensive battle statistics with A+ quality data"""
    try:
        user_id = request.args.get('user_id', 'default_user')
        
        # Try comprehensive stats service first
        try:
            from backend.services.battle_stats_service import battle_stats_service
            if battle_stats_service:
                overview_stats = battle_stats_service.get_overview_stats(user_id)
                return jsonify({
                    'success': True,
                    'stats': overview_stats
                }), 200
        except Exception as e:
            pass  # Fall through to other methods
        
        # Try quick battle system
        try:
            from backend.services.quick_battle_system import quick_battle
            stats = quick_battle.get_user_battle_stats(user_id)
            return jsonify({
                'success': True,
                'stats': stats
            }), 200
        except:
            # Fallback to enhanced battle system
            try:
                from backend.services.battle_system_enhanced import enhanced_battle_system
                stats = enhanced_battle_system.get_user_battle_stats(user_id)
                return jsonify({
                    'success': True,
                    'stats': stats
                }), 200
            except:
                # Final fallback - use stats service basic data
                try:
                    from backend.services.battle_stats_service import battle_stats_service
                    if battle_stats_service:
                        overview_stats = battle_stats_service.get_overview_stats(user_id)
                        return jsonify({
                            'success': True,
                            'stats': overview_stats
                        }), 200
                except:
                    pass
                
                # Ultimate fallback - basic stats
                return jsonify({
                    'success': True,
                    'stats': {
                        'wins': 0,
                        'losses': 0,
                        'total_battles': 0,
                        'win_rate': 0.0
                    }
                }), 200
    except Exception as e:
        # Always return 200, even on error
        return jsonify({
            'success': False,
            'error': str(e),
            'stats': {
                'wins': 0,
                'losses': 0,
                'total_battles': 0,
                'win_rate': 0.0
            }
        }), 200


# Note: Middleware strips /vidgenerator, so /vidgenerator/api/* becomes /api/* before matching
# Only need /api/* route - middleware handles the prefix
@game_bp.route('/api/game/battle/history')
def get_battle_history():
    """Get battle history"""
    try:
        user_id = request.args.get('user_id', 'default_user')
        limit = int(request.args.get('limit', 20))
        
        # Try multiple sources
        history = []
        
        try:
            from backend.services.battle_system import battle_system
            history = battle_system.get_battle_history(user_id, limit)
        except:
            try:
                from backend.services.quick_battle_system import quick_battle
                stats = quick_battle.get_user_battle_stats(user_id)
                # Convert stats to history format
                if stats:
                    history = [{
                        'battle_id': f"quick_{i}",
                        'timestamp': '2026-01-01T00:00:00',
                        'won': stats.get('wins', 0) > 0,
                        'opponent_name': 'Quick Battle Opponent'
                    } for i in range(min(limit, stats.get('total_battles', 0)))]
            except:
                pass
        
        return jsonify({
            'success': True,
            'history': history if history else []
        }), 200
    except Exception as e:
        # Always return 200 with empty history
        return jsonify({
            'success': True,
            'error': str(e),
            'history': []
        }), 200


@game_bp.route('/api/game/battle/leaderboard')
def get_battle_leaderboard():
    """Get battle leaderboard"""
    try:
        from backend.services.battle_system import battle_system
        battle_type = request.args.get('type', 'ranked')
        limit = int(request.args.get('limit', 50))
        leaderboard = battle_system.get_leaderboard(battle_type, limit)
        return jsonify({
            'success': True,
            'leaderboard': leaderboard
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'leaderboard': []
        }), 500


@game_bp.route('/api/game/tournament/create', methods=['POST'])
def create_tournament():
    """Create a tournament"""
    try:
        from backend.services.battle_system import battle_system
        data = request.get_json() or {}
        name = data.get('name', 'Tournament')
        tournament_type = data.get('type', 'daily')
        max_participants = int(data.get('max_participants', 16))
        entry_fee = int(data.get('entry_fee', 0))
        
        result = battle_system.create_tournament(name, tournament_type, max_participants, entry_fee)
        return jsonify(result)
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@game_bp.route('/api/game/tournament/join', methods=['POST'])
def join_tournament():
    """Join a tournament"""
    try:
        from backend.services.battle_system import battle_system
        data = request.get_json() or {}
        tournament_id = data.get('tournament_id')
        user_id = data.get('user_id', 'default_user')
        
        if not tournament_id:
            return jsonify({
                'success': False,
                'error': 'tournament_id required'
            }), 400
        
        result = battle_system.join_tournament(tournament_id, user_id)
        return jsonify(result)
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@game_bp.route('/api/game/tournament/list')
def list_tournaments():
    """Get active tournaments"""
    try:
        from backend.services.battle_system import battle_system
        tournaments = battle_system.get_active_tournaments()
        return jsonify({
            'success': True,
            'tournaments': tournaments
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'tournaments': []
        }), 500


@game_bp.route('/api/game/social/friends')
def get_friends():
    """Get user's friends"""
    try:
        from backend.services.social_system import social_system
        user_id = request.args.get('user_id', 'default_user')
        friends = social_system.get_friends(user_id)
        return jsonify({
            'success': True,
            'friends': friends
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'friends': []
        }), 500


@game_bp.route('/api/game/social/friend-request', methods=['POST'])
def send_friend_request():
    """Send a friend request"""
    try:
        from backend.services.social_system import social_system
        data = request.get_json() or {}
        from_user_id = data.get('user_id', 'default_user')
        to_user_id = data.get('friend_id')
        
        if not to_user_id:
            return jsonify({
                'success': False,
                'error': 'friend_id required'
            }), 400
        
        result = social_system.send_friend_request(from_user_id, to_user_id)
        return jsonify(result)
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@game_bp.route('/api/game/social/friend-requests')
def get_friend_requests():
    """Get friend requests"""
    try:
        from backend.services.social_system import social_system
        user_id = request.args.get('user_id', 'default_user')
        requests = social_system.get_friend_requests(user_id)
        return jsonify({
            'success': True,
            'requests': requests
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'requests': {'incoming': [], 'outgoing': []}
        }), 500


@game_bp.route('/api/game/social/respond-request', methods=['POST'])
def respond_friend_request():
    """Respond to friend request"""
    try:
        from backend.services.social_system import social_system
        data = request.get_json() or {}
        request_id = data.get('request_id')
        user_id = data.get('user_id', 'default_user')
        accept = data.get('accept', True)
        
        if not request_id:
            return jsonify({
                'success': False,
                'error': 'request_id required'
            }), 400
        
        result = social_system.respond_to_friend_request(request_id, user_id, accept)
        return jsonify(result)
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@game_bp.route('/api/game/social/guild/create', methods=['POST'])
def create_guild():
    """Create a guild"""
    try:
        from backend.services.social_system import social_system
        data = request.get_json() or {}
        name = data.get('name')
        leader_id = data.get('user_id', 'default_user')
        description = data.get('description', '')
        
        if not name:
            return jsonify({
                'success': False,
                'error': 'name required'
            }), 400
        
        result = social_system.create_guild(name, leader_id, description)
        return jsonify(result)
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@game_bp.route('/api/game/social/guild/join', methods=['POST'])
def join_guild():
    """Join a guild"""
    try:
        from backend.services.social_system import social_system
        data = request.get_json() or {}
        guild_id = data.get('guild_id')
        user_id = data.get('user_id', 'default_user')
        
        if not guild_id:
            return jsonify({
                'success': False,
                'error': 'guild_id required'
            }), 400
        
        result = social_system.join_guild(guild_id, user_id)
        return jsonify(result)
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@game_bp.route('/api/game/social/guild/my-guild')
def get_my_guild():
    """Get user's guild"""
    try:
        from backend.services.social_system import social_system
        user_id = request.args.get('user_id', 'default_user')
        guild = social_system.get_user_guild(user_id)
        return jsonify({
            'success': True,
            'guild': guild
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'guild': None
        }), 500


@game_bp.route('/api/game/social/guild/leaderboard')
def get_guild_leaderboard():
    """Get guild leaderboard"""
    try:
        from backend.services.social_system import social_system
        limit = int(request.args.get('limit', 20))
        leaderboard = social_system.get_guild_leaderboard(limit)
        return jsonify({
            'success': True,
            'leaderboard': leaderboard
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'leaderboard': []
        }), 500


@game_bp.route('/api/game/social/stats')
def get_social_stats():
    """Get social statistics"""
    try:
        from backend.services.social_system import social_system
        user_id = request.args.get('user_id', 'default_user')
        stats = social_system.get_social_stats(user_id)
        return jsonify({
            'success': True,
            'stats': stats
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'stats': {}
        }), 500


@game_bp.route('/api/game/shop/items')
def get_shop_items():
    """Get shop items"""
    try:
        from backend.services.game_shop import game_shop
        category = request.args.get('category')
        items = game_shop.get_shop_items(category)
        return jsonify({
            'success': True,
            'items': items
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'items': []
        }), 500


@game_bp.route('/api/game/shop/currency')
def get_currency():
    """Get user currency"""
    try:
        from backend.services.game_shop import game_shop
        user_id = request.args.get('user_id', 'default_user')
        currency = game_shop.get_user_currency(user_id)
        return jsonify({
            'success': True,
            'currency': currency
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'currency': 0
        }), 500


@game_bp.route('/api/game/shop/purchase', methods=['POST'])
def purchase_item():
    """Purchase an item"""
    try:
        from backend.services.game_shop import game_shop
        data = request.get_json() or {}
        user_id = data.get('user_id', 'default_user')
        item_id = data.get('item_id')
        
        if not item_id:
            return jsonify({
                'success': False,
                'error': 'item_id required'
            }), 400
        
        result = game_shop.purchase_item(user_id, item_id)
        return jsonify(result)
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@game_bp.route('/api/game/shop/inventory')
def get_inventory():
    """Get user inventory"""
    try:
        from backend.services.game_shop import game_shop
        user_id = request.args.get('user_id', 'default_user')
        inventory = game_shop.get_user_inventory(user_id)
        return jsonify({
            'success': True,
            'inventory': inventory
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'inventory': []
        }), 500


@game_bp.route('/api/game/events/active')
def get_active_events():
    """Get active events"""
    try:
        from backend.services.events_system import events_system
        events = events_system.get_active_events()
        return jsonify({
            'success': True,
            'events': events
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'events': []
        }), 500


@game_bp.route('/api/game/events/upcoming')
def get_upcoming_events():
    """Get upcoming events"""
    try:
        from backend.services.events_system import events_system
        limit = int(request.args.get('limit', 5))
        events = events_system.get_upcoming_events(limit)
        return jsonify({
            'success': True,
            'events': events
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'events': []
        }), 500


@game_bp.route('/api/game/events/join', methods=['POST'])
def join_event():
    """Join an event"""
    try:
        from backend.services.events_system import events_system
        data = request.get_json() or {}
        event_id = data.get('event_id')
        user_id = data.get('user_id', 'default_user')
        
        if not event_id:
            return jsonify({
                'success': False,
                'error': 'event_id required'
            }), 400
        
        result = events_system.join_event(event_id, user_id)
        return jsonify(result)
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@game_bp.route('/api/game/events/my-events')
def get_my_events():
    """Get user's events"""
    try:
        from backend.services.events_system import events_system
        user_id = request.args.get('user_id', 'default_user')
        events = events_system.get_user_events(user_id)
        return jsonify({
            'success': True,
            'events': events
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'events': []
        }), 500


@game_bp.route('/api/game/events/notifications')
def get_notifications():
    """Get event notifications"""
    try:
        from backend.services.events_system import events_system
        user_id = request.args.get('user_id', 'default_user')
        unread_only = request.args.get('unread_only', 'false').lower() == 'true'
        notifications = events_system.get_notifications(user_id, unread_only)
        return jsonify({
            'success': True,
            'notifications': notifications
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'notifications': []
        }), 500


@game_bp.route('/api/game/stats/advanced/trends')
def get_advanced_trends():
    """Get advanced trends"""
    try:
        from backend.services.advanced_stats import advanced_stats
        user_id = request.args.get('user_id', 'default_user')
        days = int(request.args.get('days', 7))
        trends = advanced_stats.get_user_trends(user_id, days)
        return jsonify({
            'success': True,
            'trends': trends
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'trends': {}
        }), 500


@game_bp.route('/api/game/stats/advanced/performance')
def get_performance_metrics():
    """Get performance metrics"""
    try:
        from backend.services.advanced_stats import advanced_stats
        user_id = request.args.get('user_id', 'default_user')
        metrics = advanced_stats.get_performance_metrics(user_id)
        return jsonify({
            'success': True,
            'metrics': metrics
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'metrics': {}
        }), 500


@game_bp.route('/api/game/stats/advanced/compare')
def compare_users():
    """Compare two users"""
    try:
        from backend.services.advanced_stats import advanced_stats
        user1_id = request.args.get('user1_id', 'default_user')
        user2_id = request.args.get('user2_id')
        
        if not user2_id:
            return jsonify({
                'success': False,
                'error': 'user2_id required'
            }), 400
        
        comparison = advanced_stats.compare_users(user1_id, user2_id)
        return jsonify({
            'success': True,
            'comparison': comparison
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'comparison': {}
        }), 500


@game_bp.route('/api/game/stats/advanced/time-series')
def get_time_series():
    """Get time series data"""
    try:
        from backend.services.advanced_stats import advanced_stats
        user_id = request.args.get('user_id', 'default_user')
        metric = request.args.get('metric', 'total_xp')
        days = int(request.args.get('days', 7))
        data = advanced_stats.get_time_series_data(user_id, metric, days)
        return jsonify({
            'success': True,
            'data': data
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'data': []
        }), 500


@game_bp.route('/api/game/stats/advanced/global')
def get_global_stats():
    """Get global statistics"""
    try:
        from backend.services.advanced_stats import advanced_stats
        stats = advanced_stats.get_global_stats()
        return jsonify({
            'success': True,
            'stats': stats
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e),
            'stats': {}
        }), 500


@cached_query(ttl=180)  # Cache for 3 minutes
def _calculate_user_stats(user_id: str) -> dict:
    """Calculate user statistics from database"""
    try:
        # Import models inside function to avoid import errors
        from src.db.models import db, Documentary
        
        # Get all completed documentaries for user (simplified - assumes all are for this user)
        # In production, you'd filter by actual user_id
        total_videos = Documentary.query.filter_by(status='completed').count()
        
        # Videos by category
        category_videos = {}
        categories = ['underholdning', 'porn', 'rettigheder']
        for cat in categories:
            count = Documentary.query.filter_by(
                status='completed',
                category_name=cat
            ).count()
            category_videos[cat] = count
        
        # Videos created today
        today = datetime.utcnow().date()
        videos_today = Documentary.query.filter(
            Documentary.status == 'completed',
            db.func.date(Documentary.created_at) == today
        ).count()
        
        # Quality stats - Calculate from Documentary
        from sqlalchemy import or_
        
        # High quality videos: documentaries with quality_score >= 0.7
        high_quality_videos = Documentary.query.filter(
            Documentary.status == 'completed',
            Documentary.quality_score >= 0.7
        ).count()
        
        # Perfect quality: check if any documentary has quality_score >= 1.0 or quality_meets_a_plus = True
        has_perfect_quality = Documentary.query.filter(
            Documentary.status == 'completed',
            or_(
                Documentary.quality_score >= 1.0,
                Documentary.quality_meets_a_plus == True
            )
        ).first() is not None
        
        # Average quality: calculate from completed documentaries with quality scores
        quality_scores = db.session.query(
            db.func.avg(Documentary.quality_score)
        ).filter(
            Documentary.status == 'completed',
            Documentary.quality_score.isnot(None),
            Documentary.quality_score > 0
        ).scalar()
        
        avg_quality = float(quality_scores) if quality_scores is not None else 0.0
        
        return {
            'total_videos': total_videos,
            'category_videos': category_videos,
            'videos_today': videos_today,
            'high_quality_videos': high_quality_videos,
            'has_perfect_quality': has_perfect_quality,
            'avg_quality': avg_quality
        }
    except Exception as e:
        print(f"[Game] Error calculating stats: {e}")
        return {
            'total_videos': 0,
            'category_videos': {},
            'videos_today': 0,
            'high_quality_videos': 0,
            'has_perfect_quality': False,
            'avg_quality': 0.0
        }

