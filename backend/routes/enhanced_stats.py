"""
Enhanced Stats Tracking Routes
Comprehensive statistics tracking with real-time updates, upgrades, and detailed counting
"""
from flask import Blueprint, request, jsonify
from datetime import datetime

enhanced_stats_bp = Blueprint('enhanced_stats', __name__)


@enhanced_stats_bp.route('/api/game/stats/comprehensive', methods=['GET'])
def get_comprehensive_stats():
    """Get comprehensive statistics with detailed counting"""
    try:
        from backend.services.enhanced_stats_tracking import enhanced_stats_tracker
        
        user_id = request.args.get('user_id', 'default_user')
        
        # Get comprehensive counts
        counts = enhanced_stats_tracker.get_comprehensive_counts(user_id)
        
        # Record the stat update
        enhanced_stats_tracker.record_stat_update(user_id, 'comprehensive_stats_request', counts)
        
        return jsonify({
            'success': True,
            'counts': counts,
            'timestamp': datetime.utcnow().isoformat(),
            'user_id': user_id
        }), 200
    except Exception as e:
        import traceback
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500


@enhanced_stats_bp.route('/api/game/stats/counts', methods=['GET'])
def get_stat_counts():
    """Get detailed counting statistics"""
    try:
        from backend.services.enhanced_stats_tracking import enhanced_stats_tracker
        
        user_id = request.args.get('user_id', 'default_user')
        category = request.args.get('category', None)  # Optional: videos, achievements, etc.
        
        counts = enhanced_stats_tracker.get_comprehensive_counts(user_id)
        
        # Filter by category if requested
        if category:
            counts = {category: counts.get(category, {})}
        
        return jsonify({
            'success': True,
            'counts': counts,
            'timestamp': datetime.utcnow().isoformat()
        }), 200
    except Exception as e:
        import traceback
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@enhanced_stats_bp.route('/api/game/stats/record-update', methods=['POST'])
def record_stat_update():
    """Record a stat update for tracking"""
    try:
        from backend.services.enhanced_stats_tracking import enhanced_stats_tracker
        
        data = request.get_json() or {}
        user_id = data.get('user_id', 'default_user')
        stat_type = data.get('stat_type', 'unknown')
        value = data.get('value', None)
        metadata = data.get('metadata', {})
        
        enhanced_stats_tracker.record_stat_update(user_id, stat_type, value, metadata)
        
        return jsonify({
            'success': True,
            'message': 'Stat update recorded',
            'timestamp': datetime.utcnow().isoformat()
        }), 200
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@enhanced_stats_bp.route('/api/game/stats/upgrades', methods=['GET'])
def get_stat_upgrades():
    """Get stat upgrade history"""
    try:
        from backend.services.enhanced_stats_tracking import enhanced_stats_tracker
        
        user_id = request.args.get('user_id', 'default_user')
        limit = int(request.args.get('limit', 50))
        
        upgrades = enhanced_stats_tracker.get_stat_upgrades(user_id)
        
        # Limit results
        if limit > 0:
            upgrades = upgrades[-limit:]
        
        return jsonify({
            'success': True,
            'upgrades': upgrades,
            'total': len(enhanced_stats_tracker.get_stat_upgrades(user_id))
        }), 200
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@enhanced_stats_bp.route('/api/game/stats/upgrade', methods=['POST'])
def upgrade_stat():
    """Upgrade a stat and record the upgrade"""
    try:
        from backend.services.enhanced_stats_tracking import enhanced_stats_tracker
        from backend.services.hunters_leveling_system import hunters_leveling_system
        
        data = request.get_json() or {}
        user_id = data.get('user_id', 'default_user')
        stat_name = data.get('stat_name', None)
        amount = data.get('amount', 1)
        
        if not stat_name:
            return jsonify({
                'success': False,
                'error': 'stat_name is required'
            }), 400
        
        if not hunters_leveling_system:
            return jsonify({
                'success': False,
                'error': 'Leveling system not available'
            }), 500
        
        # Get current stats
        current_stats = hunters_leveling_system.get_player_stats(user_id)
        old_value = current_stats.get(f'stat_{stat_name}', 0)
        
        # Allocate stat points (this will upgrade the stat)
        stat_allocations = {stat_name: amount}
        result = hunters_leveling_system.allocate_stat_points(user_id, stat_allocations)
        
        if result.get('success', False):
            # Get new stats
            new_stats = hunters_leveling_system.get_player_stats(user_id)
            new_value = new_stats.get(f'stat_{stat_name}', 0)
            
            # Record the upgrade
            cost = amount
            enhanced_stats_tracker.record_stat_upgrade(
                user_id, 
                stat_name, 
                old_value, 
                new_value, 
                cost
            )
            
            return jsonify({
                'success': True,
                'stat_name': stat_name,
                'old_value': old_value,
                'new_value': new_value,
                'improvement': new_value - old_value,
                'points_spent': cost,
                'remaining_points': new_stats.get('available_stat_points', 0)
            }), 200
        else:
            return jsonify({
                'success': False,
                'error': result.get('error', 'Failed to upgrade stat')
            }), 400
            
    except Exception as e:
        import traceback
        return jsonify({
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }), 500


@enhanced_stats_bp.route('/api/game/stats/refresh', methods=['POST'])
@enhanced_stats_bp.route('/vidgenerator/api/game/stats/refresh', methods=['POST'])
def refresh_stats():
    """Force refresh of all stats counts"""
    try:
        from backend.services.enhanced_stats_tracking import enhanced_stats_tracker
        
        data = request.get_json() or {}
        user_id = data.get('user_id') or request.args.get('user_id', 'default_user')
        
        # Clear cache and recalculate
        if hasattr(enhanced_stats_tracker, 'counting_cache') and user_id in enhanced_stats_tracker.counting_cache:
            del enhanced_stats_tracker.counting_cache[user_id]
        
        # Get fresh counts
        try:
            counts = enhanced_stats_tracker.get_comprehensive_counts(user_id)
        except Exception as count_err:
            print(f"[Stats Refresh] Error getting counts: {count_err}", flush=True)
            counts = {}
        
        return jsonify({
            'success': True,
            'message': 'Stats refreshed',
            'counts': counts,
            'timestamp': datetime.utcnow().isoformat()
        }), 200
    except Exception as e:
        import traceback
        print(f"[Stats Refresh] Error: {e}", flush=True)
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e),
            'counts': {},
            'message': 'Failed to refresh stats'
        }), 200  # Return 200 instead of 500 to prevent frontend breakage

