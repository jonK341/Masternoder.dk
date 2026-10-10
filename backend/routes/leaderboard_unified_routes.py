"""
Unified Leaderboard Routes
Comprehensive leaderboard system integrating all 178 point systems, trophies, and battle stats
"""
from flask import Blueprint, request, jsonify
import sys
import importlib

# Import leaderboard service (file name starts with number, need importlib)
try:
    leaderboard_module = importlib.import_module('backend.services.178_systems_leaderboard')
    leaderboard_178_systems = leaderboard_module.leaderboard_178_systems
except (ImportError, AttributeError, SyntaxError, Exception) as e:
    print(f"[Leaderboard] Warning: Could not import 178_systems_leaderboard: {e}", file=sys.stderr, flush=True)
    leaderboard_178_systems = None

# Note: enhanced_leaderboard_system import removed - not used in routes and causes import chain errors
# (enhanced_leaderboard_system -> ai_intelligence_system -> quest_system -> rewards_system_v2 has errors)
# This service is not used anywhere in the routes below, so we set it to None to prevent import errors
enhanced_leaderboard_system = None

try:
    from backend.services.trophy_system import trophy_system
except (ImportError, AttributeError, SyntaxError, Exception) as e:
    print(f"[Leaderboard] Warning: Could not import trophy_system: {e}", file=sys.stderr, flush=True)
    trophy_system = None

try:
    from backend.services.quick_battle_system import quick_battle
except (ImportError, AttributeError, SyntaxError, Exception) as e:
    print(f"[Leaderboard] Warning: Could not import quick_battle: {e}", file=sys.stderr, flush=True)
    quick_battle = None

leaderboard_unified_bp = Blueprint('leaderboard_unified', __name__)

# Alias routes for backward compatibility
@leaderboard_unified_bp.route('/api/178-systems/leaderboard/all')
@leaderboard_unified_bp.route('/vidgenerator/api/178-systems/leaderboard/all')
def get_all_systems_leaderboard_alias():
    """Alias for /api/leaderboard/all"""
    return get_all_systems_leaderboard()

@leaderboard_unified_bp.route('/api/178-systems/leaderboard/<system_id>')
@leaderboard_unified_bp.route('/vidgenerator/api/178-systems/leaderboard/<system_id>')
def get_system_leaderboard_alias(system_id):
    """Alias for /api/leaderboard/<system_id>"""
    return get_system_leaderboard(system_id)

@leaderboard_unified_bp.route('/api/leaderboard/stats')
@leaderboard_unified_bp.route('/vidgenerator/api/leaderboard/stats')
def get_leaderboard_stats():
    """Get leaderboard statistics"""
    try:
        stats = {
            'success': True,
            'total_systems': 178,
            'total_users': 0,
            'total_entries': 0,
            'last_updated': None
        }
        
        # Try to get stats from leaderboard service
        if leaderboard_178_systems:
            try:
                result = leaderboard_178_systems.get_all_systems_leaderboard(limit=1)
                if result.get('success'):
                    stats['total_entries'] = result.get('total_entries', 0)
                    stats['last_updated'] = result.get('updated_at')
            except:
                pass
        
        return jsonify(stats), 200
    except Exception as e:
        print(f"[Leaderboard] Error: {e}", file=sys.stderr, flush=True)
        return jsonify({
            'success': False,
            'error': str(e),
            'total_systems': 178,
            'total_users': 0,
            'total_entries': 0
        }), 200

@leaderboard_unified_bp.route('/api/leaderboard/<system_id>')
@leaderboard_unified_bp.route('/vidgenerator/api/leaderboard/<system_id>')
def get_system_leaderboard(system_id):
    """Get leaderboard for a specific point system"""
    try:
        if not leaderboard_178_systems:
            return jsonify({
                'success': False,
                'error': 'Leaderboard service not available',
                'leaderboard': []
            }), 200
        
        limit = int(request.args.get('limit', 100))
        timeframe = request.args.get('timeframe', 'all')  # all, daily, weekly, monthly
        
        result = leaderboard_178_systems.get_leaderboard(system_id, limit, timeframe)
        
        return jsonify(result), 200
    except Exception as e:
        print(f"[Leaderboard] Error: {e}", file=sys.stderr, flush=True)
        return jsonify({
            'success': False,
            'error': str(e),
            'leaderboard': []
        }), 200

@leaderboard_unified_bp.route('/api/leaderboard/all')
@leaderboard_unified_bp.route('/vidgenerator/api/leaderboard/all')
def get_all_systems_leaderboard():
    """Get combined leaderboard across all 178 systems"""
    try:
        if not leaderboard_178_systems:
            return jsonify({
                'success': False,
                'error': 'Leaderboard service not available',
                'leaderboard': []
            }), 200
        
        limit = int(request.args.get('limit', 100))
        timeframe = request.args.get('timeframe', 'all')
        
        result = leaderboard_178_systems.get_all_systems_leaderboard(limit)
        
        return jsonify(result), 200
    except Exception as e:
        print(f"[Leaderboard] Error: {e}", file=sys.stderr, flush=True)
        return jsonify({
            'success': False,
            'error': str(e),
            'leaderboard': []
        }), 200

@leaderboard_unified_bp.route('/api/leaderboard/trophies')
@leaderboard_unified_bp.route('/vidgenerator/api/leaderboard/trophies')
def get_trophy_leaderboard():
    """Get trophy leaderboard"""
    try:
        if not trophy_system:
            return jsonify({
                'success': False,
                'error': 'Trophy service not available',
                'leaderboard': []
            }), 200
        
        limit = int(request.args.get('limit', 50))
        
        # Get all users with trophy data
        leaderboard = []
        try:
            from backend.services.unified_points_database import unified_points_db
            from src.db.models import db, UserProfile
            
            users = UserProfile.query.limit(limit * 2).all()
            
            for user in users:
                try:
                    user_trophies = trophy_system.get_user_trophies(user.user_id)
                    trophy_count = len(user_trophies) if isinstance(user_trophies, list) else len(user_trophies) if user_trophies else 0
                    
                    if trophy_count > 0:
                        leaderboard.append({
                            'user_id': user.user_id,
                            'username': user.username or f'User_{user.user_id[:8]}',
                            'trophy_count': trophy_count,
                            'trophies': user_trophies if isinstance(user_trophies, list) else list(user_trophies) if user_trophies else []
                        })
                except:
                    continue
            
            # Sort by trophy count
            leaderboard.sort(key=lambda x: x['trophy_count'], reverse=True)
            leaderboard = leaderboard[:limit]
            
            # Assign ranks
            for i, entry in enumerate(leaderboard):
                entry['rank'] = i + 1
            
        except Exception as e:
            print(f"[Leaderboard] Error getting trophy data: {e}", file=sys.stderr, flush=True)
        
        return jsonify({
            'success': True,
            'leaderboard': leaderboard,
            'total_entries': len(leaderboard)
        }), 200
    except Exception as e:
        print(f"[Leaderboard] Error: {e}", file=sys.stderr, flush=True)
        return jsonify({
            'success': False,
            'error': str(e),
            'leaderboard': []
        }), 200

@leaderboard_unified_bp.route('/api/leaderboard/battle')
@leaderboard_unified_bp.route('/vidgenerator/api/leaderboard/battle')
def get_battle_leaderboard():
    """Get battle/quick battle leaderboard"""
    try:
        limit = int(request.args.get('limit', 50))
        leaderboard_type = request.args.get('type', 'quick')  # quick, pvp, all
        
        leaderboard = []
        try:
            # Get battle counters from quick battle system
            if quick_battle and hasattr(quick_battle, 'battle_counters'):
                counters = quick_battle.battle_counters
                
                for user_id, counter_data in counters.items():
                    if counter_data.get('completed_battles', 0) > 0:
                        leaderboard.append({
                            'user_id': user_id,
                            'wins': counter_data.get('wins', 0),
                            'losses': counter_data.get('losses', 0),
                            'total_battles': counter_data.get('total_battles', 0),
                            'completed_battles': counter_data.get('completed_battles', 0),
                            'win_rate': counter_data.get('win_rate', 0.0),
                            'total_actions': counter_data.get('total_actions', 0),
                            'total_clicks': counter_data.get('total_clicks', 0),
                            'total_attacks': counter_data.get('total_attacks', 0)
                        })
            
            # Sort by wins or win rate
            if leaderboard_type == 'quick':
                leaderboard.sort(key=lambda x: x['wins'], reverse=True)
            else:
                leaderboard.sort(key=lambda x: x.get('win_rate', 0), reverse=True)
            
            leaderboard = leaderboard[:limit]
            
            # Assign ranks
            for i, entry in enumerate(leaderboard):
                entry['rank'] = i + 1
                
        except Exception as e:
            print(f"[Leaderboard] Error getting battle data: {e}", file=sys.stderr, flush=True)
        
        return jsonify({
            'success': True,
            'type': leaderboard_type,
            'leaderboard': leaderboard,
            'total_entries': len(leaderboard)
        }), 200
    except Exception as e:
        print(f"[Leaderboard] Error: {e}", file=sys.stderr, flush=True)
        return jsonify({
            'success': False,
            'error': str(e),
            'leaderboard': []
        }), 200

@leaderboard_unified_bp.route('/api/leaderboard/user/<user_id>/rank')
@leaderboard_unified_bp.route('/vidgenerator/api/leaderboard/user/<user_id>/rank')
def get_user_rank(user_id):
    """Get user's rank across all systems"""
    try:
        system_id = request.args.get('system_id', 'all')
        
        if not leaderboard_178_systems:
            return jsonify({
                'success': False,
                'error': 'Leaderboard service not available'
            }), 200
        
        if system_id == 'all':
            # Get rank in combined leaderboard
            result = leaderboard_178_systems.get_all_systems_leaderboard(limit=10000)
            if result.get('success'):
                leaderboard = result.get('leaderboard', [])
                for i, entry in enumerate(leaderboard):
                    if entry['user_id'] == user_id:
                        return jsonify({
                            'success': True,
                            'user_id': user_id,
                            'rank': i + 1,
                            'total_players': len(leaderboard),
                            'points': entry.get('total_points', 0)
                        }), 200
        else:
            # Get rank in specific system
            rank_data = leaderboard_178_systems.get_user_rank(user_id, system_id)
            return jsonify({
                'success': True,
                'user_id': user_id,
                'system_id': system_id,
                **rank_data
            }), 200
        
        return jsonify({
            'success': False,
            'error': 'User rank not found'
        }), 200
    except Exception as e:
        print(f"[Leaderboard] Error: {e}", file=sys.stderr, flush=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 200

@leaderboard_unified_bp.route('/api/leaderboard/categories')
@leaderboard_unified_bp.route('/vidgenerator/api/leaderboard/categories')
def get_leaderboard_categories():
    """Get all available leaderboard categories"""
    try:
        categories = {
            'battle': {
                'name': 'Battle',
                'endpoint': '/api/leaderboard/battle',
                'description': 'Battle victories and performance'
            },
            'trophies': {
                'name': 'Trophies',
                'endpoint': '/api/leaderboard/trophies',
                'description': 'Trophy collection rankings'
            },
            'all': {
                'name': 'All Systems',
                'endpoint': '/api/leaderboard/all',
                'description': 'Combined ranking across all 178 point systems'
            },
            'xp': {
                'name': 'XP Points',
                'endpoint': '/api/leaderboard/xp',
                'description': 'Experience points leaderboard'
            },
            'activity': {
                'name': 'Activity',
                'endpoint': '/api/leaderboard/activity',
                'description': 'Activity points leaderboard'
            },
            'quick_battle': {
                'name': 'Quick Battle',
                'endpoint': '/api/leaderboard/battle?type=quick',
                'description': 'Quick battle performance rankings'
            }
        }
        
        return jsonify({
            'success': True,
            'categories': categories
        }), 200
    except Exception as e:
        print(f"[Leaderboard] Error: {e}", file=sys.stderr, flush=True)
        return jsonify({
            'success': False,
            'error': str(e),
            'categories': {}
        }), 200
