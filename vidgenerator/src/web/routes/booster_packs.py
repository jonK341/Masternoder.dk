"""
Booster Pack API Routes
"""

from flask import Blueprint, request, jsonify, session
from typing import Dict, Any

try:
    from src.services.monetization.booster_pack_system import BoosterPackSystem, InfiniteLevelingSystem, StatsCounter
    booster_system = BoosterPackSystem()
    leveling_system = InfiniteLevelingSystem()
    stats_counter = StatsCounter()
except ImportError as e:
    print(f"[BoosterPacks] Warning: Could not import booster_pack_system: {e}")
    # Create dummy classes for fallback
    class BoosterPackSystem:
        def __init__(self): pass
        def get_pack_price(self, pack_type): return {'coins': 500}
        def purchase_pack(self, pack_type, payment_method): return None
        pack_types = ['gametime', 'token', 'trophy', 'xp', 'celebration', 'premium']
    class InfiniteLevelingSystem:
        def __init__(self): pass
        def get_xp_progress(self, xp, level): return {'current_level': level, 'current_xp': xp}
        def get_level_rewards(self, level): return {'coins': level * 10}
    class StatsCounter:
        def __init__(self): pass
        def update_generation_stats(self, data): pass
        def update_monetization_stats(self, data): pass
        def get_all_stats(self): return {}
        def get_stat_summary(self): return {}
    booster_system = BoosterPackSystem()
    leveling_system = InfiniteLevelingSystem()
    stats_counter = StatsCounter()

booster_packs_bp = Blueprint('booster_packs', __name__)


@booster_packs_bp.route('/api/booster-packs/shop')
def get_booster_shop():
    """Get booster pack shop"""
    try:
        shop = {
            'packs': []
        }
        
        for pack_type in booster_system.pack_types:
            price = booster_system.get_pack_price(pack_type)
            shop['packs'].append({
                'id': pack_type,
                'name': pack_type.replace('_', ' ').title() + ' Pack',
                'description': f'{pack_type} booster pack with random contents',
                'price': price,
                'rarities': ['common', 'rare', 'epic', 'legendary']
            })
        
        return jsonify({
            'success': True,
            'shop': shop
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@booster_packs_bp.route('/api/booster-packs/purchase', methods=['POST'])
def purchase_booster_pack():
    """Purchase a booster pack"""
    try:
        data = request.get_json()
        pack_type = data.get('pack_type')
        payment_method = data.get('payment_method', 'coins')
        
        if not pack_type or pack_type not in booster_system.pack_types:
            return jsonify({'error': 'Invalid pack type'}), 400
        
        # Purchase pack
        pack = booster_system.purchase_pack(pack_type, payment_method)
        
        if not pack:
            return jsonify({'error': 'Purchase failed'}), 400
        
        # Update monetization stats
        price = booster_system.get_pack_price(pack_type)
        stats_counter.update_monetization_stats({
            'type': 'booster_pack',
            'amount': price.get(payment_method, 0),
            'coins_spent': price.get('coins', 0) if payment_method == 'coins' else 0,
            'premium_coins_spent': price.get('premium_coins', 0) if payment_method == 'premium_coins' else 0
        })
        
        return jsonify({
            'success': True,
            'pack': {
                'type': pack.pack_type,
                'rarity': pack.rarity,
                'contents': pack.contents
            }
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@booster_packs_bp.route('/api/booster-packs/open', methods=['POST'])
def open_booster_pack():
    """Open a booster pack"""
    try:
        data = request.get_json()
        pack_type = data.get('pack_type')
        rarity = data.get('rarity', 'common')
        
        pack = booster_system.create_pack(pack_type, rarity)
        opened = booster_system.open_pack(pack)
        
        # Award contents
        # In production, this would update user inventory
        
        return jsonify({
            'success': True,
            'opened_pack': opened
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@booster_packs_bp.route('/api/leveling/infinite')
def get_infinite_leveling():
    """Get infinite leveling information"""
    try:
        user_id = session.get('user_id', 'anonymous')
        
        # Get user's current level and XP (from database in production)
        current_level = 1
        current_xp = 0
        
        progress = leveling_system.get_xp_progress(current_xp, current_level)
        rewards = leveling_system.get_level_rewards(current_level)
        
        return jsonify({
            'success': True,
            'leveling': {
                'current_level': current_level,
                'current_xp': current_xp,
                'progress': progress,
                'next_level_rewards': leveling_system.get_level_rewards(current_level + 1),
                'is_infinite': True
            }
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@booster_packs_bp.route('/api/stats/all')
def get_all_stats():
    """Get all statistics and attributes"""
    try:
        user_id = session.get('user_id', 'anonymous')
        
        all_stats = stats_counter.get_all_stats()
        summary = stats_counter.get_stat_summary()
        
        return jsonify({
            'success': True,
            'stats': all_stats,
            'summary': summary
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@booster_packs_bp.route('/api/stats/update', methods=['POST'])
def update_stats():
    """Update statistics"""
    try:
        data = request.get_json()
        stat_type = data.get('type')
        stat_data = data.get('data', {})
        
        if stat_type == 'generation':
            stats_counter.update_generation_stats(stat_data)
        elif stat_type == 'leveling':
            stats_counter.update_leveling_stats(stat_data.get('xp', 0), stat_data.get('source', 'unknown'))
        elif stat_type == 'monetization':
            stats_counter.update_monetization_stats(stat_data)
        elif stat_type == 'engagement':
            stats_counter.update_engagement_stats(stat_data)
        elif stat_type == 'game':
            stats_counter.update_game_stats(stat_data)
        elif stat_type == 'attributes':
            stats_counter.update_attributes(stat_data)
        
        # Recalculate attributes after any update
        stats_counter.calculate_attributes_from_stats()
        
        return jsonify({
            'success': True,
            'message': 'Stats updated',
            'stats': stats_counter.get_all_stats()
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@booster_packs_bp.route('/api/stats/add-points', methods=['POST'])
def add_stat_points():
    """Add points to a specific stat and update all related stats"""
    try:
        data = request.get_json()
        category = data.get('category')
        stat_name = data.get('stat_name')
        points = data.get('points', 1)
        update_related = data.get('update_related', True)
        
        if not category or not stat_name:
            return jsonify({'error': 'category and stat_name are required'}), 400
        
        success = stats_counter.add_points(category, stat_name, points, update_related)
        
        if success:
            # Recalculate attributes after adding points
            stats_counter.calculate_attributes_from_stats()
            
            return jsonify({
                'success': True,
                'message': f'Added {points} points to {category}.{stat_name}',
                'stats': stats_counter.get_all_stats(),
                'updated_stat': {
                    'category': category,
                    'stat_name': stat_name,
                    'value': stats_counter.get_stat(category, stat_name)
                }
            })
        else:
            return jsonify({'error': 'Failed to add points'}), 400
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@booster_packs_bp.route('/api/stats/increment', methods=['POST'])
def increment_stat():
    """Increment a stat by a specific amount"""
    try:
        data = request.get_json()
        category = data.get('category')
        stat_name = data.get('stat_name')
        amount = data.get('amount', 1)
        
        if not category or not stat_name:
            return jsonify({'error': 'category and stat_name are required'}), 400
        
        success = stats_counter.increment_stat(category, stat_name, amount)
        
        if success:
            stats_counter.calculate_attributes_from_stats()
            
            return jsonify({
                'success': True,
                'message': f'Incremented {category}.{stat_name} by {amount}',
                'stats': stats_counter.get_all_stats()
            })
        else:
            return jsonify({'error': 'Failed to increment stat'}), 400
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@booster_packs_bp.route('/stats/department')
@booster_packs_bp.route('/api/stats/department')
def stats_department():
    """Stats Department page"""
    from flask import render_template
    try:
        return render_template('stats/stats_department.html')
    except Exception as e:
        print(f"[BoosterPacks] Error rendering stats_department template: {e}")
        import traceback
        traceback.print_exc()
        return f"Error loading stats department: {str(e)}", 500


def register_booster_pack_routes(app):
    """Register booster pack routes"""
    try:
        # Register BOTH with and without prefix to handle all scenarios
        app.register_blueprint(booster_packs_bp, url_prefix='')
        app.register_blueprint(booster_packs_bp, url_prefix='/vidgenerator', name='booster_packs_with_prefix')
        print("[Routes] Booster pack routes registered successfully (with AND without prefix)")
        booster_routes = [rule.rule for rule in app.url_map.iter_rules() if 'booster' in rule.rule or 'stats' in rule.rule]
        print(f"[Routes] Booster pack routes: {booster_routes[:10]}...")  # Show first 10
    except Exception as e:
        print(f"[Routes] Error registering booster pack routes: {e}")
        import traceback
        traceback.print_exc()

