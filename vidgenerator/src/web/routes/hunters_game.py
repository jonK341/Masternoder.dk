"""
Hunters Game with Theme Logic and XP System
Similar to old themes but as a game
"""
from flask import Blueprint, jsonify, request
from datetime import datetime
import json
import random

hunters_game_bp = Blueprint('hunters_game', __name__)

# Game state storage (in production, use database)
game_states = {}

class HuntersGame:
    """Hunters Game with theme-based logic"""
    
    def __init__(self):
        self.themes = {
            'matrix': {'xp_multiplier': 1.5, 'difficulty': 'medium', 'color': '#00ff00'},
            'cyberpunk': {'xp_multiplier': 1.3, 'difficulty': 'medium', 'color': '#ff00ff'},
            'sci-fi': {'xp_multiplier': 1.2, 'difficulty': 'easy', 'color': '#00ccff'},
            'nature': {'xp_multiplier': 1.0, 'difficulty': 'easy', 'color': '#00ff88'},
            'mtg': {'xp_multiplier': 1.4, 'difficulty': 'hard', 'color': '#ffaa00'},
            'halo4': {'xp_multiplier': 1.6, 'difficulty': 'hard', 'color': '#00aaff'},
            'wwii': {'xp_multiplier': 1.1, 'difficulty': 'medium', 'color': '#ccaa00'},
            'fantasy': {'xp_multiplier': 1.3, 'difficulty': 'medium', 'color': '#aa00ff'},
            'horror': {'xp_multiplier': 1.7, 'difficulty': 'hard', 'color': '#ff0000'},
            'comedy': {'xp_multiplier': 0.9, 'difficulty': 'easy', 'color': '#ffff00'},
            'romance': {'xp_multiplier': 1.0, 'difficulty': 'easy', 'color': '#ff88cc'},
            'action': {'xp_multiplier': 1.5, 'difficulty': 'hard', 'color': '#ff3300'}
        }
    
    def calculate_xp(self, theme: str, base_xp: int, success: bool = True) -> int:
        """Calculate XP based on theme"""
        theme_data = self.themes.get(theme, {'xp_multiplier': 1.0})
        multiplier = theme_data['xp_multiplier']
        
        if success:
            return int(base_xp * multiplier)
        else:
            return int(base_xp * multiplier * 0.5)
    
    def get_theme_bonus(self, theme: str) -> dict:
        """Get theme-specific bonuses"""
        return self.themes.get(theme, {})

# Initialize game
hunters_game = HuntersGame()

@hunters_game_bp.route('/api/game/hunters/start', methods=['POST'])
def start_hunters_game():
    """Start a new hunters game"""
    try:
        data = request.get_json() or {}
        user_id = data.get('user_id', 'anonymous')
        theme = data.get('theme', 'matrix')
        
        game_state = {
            'user_id': user_id,
            'theme': theme,
            'level': 1,
            'xp': 0,
            'total_xp': 0,
            'hunts_completed': 0,
            'started_at': datetime.now().isoformat(),
            'theme_bonus': hunters_game.get_theme_bonus(theme)
        }
        
        game_states[user_id] = game_state
        
        return jsonify({
            'success': True,
            'game_state': game_state
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@hunters_game_bp.route('/api/game/hunters/complete-hunt', methods=['POST'])
def complete_hunt():
    """Complete a hunt and earn XP"""
    try:
        data = request.get_json() or {}
        user_id = data.get('user_id', 'anonymous')
        base_xp = data.get('base_xp', 100)
        success = data.get('success', True)
        
        if user_id not in game_states:
            return jsonify({
                'success': False,
                'error': 'Game not started'
            }), 400
        
        game_state = game_states[user_id]
        theme = game_state.get('theme', 'matrix')
        
        # Calculate XP with theme multiplier
        xp_earned = hunters_game.calculate_xp(theme, base_xp, success)
        
        # Update game state
        game_state['xp'] += xp_earned
        game_state['total_xp'] += xp_earned
        game_state['hunts_completed'] += 1
        
        # Level up check (every 1000 XP)
        new_level = (game_state['total_xp'] // 1000) + 1
        leveled_up = new_level > game_state['level']
        if leveled_up:
            game_state['level'] = new_level
        
        return jsonify({
            'success': True,
            'xp_earned': xp_earned,
            'total_xp': game_state['total_xp'],
            'level': game_state['level'],
            'leveled_up': leveled_up,
            'game_state': game_state
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@hunters_game_bp.route('/api/game/hunters/state/<user_id>', methods=['GET'])
def get_game_state(user_id):
    """Get current game state"""
    try:
        if user_id not in game_states:
            return jsonify({
                'success': False,
                'error': 'Game not started'
            }), 404
        
        return jsonify({
            'success': True,
            'game_state': game_states[user_id]
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@hunters_game_bp.route('/api/game/hunters/themes', methods=['GET'])
def get_themes():
    """Get available themes for game"""
    try:
        return jsonify({
            'success': True,
            'themes': hunters_game.themes
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@hunters_game_bp.route('/api/game/hunters/leaderboard', methods=['GET'])
def get_leaderboard():
    """Get game leaderboard"""
    try:
        leaderboard = sorted(
            game_states.values(),
            key=lambda x: x.get('total_xp', 0),
            reverse=True
        )[:10]
        
        return jsonify({
            'success': True,
            'leaderboard': leaderboard
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

