"""
Guild vs Clan BattleGrounds Routes - Live GPS, online counters, payment tickets
"""
from flask import Blueprint, request, jsonify
from backend.services.guild_vs_clan_battlegrounds import guild_vs_clan_battlegrounds
from src.utils.input_validator import InputValidator
from src.utils.error_handler import ErrorHandler
from src.utils.rate_limiter import rate_limit

battlegrounds_bp = Blueprint('battlegrounds', __name__)


@battlegrounds_bp.route('/api/battlegrounds/create', methods=['POST'])
@rate_limit
def create_battleground():
    """Create a Guild vs Clan battleground"""
    try:
        data = InputValidator.get_json_safe(request)
        battleground_id = InputValidator.sanitize_string(data.get('battleground_id', ''))
        name = InputValidator.sanitize_string(data.get('name', ''))
        guild_id = InputValidator.sanitize_string(data.get('guild_id', ''))
        clan_id = InputValidator.sanitize_string(data.get('clan_id', ''))
        scenario_type = InputValidator.sanitize_string(data.get('scenario_type', 'standard'))
        theme = InputValidator.sanitize_string(data.get('theme', ''))
        
        if not all([battleground_id, name, guild_id, clan_id]):
            return jsonify({'success': False, 'error': 'All fields required'}), 400
        
        result = guild_vs_clan_battlegrounds.create_battleground(
            battleground_id, name, guild_id, clan_id, scenario_type, theme
        )
        return jsonify(result), 200
        
    except Exception as e:
        return ErrorHandler.create_error_response(str(e), 500)


@battlegrounds_bp.route('/api/battlegrounds/<battleground_id>/points', methods=['POST'])
@rate_limit
def award_points(battleground_id: str):
    """Award points in battleground"""
    try:
        data = InputValidator.get_json_safe(request)
        team = InputValidator.sanitize_string(data.get('team', 'guild'))
        points = int(data.get('points', 0))
        point_type = InputValidator.sanitize_string(data.get('point_type', 'battle'))
        
        result = guild_vs_clan_battlegrounds.award_points(
            battleground_id, team, points, point_type
        )
        return jsonify(result), 200
        
    except Exception as e:
        return ErrorHandler.create_error_response(str(e), 500)


@battlegrounds_bp.route('/api/battlegrounds/<battleground_id>/item', methods=['POST'])
@rate_limit
def add_item(battleground_id: str):
    """Add item to team in battleground"""
    try:
        data = InputValidator.get_json_safe(request)
        team = InputValidator.sanitize_string(data.get('team', 'guild'))
        item_id = InputValidator.sanitize_string(data.get('item_id', ''))
        item_data = data.get('item_data', {})
        
        if not item_id:
            return jsonify({'success': False, 'error': 'item_id required'}), 400
        
        result = guild_vs_clan_battlegrounds.add_item(
            battleground_id, team, item_id, item_data
        )
        return jsonify(result), 200
        
    except Exception as e:
        return ErrorHandler.create_error_response(str(e), 500)


@battlegrounds_bp.route('/api/battlegrounds/<battleground_id>/stats', methods=['POST'])
@rate_limit
def update_stats(battleground_id: str):
    """Update team battle stats"""
    try:
        data = InputValidator.get_json_safe(request)
        team = InputValidator.sanitize_string(data.get('team', 'guild'))
        stats_update = data.get('stats_update', {})
        
        result = guild_vs_clan_battlegrounds.update_stats(
            battleground_id, team, stats_update
        )
        return jsonify(result), 200
        
    except Exception as e:
        return ErrorHandler.create_error_response(str(e), 500)


@battlegrounds_bp.route('/api/battlegrounds/<battleground_id>/location', methods=['POST'])
@rate_limit
def update_location(battleground_id: str):
    """Update player GPS location"""
    try:
        data = InputValidator.get_json_safe(request)
        user_id = InputValidator.sanitize_string(data.get('user_id', 'default_user'))
        lat = float(data.get('lat', 0))
        lng = float(data.get('lng', 0))
        team = InputValidator.sanitize_string(data.get('team', 'guild'))
        
        result = guild_vs_clan_battlegrounds.update_player_location(
            battleground_id, user_id, lat, lng, team
        )
        return jsonify(result), 200
        
    except Exception as e:
        return ErrorHandler.create_error_response(str(e), 500)


@battlegrounds_bp.route('/api/battlegrounds/<battleground_id>/online', methods=['POST'])
@rate_limit
def update_online(battleground_id: str):
    """Update online player counter"""
    try:
        data = InputValidator.get_json_safe(request)
        user_id = InputValidator.sanitize_string(data.get('user_id', 'default_user'))
        team = InputValidator.sanitize_string(data.get('team', 'guild'))
        is_online = bool(data.get('is_online', True))
        
        result = guild_vs_clan_battlegrounds.update_online_counter(
            battleground_id, user_id, team, is_online
        )
        return jsonify(result), 200
        
    except Exception as e:
        return ErrorHandler.create_error_response(str(e), 500)


@battlegrounds_bp.route('/api/battlegrounds/<battleground_id>/live', methods=['GET'])
def get_live_data(battleground_id: str):
    """Get live battleground data"""
    try:
        battleground_id = InputValidator.sanitize_string(battleground_id)
        result = guild_vs_clan_battlegrounds.get_live_data(battleground_id)
        return jsonify(result), 200
        
    except Exception as e:
        return ErrorHandler.create_error_response(str(e), 500)


@battlegrounds_bp.route('/api/payment/ticket/create', methods=['POST'])
@rate_limit
def create_payment_ticket():
    """Create a $1 payment ticket"""
    try:
        data = InputValidator.get_json_safe(request)
        ticket_id = InputValidator.sanitize_string(data.get('ticket_id', ''))
        user_id = InputValidator.sanitize_string(data.get('user_id', 'default_user'))
        amount = float(data.get('amount', 1.0))
        currency = InputValidator.sanitize_string(data.get('currency', 'USD'))
        ticket_type = InputValidator.sanitize_string(data.get('type', 'battleground_access'))
        
        if not ticket_id:
            return jsonify({'success': False, 'error': 'ticket_id required'}), 400
        
        result = guild_vs_clan_battlegrounds.create_payment_ticket(
            ticket_id, user_id, amount, currency, ticket_type
        )
        return jsonify(result), 200
        
    except Exception as e:
        return ErrorHandler.create_error_response(str(e), 500)


@battlegrounds_bp.route('/api/payment/process/<ticket_id>', methods=['POST'])
@rate_limit
def process_payment(ticket_id: str):
    """Process payment for ticket"""
    try:
        data = InputValidator.get_json_safe(request)
        payment_data = data.get('payment_data', {})
        
        result = guild_vs_clan_battlegrounds.process_payment(ticket_id, payment_data)
        return jsonify(result), 200
        
    except Exception as e:
        return ErrorHandler.create_error_response(str(e), 500)


@battlegrounds_bp.route('/api/champions-league/entry', methods=['POST'])
@rate_limit
def add_champions_entry():
    """Add entry to Champions League Top 10"""
    try:
        data = InputValidator.get_json_safe(request)
        season = InputValidator.sanitize_string(data.get('season', '2024'))
        user_id = InputValidator.sanitize_string(data.get('user_id', 'default_user'))
        guild_id = InputValidator.sanitize_string(data.get('guild_id', ''))
        clan_id = InputValidator.sanitize_string(data.get('clan_id', ''))
        points = int(data.get('points', 0))
        rank = int(data.get('rank', 0))
        
        result = guild_vs_clan_battlegrounds.add_champions_league_entry(
            season, user_id, guild_id, clan_id, points, rank
        )
        return jsonify(result), 200
        
    except Exception as e:
        return ErrorHandler.create_error_response(str(e), 500)


@battlegrounds_bp.route('/api/champions-league/top10', methods=['GET'])
def get_champions_top10():
    """Get Champions League Top 10"""
    try:
        season = request.args.get('season')
        result = guild_vs_clan_battlegrounds.get_champions_league_top10(season)
        return jsonify(result), 200
        
    except Exception as e:
        return ErrorHandler.create_error_response(str(e), 500)

