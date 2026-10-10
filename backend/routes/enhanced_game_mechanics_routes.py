"""
Enhanced Game Mechanics API Routes
Comprehensive point earning and competitive features
"""
from flask import Blueprint, request, jsonify
from backend.services.enhanced_game_mechanics import enhanced_game_mechanics
from backend.services.unified_point_system_reconstructed import unified_point_system
from src.utils.rate_limiter import rate_limit
import sys

enhanced_mechanics_bp = Blueprint('enhanced_mechanics', __name__)

# Inject unified points system
enhanced_game_mechanics.set_unified_points(unified_point_system)


@enhanced_mechanics_bp.route('/api/game-mechanics/award-points', methods=['POST'])
@enhanced_mechanics_bp.route('/vidgenerator/api/game-mechanics/award-points', methods=['POST'])
@rate_limit()
def award_comprehensive_points():
    """Award comprehensive points from all categories"""
    try:
        data = request.get_json() or {}
        user_id = data.get('user_id', 'default_user')
        action = data.get('action', 'battle_win')
        difficulty = data.get('difficulty', 'normal')
        multiplier = float(data.get('multiplier', 1.0))
        
        result = enhanced_game_mechanics.award_comprehensive_points(
            user_id, action, difficulty, multiplier
        )
        
        return jsonify(result), 200
    except Exception as e:
        print(f"[Enhanced Mechanics Award Points] Error: {e}", file=sys.stderr, flush=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 200


@enhanced_mechanics_bp.route('/api/game-mechanics/quest/create', methods=['POST'])
@enhanced_mechanics_bp.route('/vidgenerator/api/game-mechanics/quest/create', methods=['POST'])
@rate_limit()
def create_quest():
    """Create a new quest for user"""
    try:
        data = request.get_json() or {}
        user_id = data.get('user_id', 'default_user')
        quest_type = data.get('quest_type', 'daily_battle')
        difficulty = data.get('difficulty', 'normal')
        
        result = enhanced_game_mechanics.create_quest(user_id, quest_type, difficulty)
        return jsonify(result), 200
    except Exception as e:
        print(f"[Enhanced Mechanics Create Quest] Error: {e}", file=sys.stderr, flush=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 200


@enhanced_mechanics_bp.route('/api/game-mechanics/quest/complete', methods=['POST'])
@enhanced_mechanics_bp.route('/vidgenerator/api/game-mechanics/quest/complete', methods=['POST'])
@rate_limit()
def complete_quest():
    """Complete a quest and award rewards"""
    try:
        data = request.get_json() or {}
        user_id = data.get('user_id', 'default_user')
        quest_id = data.get('quest_id')
        
        if not quest_id:
            return jsonify({'success': False, 'error': 'quest_id required'}), 200
        
        result = enhanced_game_mechanics.complete_quest(user_id, quest_id)
        return jsonify(result), 200
    except Exception as e:
        print(f"[Enhanced Mechanics Complete Quest] Error: {e}", file=sys.stderr, flush=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 200


@enhanced_mechanics_bp.route('/api/game-mechanics/quests', methods=['GET'])
@enhanced_mechanics_bp.route('/vidgenerator/api/game-mechanics/quests', methods=['GET'])
@rate_limit()
def get_active_quests():
    """Get active quests for user"""
    try:
        user_id = request.args.get('user_id', 'default_user')
        quests = enhanced_game_mechanics.get_active_quests(user_id)
        return jsonify({
            'success': True,
            'quests': quests
        }), 200
    except Exception as e:
        print(f"[Enhanced Mechanics Get Quests] Error: {e}", file=sys.stderr, flush=True)
        return jsonify({
            'success': True,
            'quests': [],
            'error': str(e)
        }), 200


@enhanced_mechanics_bp.route('/api/game-mechanics/daily-challenges', methods=['GET', 'POST'])
@enhanced_mechanics_bp.route('/vidgenerator/api/game-mechanics/daily-challenges', methods=['GET', 'POST'])
@rate_limit()
def daily_challenges():
    """Get or generate daily challenges"""
    try:
        user_id = request.args.get('user_id') or (request.get_json() or {}).get('user_id', 'default_user')
        
        if request.method == 'POST':
            challenges = enhanced_game_mechanics.generate_daily_challenges(user_id)
        else:
            challenges = enhanced_game_mechanics.generate_daily_challenges(user_id)
        
        return jsonify({
            'success': True,
            'challenges': challenges
        }), 200
    except Exception as e:
        print(f"[Enhanced Mechanics Daily Challenges] Error: {e}", file=sys.stderr, flush=True)
        return jsonify({
            'success': True,
            'challenges': [],
            'error': str(e)
        }), 200


@enhanced_mechanics_bp.route('/api/game-mechanics/daily-challenge/complete', methods=['POST'])
@enhanced_mechanics_bp.route('/vidgenerator/api/game-mechanics/daily-challenge/complete', methods=['POST'])
@rate_limit()
def complete_daily_challenge():
    """Complete a daily challenge"""
    try:
        data = request.get_json() or {}
        user_id = data.get('user_id', 'default_user')
        challenge_id = data.get('challenge_id')
        
        if not challenge_id:
            return jsonify({'success': False, 'error': 'challenge_id required'}), 200
        
        result = enhanced_game_mechanics.complete_daily_challenge(user_id, challenge_id)
        return jsonify(result), 200
    except Exception as e:
        print(f"[Enhanced Mechanics Complete Challenge] Error: {e}", file=sys.stderr, flush=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 200


@enhanced_mechanics_bp.route('/api/game-mechanics/streak', methods=['GET'])
@enhanced_mechanics_bp.route('/vidgenerator/api/game-mechanics/streak', methods=['GET'])
@rate_limit()
def get_streak():
    """Get streak for user"""
    try:
        user_id = request.args.get('user_id', 'default_user')
        streak_type = request.args.get('streak_type', 'battle')
        
        streak = enhanced_game_mechanics.get_streak(user_id, streak_type)
        return jsonify({
            'success': True,
            'user_id': user_id,
            'streak_type': streak_type,
            'streak': streak
        }), 200
    except Exception as e:
        print(f"[Enhanced Mechanics Get Streak] Error: {e}", file=sys.stderr, flush=True)
        return jsonify({
            'success': True,
            'streak': 0,
            'error': str(e)
        }), 200
