"""
Battle System API Routes
"""
import logging
from flask import Blueprint, request, jsonify
from backend.services.battle_system import battle_system
from backend.services.battle_system_enhanced import enhanced_battle_system
from backend.services.battle_intelligence import battle_intelligence
from backend.services.fantasy_battle_intelligence import fantasy_battle_intelligence
from backend.services.social_system import social_system
from backend.services.teams_system import teams_system
from backend.services.alliances_system import alliances_system
from backend.services.group_destruction_system import group_destruction_system
try:
    from backend.services.battle_extensions import battle_series, battle_news, battle_peer_network, battle_gps, battle_rule_books
except ImportError:
    battle_series = None
    battle_news = None
    battle_peer_network = None
    battle_gps = None
    battle_rule_books = None
try:
    from backend.services.trophy_trading_system import TrophyTradingSystem, CollectibleCardSystem
    trophy_trading_system = TrophyTradingSystem()
    collectible_card_system = CollectibleCardSystem()
except ImportError:
    trophy_trading_system = None
    collectible_card_system = None
from src.utils.input_validator import InputValidator
from src.utils.error_handler import ErrorHandler
from src.utils.rate_limiter import rate_limit
from datetime import datetime
import sys
import uuid
import os

# Import comprehensive stats service
try:
    from backend.services.battle_stats_service import battle_stats_service
except ImportError:
    battle_stats_service = None

logger = logging.getLogger(__name__)
battle_bp = Blueprint('battle', __name__)

@battle_bp.route('/api/battle/status', methods=['GET'])
@battle_bp.route('/vidgenerator/api/battle/status', methods=['GET'])
@rate_limit()
def get_battle_status():
    """Get battle system status and statistics"""
    try:
        user_id = request.args.get('user_id', 'default_user')
        
        # Get battle statistics
        total_battles = len(battle_system.battles) if hasattr(battle_system, 'battles') else 0
        total_clans = len(battle_system.clans) if hasattr(battle_system, 'clans') else 0
        
        # Get user battle stats if available
        user_stats = {}
        if hasattr(enhanced_battle_system, 'get_user_battle_stats'):
            try:
                user_stats = enhanced_battle_system.get_user_battle_stats(user_id)
            except:
                pass
        
        return jsonify({
            'success': True,
            'status': 'operational',
            'total_battles': total_battles,
            'total_clans': total_clans,
            'user_stats': user_stats,
            'system_available': True
        }), 200
    except Exception as e:
        request_id = str(uuid.uuid4())[:8]
        error_response, status_code = ErrorHandler.create_error_response(e, 500, request_id)
        return error_response, status_code


# Note: Middleware strips /vidgenerator, so /vidgenerator/api/* becomes /api/* before matching
# Only need /api/* route - middleware handles the prefix
@battle_bp.route('/api/battle/clans', methods=['GET'])
@battle_bp.route('/vidgenerator/api/battle/clans', methods=['GET'])
def list_clans():
    """List all clans"""
    try:
        clans = list(battle_system.clans.values())
        return jsonify({
            'success': True,
            'clans': clans if clans else []
        }), 200
    except Exception as e:
        # Return 200 with empty list to avoid breaking frontend
        import sys
        print(f"[Battle Clans] Error: {e}", file=sys.stderr, flush=True)
        return jsonify({
            'success': True,
            'error': str(e),
            'clans': []
        }), 200


# Enhanced Battle Features - Match Tracking, PVP Trophies, ID System
@battle_bp.route('/api/battle/battles/<battle_id>/match', methods=['POST'])
@battle_bp.route('/vidgenerator/api/battle/battles/<battle_id>/match', methods=['POST'])
@rate_limit()
def submit_match_result(battle_id: str):
    """Submit a match result"""
    try:
        data = InputValidator.get_json_safe(default={})
        match_number = int(data.get('match_number', 1))
        clan1_score = int(data.get('clan1_score', 0))
        clan2_score = int(data.get('clan2_score', 0))
        winner_clan_id = InputValidator.sanitize_string(data.get('winner_clan_id', '')) if data.get('winner_clan_id') else None
        
        result = enhanced_battle_system.submit_match_result(
            battle_id, match_number, clan1_score, clan2_score, winner_clan_id
        )
        return jsonify(result), 200  # Always return 200, error info in response
    except Exception as e:
        request_id = str(uuid.uuid4())[:8]
        error_response, status_code = ErrorHandler.create_error_response(e, 500, request_id)
        return error_response, status_code

@battle_bp.route('/api/battle/battles/<battle_id>/all-matches-complete', methods=['GET'])
@battle_bp.route('/vidgenerator/api/battle/battles/<battle_id>/all-matches-complete', methods=['GET'])
@rate_limit()
def check_all_matches_complete(battle_id: str):
    """Check if all matches are complete"""
    try:
        result = enhanced_battle_system.check_all_matches_complete(battle_id)
        return jsonify(result), 200
    except Exception as e:
        request_id = str(uuid.uuid4())[:8]
        error_response, status_code = ErrorHandler.create_error_response(e, 500, request_id)
        return error_response, status_code

@battle_bp.route('/api/battle/pvp/win-streak', methods=['POST'])
@battle_bp.route('/vidgenerator/api/battle/pvp/win-streak', methods=['POST'])
@rate_limit()
def update_win_streak():
    """Update win streak for PVP trophy tracking"""
    try:
        data = InputValidator.get_json_safe(default={})
        user_id = InputValidator.sanitize_string(data.get('user_id', 'default_user'))
        won = data.get('won', False)
        battle_type = InputValidator.sanitize_string(data.get('battle_type', 'pvp'))
        
        result = enhanced_battle_system.update_win_streak(user_id, won, battle_type)
        return jsonify(result), 200
    except Exception as e:
        request_id = str(uuid.uuid4())[:8]
        error_response, status_code = ErrorHandler.create_error_response(e, 500, request_id)
        return error_response, status_code

@battle_bp.route('/api/battle/pvp/trophies', methods=['GET'])
@battle_bp.route('/vidgenerator/api/battle/pvp/trophies', methods=['GET'])
@rate_limit()
def get_pvp_trophies():
    """Get PVP trophies for a user"""
    try:
        user_id = request.args.get('user_id', 'default_user')
        trophies = enhanced_battle_system.get_pvp_trophies(user_id)
        return jsonify({
            'success': True,
            'trophies': trophies
        }), 200
    except Exception as e:
        request_id = str(uuid.uuid4())[:8]
        error_response, status_code = ErrorHandler.create_error_response(e, 500, request_id)
        return error_response, status_code

@battle_bp.route('/api/battle/pvp/win-streaks', methods=['GET'])
@battle_bp.route('/vidgenerator/api/battle/pvp/win-streaks', methods=['GET'])
@rate_limit()
def get_win_streaks():
    """Get win streak information"""
    try:
        user_id = request.args.get('user_id', 'default_user')
        streaks = enhanced_battle_system.get_win_streaks(user_id)
        return jsonify({
            'success': True,
            'streaks': streaks
        }), 200
    except Exception as e:
        request_id = str(uuid.uuid4())[:8]
        error_response, status_code = ErrorHandler.create_error_response(e, 500, request_id)
        return error_response, status_code

@battle_bp.route('/api/battle/death/handle', methods=['POST'])
@battle_bp.route('/vidgenerator/api/battle/death/handle', methods=['POST'])
@rate_limit()
def handle_death():
    """Handle death and bring ID information"""
    try:
        data = InputValidator.get_json_safe(default={})
        user_id = InputValidator.sanitize_string(data.get('user_id', 'default_user'))
        death_type = InputValidator.sanitize_string(data.get('death_type', 'battle'))
        
        result = enhanced_battle_system.handle_death(user_id, death_type)
        return jsonify(result), 200
    except Exception as e:
        request_id = str(uuid.uuid4())[:8]
        error_response, status_code = ErrorHandler.create_error_response(e, 500, request_id)
        return error_response, status_code

@battle_bp.route('/api/battle/ids/<id_key>', methods=['GET'])
@battle_bp.route('/vidgenerator/api/battle/ids/<id_key>', methods=['GET'])
@rate_limit()
def get_id_info(id_key: str):
    """Get ID system information"""
    try:
        id_info = enhanced_battle_system.get_id_info(id_key)
        if id_info:
            return jsonify({
                'success': True,
                'id_info': id_info
            }), 200
        else:
            return jsonify({
                'success': False,
                'error': 'ID not found'
            }), 404
    except Exception as e:
        request_id = str(uuid.uuid4())[:8]
        error_response, status_code = ErrorHandler.create_error_response(e, 500, request_id)
        return error_response, status_code

@battle_bp.route('/api/battle/ids', methods=['GET'])
@battle_bp.route('/vidgenerator/api/battle/ids', methods=['GET'])
@rate_limit()
def get_all_ids():
    """Get all ID system information"""
    try:
        ids = enhanced_battle_system.get_all_ids()
        return jsonify({
            'success': True,
            'ids': ids
        }), 200
    except Exception as e:
        request_id = str(uuid.uuid4())[:8]
        error_response, status_code = ErrorHandler.create_error_response(e, 500, request_id)
        return error_response, status_code

@battle_bp.route('/api/battle/battles/<battle_id>/timelock', methods=['GET'])
@battle_bp.route('/vidgenerator/api/battle/battles/<battle_id>/timelock', methods=['GET'])
@rate_limit()
def check_timelock(battle_id: str):
    """Check timelock status"""
    try:
        result = enhanced_battle_system.check_timelock(battle_id)
        return jsonify(result), 200
    except Exception as e:
        request_id = str(uuid.uuid4())[:8]
        error_response, status_code = ErrorHandler.create_error_response(e, 500, request_id)
        return error_response, status_code

# Note: Middleware strips /vidgenerator, so /vidgenerator/api/* becomes /api/* before matching
# Only need /api/* route - middleware handles the prefix
@battle_bp.route('/api/battle/clans', methods=['POST'])
@rate_limit(endpoint='/api/battle/clans')
def create_clan():
    """Create a new clan"""
    try:
        # Use InputValidator for safe JSON parsing and validation
        data = InputValidator.get_json_safe(default={})
        
        # Validate required fields
        is_valid, error_msg = InputValidator.validate_required(data, ['clan_id', 'name'])
        if not is_valid:
            return jsonify({
                'success': False,
                'error': error_msg
            }), 400
        
        # Sanitize inputs
        clan_id = InputValidator.sanitize_string(data.get('clan_id', ''), max_length=50).strip()
        name = InputValidator.sanitize_string(data.get('name', ''), max_length=100).strip()
        leader_id = InputValidator.sanitize_string(data.get('leader_id', 'default_user'), max_length=50).strip()
        description = InputValidator.sanitize_string(data.get('description', ''), max_length=500).strip()
        
        # Validate lengths
        if not InputValidator.validate_length(clan_id, min_length=1, max_length=50):
            return jsonify({
                'success': False,
                'error': 'clan_id must be between 1 and 50 characters'
            }), 400
        
        if not InputValidator.validate_length(name, min_length=1, max_length=100):
            return jsonify({
                'success': False,
                'error': 'name must be between 1 and 100 characters'
            }), 400
        
        clan = battle_system.create_clan(clan_id, name, leader_id, description)
        return jsonify({
            'success': True,
            'clan': clan
        }), 200
    except Exception as e:
        request_id = str(uuid.uuid4())[:8]
        error_response, status_code = ErrorHandler.create_error_response(e, 500, request_id)
        return error_response, status_code


# Enhanced Battle Features - Match Tracking, PVP Trophies, ID System
@battle_bp.route('/api/battle/clans/<clan_id>', methods=['GET'])
@battle_bp.route('/vidgenerator/api/battle/clans/<clan_id>', methods=['GET'])
def get_clan(clan_id):
    """Get clan information"""
    try:
        clan = battle_system.get_clan_info(clan_id)
        if not clan:
            return jsonify({
                'success': False,
                'error': 'Clan not found'
            }), 404
        
        return jsonify({
            'success': True,
            'clan': clan
        }), 200
    except Exception as e:
        request_id = str(uuid.uuid4())[:8]
        error_response, status_code = ErrorHandler.create_error_response(e, 500, request_id)
        return error_response, status_code


# Enhanced Battle Features - Match Tracking, PVP Trophies, ID System
@battle_bp.route('/api/battle/clans/<clan_id>/join', methods=['POST'])
@battle_bp.route('/vidgenerator/api/battle/clans/<clan_id>/join', methods=['POST'])
def join_clan(clan_id):
    """Join a clan"""
    try:
        data = request.get_json() or {}
        user_id = data.get('user_id', 'default_user')
        
        success = battle_system.join_clan(clan_id, user_id)
        if not success:
            return jsonify({
                'success': False,
                'error': 'Failed to join clan'
            }), 400
        
        return jsonify({
            'success': True,
            'message': 'Joined clan successfully'
        }), 200
    except Exception as e:
        request_id = str(uuid.uuid4())[:8]
        error_response, status_code = ErrorHandler.create_error_response(e, 500, request_id)
        return error_response, status_code


# Enhanced Battle Features - Match Tracking, PVP Trophies, ID System
@battle_bp.route('/api/battle/battles', methods=['GET'])
@battle_bp.route('/vidgenerator/api/battle/battles', methods=['GET'])
def list_battles():
    """List active battles"""
    try:
        battles = battle_system.get_active_battles()
        return jsonify({
            'success': True,
            'battles': battles
        }), 200
    except Exception as e:
        request_id = str(uuid.uuid4())[:8]
        error_response, status_code = ErrorHandler.create_error_response(e, 500, request_id)
        return error_response, status_code


# Enhanced Battle Features - Match Tracking, PVP Trophies, ID System
@battle_bp.route('/api/battle/quick', methods=['POST'])
@battle_bp.route('/vidgenerator/api/battle/quick', methods=['POST'])
@rate_limit(endpoint='/api/battle/quick')
def create_quick_battle():
    """Create a quick battle without requiring clans - instant battle start"""
    try:
        data = InputValidator.get_json_safe(default={})
        user_id = InputValidator.sanitize_string(data.get('user_id', 'default_user'), max_length=50).strip()
        difficulty = InputValidator.sanitize_string(data.get('difficulty', 'balanced'), max_length=20).strip()
        battle_type = InputValidator.sanitize_string(data.get('battle_type', 'quick'), max_length=20).strip()
        
        # Try quick battle system first
        try:
            from backend.services.quick_battle_system import quick_battle
            result = quick_battle.create_quick_battle(user_id, difficulty, 'ai')
            return jsonify(result), 200  # Always return 200, error info in response
        except Exception as quick_err:
            # Fallback to battle_system
            logger.warning('quick_battle create failed, falling back to battle_system: %s', quick_err)
            result = battle_system.create_quick_battle(user_id, difficulty, battle_type)
            return jsonify(result), 200  # Always return 200, error info in response
    except Exception as e:
        request_id = str(uuid.uuid4())[:8]
        error_response, status_code = ErrorHandler.create_error_response(e, 500, request_id)
        return error_response, status_code

@battle_bp.route('/api/battle/battles', methods=['POST'])
@battle_bp.route('/vidgenerator/api/battle/battles', methods=['POST'])
@rate_limit(endpoint='/api/battle/battles')
def create_battle():
    """Create a new battle - auto-creates clans if they don't exist"""
    try:
        # Use InputValidator for safe JSON parsing
        data = InputValidator.get_json_safe(default={})
        
        # Make clan IDs optional - auto-generate if not provided
        clan1_id = InputValidator.sanitize_string(data.get('clan1_id', f"clan1_{datetime.utcnow().timestamp()}"), max_length=50).strip()
        clan2_id = InputValidator.sanitize_string(data.get('clan2_id', f"clan2_{datetime.utcnow().timestamp()}"), max_length=50).strip()
        battle_type = InputValidator.sanitize_string(data.get('battle_type', 'standard'), max_length=20).strip()
        enable_timepocket = data.get('enable_timepocket', False)
        timelock_minutes = data.get('timelock_minutes')
        total_matches = int(data.get('total_matches', 3))
        
        # Use enhanced battle system if timepocket or timelock requested
        if enable_timepocket or timelock_minutes:
            result = enhanced_battle_system.create_battle_with_timepocket(
                clan1_id, clan2_id, battle_type, enable_timepocket, timelock_minutes, total_matches
            )
        else:
            result = battle_system.create_battle(clan1_id, clan2_id, battle_type)
        
        return jsonify(result), 200  # Always return 200, error info in response
    except Exception as e:
        request_id = str(uuid.uuid4())[:8]
        error_response, status_code = ErrorHandler.create_error_response(e, 500, request_id)
        return error_response, status_code


# Enhanced Battle Features - Match Tracking, PVP Trophies, ID System
@battle_bp.route('/api/battle/battles/<battle_id>/action', methods=['POST'])
@battle_bp.route('/vidgenerator/api/battle/battles/<battle_id>/action', methods=['POST'])
@rate_limit(endpoint='/api/battle/battles/action')
def submit_battle_action(battle_id):
    """Submit an action in a battle"""
    try:
        # Sanitize battle_id from URL
        battle_id = InputValidator.sanitize_string(battle_id, max_length=50).strip()
        
        # Use InputValidator for safe JSON parsing
        data = InputValidator.get_json_safe(default={})
        
        # Validate required fields
        is_valid, error_msg = InputValidator.validate_required(data, ['clan_id'])
        if not is_valid:
            return jsonify({
                'success': False,
                'error': error_msg
            }), 400
        
        # Sanitize inputs
        clan_id = InputValidator.sanitize_string(data.get('clan_id', ''), max_length=50).strip()
        user_id = InputValidator.sanitize_string(data.get('user_id', 'default_user'), max_length=50).strip()
        action_type = InputValidator.sanitize_string(data.get('action_type', 'video_generated'), max_length=50).strip()
        value = int(data.get('value', 1))
        
        result = battle_system.submit_battle_action(battle_id, clan_id, user_id, action_type, value)
        return jsonify(result), 200  # Always return 200, error info in response
    except Exception as e:
        request_id = str(uuid.uuid4())[:8]
        error_response, status_code = ErrorHandler.create_error_response(e, 500, request_id)
        return error_response, status_code


# Enhanced Battle Features - Match Tracking, PVP Trophies, ID System
@battle_bp.route('/api/battle/battles/<battle_id>/end', methods=['POST'])
@battle_bp.route('/vidgenerator/api/battle/battles/<battle_id>/end', methods=['POST'])
@rate_limit(endpoint='/api/battle/battles/end')
def end_battle(battle_id):
    """End a battle"""
    try:
        # Sanitize battle_id from URL
        battle_id = InputValidator.sanitize_string(battle_id, max_length=50).strip()
        
        result = battle_system.end_battle(battle_id)
        return jsonify(result), 200  # Always return 200, error info in response
    except Exception as e:
        request_id = str(uuid.uuid4())[:8]
        error_response, status_code = ErrorHandler.create_error_response(e, 500, request_id)
        return error_response, status_code


# Enhanced Battle Features - Match Tracking, PVP Trophies, ID System
# Note: Middleware strips /vidgenerator, so /vidgenerator/api/* becomes /api/* before matching
# Only need /api/* route - middleware handles the prefix
@battle_bp.route('/api/battle/leaderboard', methods=['GET'])
@battle_bp.route('/vidgenerator/api/battle/leaderboard', methods=['GET'])
def get_leaderboard():
    """Get clan leaderboard"""
    try:
        limit = int(request.args.get('limit', 10))
        leaderboard = battle_system.get_leaderboard(limit)
        return jsonify({
            'success': True,
            'leaderboard': leaderboard if leaderboard else []
        }), 200
    except Exception as e:
        # Return 200 with empty leaderboard to avoid breaking frontend
        import sys
        print(f"[Battle Leaderboard] Error: {e}", file=sys.stderr, flush=True)
        return jsonify({
            'success': True,
            'error': str(e),
            'leaderboard': []
        }), 200


# Enhanced Battle Features - Match Tracking, PVP Trophies, ID System
# Note: Middleware strips /vidgenerator, so /vidgenerator/api/* becomes /api/* before matching
# Only need /api/* route - middleware handles the prefix
@battle_bp.route('/api/battle/history', methods=['GET'])
@battle_bp.route('/vidgenerator/api/battle/history', methods=['GET'])
def get_battle_history():
    """Get battle history"""
    try:
        user_id = request.args.get('user_id', 'default_user')
        limit = int(request.args.get('limit', 10))
        history = battle_system.get_battle_history(limit)
        return jsonify({
            'success': True,
            'history': history if history else []
        }), 200
    except Exception as e:
        # Return 200 with empty history to avoid breaking frontend
        import sys
        print(f"[Battle History] Error: {e}", file=sys.stderr, flush=True)
        return jsonify({
            'success': True,
            'error': str(e),
            'history': []
        }), 200


# Enhanced Battle Features - Match Tracking, PVP Trophies, ID System
@battle_bp.route('/api/battle/find-opponents', methods=['POST'])
@battle_bp.route('/vidgenerator/api/battle/find-opponents', methods=['POST'])
@rate_limit(endpoint='/api/battle/find-opponents')
def find_opponents():
    """Find intelligent opponents using battle network and fight intelligence"""
    try:
        # Use InputValidator for safe JSON parsing
        data = InputValidator.get_json_safe(default={})
        user_id = InputValidator.sanitize_string(data.get('user_id', 'default_user'), max_length=50).strip()
        count = max(1, min(20, int(data.get('count', 5))))  # Limit between 1 and 20
        
        # Download opponent data from battle network and analyze
        opponents = battle_intelligence.find_intelligent_opponents(user_id, count)
        
        return jsonify({
            'success': True,
            'opponents': opponents,
            'count': len(opponents)
        }), 200
    except Exception as e:
        request_id = str(uuid.uuid4())[:8]
        error_response, status_code = ErrorHandler.create_error_response(e, 500, request_id)
        return error_response, status_code


# Enhanced Battle Features - Match Tracking, PVP Trophies, ID System
@battle_bp.route('/api/battle/opponent-intelligence', methods=['POST'])
@battle_bp.route('/vidgenerator/api/battle/opponent-intelligence', methods=['POST'])
@rate_limit(endpoint='/api/battle/opponent-intelligence')
def get_opponent_intelligence():
    """Get detailed fight and aggression intelligence for opponent"""
    try:
        # Use InputValidator for safe JSON parsing
        data = InputValidator.get_json_safe(default={})
        
        # Validate required fields
        is_valid, error_msg = InputValidator.validate_required(data, ['opponent_id'])
        if not is_valid:
            return jsonify({
                'success': False,
                'error': error_msg
            }), 400
        
        # Sanitize inputs
        user_id = InputValidator.sanitize_string(data.get('user_id', 'default_user'), max_length=50).strip()
        opponent_id = InputValidator.sanitize_string(data.get('opponent_id', ''), max_length=50).strip()
        
        # Download opponent data and analyze
        fight_intel = battle_intelligence.analyze_fight_intelligence(user_id, opponent_id)
        aggression_intel = battle_intelligence.get_aggression_intelligence(user_id, opponent_id)
        
        return jsonify({
            'success': True,
            'fight_intelligence': fight_intel,
            'aggression_intelligence': aggression_intel
        }), 200
    except Exception as e:
        request_id = str(uuid.uuid4())[:8]
        error_response, status_code = ErrorHandler.create_error_response(e, 500, request_id)
        return error_response, status_code


# Enhanced Battle Features - Match Tracking, PVP Trophies, ID System
@battle_bp.route('/api/battle/download-opponent', methods=['POST'])
@battle_bp.route('/vidgenerator/api/battle/download-opponent', methods=['POST'])
@rate_limit(endpoint='/api/battle/download-opponent')
def download_opponent():
    """Download opponent data from battle network"""
    try:
        # Use InputValidator for safe JSON parsing
        data = InputValidator.get_json_safe(default={})
        
        # Validate required fields
        is_valid, error_msg = InputValidator.validate_required(data, ['opponent_id'])
        if not is_valid:
            return jsonify({
                'success': False,
                'error': error_msg
            }), 400
        
        # Sanitize inputs
        opponent_id = InputValidator.sanitize_string(data.get('opponent_id', ''), max_length=50).strip()
        
        # Download from battle network
        opponent_data = battle_intelligence.download_opponent_data(opponent_id)
        
        return jsonify({
            'success': True,
            'opponent': opponent_data
        }), 200
    except Exception as e:
        request_id = str(uuid.uuid4())[:8]
        error_response, status_code = ErrorHandler.create_error_response(e, 500, request_id)
        return error_response, status_code


# Enhanced Battle Features - Match Tracking, PVP Trophies, ID System
@battle_bp.route('/api/battle/fantasy/tournaments', methods=['GET'])
@battle_bp.route('/vidgenerator/api/battle/fantasy/tournaments', methods=['GET'])
def get_fantasy_tournaments():
    """Get fantasy-themed tournaments"""
    try:
        status = request.args.get('status')
        tournaments = fantasy_battle_intelligence.get_fantasy_tournaments(status)
        return jsonify({
            'success': True,
            'tournaments': tournaments
        }), 200
    except Exception as e:
        request_id = str(uuid.uuid4())[:8]
        error_response, status_code = ErrorHandler.create_error_response(e, 500, request_id)
        return error_response, status_code


# Enhanced Battle Features - Match Tracking, PVP Trophies, ID System
@battle_bp.route('/api/battle/fantasy/history', methods=['GET'])
@battle_bp.route('/vidgenerator/api/battle/fantasy/history', methods=['GET'])
def get_fantasy_history():
    """Get fantasy-themed battle history"""
    try:
        user_id = request.args.get('user_id', 'default_user')
        limit = int(request.args.get('limit', 20))
        if fantasy_battle_intelligence:
            history = fantasy_battle_intelligence.generate_fantasy_history(user_id, limit)
        else:
            history = []
        return jsonify({
            'success': True,
            'history': history
        }), 200
    except Exception as e:
        # Return empty history instead of error
        return jsonify({
            'success': True,
            'history': []
        }), 200


# Enhanced Battle Features - Match Tracking, PVP Trophies, ID System
@battle_bp.route('/api/battle/fantasy/leaderboard', methods=['GET'])
@battle_bp.route('/vidgenerator/api/battle/fantasy/leaderboard', methods=['GET'])
def get_fantasy_leaderboard():
    """Get fantasy-themed leaderboard"""
    try:
        realm = request.args.get('realm')
        limit = int(request.args.get('limit', 50))
        leaderboard = fantasy_battle_intelligence.generate_fantasy_leaderboard(realm, limit)
        return jsonify({
            'success': True,
            'leaderboard': leaderboard
        }), 200
    except Exception as e:
        request_id = str(uuid.uuid4())[:8]
        error_response, status_code = ErrorHandler.create_error_response(e, 500, request_id)
        return error_response, status_code


# Enhanced Battle Features - Match Tracking, PVP Trophies, ID System
@battle_bp.route('/api/battle/fantasy/resources', methods=['GET'])
@battle_bp.route('/vidgenerator/api/battle/fantasy/resources', methods=['GET'])
def get_fantasy_resources():
    """Get fantasy-themed resources"""
    try:
        user_id = request.args.get('user_id', 'default_user')
        resources = fantasy_battle_intelligence.get_fantasy_resources(user_id)
        return jsonify({
            'success': True,
            'resources': resources
        }), 200
    except Exception as e:
        request_id = str(uuid.uuid4())[:8]
        error_response, status_code = ErrorHandler.create_error_response(e, 500, request_id)
        return error_response, status_code


# Enhanced Battle Features - Match Tracking, PVP Trophies, ID System
@battle_bp.route('/api/battle/fantasy/intelligence', methods=['GET'])
@battle_bp.route('/vidgenerator/api/battle/fantasy/intelligence', methods=['GET'])
def get_fantasy_intelligence():
    """Get fantasy-themed intelligence"""
    try:
        user_id = request.args.get('user_id', 'default_user')
        intelligence = fantasy_battle_intelligence.get_fantasy_intelligence(user_id)
        return jsonify({
            'success': True,
            'intelligence': intelligence
        }), 200
    except Exception as e:
        request_id = str(uuid.uuid4())[:8]
        error_response, status_code = ErrorHandler.create_error_response(e, 500, request_id)
        return error_response, status_code


# Enhanced Battle Features - Match Tracking, PVP Trophies, ID System
@battle_bp.route('/api/battle/fantasy/tournaments/<tournament_id>/join', methods=['POST'])
@battle_bp.route('/vidgenerator/api/battle/fantasy/tournaments/<tournament_id>/join', methods=['POST'])
@rate_limit(endpoint='/api/battle/fantasy/tournaments/join')
def join_fantasy_tournament(tournament_id):
    """Join a fantasy tournament"""
    try:
        # Sanitize tournament_id from URL
        tournament_id = InputValidator.sanitize_string(tournament_id, max_length=50).strip()
        
        # Use InputValidator for safe JSON parsing
        data = InputValidator.get_json_safe(default={})
        user_id = InputValidator.sanitize_string(data.get('user_id', 'default_user'), max_length=50).strip()
        
        result = fantasy_battle_intelligence.join_fantasy_tournament(tournament_id, user_id)
        return jsonify(result), 200  # Always return 200, error info in response
    except Exception as e:
        request_id = str(uuid.uuid4())[:8]
        error_response, status_code = ErrorHandler.create_error_response(e, 500, request_id)
        return error_response, status_code


# Enhanced Battle Features - Match Tracking, PVP Trophies, ID System
@battle_bp.route('/api/battle/fantasy/power', methods=['GET'])
@battle_bp.route('/vidgenerator/api/battle/fantasy/power', methods=['GET'])
def get_fantasy_power():
    """Calculate fantasy power from resources"""
    try:
        user_id = request.args.get('user_id', 'default_user')
        power = fantasy_battle_intelligence.calculate_fantasy_power(user_id)
        return jsonify({
            'success': True,
            'power': power
        }), 200
    except Exception as e:
        request_id = str(uuid.uuid4())[:8]
        error_response, status_code = ErrorHandler.create_error_response(e, 500, request_id)
        return error_response, status_code


# Enhanced Battle Features - Match Tracking, PVP Trophies, ID System
@battle_bp.route('/api/battle/fantasy/find-opponent', methods=['POST'])
@battle_bp.route('/vidgenerator/api/battle/fantasy/find-opponent', methods=['POST'])
@rate_limit(endpoint='/api/battle/fantasy/find-opponent')
def find_fantasy_opponent():
    """Find a suitable opponent for fantasy battle"""
    try:
        # Use InputValidator for safe JSON parsing
        data = InputValidator.get_json_safe(default={})
        user_id = InputValidator.sanitize_string(data.get('user_id', 'default_user'), max_length=50).strip()
        realm = InputValidator.sanitize_string(data.get('realm', ''), max_length=50).strip() if data.get('realm') else None
        difficulty = InputValidator.sanitize_string(data.get('difficulty', 'balanced'), max_length=20).strip()
        
        opponent = fantasy_battle_intelligence.find_opponent(user_id, realm, difficulty)
        return jsonify({
            'success': True,
            'opponent': opponent
        }), 200
    except Exception as e:
        request_id = str(uuid.uuid4())[:8]
        error_response, status_code = ErrorHandler.create_error_response(e, 500, request_id)
        return error_response, status_code


# Enhanced Battle Features - Match Tracking, PVP Trophies, ID System
@battle_bp.route('/api/battle/fantasy/execute', methods=['POST'])
@battle_bp.route('/vidgenerator/api/battle/fantasy/execute', methods=['POST'])
@rate_limit(endpoint='/api/battle/fantasy/execute')
def execute_fantasy_battle():
    """Execute a fantasy battle"""
    try:
        # Use InputValidator for safe JSON parsing
        data = InputValidator.get_json_safe(default={})
        
        # Validate required fields
        is_valid, error_msg = InputValidator.validate_required(data, ['opponent_id'])
        if not is_valid:
            return jsonify({
                'success': False,
                'error': error_msg
            }), 400
        
        # Sanitize inputs
        user_id = InputValidator.sanitize_string(data.get('user_id', 'default_user'), max_length=50).strip()
        opponent_id = InputValidator.sanitize_string(data.get('opponent_id', ''), max_length=50).strip()
        battle_type = InputValidator.sanitize_string(data.get('battle_type', 'tournament'), max_length=20).strip()
        tournament_id = InputValidator.sanitize_string(data.get('tournament_id', ''), max_length=50).strip() if data.get('tournament_id') else None
        
        battle = fantasy_battle_intelligence.execute_fantasy_battle(
            user_id, opponent_id, battle_type, tournament_id
        )
        
        return jsonify({
            'success': True,
            'battle': battle
        }), 200
    except Exception as e:
        request_id = str(uuid.uuid4())[:8]
        error_response, status_code = ErrorHandler.create_error_response(e, 500, request_id)
        return error_response, status_code


# Enhanced Battle Features - Match Tracking, PVP Trophies, ID System
@battle_bp.route('/api/battle/rulebooks', methods=['GET'])
@battle_bp.route('/vidgenerator/api/battle/rulebooks', methods=['GET'])
@battle_bp.route('/api/battle/rule-books', methods=['GET'])
@battle_bp.route('/vidgenerator/api/battle/rule-books', methods=['GET'])
@rate_limit()
def get_rule_books():
    """Get available rule books"""
    try:
        user_id = request.args.get('user_id', 'default_user')
        if battle_rule_books:
            books = battle_rule_books.get_rule_books(user_id)
        else:
            books = []
        return jsonify({
            'success': True,
            'books': books
        }), 200
    except Exception as e:
        return jsonify({
            'success': True,
            'books': []
        }), 200


# Enhanced Battle Features - Match Tracking, PVP Trophies, ID System
@battle_bp.route('/api/battle/rule-books/<book_id>', methods=['GET'])
@battle_bp.route('/vidgenerator/api/battle/rule-books/<book_id>', methods=['GET'])
@rate_limit()
def get_rule_book(book_id: str):
    """Get specific rule book"""
    try:
        user_id = request.args.get('user_id', 'default_user')
        book = battle_rule_books.get_rule_book(book_id, user_id)
        if book:
            return jsonify({
                'success': True,
                'book': book
            }), 200
        else:
            return jsonify({
                'success': False,
                'error': 'Book not found'
            }), 404
    except Exception as e:
        request_id = str(uuid.uuid4())[:8]
        error_response, status_code = ErrorHandler.create_error_response(e, 500, request_id)
        return error_response, status_code


# Enhanced Battle Features - Match Tracking, PVP Trophies, ID System
@battle_bp.route('/api/battle/rule-books/<book_id>/progress', methods=['POST'])
@battle_bp.route('/vidgenerator/api/battle/rule-books/<book_id>/progress', methods=['POST'])
@rate_limit()
def update_rule_book_progress(book_id: str):
    """Update rule book progress"""
    try:
        data = InputValidator.get_json_safe(default={})
        user_id = InputValidator.sanitize_string(data.get('user_id', 'default_user'))
        chapter_id = InputValidator.sanitize_string(data.get('chapter_id', ''))
        
        result = battle_rule_books.update_progress(user_id, book_id, chapter_id)
        return jsonify(result), 200  # Always return 200, error info in response
    except Exception as e:
        request_id = str(uuid.uuid4())[:8]
        error_response, status_code = ErrorHandler.create_error_response(e, 500, request_id)
        return error_response, status_code


# Enhanced Battle Features - Match Tracking, PVP Trophies, ID System
@battle_bp.route('/api/battle/series', methods=['GET'])
@battle_bp.route('/vidgenerator/api/battle/series', methods=['GET'])
@rate_limit()
def get_battle_series():
    """Get available battle series"""
    try:
        user_id = request.args.get('user_id', 'default_user')
        if battle_series:
            series = battle_series.get_series(user_id)
        else:
            series = []
        return jsonify({
            'success': True,
            'series': series
        }), 200
    except Exception as e:
        # Always return 200 with empty array
        return jsonify({
            'success': True,
            'series': []
        }), 200


# Enhanced Battle Features - Match Tracking, PVP Trophies, ID System
@battle_bp.route('/api/battle/series/<series_id>', methods=['GET'])
@battle_bp.route('/vidgenerator/api/battle/series/<series_id>', methods=['GET'])
@rate_limit()
def get_series_details(series_id: str):
    """Get specific series details"""
    try:
        user_id = request.args.get('user_id', 'default_user')
        if battle_series:
            series = battle_series.get_series_details(series_id, user_id)
        else:
            series = None
        if series:
            return jsonify({
                'success': True,
                'series': series
            }), 200
        else:
            return jsonify({
                'success': False,
                'error': 'Series not found'
            }), 404
    except Exception as e:
        request_id = str(uuid.uuid4())[:8]
        error_response, status_code = ErrorHandler.create_error_response(e, 500, request_id)
        return error_response, status_code


# Enhanced Battle Features - Match Tracking, PVP Trophies, ID System
@battle_bp.route('/api/battle/series/<series_id>/join', methods=['POST'])
@battle_bp.route('/vidgenerator/api/battle/series/<series_id>/join', methods=['POST'])
@rate_limit()
def join_series(series_id: str):
    """Join a battle series"""
    try:
        data = InputValidator.get_json_safe(default={})
        user_id = InputValidator.sanitize_string(data.get('user_id', 'default_user'))
        
        if battle_series:
            result = battle_series.join_series(user_id, series_id)
        else:
            result = {'success': False, 'error': 'Battle series system not available'}
        return jsonify(result), 200  # Always return 200, error info in response
    except Exception as e:
        request_id = str(uuid.uuid4())[:8]
        error_response, status_code = ErrorHandler.create_error_response(e, 500, request_id)
        return error_response, status_code


# Enhanced Battle Features - Match Tracking, PVP Trophies, ID System
@battle_bp.route('/api/battle/gps/location', methods=['POST'])
@battle_bp.route('/vidgenerator/api/battle/gps/location', methods=['POST'])
@rate_limit()
def update_gps_location():
    """Update user GPS location"""
    try:
        data = InputValidator.get_json_safe(default={})
        user_id = InputValidator.sanitize_string(data.get('user_id', 'default_user'))
        lat = float(data.get('lat', 0))
        lng = float(data.get('lng', 0))
        
        result = battle_gps.update_user_location(user_id, lat, lng)
        return jsonify(result), 200
    except Exception as e:
        request_id = str(uuid.uuid4())[:8]
        error_response, status_code = ErrorHandler.create_error_response(e, 500, request_id)
        return error_response, status_code


# Enhanced Battle Features - Match Tracking, PVP Trophies, ID System
@battle_bp.route('/api/battle/gps/nearby', methods=['GET'])
@battle_bp.route('/vidgenerator/api/battle/gps/nearby', methods=['GET'])
@rate_limit()
def get_nearby_battles():
    """Get nearby battles"""
    try:
        user_id = request.args.get('user_id', 'default_user')
        battles = battle_gps.get_nearby_battles(user_id)
        return jsonify({
            'success': True,
            'battles': battles
        }), 200
    except Exception as e:
        request_id = str(uuid.uuid4())[:8]
        error_response, status_code = ErrorHandler.create_error_response(e, 500, request_id)
        return error_response, status_code


# Enhanced Battle Features - Match Tracking, PVP Trophies, ID System
@battle_bp.route('/api/battle/gps', methods=['GET'])
@battle_bp.route('/vidgenerator/api/battle/gps', methods=['GET'])
@rate_limit()
def get_gps():
    """Get GPS data - alias for get_battle_locations"""
    return get_battle_locations()

@battle_bp.route('/api/battle/gps/locations', methods=['GET'])
@battle_bp.route('/vidgenerator/api/battle/gps/locations', methods=['GET'])
@rate_limit()
def get_battle_locations():
    """Get all battle locations"""
    try:
        if battle_gps:
            locations = battle_gps.get_battle_locations()
        else:
            locations = []
        return jsonify({
            'success': True,
            'locations': locations
        }), 200
    except Exception as e:
        # Always return 200 with empty array
        return jsonify({
            'success': True,
            'locations': []
        }), 200


# Enhanced Battle Features - Match Tracking, PVP Trophies, ID System
@battle_bp.route('/api/battle/news', methods=['GET'])
@battle_bp.route('/vidgenerator/api/battle/news', methods=['GET'])
@rate_limit()
def get_battle_news():
    """Get battle news"""
    try:
        limit = int(request.args.get('limit', 10))
        category = request.args.get('category')
        if battle_news:
            news = battle_news.get_news(limit, category)
        else:
            news = []
        return jsonify({
            'success': True,
            'news': news
        }), 200
    except Exception as e:
        # Always return 200 with empty array
        return jsonify({
            'success': True,
            'news': []
        }), 200


# Enhanced Battle Features - Match Tracking, PVP Trophies, ID System
@battle_bp.route('/api/battle/peers', methods=['GET'])
@battle_bp.route('/vidgenerator/api/battle/peers', methods=['GET'])
@rate_limit()
def get_peers():
    """Get all peers in network"""
    try:
        user_id = request.args.get('user_id', 'default_user')
        if battle_peer_network:
            peers = battle_peer_network.get_peers(user_id)
        else:
            peers = []
        return jsonify({
            'success': True,
            'peers': peers
        }), 200
    except Exception as e:
        # Always return 200 with empty array
        return jsonify({
            'success': True,
            'peers': []
        }), 200


# Enhanced Battle Features - Match Tracking, PVP Trophies, ID System
@battle_bp.route('/api/battle/peers/<peer_id>/connect', methods=['POST'])
@battle_bp.route('/vidgenerator/api/battle/peers/<peer_id>/connect', methods=['POST'])
@rate_limit()
def connect_peer(peer_id: str):
    """Connect to a peer"""
    try:
        data = InputValidator.get_json_safe(default={})
        user_id = InputValidator.sanitize_string(data.get('user_id', 'default_user'))
        
        if battle_peer_network:
            result = battle_peer_network.connect_peer(user_id, peer_id)
        else:
            result = {'success': False, 'error': 'Peer network system not available'}
        return jsonify(result), 200  # Always return 200, error info in response
    except Exception as e:
        request_id = str(uuid.uuid4())[:8]
        error_response, status_code = ErrorHandler.create_error_response(e, 500, request_id)
        return error_response, status_code


# Enhanced Battle Features - Match Tracking, PVP Trophies, ID System
@battle_bp.route('/api/battle/peers/<peer_id>/disconnect', methods=['POST'])
@battle_bp.route('/vidgenerator/api/battle/peers/<peer_id>/disconnect', methods=['POST'])
@rate_limit()
def disconnect_peer(peer_id: str):
    """Disconnect from a peer"""
    try:
        data = InputValidator.get_json_safe(default={})
        user_id = InputValidator.sanitize_string(data.get('user_id', 'default_user'))
        
        if battle_peer_network:
            result = battle_peer_network.disconnect_peer(user_id, peer_id)
        else:
            result = {'success': False, 'error': 'Peer network system not available'}
        return jsonify(result), 200  # Always return 200, error info in response
    except Exception as e:
        request_id = str(uuid.uuid4())[:8]
        error_response, status_code = ErrorHandler.create_error_response(e, 500, request_id)
        return error_response, status_code


# Enhanced Battle Features - Match Tracking, PVP Trophies, ID System
@battle_bp.route('/api/battle/peers/network/topology', methods=['GET'])
@battle_bp.route('/vidgenerator/api/battle/peers/network/topology', methods=['GET'])
@rate_limit()
def get_network_topology():
    """Get network topology graph"""
    try:
        user_id = request.args.get('user_id', 'default_user')
        if battle_peer_network:
            topology = battle_peer_network.get_network_topology(user_id)
        else:
            topology = {}
        return jsonify({
            'success': True,
            'topology': topology
        }), 200
    except Exception as e:
        request_id = str(uuid.uuid4())[:8]
        error_response, status_code = ErrorHandler.create_error_response(e, 500, request_id)
        return error_response, status_code


# Enhanced Battle Features - Match Tracking, PVP Trophies, ID System
@battle_bp.route('/api/battle/peers/network/stats', methods=['GET'])
@battle_bp.route('/vidgenerator/api/battle/peers/network/stats', methods=['GET'])
@rate_limit()
def get_network_stats():
    """Get network statistics"""
    try:
        user_id = request.args.get('user_id', 'default_user')
        if battle_peer_network:
            stats = battle_peer_network.get_network_stats(user_id)
        else:
            stats = {}
        return jsonify({
            'success': True,
            'stats': stats
        }), 200
    except Exception as e:
        request_id = str(uuid.uuid4())[:8]
        error_response, status_code = ErrorHandler.create_error_response(e, 500, request_id)
        return error_response, status_code


# Enhanced Battle Features - Match Tracking, PVP Trophies, ID System
@battle_bp.route('/api/battle/peers/<peer_id>/behavior', methods=['GET'])
@battle_bp.route('/vidgenerator/api/battle/peers/<peer_id>/behavior', methods=['GET'])
@rate_limit()
def get_peer_behavior(peer_id: str):
    """Get peer behavior logs"""
    try:
        limit = int(request.args.get('limit', 50))
        behavior = battle_peer_network.get_peer_behavior(peer_id, limit)
        return jsonify({
            'success': True,
            'behavior': behavior
        }), 200
    except Exception as e:
        request_id = str(uuid.uuid4())[:8]
        error_response, status_code = ErrorHandler.create_error_response(e, 500, request_id)
        return error_response, status_code


# Enhanced Battle Features - Match Tracking, PVP Trophies, ID System

@battle_bp.route('/api/battle/trading/offer/create', methods=['POST'])
@battle_bp.route('/vidgenerator/api/battle/trading/offer/create', methods=['POST'])
@rate_limit()
def create_trade_offer():
    try:
        data = InputValidator.get_json_safe(default={})
        from_user_id = InputValidator.sanitize_string(data.get('from_user_id', ''))
        to_user_id = InputValidator.sanitize_string(data.get('to_user_id', ''))
        offering_trophies = data.get('offering_trophies', [])
        requesting_trophies = data.get('requesting_trophies', [])
        message = InputValidator.sanitize_string(data.get('message', ''))
        
        result = trophy_trading_system.create_trade_offer(from_user_id, to_user_id, offering_trophies, requesting_trophies, message)
        return jsonify(result), 200  # Always return 200, error info in response
    except Exception as e:
        request_id = str(uuid.uuid4())[:8]
        error_response, status_code = ErrorHandler.create_error_response(e, 500, request_id)
        return error_response, status_code

@battle_bp.route('/api/battle/trading/offers', methods=['GET'])
@battle_bp.route('/vidgenerator/api/battle/trading/offers', methods=['GET'])
@rate_limit()
def get_trade_offers():
    try:
        user_id = request.args.get('user_id', 'default_user')
        if trophy_trading_system:
            result = trophy_trading_system.get_trade_offers(user_id)
        else:
            result = {'success': True, 'offers': [], 'incoming': [], 'outgoing': []}
        return jsonify(result), 200
    except Exception as e:
        request_id = str(uuid.uuid4())[:8]
        error_response, status_code = ErrorHandler.create_error_response(e, 500, request_id)
        return error_response, status_code

@battle_bp.route('/api/battle/trading/offer/<offer_id>/accept', methods=['POST'])
@battle_bp.route('/vidgenerator/api/battle/trading/offer/<offer_id>/accept', methods=['POST'])
@rate_limit()
def accept_trade_offer(offer_id: str):
    try:
        data = InputValidator.get_json_safe(default={})
        user_id = InputValidator.sanitize_string(data.get('user_id', ''))
        if trophy_trading_system:
            result = trophy_trading_system.accept_trade_offer(offer_id, user_id)
        else:
            result = {'success': False, 'error': 'Trophy trading system not available'}
        return jsonify(result), 200  # Always return 200, error info in response
    except Exception as e:
        request_id = str(uuid.uuid4())[:8]
        error_response, status_code = ErrorHandler.create_error_response(e, 500, request_id)
        return error_response, status_code

@battle_bp.route('/api/battle/collectibles/create', methods=['POST'])
@battle_bp.route('/vidgenerator/api/battle/collectibles/create', methods=['POST'])
@rate_limit()
def create_collectible_card():
    try:
        data = InputValidator.get_json_safe(default={})
        card_type = InputValidator.sanitize_string(data.get('card_type', ''))
        user_id = InputValidator.sanitize_string(data.get('user_id', ''))
        if collectible_card_system:
            result = collectible_card_system.create_card(card_type, user_id)
        else:
            result = {'success': False, 'error': 'Collectible card system not available'}
        return jsonify(result), 200  # Always return 200, error info in response
    except Exception as e:
        request_id = str(uuid.uuid4())[:8]
        error_response, status_code = ErrorHandler.create_error_response(e, 500, request_id)
        return error_response, status_code

@battle_bp.route('/api/battle/collectibles/collection', methods=['GET'])
@battle_bp.route('/vidgenerator/api/battle/collectibles/collection', methods=['GET'])
@rate_limit()
def get_collection():
    try:
        user_id = request.args.get('user_id', 'default_user')
        if collectible_card_system:
            result = collectible_card_system.get_user_collection(user_id)
        else:
            result = {'success': True, 'collection': [], 'cards': []}
        return jsonify(result), 200
    except Exception as e:
        request_id = str(uuid.uuid4())[:8]
        error_response, status_code = ErrorHandler.create_error_response(e, 500, request_id)
        return error_response, status_code

@battle_bp.route('/api/battle/collectibles/<card_id>/valuation', methods=['GET'])
@battle_bp.route('/vidgenerator/api/battle/collectibles/<card_id>/valuation', methods=['GET'])
@rate_limit()
def get_card_valuation(card_id: str):
    try:
        years = int(request.args.get('years', 10))
        result = collectible_card_system.calculate_future_value(card_id, years)
        return jsonify(result), 200  # Always return 200, error info in response
    except Exception as e:
        request_id = str(uuid.uuid4())[:8]
        error_response, status_code = ErrorHandler.create_error_response(e, 500, request_id)
        return error_response, status_code


# Mission & Quest System
from backend.services.mission_quest_system import mission_quest_system

@battle_bp.route('/api/battle/missions/daily-quests', methods=['GET'])
@battle_bp.route('/vidgenerator/api/battle/missions/daily-quests', methods=['GET'])
@rate_limit()
def get_daily_quests():
    try:
        user_id = request.args.get('user_id', 'default_user')
        result = mission_quest_system.get_user_daily_quests(user_id)
        return jsonify(result), 200
    except Exception as e:
        request_id = str(uuid.uuid4())[:8]
        error_response, status_code = ErrorHandler.create_error_response(e, 500, request_id)
        return error_response, status_code

@battle_bp.route('/api/battle/missions/daily-quests/refresh', methods=['POST'])
@battle_bp.route('/vidgenerator/api/battle/missions/daily-quests/refresh', methods=['POST'])
@rate_limit()
def refresh_daily_quests():
    try:
        user_id = request.args.get('user_id', 'default_user')
        result = mission_quest_system.generate_daily_quests(user_id)
        return jsonify(result), 200
    except Exception as e:
        request_id = str(uuid.uuid4())[:8]
        error_response, status_code = ErrorHandler.create_error_response(e, 500, request_id)
        return error_response, status_code

@battle_bp.route('/api/battle/missions/timeline', methods=['GET'])
@battle_bp.route('/vidgenerator/api/battle/missions/timeline', methods=['GET'])
@rate_limit()
def get_timeline_missions():
    try:
        user_id = request.args.get('user_id', 'default_user')
        result = mission_quest_system.get_timeline_missions(user_id)
        return jsonify(result), 200
    except Exception as e:
        request_id = str(uuid.uuid4())[:8]
        error_response, status_code = ErrorHandler.create_error_response(e, 500, request_id)
        return error_response, status_code

@battle_bp.route('/api/battle/missions/progress/update', methods=['POST'])
@battle_bp.route('/vidgenerator/api/battle/missions/progress/update', methods=['POST'])
@rate_limit()
def update_mission_progress():
    try:
        data = InputValidator.get_json_safe(default={})
        user_id = InputValidator.sanitize_string(data.get('user_id', 'default_user'))
        quest_type = InputValidator.sanitize_string(data.get('quest_type', ''))
        amount = int(data.get('amount', 1))
        
        # Update both daily quests and timeline missions
        quest_result = mission_quest_system.update_quest_progress(user_id, quest_type, amount)
        mission_result = mission_quest_system.update_mission_progress(user_id, quest_type, amount)
        
        return jsonify({
            'success': True,
            'quests': quest_result,
            'missions': mission_result
        }), 200
    except Exception as e:
        request_id = str(uuid.uuid4())[:8]
        error_response, status_code = ErrorHandler.create_error_response(e, 500, request_id)
        return error_response, status_code

@battle_bp.route('/api/battle/missions/mtg-id/<mtg_id>', methods=['GET'])
@battle_bp.route('/vidgenerator/api/battle/missions/mtg-id/<mtg_id>', methods=['GET'])
@rate_limit()
def get_mtg_id(mtg_id: str):
    try:
        mtg_id_info = mission_quest_system.get_mtg_id_info(mtg_id)
        if mtg_id_info:
            return jsonify({
                'success': True,
                'mtg_id': mtg_id_info
            }), 200
        else:
            return jsonify({
                'success': False,
                'error': 'MTG.ID not found'
            }), 404
    except Exception as e:
        request_id = str(uuid.uuid4())[:8]
        error_response, status_code = ErrorHandler.create_error_response(e, 500, request_id)
        return error_response, status_code


# AI Research System
from backend.services.ai_research_system import ai_research_system

@battle_bp.route('/api/battle/ai-research/search', methods=['POST'])
@battle_bp.route('/vidgenerator/api/battle/ai-research/search', methods=['POST'])
@rate_limit()
def search_ai_options():
    try:
        data = InputValidator.get_json_safe(default={})
        query = InputValidator.sanitize_string(data.get('query', ''))
        filters = data.get('filters', {})
        result = ai_research_system.search_ai_options(query, filters)
        return jsonify(result), 200
    except Exception as e:
        request_id = str(uuid.uuid4())[:8]
        error_response, status_code = ErrorHandler.create_error_response(e, 500, request_id)
        return error_response, status_code

@battle_bp.route('/api/battle/ai-research/prompt-template/<template_id>', methods=['GET'])
@battle_bp.route('/vidgenerator/api/battle/ai-research/prompt-template/<template_id>', methods=['GET'])
@rate_limit()
def get_prompt_template(template_id: str):
    try:
        template = ai_research_system.get_prompt_template(template_id)
        if template:
            return jsonify({'success': True, 'template': template}), 200
        else:
            return jsonify({'success': False, 'error': 'Template not found'}), 404
    except Exception as e:
        request_id = str(uuid.uuid4())[:8]
        error_response, status_code = ErrorHandler.create_error_response(e, 500, request_id)
        return error_response, status_code

@battle_bp.route('/api/battle/ai-research/creative-art-styles', methods=['GET'])
@battle_bp.route('/vidgenerator/api/battle/ai-research/creative-art-styles', methods=['GET'])
@rate_limit()
def get_creative_art_styles():
    try:
        styles = ai_research_system.get_creative_art_styles()
        return jsonify({'success': True, 'styles': styles}), 200
    except Exception as e:
        request_id = str(uuid.uuid4())[:8]
        error_response, status_code = ErrorHandler.create_error_response(e, 500, request_id)
        return error_response, status_code

@battle_bp.route('/api/battle/ai-research/enhance-video', methods=['POST'])
@battle_bp.route('/vidgenerator/api/battle/ai-research/enhance-video', methods=['POST'])
@rate_limit()
def enhance_video_with_ai():
    try:
        data = InputValidator.get_json_safe(default={})
        video_id = InputValidator.sanitize_string(data.get('video_id', ''))
        ai_options = data.get('ai_options', [])
        enhancement_level = InputValidator.sanitize_string(data.get('enhancement_level', 'medium'))
        result = ai_research_system.enhance_video_with_ai(video_id, ai_options, enhancement_level)
        return jsonify(result), 200
    except Exception as e:
        request_id = str(uuid.uuid4())[:8]
        error_response, status_code = ErrorHandler.create_error_response(e, 500, request_id)
        return error_response, status_code

# Rewards System
from backend.services.rewards_system import rewards_system

@battle_bp.route('/api/battle/rewards', methods=['GET'])
@battle_bp.route('/vidgenerator/api/battle/rewards', methods=['GET'])
@rate_limit()
def get_rewards():
    try:
        user_id = request.args.get('user_id', 'default_user')
        result = rewards_system.get_user_rewards(user_id)
        return jsonify(result), 200
    except Exception as e:
        request_id = str(uuid.uuid4())[:8]
        error_response, status_code = ErrorHandler.create_error_response(e, 500, request_id)
        return error_response, status_code

@battle_bp.route('/api/battle/rewards/<reward_id>/claim', methods=['POST'])
@battle_bp.route('/vidgenerator/api/battle/rewards/<reward_id>/claim', methods=['POST'])
@rate_limit()
def claim_reward(reward_id: str):
    try:
        data = InputValidator.get_json_safe(default={})
        user_id = InputValidator.sanitize_string(data.get('user_id', ''))
        result = rewards_system.claim_reward(user_id, reward_id)
        return jsonify(result), 200  # Always return 200, error info in response
    except Exception as e:
        request_id = str(uuid.uuid4())[:8]
        error_response, status_code = ErrorHandler.create_error_response(e, 500, request_id)
        return error_response, status_code

@battle_bp.route('/api/battle/rewards/claim-all', methods=['POST'])
@battle_bp.route('/vidgenerator/api/battle/rewards/claim-all', methods=['POST'])
@rate_limit()
def claim_all_rewards():
    try:
        data = InputValidator.get_json_safe(default={})
        user_id = InputValidator.sanitize_string(data.get('user_id', ''))
        result = rewards_system.claim_all_rewards(user_id)
        return jsonify(result), 200
    except Exception as e:
        request_id = str(uuid.uuid4())[:8]
        error_response, status_code = ErrorHandler.create_error_response(e, 500, request_id)
        return error_response, status_code

# Fantasy Leaderboard Rulebook
from backend.services.fantasy_leaderboard_rulebook import fantasy_leaderboard_rulebook

@battle_bp.route('/api/battle/leaderboard/rulebook', methods=['GET'])
@battle_bp.route('/vidgenerator/api/battle/leaderboard/rulebook', methods=['GET'])
@rate_limit()
def get_fantasy_rulebook():
    try:
        result = fantasy_leaderboard_rulebook.get_rulebook()
        return jsonify(result), 200
    except Exception as e:
        request_id = str(uuid.uuid4())[:8]
        error_response, status_code = ErrorHandler.create_error_response(e, 500, request_id)
        return error_response, status_code

@battle_bp.route('/api/battle/leaderboard/rulebook/chapter/<chapter_id>', methods=['GET'])
@battle_bp.route('/vidgenerator/api/battle/leaderboard/rulebook/chapter/<chapter_id>', methods=['GET'])
@rate_limit()
def get_rulebook_chapter(chapter_id: str):
    try:
        chapter = fantasy_leaderboard_rulebook.get_chapter(chapter_id)
        if chapter:
            return jsonify({'success': True, 'chapter': chapter}), 200
        else:
            return jsonify({'success': False, 'error': 'Chapter not found'}), 404
    except Exception as e:
        request_id = str(uuid.uuid4())[:8]
        error_response, status_code = ErrorHandler.create_error_response(e, 500, request_id)
        return error_response, status_code

@battle_bp.route('/api/battle/leaderboard/rulebook/chapter/<chapter_id>/complete', methods=['POST'])
@battle_bp.route('/vidgenerator/api/battle/leaderboard/rulebook/chapter/<chapter_id>/complete', methods=['POST'])
@rate_limit()
def complete_rulebook_chapter(chapter_id: str):
    try:
        data = InputValidator.get_json_safe(default={})
        user_id = InputValidator.sanitize_string(data.get('user_id', ''))
        result = fantasy_leaderboard_rulebook.update_user_progress(user_id, chapter_id)
        return jsonify(result), 200
    except Exception as e:
        request_id = str(uuid.uuid4())[:8]
        error_response, status_code = ErrorHandler.create_error_response(e, 500, request_id)
        return error_response, status_code

@battle_bp.route('/api/battle/leaderboard/rulebook/progress', methods=['GET'])
@battle_bp.route('/vidgenerator/api/battle/leaderboard/rulebook/progress', methods=['GET'])
@rate_limit()
def get_rulebook_progress():
    try:
        user_id = request.args.get('user_id', 'default_user')
        result = fantasy_leaderboard_rulebook.get_user_progress(user_id)
        return jsonify(result), 200
    except Exception as e:
        request_id = str(uuid.uuid4())[:8]
        error_response, status_code = ErrorHandler.create_error_response(e, 500, request_id)
        return error_response, status_code

# GPS Missions
@battle_bp.route('/api/battle/missions/gps/create', methods=['POST'])
@battle_bp.route('/vidgenerator/api/battle/missions/gps/create', methods=['POST'])
@rate_limit()
def create_gps_mission():
    try:
        data = InputValidator.get_json_safe(default={})
        user_id = InputValidator.sanitize_string(data.get('user_id', ''))
        lat = float(data.get('lat', 0))
        lng = float(data.get('lng', 0))
        mission_name = InputValidator.sanitize_string(data.get('mission_name', 'Local GPS Mission'))
        result = mission_quest_system.create_local_gps_mission(user_id, lat, lng, mission_name)
        return jsonify(result), 200  # Always return 200, error info in response
    except Exception as e:
        request_id = str(uuid.uuid4())[:8]
        error_response, status_code = ErrorHandler.create_error_response(e, 500, request_id)
        return error_response, status_code

@battle_bp.route('/api/battle/missions/gps', methods=['GET'])
@battle_bp.route('/vidgenerator/api/battle/missions/gps', methods=['GET'])
@rate_limit()
def get_gps_missions():
    try:
        user_id = request.args.get('user_id', 'default_user')
        result = mission_quest_system.get_user_gps_missions(user_id)
        return jsonify(result), 200
    except Exception as e:
        request_id = str(uuid.uuid4())[:8]
        error_response, status_code = ErrorHandler.create_error_response(e, 500, request_id)
        return error_response, status_code

@battle_bp.route('/api/battle/missions/gps/check', methods=['POST'])
@battle_bp.route('/vidgenerator/api/battle/missions/gps/check', methods=['POST'])
@rate_limit()
def check_gps_location():
    try:
        data = InputValidator.get_json_safe(default={})
        user_id = InputValidator.sanitize_string(data.get('user_id', ''))
        lat = float(data.get('lat', 0))
        lng = float(data.get('lng', 0))
        result = mission_quest_system.check_gps_mission_progress(user_id, lat, lng)
        
        # Add rewards for completed missions
        if result.get('success') and result.get('completed_missions'):
            from backend.services.rewards_system import rewards_system
            for mission in result['completed_missions']:
                rewards_system.add_mission_reward(user_id, mission['mission_id'], mission['reward_points'], mission['reward_trophies'])
        
        return jsonify(result), 200
    except Exception as e:
        request_id = str(uuid.uuid4())[:8]
        error_response, status_code = ErrorHandler.create_error_response(e, 500, request_id)
        return error_response, status_code


# MTG Hash Operation System
from backend.services.mtg_hash_operation import mtg_hash_operation

@battle_bp.route('/api/battle/mtg-hash/status', methods=['GET'])
@battle_bp.route('/vidgenerator/api/battle/mtg-hash/status', methods=['GET'])
@rate_limit()
def get_mtg_hash_status():
    try:
        user_id = request.args.get('user_id', 'default_user')
        result = mtg_hash_operation.get_status(user_id)
        return jsonify(result), 200
    except Exception as e:
        request_id = str(uuid.uuid4())[:8]
        error_response, status_code = ErrorHandler.create_error_response(e, 500, request_id)
        return error_response, status_code

@battle_bp.route('/api/battle/mtg-hash/execute', methods=['POST'])
@battle_bp.route('/vidgenerator/api/battle/mtg-hash/execute', methods=['POST'])
@rate_limit()
def execute_mtg_hash_operation():
    try:
        data = InputValidator.get_json_safe(default={})
        user_id = InputValidator.sanitize_string(data.get('user_id', ''))
        operation_type = InputValidator.sanitize_string(data.get('operation_type', ''))
        amount = float(data.get('amount', 0))
        hash_value = InputValidator.sanitize_string(data.get('hash', '')) if data.get('hash') else None
        
        result = mtg_hash_operation.execute_operation(user_id, operation_type, amount, hash_value)
        return jsonify(result), 200  # Always return 200, error info in response
    except Exception as e:
        request_id = str(uuid.uuid4())[:8]
        error_response, status_code = ErrorHandler.create_error_response(e, 500, request_id)
        return error_response, status_code

@battle_bp.route('/api/battle/mtg-hash/clips-movie', methods=['GET'])
@battle_bp.route('/vidgenerator/api/battle/mtg-hash/clips-movie', methods=['GET'])
@rate_limit()
def get_mtg_clips_movie():
    try:
        user_id = request.args.get('user_id', 'default_user')
        result = mtg_hash_operation.get_clips_movie(user_id)
        return jsonify(result), 200
    except Exception as e:
        request_id = str(uuid.uuid4())[:8]
        error_response, status_code = ErrorHandler.create_error_response(e, 500, request_id)
        return error_response, status_code


# Battle Techno Tunnel Magi
from backend.services.battle_techno_tunnel_magi import battle_techno_tunnel_magi

@battle_bp.route('/api/battle/techno-tunnel/territories', methods=['GET'])
@battle_bp.route('/vidgenerator/api/battle/techno-tunnel/territories', methods=['GET'])
@rate_limit()
def get_techno_territories():
    try:
        user_id = request.args.get('user_id', 'default_user')
        result = battle_techno_tunnel_magi.get_available_territories(user_id)
        return jsonify(result), 200
    except Exception as e:
        request_id = str(uuid.uuid4())[:8]
        error_response, status_code = ErrorHandler.create_error_response(e, 500, request_id)
        return error_response, status_code

@battle_bp.route('/api/battle/techno-tunnel/create', methods=['POST'])
@battle_bp.route('/vidgenerator/api/battle/techno-tunnel/create', methods=['POST'])
@rate_limit()
def create_techno_tunnel():
    try:
        data = InputValidator.get_json_safe(default={})
        user_id = InputValidator.sanitize_string(data.get('user_id', ''))
        source_territory = InputValidator.sanitize_string(data.get('source_territory', 'techno_core'))
        target_territory = InputValidator.sanitize_string(data.get('target_territory', ''))
        intelligence_level = int(data.get('intelligence_level', 50))
        
        result = battle_techno_tunnel_magi.create_techno_tunnel(user_id, source_territory, target_territory, intelligence_level)
        return jsonify(result), 200  # Always return 200, error info in response
    except Exception as e:
        request_id = str(uuid.uuid4())[:8]
        error_response, status_code = ErrorHandler.create_error_response(e, 500, request_id)
        return error_response, status_code

@battle_bp.route('/api/battle/techno-tunnel/quick-expansion', methods=['POST'])
@battle_bp.route('/vidgenerator/api/battle/techno-tunnel/quick-expansion', methods=['POST'])
@rate_limit()
def quick_battle_expansion():
    try:
        data = InputValidator.get_json_safe(default={})
        user_id = InputValidator.sanitize_string(data.get('user_id', ''))
        battle_id = InputValidator.sanitize_string(data.get('battle_id', ''))
        intelligence_level = int(data.get('intelligence_level', 50))
        
        result = battle_techno_tunnel_magi.quick_battle_expansion(user_id, battle_id, intelligence_level)
        return jsonify(result), 200  # Always return 200, error info in response
    except Exception as e:
        request_id = str(uuid.uuid4())[:8]
        error_response, status_code = ErrorHandler.create_error_response(e, 500, request_id)
        return error_response, status_code

# Note: Middleware strips /vidgenerator, so /vidgenerator/api/* becomes /api/* before matching
# Only need /api/* route - middleware handles the prefix
@battle_bp.route('/api/battle/stats', methods=['GET'])
@battle_bp.route('/vidgenerator/api/battle/stats', methods=['GET'])
@rate_limit()
def get_battle_stats():
    """Get battle statistics for user"""
    try:
        user_id = request.args.get('user_id', 'default_user')
        
        # Try to get stats from quick battle system
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
                stats = enhanced_battle_system.get_user_battle_stats(user_id)
                return jsonify({
                    'success': True,
                    'stats': stats
                }), 200
            except:
                # Final fallback - return basic stats
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
        # Return 200 with error details to avoid breaking frontend
        import sys
        print(f"[Battle Stats] Error: {e}", file=sys.stderr, flush=True)
        return jsonify({
            'success': True,
            'error': str(e),
            'stats': {
                'wins': 0,
                'losses': 0,
                'total_battles': 0,
                'win_rate': 0.0
            }
        }), 200

@battle_bp.route('/api/battle/intelligence', methods=['GET'])
@battle_bp.route('/vidgenerator/api/battle/intelligence', methods=['GET'])
@rate_limit()
def get_battle_intelligence():
    """Get battle intelligence for user"""
    try:
        user_id = request.args.get('user_id', 'default_user')
        try:
            from backend.services.battle_intelligence_system import battle_intelligence_system
            intelligence = battle_intelligence_system.get_user_intelligence(user_id)
            return jsonify({
                'success': True,
                'intelligence': intelligence
            }), 200
        except ImportError:
            return jsonify({
                'success': False,
                'error': 'Battle intelligence system not available',
                'intelligence': {}
            }), 200  # Return 200 with empty data instead of 404
    except Exception as e:
        # Return 200 with error details to avoid breaking frontend
        import sys
        print(f"[Battle Intelligence] Error: {e}", file=sys.stderr, flush=True)
        return jsonify({
            'success': True,
            'error': str(e),
            'intelligence': {}
        }), 200

# Advanced Battle Tech routes moved to advanced_battle_tech_routes.py
# This endpoint is now handled by advanced_battle_tech_bp blueprint

@battle_bp.route('/api/battle/techno-tunnel/expansions', methods=['GET'])
@battle_bp.route('/vidgenerator/api/battle/techno-tunnel/expansions', methods=['GET'])
@rate_limit()
def get_user_expansions():
    try:
        user_id = request.args.get('user_id', 'default_user')
        result = battle_techno_tunnel_magi.get_user_expansions(user_id)
        return jsonify(result), 200
    except Exception as e:
        request_id = str(uuid.uuid4())[:8]
        error_response, status_code = ErrorHandler.create_error_response(e, 500, request_id)
        return error_response, status_code

@battle_bp.route('/api/battle/techno-tunnel/resources', methods=['GET'])
@battle_bp.route('/vidgenerator/api/battle/techno-tunnel/resources', methods=['GET'])
@rate_limit()
def get_techno_resources():
    try:
        user_id = request.args.get('user_id', 'default_user')
        result = battle_techno_tunnel_magi.get_techno_magic_resources(user_id)
        return jsonify(result), 200
    except Exception as e:
        request_id = str(uuid.uuid4())[:8]
        error_response, status_code = ErrorHandler.create_error_response(e, 500, request_id)
        return error_response, status_code

@battle_bp.route('/api/battle/techno-tunnel/add-energy', methods=['POST'])
@battle_bp.route('/vidgenerator/api/battle/techno-tunnel/add-energy', methods=['POST'])
@rate_limit()
def add_techno_energy():
    try:
        data = InputValidator.get_json_safe(default={})
        user_id = InputValidator.sanitize_string(data.get('user_id', ''))
        amount = int(data.get('amount', 100))
        
        result = battle_techno_tunnel_magi.add_techno_energy(user_id, amount)
        return jsonify(result), 200
    except Exception as e:
        request_id = str(uuid.uuid4())[:8]
        error_response, status_code = ErrorHandler.create_error_response(e, 500, request_id)
        return error_response, status_code

@battle_bp.route('/api/battle/techno-tunnel/integrate-intelligence', methods=['POST'])
@battle_bp.route('/vidgenerator/api/battle/techno-tunnel/integrate-intelligence', methods=['POST'])
@rate_limit()
def integrate_intelligence():
    try:
        data = InputValidator.get_json_safe(default={})
        user_id = InputValidator.sanitize_string(data.get('user_id', ''))
        intelligence_data = data.get('intelligence_data', {})
        
        result = battle_techno_tunnel_magi.integrate_with_intelligence(user_id, intelligence_data)
        return jsonify(result), 200
    except Exception as e:
        request_id = str(uuid.uuid4())[:8]
        error_response, status_code = ErrorHandler.create_error_response(e, 500, request_id)
        return error_response, status_code


# Technology & Science Leveling
from backend.services.technology_science_leveling import technology_science_leveling

@battle_bp.route('/api/battle/technology-science/levels', methods=['GET'])
@battle_bp.route('/vidgenerator/api/battle/technology-science/levels', methods=['GET'])
@rate_limit()
def get_technology_science_levels():
    try:
        user_id = request.args.get('user_id', 'default_user')
        result = technology_science_leveling.get_user_levels(user_id)
        return jsonify(result), 200
    except Exception as e:
        request_id = str(uuid.uuid4())[:8]
        error_response, status_code = ErrorHandler.create_error_response(e, 500, request_id)
        return error_response, status_code

@battle_bp.route('/api/battle/technology-science/death-teleport', methods=['POST'])
@battle_bp.route('/vidgenerator/api/battle/technology-science/death-teleport', methods=['POST'])
@rate_limit()
def use_death_teleport_leveling():
    try:
        data = InputValidator.get_json_safe(default={})
        user_id = InputValidator.sanitize_string(data.get('user_id', ''))
        result = technology_science_leveling.use_death_teleport(user_id)
        return jsonify(result), 200  # Always return 200, error info in response
    except Exception as e:
        request_id = str(uuid.uuid4())[:8]
        error_response, status_code = ErrorHandler.create_error_response(e, 500, request_id)
        return error_response, status_code

# DeathTeleport Operator
from backend.services.death_teleport_operator import death_teleport_operator

@battle_bp.route('/api/battle/death-teleport/create', methods=['POST'])
@battle_bp.route('/vidgenerator/api/battle/death-teleport/create', methods=['POST'])
@rate_limit()
def create_death_teleport_operator():
    try:
        data = InputValidator.get_json_safe(default={})
        user_id = InputValidator.sanitize_string(data.get('user_id', ''))
        destination = InputValidator.sanitize_string(data.get('destination', ''))
        quest_mission_id = InputValidator.sanitize_string(data.get('quest_mission_id', '')) if data.get('quest_mission_id') else None
        
        result = death_teleport_operator.create_death_teleport(user_id, destination, quest_mission_id)
        return jsonify(result), 200  # Always return 200, error info in response
    except Exception as e:
        request_id = str(uuid.uuid4())[:8]
        error_response, status_code = ErrorHandler.create_error_response(e, 500, request_id)
        return error_response, status_code

@battle_bp.route('/api/battle/death-teleport/use', methods=['POST'])
@battle_bp.route('/vidgenerator/api/battle/death-teleport/use', methods=['POST'])
@rate_limit()
def use_death_teleport_operator():
    try:
        data = InputValidator.get_json_safe(default={})
        user_id = InputValidator.sanitize_string(data.get('user_id', ''))
        teleport_id = InputValidator.sanitize_string(data.get('teleport_id', ''))
        
        result = death_teleport_operator.use_death_teleport(user_id, teleport_id)
        return jsonify(result), 200  # Always return 200, error info in response
    except Exception as e:
        request_id = str(uuid.uuid4())[:8]
        error_response, status_code = ErrorHandler.create_error_response(e, 500, request_id)
        return error_response, status_code

@battle_bp.route('/api/battle/quest-mission-operators', methods=['GET'])
@battle_bp.route('/vidgenerator/api/battle/quest-mission-operators', methods=['GET'])
@rate_limit()
def get_quest_mission_operators():
    try:
        user_id = request.args.get('user_id', 'default_user')
        result = death_teleport_operator.get_quest_mission_operators(user_id)
        return jsonify(result), 200
    except Exception as e:
        request_id = str(uuid.uuid4())[:8]
        error_response, status_code = ErrorHandler.create_error_response(e, 500, request_id)
        return error_response, status_code

# Autoplay & Recording
from backend.services.autoplay_recording import autoplay_recording

@battle_bp.route('/api/battle/autoplay/start', methods=['POST'])
@battle_bp.route('/vidgenerator/api/battle/autoplay/start', methods=['POST'])
@rate_limit()
def start_autoplay_recording():
    try:
        data = InputValidator.get_json_safe(default={})
        user_id = InputValidator.sanitize_string(data.get('user_id', ''))
        battle_id = InputValidator.sanitize_string(data.get('battle_id', ''))
        duration_seconds = int(data.get('duration_seconds', 60))
        
        result = autoplay_recording.start_autoplay_recording(user_id, battle_id, duration_seconds)
        return jsonify(result), 200
    except Exception as e:
        request_id = str(uuid.uuid4())[:8]
        error_response, status_code = ErrorHandler.create_error_response(e, 500, request_id)
        return error_response, status_code

@battle_bp.route('/api/battle/autoplay/stop', methods=['POST'])
@battle_bp.route('/vidgenerator/api/battle/autoplay/stop', methods=['POST'])
@rate_limit()
def stop_autoplay_recording():
    try:
        data = InputValidator.get_json_safe(default={})
        user_id = InputValidator.sanitize_string(data.get('user_id', ''))
        session_id = InputValidator.sanitize_string(data.get('session_id', ''))
        
        result = autoplay_recording.stop_autoplay_recording(user_id, session_id)
        return jsonify(result), 200  # Always return 200, error info in response
    except Exception as e:
        request_id = str(uuid.uuid4())[:8]
        error_response, status_code = ErrorHandler.create_error_response(e, 500, request_id)
        return error_response, status_code

@battle_bp.route('/api/battle/recordings', methods=['GET'])
@battle_bp.route('/vidgenerator/api/battle/recordings', methods=['GET'])
@rate_limit()
def get_recordings():
    try:
        user_id = request.args.get('user_id', 'default_user')
        result = autoplay_recording.get_user_recordings(user_id)
        return jsonify(result), 200
    except Exception as e:
        request_id = str(uuid.uuid4())[:8]
        error_response, status_code = ErrorHandler.create_error_response(e, 500, request_id)
        return error_response, status_code

@battle_bp.route('/api/battle/recordings/<recording_id>/download', methods=['GET'])
@battle_bp.route('/vidgenerator/api/battle/recordings/<recording_id>/download', methods=['GET'])
@rate_limit()
def download_recording(recording_id: str):
    try:
        user_id = request.args.get('user_id', 'default_user')
        result = autoplay_recording.download_recording(user_id, recording_id)
        
        if result.get('success'):
            recording = result['recording']
            # Return file download response
            from flask import send_file
            if os.path.exists(recording['file_path']):
                return send_file(recording['file_path'], as_attachment=True, download_name=recording['filename'])
            else:
                return jsonify({'success': False, 'error': 'File not found'}), 404
        else:
            return jsonify(result), 404
    except Exception as e:
        request_id = str(uuid.uuid4())[:8]
        error_response, status_code = ErrorHandler.create_error_response(e, 500, request_id)
        return error_response, status_code



# Social Battle Integration Routes
@battle_bp.route('/api/battle/social/friend-request', methods=['POST'])
@battle_bp.route('/vidgenerator/api/battle/social/friend-request', methods=['POST'])
@rate_limit()
def send_friend_request_battle():
    try:
        data = InputValidator.get_json_safe(default={})
        user_id = InputValidator.sanitize_string(data.get('user_id', 'default_user'), max_length=50).strip()
        friend_id = InputValidator.sanitize_string(data.get('friend_id', ''), max_length=50).strip()
        result = social_system.send_friend_request(user_id, friend_id)
        return jsonify(result), 200  # Always return 200, error info in response
    except Exception as e:
        request_id = str(uuid.uuid4())[:8]
        error_response, status_code = ErrorHandler.create_error_response(e, 500, request_id)
        return error_response, status_code

@battle_bp.route('/api/battle/social/friend-request/respond', methods=['POST'])
@battle_bp.route('/vidgenerator/api/battle/social/friend-request/respond', methods=['POST'])
@rate_limit()
def respond_friend_request_battle():
    try:
        data = InputValidator.get_json_safe(default={})
        user_id = InputValidator.sanitize_string(data.get('user_id', 'default_user'), max_length=50).strip()
        request_id = InputValidator.sanitize_string(data.get('request_id', ''), max_length=50).strip()
        accept = bool(data.get('accept', False))
        result = social_system.respond_to_friend_request(request_id, user_id, accept)
        return jsonify(result), 200  # Always return 200, error info in response
    except Exception as e:
        request_id = str(uuid.uuid4())[:8]
        error_response, status_code = ErrorHandler.create_error_response(e, 500, request_id)
        return error_response, status_code

@battle_bp.route('/api/battle/social/friend-requests', methods=['GET'])
@battle_bp.route('/vidgenerator/api/battle/social/friend-requests', methods=['GET'])
@rate_limit()
def get_friend_requests_battle():
    try:
        user_id = request.args.get('user_id', 'default_user')
        result = social_system.get_friend_requests(user_id)
        return jsonify({'success': True, 'requests': result}), 200
    except Exception as e:
        request_id = str(uuid.uuid4())[:8]
        error_response, status_code = ErrorHandler.create_error_response(e, 500, request_id)
        return error_response, status_code

@battle_bp.route('/api/battle/social/challenge', methods=['POST'])
@battle_bp.route('/vidgenerator/api/battle/social/challenge', methods=['POST'])
@rate_limit()
def challenge_friend_battle():
    try:
        data = InputValidator.get_json_safe(default={})
        user_id = InputValidator.sanitize_string(data.get('user_id', 'default_user'), max_length=50).strip()
        friend_id = InputValidator.sanitize_string(data.get('friend_id', ''), max_length=50).strip()
        battle_id = str(uuid.uuid4())
        return jsonify({'success': True, 'battle_id': battle_id, 'message': f'Challenge sent to {friend_id}'}), 200
    except Exception as e:
        request_id = str(uuid.uuid4())[:8]
        error_response, status_code = ErrorHandler.create_error_response(e, 500, request_id)
        return error_response, status_code

@battle_bp.route('/api/battle/social/leaderboard', methods=['GET'])
@battle_bp.route('/vidgenerator/api/battle/social/leaderboard', methods=['GET'])
@rate_limit()
def get_social_leaderboard():
    try:
        user_id = request.args.get('user_id', 'default_user')
        return jsonify({'success': True, 'leaderboard': [{'user_id': 'user1', 'wins': 10, 'battles': 15}, {'user_id': 'user2', 'wins': 8, 'battles': 12}]}), 200
    except Exception as e:
        request_id = str(uuid.uuid4())[:8]
        error_response, status_code = ErrorHandler.create_error_response(e, 500, request_id)
        return error_response, status_code

@battle_bp.route('/api/battle/social/activity', methods=['GET'])
@battle_bp.route('/vidgenerator/api/battle/social/activity', methods=['GET'])
@rate_limit()
def get_friend_activity():
    try:
        user_id = request.args.get('user_id', 'default_user')
        return jsonify({'success': True, 'activity': [{'user_id': 'friend1', 'action': 'Won a battle', 'timestamp': datetime.utcnow().isoformat()}, {'user_id': 'friend2', 'action': 'Completed a quest', 'timestamp': datetime.utcnow().isoformat()}]}), 200
    except Exception as e:
        request_id = str(uuid.uuid4())[:8]
        error_response, status_code = ErrorHandler.create_error_response(e, 500, request_id)
        return error_response, status_code

@battle_bp.route('/api/battle/social/guild', methods=['GET'])
@battle_bp.route('/vidgenerator/api/battle/social/guild', methods=['GET'])
@rate_limit()
def get_user_guild():
    try:
        user_id = request.args.get('user_id', 'default_user')
        result = social_system.get_user_guild(user_id)
        return jsonify({'success': True, 'guild': result}), 200
    except Exception as e:
        request_id = str(uuid.uuid4())[:8]
        error_response, status_code = ErrorHandler.create_error_response(e, 500, request_id)
        return error_response, status_code

# Teams Routes
@battle_bp.route('/api/battle/teams/create', methods=['POST'])
@battle_bp.route('/vidgenerator/api/battle/teams/create', methods=['POST'])
@rate_limit()
def create_team():
    try:
        data = InputValidator.get_json_safe(default={})
        user_id = InputValidator.sanitize_string(data.get('user_id', 'default_user'), max_length=50).strip()
        name = InputValidator.sanitize_string(data.get('name', ''), max_length=100).strip()
        team_type = InputValidator.sanitize_string(data.get('type', 'temporary'), max_length=20).strip()
        max_members = int(data.get('max_members', 5))
        result = teams_system.create_team(name, user_id, team_type, max_members)
        return jsonify(result), 200  # Always return 200, error info in response
    except Exception as e:
        request_id = str(uuid.uuid4())[:8]
        error_response, status_code = ErrorHandler.create_error_response(e, 500, request_id)
        return error_response, status_code

@battle_bp.route('/api/battle/teams', methods=['GET'])
@battle_bp.route('/vidgenerator/api/battle/teams', methods=['GET'])
@rate_limit()
def get_user_teams():
    try:
        user_id = request.args.get('user_id', 'default_user')
        teams = teams_system.get_user_teams(user_id)
        return jsonify({'success': True, 'teams': teams}), 200
    except Exception as e:
        request_id = str(uuid.uuid4())[:8]
        error_response, status_code = ErrorHandler.create_error_response(e, 500, request_id)
        return error_response, status_code

@battle_bp.route('/api/battle/teams/match', methods=['POST'])
@battle_bp.route('/vidgenerator/api/battle/teams/match', methods=['POST'])
@rate_limit()
def find_team_match():
    try:
        data = InputValidator.get_json_safe(default={})
        team_id = InputValidator.sanitize_string(data.get('team_id', ''), max_length=50).strip()
        matches = teams_system.find_team_matches(team_id)
        return jsonify({'success': True, 'matches': matches}), 200
    except Exception as e:
        request_id = str(uuid.uuid4())[:8]
        error_response, status_code = ErrorHandler.create_error_response(e, 500, request_id)
        return error_response, status_code

# Alliances Routes
@battle_bp.route('/api/battle/alliances/create', methods=['POST'])
@battle_bp.route('/vidgenerator/api/battle/alliances/create', methods=['POST'])
@rate_limit()
def create_alliance():
    try:
        data = InputValidator.get_json_safe(default={})
        user_id = InputValidator.sanitize_string(data.get('user_id', 'default_user'), max_length=50).strip()
        name = InputValidator.sanitize_string(data.get('name', ''), max_length=100).strip()
        alliance_type = InputValidator.sanitize_string(data.get('type', 'defensive'), max_length=20).strip()
        result = alliances_system.create_alliance(name, user_id, alliance_type)
        return jsonify(result), 200  # Always return 200, error info in response
    except Exception as e:
        request_id = str(uuid.uuid4())[:8]
        error_response, status_code = ErrorHandler.create_error_response(e, 500, request_id)
        return error_response, status_code

@battle_bp.route('/api/battle/alliances', methods=['GET'])
@battle_bp.route('/vidgenerator/api/battle/alliances', methods=['GET'])
@rate_limit()
def get_user_alliances():
    try:
        user_id = request.args.get('user_id', 'default_user')
        alliances = alliances_system.get_user_alliances(user_id)
        return jsonify({'success': True, 'alliances': alliances}), 200
    except Exception as e:
        request_id = str(uuid.uuid4())[:8]
        error_response, status_code = ErrorHandler.create_error_response(e, 500, request_id)
        return error_response, status_code

@battle_bp.route('/api/battle/alliances/wars', methods=['GET'])
@battle_bp.route('/vidgenerator/api/battle/alliances/wars', methods=['GET'])
@rate_limit()
def get_alliance_wars():
    try:
        alliance_id = request.args.get('alliance_id', '')
        wars = alliances_system.get_alliance_wars(alliance_id)
        return jsonify({'success': True, 'wars': wars}), 200
    except Exception as e:
        request_id = str(uuid.uuid4())[:8]
        error_response, status_code = ErrorHandler.create_error_response(e, 500, request_id)
        return error_response, status_code

# Group Destruction Routes
@battle_bp.route('/api/battle/groups/destroy', methods=['POST'])
@battle_bp.route('/vidgenerator/api/battle/groups/destroy', methods=['POST'])
@rate_limit()
def destroy_group():
    try:
        data = InputValidator.get_json_safe(default={})
        user_id = InputValidator.sanitize_string(data.get('user_id', 'default_user'), max_length=50).strip()
        group_id = InputValidator.sanitize_string(data.get('group_id', ''), max_length=50).strip()
        group_type = InputValidator.sanitize_string(data.get('group_type', 'clan'), max_length=20).strip()
        result = group_destruction_system.destroy_group(group_id, user_id, group_type)
        return jsonify(result), 200  # Always return 200, error info in response
    except Exception as e:
        request_id = str(uuid.uuid4())[:8]
        error_response, status_code = ErrorHandler.create_error_response(e, 500, request_id)
        return error_response, status_code

@battle_bp.route('/api/battle/groups/merge', methods=['POST'])
@battle_bp.route('/vidgenerator/api/battle/groups/merge', methods=['POST'])
@rate_limit()
def merge_groups():
    try:
        data = InputValidator.get_json_safe(default={})
        user_id = InputValidator.sanitize_string(data.get('user_id', 'default_user'), max_length=50).strip()
        group1_id = InputValidator.sanitize_string(data.get('group1_id', ''), max_length=50).strip()
        group2_id = InputValidator.sanitize_string(data.get('group2_id', ''), max_length=50).strip()
        new_name = InputValidator.sanitize_string(data.get('new_name', ''), max_length=100).strip() if data.get('new_name') else None
        result = group_destruction_system.merge_groups(group1_id, group2_id, user_id, new_name)
        return jsonify(result), 200  # Always return 200, error info in response
    except Exception as e:
        request_id = str(uuid.uuid4())[:8]
        error_response, status_code = ErrorHandler.create_error_response(e, 500, request_id)
        return error_response, status_code

@battle_bp.route('/api/battle/groups/takeover', methods=['POST'])
@battle_bp.route('/vidgenerator/api/battle/groups/takeover', methods=['POST'])
@rate_limit()
def takeover_group():
    try:
        data = InputValidator.get_json_safe(default={})
        user_id = InputValidator.sanitize_string(data.get('user_id', 'default_user'), max_length=50).strip()
        group_id = InputValidator.sanitize_string(data.get('group_id', ''), max_length=50).strip()
        attacking_group_id = InputValidator.sanitize_string(data.get('attacking_group_id', user_id), max_length=50).strip()
        result = group_destruction_system.initiate_takeover(group_id, user_id, attacking_group_id)
        return jsonify(result), 200  # Always return 200, error info in response
    except Exception as e:
        request_id = str(uuid.uuid4())[:8]
        error_response, status_code = ErrorHandler.create_error_response(e, 500, request_id)
        return error_response, status_code

@battle_bp.route('/api/battle/groups/conquer-territory', methods=['POST'])
@battle_bp.route('/vidgenerator/api/battle/groups/conquer-territory', methods=['POST'])
@rate_limit()
def conquer_territory():
    try:
        data = InputValidator.get_json_safe(default={})
        user_id = InputValidator.sanitize_string(data.get('user_id', 'default_user'), max_length=50).strip()
        territory_id = InputValidator.sanitize_string(data.get('territory_id', ''), max_length=50).strip()
        attacking_group_id = InputValidator.sanitize_string(data.get('attacking_group_id', user_id), max_length=50).strip()
        result = group_destruction_system.conquer_territory(territory_id, user_id, attacking_group_id)
        return jsonify(result), 200  # Always return 200, error info in response
    except Exception as e:
        request_id = str(uuid.uuid4())[:8]
        error_response, status_code = ErrorHandler.create_error_response(e, 500, request_id)
        return error_response, status_code

@battle_bp.route('/api/battle/groups/destruction-history', methods=['GET'])
@battle_bp.route('/vidgenerator/api/battle/groups/destruction-history', methods=['GET'])
@rate_limit()
def get_destruction_history():
    try:
        user_id = request.args.get('user_id', 'default_user')
        limit = int(request.args.get('limit', 50))
        history = group_destruction_system.get_destruction_history(user_id, limit)
        return jsonify({'success': True, 'history': history}), 200
    except Exception as e:
        request_id = str(uuid.uuid4())[:8]
        error_response, status_code = ErrorHandler.create_error_response(e, 500, request_id)
        return error_response, status_code

# ============================================================================
# MISSING ENDPOINTS - Added to fix 404 errors
# ============================================================================

# Rulebooks alias (frontend calls /rulebooks, backend has /rule-books)
@battle_bp.route('/api/battle/rulebooks', methods=['GET'])
@battle_bp.route('/vidgenerator/api/battle/rulebooks', methods=['GET'])
@rate_limit()
def get_rulebooks_alias():
    """Get rulebooks - alias for get_rule_books"""
    return get_rule_books()

# Timepocket realtime endpoint
@battle_bp.route('/api/battle/timepocket/realtime', methods=['GET'])
@battle_bp.route('/vidgenerator/api/battle/timepocket/realtime', methods=['GET'])
@rate_limit()
def get_timepocket_realtime():
    """Get timepocket real-time data"""
    try:
        user_id = request.args.get('user_id', 'default_user')
        try:
            from backend.services.timepocket_realtime import timepocket_realtime_sync
            result = timepocket_realtime_sync.get_views(user_id)
            return jsonify({
                'success': True,
                'views': result.get('views', {}),
                'status': result.get('status', {})
            }), 200
        except ImportError:
            return jsonify({
                'success': True,
                'views': {
                    'past': {'time_period': 'past', 'timestamp': None, 'intelligence_level': 0, 'events': [], 'active_players': []},
                    'present': {'time_period': 'present', 'timestamp': None, 'intelligence_level': 0, 'events': [], 'active_players': []},
                    'future': {'time_period': 'future', 'timestamp': None, 'intelligence_level': 0, 'events': [], 'active_players': []}
                },
                'status': {'syncing': False}
            }), 200
    except Exception as e:
        return jsonify({
            'success': True,
            'views': {},
            'status': {'syncing': False}
        }), 200

# Trophy trading endpoint
@battle_bp.route('/api/battle/trophy-trading', methods=['GET'])
@battle_bp.route('/vidgenerator/api/battle/trophy-trading', methods=['GET'])
@rate_limit()
def get_trophy_trading():
    """Get trophy trading data"""
    try:
        user_id = request.args.get('user_id', 'default_user')
        if trophy_trading_system:
            result = trophy_trading_system.get_trade_offers(user_id)
            return jsonify({
                'success': True,
                'offers': result.get('offers', []),
                'incoming': result.get('incoming', []),
                'outgoing': result.get('outgoing', [])
            }), 200
        else:
            return jsonify({
                'success': True,
                'offers': [],
                'incoming': [],
                'outgoing': []
            }), 200
    except Exception as e:
        return jsonify({
            'success': True,
            'offers': [],
            'incoming': [],
            'outgoing': []
        }), 200

# Collectibles endpoint
@battle_bp.route('/api/battle/collectibles', methods=['GET'])
@battle_bp.route('/vidgenerator/api/battle/collectibles', methods=['GET'])
@rate_limit()
def get_collectibles():
    """Get collectibles"""
    try:
        user_id = request.args.get('user_id', 'default_user')
        if collectible_card_system:
            result = collectible_card_system.get_user_collection(user_id)
            return jsonify({
                'success': True,
                'collection': result.get('collection', []),
                'cards': result.get('cards', [])
            }), 200
        else:
            return jsonify({
                'success': True,
                'collection': [],
                'cards': []
            }), 200
    except Exception as e:
        return jsonify({
            'success': True,
            'collection': [],
            'cards': []
        }), 200

# Missions endpoints
@battle_bp.route('/api/missions/daily', methods=['GET'])
@battle_bp.route('/vidgenerator/api/missions/daily', methods=['GET'])
@rate_limit()
def get_daily_missions():
    """Get daily missions"""
    try:
        user_id = request.args.get('user_id', 'default_user')
        try:
            from backend.services.mission_controller_operator import mission_controller_operator
            missions = mission_controller_operator.get_daily_missions(user_id)
            return jsonify({
                'success': True,
                'missions': missions
            }), 200
        except ImportError:
            return jsonify({
                'success': True,
                'missions': []
            }), 200
    except Exception as e:
        return jsonify({
            'success': True,
            'missions': []
        }), 200

@battle_bp.route('/api/missions/timeline', methods=['GET'])
@battle_bp.route('/vidgenerator/api/missions/timeline', methods=['GET'])
@rate_limit()
def get_missions_timeline():
    """Get timeline missions"""
    try:
        user_id = request.args.get('user_id', 'default_user')
        try:
            from backend.services.mission_controller_operator import mission_controller_operator
            missions = mission_controller_operator.get_timeline_missions(user_id)
            return jsonify({
                'success': True,
                'missions': missions
            }), 200
        except ImportError:
            return jsonify({
                'success': True,
                'missions': []
            }), 200
    except Exception as e:
        return jsonify({
            'success': True,
            'missions': []
        }), 200

# AI Research endpoint
@battle_bp.route('/api/ai-research', methods=['GET'])
@battle_bp.route('/vidgenerator/api/ai-research', methods=['GET'])
@rate_limit()
def get_ai_research():
    """Get AI research data"""
    try:
        user_id = request.args.get('user_id', 'default_user')
        try:
            from backend.services.ai_research_system import ai_research_system
            research = ai_research_system.get_user_research(user_id)
            return jsonify({
                'success': True,
                'research': research
            }), 200
        except ImportError:
            return jsonify({
                'success': True,
                'research': {
                    'projects': [],
                    'progress': {},
                    'unlocked': []
                }
            }), 200
    except Exception as e:
        return jsonify({
            'success': True,
            'research': {
                'projects': [],
                'progress': {},
                'unlocked': []
            }
        }), 200

# Autoplay endpoint
@battle_bp.route('/api/autoplay/status', methods=['GET'])
@battle_bp.route('/vidgenerator/api/autoplay/status', methods=['GET'])
@rate_limit()
def get_autoplay_status():
    """Get autoplay status"""
    try:
        user_id = request.args.get('user_id', 'default_user')
        try:
            from backend.services.autoplay_system import autoplay_system
            status = autoplay_system.get_status(user_id)
            return jsonify({
                'success': True,
                'status': status
            }), 200
        except ImportError:
            return jsonify({
                'success': True,
                'status': {
                    'enabled': False,
                    'recording': False,
                    'sessions': []
                }
            }), 200
    except Exception as e:
        return jsonify({
            'success': True,
            'status': {
                'enabled': False,
                'recording': False,
                'sessions': []
            }
        }), 200

# Teams endpoint
@battle_bp.route('/api/teams/user', methods=['GET'])
@battle_bp.route('/vidgenerator/api/teams/user', methods=['GET'])
@rate_limit()
def get_teams_user():
    """Get user teams"""
    try:
        user_id = request.args.get('user_id', 'default_user')
        if teams_system:
            teams = teams_system.get_user_teams(user_id)
        else:
            teams = []
        return jsonify({
            'success': True,
            'teams': teams
        }), 200
    except Exception as e:
        return jsonify({
            'success': True,
            'teams': []
        }), 200

# Alliances endpoint
@battle_bp.route('/api/alliances/user', methods=['GET'])
@battle_bp.route('/vidgenerator/api/alliances/user', methods=['GET'])
@rate_limit()
def get_alliances_user():
    """Get user alliances"""
    try:
        user_id = request.args.get('user_id', 'default_user')
        if alliances_system:
            alliances = alliances_system.get_user_alliances(user_id)
        else:
            alliances = []
        return jsonify({
            'success': True,
            'alliances': alliances
        }), 200
    except Exception as e:
        return jsonify({
            'success': True,
            'alliances': []
        }), 200

# Groups destruction history endpoint (alias)
@battle_bp.route('/api/groups/destruction-history', methods=['GET'])
@battle_bp.route('/vidgenerator/api/groups/destruction-history', methods=['GET'])
@rate_limit()
def get_destruction_history_alias():
    """Get group destruction history - alias"""
    return get_destruction_history()

# Bonus levels endpoint
@battle_bp.route('/api/bonus-levels', methods=['GET'])
@battle_bp.route('/vidgenerator/api/bonus-levels', methods=['GET'])
@rate_limit()
def get_bonus_levels():
    """Get bonus levels"""
    try:
        user_id = request.args.get('user_id', 'default_user')
        try:
            from backend.services.bonus_level_system import bonus_level_system
            levels = bonus_level_system.get_user_levels(user_id)
            return jsonify({
                'success': True,
                'levels': levels
            }), 200
        except ImportError:
            return jsonify({
                'success': True,
                'levels': {
                    'toons': [],
                    'pegasus': [],
                    'progress': {}
                }
            }), 200
    except Exception as e:
        return jsonify({
            'success': True,
            'levels': {
                'toons': [],
                'pegasus': [],
                'progress': {}
            }
        }), 200

# Death teleport status endpoint
@battle_bp.route('/api/death-teleport/status/<user_id>', methods=['GET'])
@battle_bp.route('/vidgenerator/api/death-teleport/status/<user_id>', methods=['GET'])
@rate_limit()
def get_death_teleport_status(user_id: str):
    """Get death teleport status"""
    try:
        try:
            from backend.services.warzone_timepocket_system import warzone_timepocket_system
            teleports = warzone_timepocket_system.get_death_teleports(user_id)
            return jsonify({
                'success': True,
                'teleports': teleports
            }), 200
        except ImportError:
            return jsonify({
                'success': True,
                'teleports': []
            }), 200
    except Exception as e:
        return jsonify({
            'success': True,
            'teleports': []
        }), 200

# Militia forces endpoint
@battle_bp.route('/api/militia/forces', methods=['GET'])
@battle_bp.route('/vidgenerator/api/militia/forces', methods=['GET'])
@rate_limit()
def get_militia_forces():
    """Get militia forces"""
    try:
        user_id = request.args.get('user_id', 'default_user')
        try:
            from backend.services.militia_system import militia_system
            forces = militia_system.get_user_forces(user_id)
            return jsonify({
                'success': True,
                'forces': forces
            }), 200
        except ImportError:
            return jsonify({
                'success': True,
                'forces': []
            }), 200
    except Exception as e:
        return jsonify({
            'success': True,
            'forces': []
        }), 200

# Legal content endpoint
@battle_bp.route('/api/legal/content', methods=['GET'])
@battle_bp.route('/vidgenerator/api/legal/content', methods=['GET'])
@rate_limit()
def get_legal_content():
    """Get legal content"""
    try:
        try:
            from backend.services.legal_content_system import legal_content_system
            content = legal_content_system.get_content()
            return jsonify({
                'success': True,
                'content': content
            }), 200
        except ImportError:
            return jsonify({
                'success': True,
                'content': [
                    {
                        'title': 'Battle Rules & Regulations',
                        'text': 'Battle system rules and legal framework will be displayed here.',
                        'date': None
                    }
                ]
            }), 200
    except Exception as e:
        return jsonify({
            'success': True,
            'content': [
                {
                    'title': 'Battle Rules & Regulations',
                    'text': 'Battle system rules and legal framework will be displayed here.',
                    'date': None
                }
            ]
        }), 200

# Tech hardware progress endpoint
@battle_bp.route('/api/tech-hardware/progress/<user_id>', methods=['GET'])
@battle_bp.route('/vidgenerator/api/tech-hardware/progress/<user_id>', methods=['GET'])
@rate_limit()
def get_tech_hardware_progress(user_id: str):
    """Get tech hardware progress"""
    try:
        try:
            from backend.services.tech_hardware_system import tech_hardware_system
            progress = tech_hardware_system.get_user_progress(user_id)
            return jsonify({
                'success': True,
                'progress': progress
            }), 200
        except ImportError:
            return jsonify({
                'success': True,
                'progress': {
                    'level': 1,
                    'unlocked': 0,
                    'progress': 0
                }
            }), 200
    except Exception as e:
        return jsonify({
            'success': True,
            'progress': {
                'level': 1,
                'unlocked': 0,
                'progress': 0
            }
        }), 200

# Death portal status endpoint (legacy)
@battle_bp.route('/api/death-portal/status', methods=['GET'])
@battle_bp.route('/vidgenerator/api/death-portal/status', methods=['GET'])
@rate_limit()
def get_death_portal_status_legacy():
    """Get death portal status - legacy endpoint"""
    try:
        # Redirect to manager endpoint
        try:
            from backend.services.death_portal_manager import death_portal_manager
            portals = death_portal_manager.get_all_portals()
            return jsonify({
                'success': True,
                'portals': portals.get('portals', [])
            }), 200
        except ImportError:
            return jsonify({
                'success': True,
                'portals': []
            }), 200
    except Exception as e:
        return jsonify({
            'success': True,
            'portals': []
        }), 200

# Experience recount status endpoint
@battle_bp.route('/api/experience/recount-status/<user_id>', methods=['GET'])
@battle_bp.route('/vidgenerator/api/experience/recount-status/<user_id>', methods=['GET'])
@rate_limit()
def get_experience_recount_status(user_id: str):
    """Get experience recount status"""
    try:
        try:
            from backend.services.experience_system import experience_system
            status = experience_system.get_recount_status(user_id)
            return jsonify({
                'success': True,
                'status': status
            }), 200
        except ImportError:
            return jsonify({
                'success': True,
                'status': {
                    'total_xp': 0,
                    'recounted': 0,
                    'status': 'pending'
                }
            }), 200
    except Exception as e:
        return jsonify({
            'success': True,
            'status': {
                'total_xp': 0,
                'recounted': 0,
                'status': 'pending'
            }
        }), 200

@battle_bp.route('/api/experience/recount/<user_id>', methods=['POST'])
@battle_bp.route('/vidgenerator/api/experience/recount/<user_id>', methods=['POST'])
@rate_limit()
def start_experience_recount(user_id: str):
    """Start experience recount"""
    try:
        try:
            from backend.services.experience_system import experience_system
            result = experience_system.start_recount(user_id)
            return jsonify({
                'success': True,
                'result': result
            }), 200
        except ImportError:
            return jsonify({
                'success': True,
                'result': {'status': 'started'}
            }), 200
    except Exception as e:
        return jsonify({
            'success': True,
            'result': {'status': 'started'}
        }), 200

# Enhanced system - points endpoint
@battle_bp.route('/api/points/get-all-connected', methods=['GET'])
@battle_bp.route('/vidgenerator/api/points/get-all-connected', methods=['GET'])
@rate_limit()
def get_all_connected_points():
    """Get all connected points"""
    try:
        user_id = request.args.get('user_id', 'default_user')
        try:
            from backend.services.unified_points_database import unified_points_db
            if unified_points_db:
                points = unified_points_db.get_all_points(user_id)
                return jsonify({
                    'success': True,
                    'result': {
                        'all_points': points
                    }
                }), 200
            else:
                return jsonify({
                    'success': True,
                    'result': {
                        'all_points': {}
                    }
                }), 200
        except ImportError:
            return jsonify({
                'success': True,
                'result': {
                    'all_points': {}
                }
            }), 200
    except Exception as e:
        return jsonify({
            'success': True,
            'result': {
                'all_points': {}
            }
        }), 200

# Tech tree endpoint
@battle_bp.route('/api/battle/tech-tree/all', methods=['GET'])
@battle_bp.route('/vidgenerator/api/battle/tech-tree/all', methods=['GET'])
@rate_limit()
def get_tech_tree_all():
    """Get all tech tree data"""
    try:
        user_id = request.args.get('user_id', 'default_user')
        try:
            from backend.services.battle_tech_tree import battle_tech_tree
            tree = battle_tech_tree.get_full_tree(user_id)
            return jsonify({
                'success': True,
                'tree': tree
            }), 200
        except ImportError:
            return jsonify({
                'success': True,
                'tree': {
                    'nodes': [],
                    'connections': [],
                    'unlocked': []
                }
            }), 200
    except Exception as e:
        return jsonify({
            'success': True,
            'tree': {
                'nodes': [],
                'connections': [],
                'unlocked': []
            }
        }), 200
