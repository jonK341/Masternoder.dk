"""
Leveling API Routes
Infinite leveling system
"""

from flask import Blueprint, request, jsonify, session
from typing import Dict, Any

try:
    from src.services.monetization.booster_pack_system import InfiniteLevelingSystem
    leveling_system = InfiniteLevelingSystem()
except ImportError as e:
    print(f"[LevelingAPI] Warning: Could not import InfiniteLevelingSystem: {e}")
    class InfiniteLevelingSystem:
        def __init__(self): pass
        def get_xp_progress(self, xp, level): return {'current_level': level, 'current_xp': xp}
        def get_level_rewards(self, level): return {'coins': level * 10}
    leveling_system = InfiniteLevelingSystem()

leveling_api_bp = Blueprint('leveling_api', __name__)


@leveling_api_bp.route('/api/leveling/rewards')
def get_level_rewards():
    """Get rewards for a specific level"""
    try:
        level = request.args.get('level', type=int, default=1)
        rewards = leveling_system.get_level_rewards(level)
        
        return jsonify({
            'success': True,
            'level': level,
            'rewards': rewards
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@leveling_api_bp.route('/api/leveling/add-xp', methods=['POST'])
def add_xp():
    """Add XP to user"""
    try:
        data = request.get_json()
        xp_amount = data.get('xp', 0)
        source = data.get('source', 'generation')
        
        user_id = session.get('user_id', 'anonymous')
        
        # In production, update user's XP in database
        # For now, just return success
        
        return jsonify({
            'success': True,
            'xp_added': xp_amount,
            'source': source
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


def register_leveling_api_routes(app):
    """Register leveling API routes"""
    app.register_blueprint(leveling_api_bp, url_prefix='/vidgenerator')
    print("[Routes] Leveling API routes registered")

