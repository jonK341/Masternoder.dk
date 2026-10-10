"""
Competitive Battle System API Routes
Tournaments, Seasons, Challenges, Leaderboards
"""
from flask import Blueprint, request, jsonify
from backend.services.competitive_battle_system import competitive_battle_system
from src.utils.rate_limiter import rate_limit
import sys

competitive_battle_bp = Blueprint('competitive_battle', __name__)


@competitive_battle_bp.route('/api/battle/tournament/create', methods=['POST'])
@competitive_battle_bp.route('/vidgenerator/api/battle/tournament/create', methods=['POST'])
@rate_limit()
def create_tournament():
    """Create a new tournament"""
    try:
        data = request.get_json() or {}
        name = data.get('name', 'New Tournament')
        tournament_type = data.get('type', 'single_elimination')
        max_participants = int(data.get('max_participants', 16))
        entry_fee = int(data.get('entry_fee', 0))
        prize_pool = data.get('prize_pool')
        
        result = competitive_battle_system.create_tournament(
            name, tournament_type, max_participants, entry_fee, prize_pool
        )
        return jsonify(result), 200
    except Exception as e:
        print(f"[Competitive Battle Create Tournament] Error: {e}", file=sys.stderr, flush=True)
        return jsonify({'success': False, 'error': str(e)}), 200


@competitive_battle_bp.route('/api/battle/tournament/join', methods=['POST'])
@competitive_battle_bp.route('/vidgenerator/api/battle/tournament/join', methods=['POST'])
@rate_limit()
def join_tournament():
    """Join a tournament"""
    try:
        data = request.get_json() or {}
        tournament_id = data.get('tournament_id')
        user_id = data.get('user_id', 'default_user')
        
        if not tournament_id:
            return jsonify({'success': False, 'error': 'tournament_id required'}), 200
        
        result = competitive_battle_system.join_tournament(tournament_id, user_id)
        return jsonify(result), 200
    except Exception as e:
        print(f"[Competitive Battle Join Tournament] Error: {e}", file=sys.stderr, flush=True)
        return jsonify({'success': False, 'error': str(e)}), 200


@competitive_battle_bp.route('/api/battle/tournament/<tournament_id>', methods=['GET'])
@competitive_battle_bp.route('/vidgenerator/api/battle/tournament/<tournament_id>', methods=['GET'])
@rate_limit()
def get_tournament(tournament_id: str):
    """Get tournament details"""
    try:
        result = competitive_battle_system.get_tournament(tournament_id)
        return jsonify(result), 200
    except Exception as e:
        print(f"[Competitive Battle Get Tournament] Error: {e}", file=sys.stderr, flush=True)
        return jsonify({'success': False, 'error': str(e)}), 200


@competitive_battle_bp.route('/api/battle/tournaments', methods=['GET'])
@competitive_battle_bp.route('/vidgenerator/api/battle/tournaments', methods=['GET'])
@rate_limit()
def list_tournaments():
    """List tournaments"""
    try:
        status = request.args.get('status')
        tournaments = competitive_battle_system.list_tournaments(status)
        return jsonify({'success': True, 'tournaments': tournaments}), 200
    except Exception as e:
        print(f"[Competitive Battle List Tournaments] Error: {e}", file=sys.stderr, flush=True)
        return jsonify({'success': True, 'tournaments': [], 'error': str(e)}), 200


@competitive_battle_bp.route('/api/battle/season/create', methods=['POST'])
@competitive_battle_bp.route('/vidgenerator/api/battle/season/create', methods=['POST'])
@rate_limit()
def create_season():
    """Create a new season"""
    try:
        data = request.get_json() or {}
        name = data.get('name', 'New Season')
        duration_days = int(data.get('duration_days', 30))
        
        result = competitive_battle_system.create_season(name, duration_days)
        return jsonify(result), 200
    except Exception as e:
        print(f"[Competitive Battle Create Season] Error: {e}", file=sys.stderr, flush=True)
        return jsonify({'success': False, 'error': str(e)}), 200


@competitive_battle_bp.route('/api/battle/season/<season_id>/leaderboard', methods=['GET'])
@competitive_battle_bp.route('/vidgenerator/api/battle/season/<season_id>/leaderboard', methods=['GET'])
@rate_limit()
def get_season_leaderboard(season_id: str):
    """Get season leaderboard"""
    try:
        limit = int(request.args.get('limit', 100))
        result = competitive_battle_system.get_season_leaderboard(season_id, limit)
        return jsonify(result), 200
    except Exception as e:
        print(f"[Competitive Battle Season Leaderboard] Error: {e}", file=sys.stderr, flush=True)
        return jsonify({'success': True, 'leaderboard': [], 'error': str(e)}), 200


@competitive_battle_bp.route('/api/battle/challenges', methods=['GET'])
@competitive_battle_bp.route('/vidgenerator/api/battle/challenges', methods=['GET'])
@rate_limit()
def list_challenges():
    """List active challenges"""
    try:
        challenges = competitive_battle_system.list_challenges()
        return jsonify({'success': True, 'challenges': challenges}), 200
    except Exception as e:
        print(f"[Competitive Battle List Challenges] Error: {e}", file=sys.stderr, flush=True)
        return jsonify({'success': True, 'challenges': [], 'error': str(e)}), 200


@competitive_battle_bp.route('/api/battle/leaderboard/<leaderboard_type>', methods=['GET'])
@competitive_battle_bp.route('/vidgenerator/api/battle/leaderboard/<leaderboard_type>', methods=['GET'])
@rate_limit()
def get_leaderboard(leaderboard_type: str):
    """Get leaderboard"""
    try:
        limit = int(request.args.get('limit', 100))
        result = competitive_battle_system.get_leaderboard(leaderboard_type, limit)
        return jsonify(result), 200
    except Exception as e:
        print(f"[Competitive Battle Leaderboard] Error: {e}", file=sys.stderr, flush=True)
        return jsonify({'success': True, 'leaderboard': [], 'error': str(e)}), 200
