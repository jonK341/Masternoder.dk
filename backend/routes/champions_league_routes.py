"""
Champions League Routes
API endpoints for champions league with point data and user rankings
"""
from flask import Blueprint, request, jsonify
from backend.services.champions_league_system import champions_league

champions_league_bp = Blueprint('champions_league', __name__, url_prefix='/api/champions-league')

@champions_league_bp.route('/test', methods=['GET'])
def test_champions_league():
    """Test endpoint for champions league"""
    return jsonify({'message': 'Champions League API is working!'}), 200

@champions_league_bp.route('/user-league/<string:user_id>', methods=['GET'])
def get_user_league(user_id):
    """Get user's current league"""
    league_data = champions_league.get_user_league(user_id)
    return jsonify({'success': True, 'league_data': league_data}), 200

@champions_league_bp.route('/user-points/<string:user_id>', methods=['GET'])
def get_user_points(user_id):
    """Get user's total points from all systems"""
    points_data = champions_league.calculate_user_total_points(user_id)
    return jsonify({'success': True, 'points_data': points_data}), 200

@champions_league_bp.route('/update-ranking/<string:user_id>', methods=['POST'])
def update_user_ranking(user_id):
    """Update user ranking"""
    ranking = champions_league.update_user_ranking(user_id)
    return jsonify({'success': True, 'ranking': ranking}), 200

@champions_league_bp.route('/global-rankings', methods=['GET'])
def get_global_rankings():
    """Get global user rankings"""
    limit = request.args.get('limit', type=int, default=100)
    rankings = champions_league.get_global_rankings(limit)
    return jsonify({'success': True, 'rankings': rankings}), 200

@champions_league_bp.route('/league-rankings/<string:league>', methods=['GET'])
def get_league_rankings(league):
    """Get rankings for specific league"""
    limit = request.args.get('limit', type=int, default=50)
    rankings = champions_league.get_league_rankings(league, limit)
    return jsonify({'success': True, 'league': league, 'rankings': rankings}), 200

@champions_league_bp.route('/user-ranking/<string:user_id>', methods=['GET'])
def get_user_ranking(user_id):
    """Get user's ranking data"""
    ranking = champions_league.get_user_ranking(user_id)
    return jsonify({'success': True, 'ranking': ranking}), 200

@champions_league_bp.route('/top-players', methods=['GET'])
def get_top_players():
    """Get top players by category"""
    category = request.args.get('category', 'total')
    limit = request.args.get('limit', type=int, default=10)
    top_players = champions_league.get_top_players(category, limit)
    return jsonify({'success': True, 'category': category, 'top_players': top_players}), 200

@champions_league_bp.route('/league-statistics', methods=['GET'])
def get_league_statistics():
    """Get statistics for all leagues"""
    stats = champions_league.get_league_statistics()
    return jsonify({'success': True, 'statistics': stats}), 200

