"""
Hunters Game Routes
API endpoints for the Hunters Game leveling system, rewards, star map, specials, rulebook V.2
All endpoints resolve user_id via session > query > identification.
"""
from flask import Blueprint, jsonify, request
import json
import os
from datetime import datetime, date, timedelta
from typing import Dict, Optional
from sqlalchemy import text

_BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _resolve_uid() -> str:
    try:
        from backend.services.account_resolution_service import resolve_user_id
        return resolve_user_id(from_body=True, from_query=True)
    except Exception:
        return request.args.get('user_id', 'default_user')

# Try to import db from different locations
try:
    from src.db.models import db
except ImportError:
    try:
        from vidgenerator.src.db.models import db
    except ImportError:
        try:
            from flask_sqlalchemy import SQLAlchemy
            from flask import current_app
            db = SQLAlchemy()
        except ImportError:
            # Fallback - will need to handle db access differently
            db = None

hunters_game_bp = Blueprint('hunters_game', __name__)


def _default_level_info():
    """Default level info when db unavailable or outside app context."""
    return {
        'current_level': 1,
        'current_xp': 0,
        'total_xp': 0,
        'xp_to_next_level': 1000,
        'level_progress': 0.0,
        'title': 'Novice Hunter',
        'prestige_level': 0,
        'stat_creativity': 0,
        'stat_efficiency': 0,
        'stat_quality': 0,
        'stat_social': 0,
        'stat_knowledge': 0,
        'available_stat_points': 0
    }


# Helper function to get user level info
def get_user_level_info(user_id):
    """Get user level information from database. Safe when called outside app/request context."""
    # Only touch DB when we have both app and request context (avoids worker crash / 502)
    try:
        from flask import has_app_context, has_request_context
        if not has_app_context() or not has_request_context():
            return _default_level_info()
    except Exception:
        return _default_level_info()
    try:
        if not db:
            return _default_level_info()
        result = db.session.execute(
            text("SELECT * FROM player_levels WHERE user_id = :user_id"),
            {'user_id': user_id}
        )
        row = result.fetchone()
        
        if row:
            return {
                'current_level': row[1],
                'current_xp': row[2],
                'total_xp': row[3],
                'xp_to_next_level': row[4],
                'level_progress': float(row[5]) if row[5] else 0.0,
                'title': row[6],
                'prestige_level': row[7],
                'stat_creativity': row[8],
                'stat_efficiency': row[9],
                'stat_quality': row[10],
                'stat_social': row[11],
                'stat_knowledge': row[12],
                'available_stat_points': row[13]
            }
        else:
            # Create default entry
            db.session.execute(
                text("""INSERT INTO player_levels 
                   (user_id, current_level, current_xp, total_xp, xp_to_next_level, level_progress, title)
                   VALUES (:user_id, 1, 0, 0, 1000, 0.0, 'Novice Hunter')"""),
                {'user_id': user_id}
            )
            db.session.commit()
            return _default_level_info()
    except Exception:
        # Return default on any error (context, db, etc.) - never print or re-raise
        return _default_level_info()


# Helper function to check if user has claimed a reward
def has_claimed_reward(user_id, reward_id):
    """Check if user has already claimed a reward"""
    try:
        result = db.session.execute(
            text("SELECT COUNT(*) FROM user_rewards WHERE user_id = :user_id AND reward_id = :reward_id"),
            {'user_id': user_id, 'reward_id': reward_id}
        )
        return result.scalar() > 0
    except:
        return False


# Existing endpoints (stubs - implement as needed)
@hunters_game_bp.route('/api/game/hunters/level', methods=['GET'])
def get_level():
    """Get player level information"""
    user_id = _resolve_uid()
    level_info = get_user_level_info(user_id)
    
    if level_info:
        return jsonify({
            'success': True,
            'level_info': level_info
        })
    else:
        return jsonify({
            'success': False,
            'error': 'Failed to get level info'
        }), 500


@hunters_game_bp.route('/api/game/hunters/rewards', methods=['GET'])
def get_rewards():
    """Get rewards for user"""
    user_id = _resolve_uid()
    level = request.args.get('level', type=int)
    
    try:
        # Get user level if not provided
        if not level:
            level_info = get_user_level_info(user_id)
            level = level_info['current_level'] if level_info else 1
        
        # Build query
        query = "SELECT * FROM rewards WHERE 1=1"
        params = {}
        
        if level:
            query += " AND (level_required IS NULL OR level_required <= :level)"
            params['level'] = level
        
        query += " ORDER BY level_required ASC, points_required ASC"
        
        result = db.session.execute(text(query), params)
        rows = result.fetchall()
        
        rewards = []
        for row in rows:
            # Check if user has claimed this reward
            claimed = has_claimed_reward(user_id, row[0])
            
            # Determine if reward is available
            available = False
            if row[2] == 'level':  # reward_type
                available = (row[4] is None or row[4] <= level) and not claimed
            elif row[2] == 'points':  # reward_type
                # Need to check point values - for now assume available if not claimed
                available = not claimed
            
            reward_data = {}
            if row[7]:  # reward_data
                try:
                    reward_data = json.loads(row[7])
                except:
                    pass
            
            rewards.append({
                'id': row[0],
                'type': row[2],  # reward_type
                'name': row[3],  # reward_name
                'description': row[4] if len(row) > 4 else None,  # reward_description
                'level_required': row[5] if len(row) > 5 else None,  # level_required
                'points_required': row[6] if len(row) > 6 else None,  # points_required
                'point_type': row[7] if len(row) > 7 else None,  # point_type
                'icon': row[9] if len(row) > 9 else '🎁',  # icon
                'available': available,
                'claimed': claimed,
                'reward_data': reward_data
            })
        
        return jsonify({
            'success': True,
            'rewards': rewards
        })
    except Exception as e:
        print(f"Error getting rewards: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# NEW ENDPOINTS FOR POINTS PAGE

@hunters_game_bp.route('/api/game/hunters/rewards/next', methods=['GET'])
def get_next_reward():
    """Get next available reward for a point type"""
    point_type = request.args.get('point_type')
    current_value = request.args.get('current_value', type=int, default=0)
    
    if not point_type:
        return jsonify({
            'success': False,
            'error': 'point_type parameter required'
        }), 400
    
    try:
        # Find next reward for this point type
        query = """
            SELECT * FROM rewards 
            WHERE reward_type = 'points' 
            AND point_type = :point_type
            AND points_required > :current_value
            ORDER BY points_required ASC
            LIMIT 1
        """
        
        result = db.session.execute(text(query), {
            'point_type': point_type,
            'current_value': current_value
        })
        row = result.fetchone()
        
        if row:
            reward_data = {}
            if row[7]:  # reward_data
                try:
                    reward_data = json.loads(row[7])
                except:
                    pass
            
            return jsonify({
                'success': True,
                'next_reward': {
                    'id': row[0],
                    'name': row[3],  # reward_name
                    'points_required': row[6],  # points_required
                    'description': row[4] if len(row) > 4 else None,  # reward_description
                    'icon': row[9] if len(row) > 9 else '🎁',  # icon
                    'reward_data': reward_data
                }
            })
        else:
            return jsonify({
                'success': True,
                'next_reward': None
            })
    except Exception as e:
        print(f"Error getting next reward: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@hunters_game_bp.route('/api/game/hunters/rewards/by-points', methods=['GET'])
def get_rewards_by_points():
    """Get rewards available for a point type"""
    point_type = request.args.get('point_type')
    current_value = request.args.get('current_value', type=int, default=0)
    user_id = _resolve_uid()
    
    if not point_type:
        return jsonify({
            'success': False,
            'error': 'point_type parameter required'
        }), 400
    
    try:
        # Get all rewards for this point type
        query = """
            SELECT * FROM rewards 
            WHERE reward_type = 'points' 
            AND point_type = :point_type
            ORDER BY points_required ASC
        """
        
        result = db.session.execute(text(query), {'point_type': point_type})
        rows = result.fetchall()
        
        rewards = []
        for row in rows:
            claimed = has_claimed_reward(user_id, row[0])
            available = (row[6] is None or row[6] <= current_value) and not claimed
            
            reward_data = {}
            if row[7]:  # reward_data
                try:
                    reward_data = json.loads(row[7])
                except:
                    pass
            
            rewards.append({
                'id': row[0],
                'name': row[3],  # reward_name
                'description': row[4] if len(row) > 4 else None,  # reward_description
                'points_required': row[6],  # points_required
                'icon': row[9] if len(row) > 9 else '🎁',  # icon
                'available': available,
                'claimed': claimed,
                'reward_data': reward_data
            })
        
        return jsonify({
            'success': True,
            'rewards': rewards
        })
    except Exception as e:
        print(f"Error getting rewards by points: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@hunters_game_bp.route('/api/game/hunters/rewards/claim', methods=['POST'])
def claim_reward():
    """Claim a reward"""
    data = request.get_json()
    user_id = data.get('user_id', 'default_user')
    reward_id = data.get('reward_id')
    
    if not reward_id:
        return jsonify({
            'success': False,
            'error': 'reward_id required'
        }), 400
    
    try:
        # Check if already claimed
        if has_claimed_reward(user_id, reward_id):
            return jsonify({
                'success': False,
                'error': 'Reward already claimed'
            }), 400
        
        # Get reward info
        result = db.session.execute(
            text("SELECT * FROM rewards WHERE id = :reward_id"),
            {'reward_id': reward_id}
        )
        reward = result.fetchone()
        
        if not reward:
            return jsonify({
                'success': False,
                'error': 'Reward not found'
            }), 404
        
        # Check if user meets requirements
        level_info = get_user_level_info(user_id)
        
        # Check level requirement
        if reward[5] and level_info and reward[5] > level_info['current_level']:
            return jsonify({
                'success': False,
                'error': f'Level {reward[5]} required'
            }), 400
        
        # Check points requirement
        if reward[6] and reward[7]:  # points_required and point_type
            points_required = reward[6]
            point_type = reward[7]
            
            try:
                # Get user's current points from unified points system
                from backend.services.unified_points_database import unified_points_db
                user_points_data = unified_points_db.get_all_points(user_id)
                
                if user_points_data and user_points_data.get('success'):
                    # Get points for the specific point type
                    systems = user_points_data.get('systems', {})
                    current_points = 0
                    
                    # Map point_type to system name
                    point_type_mapping = {
                        'xp': 'xp_total',
                        'generation': 'generation_points',
                        'battle': 'battle_points',
                        'social': 'social_points',
                        'achievement': 'achievement_points',
                        'trophy': 'trophy_points',
                        'milestone': 'milestone_points'
                    }
                    
                    system_name = point_type_mapping.get(point_type.lower(), point_type.lower() + '_points')
                    
                    # Try to get points from systems dict
                    if system_name in systems:
                        current_points = int(systems[system_name] or 0)
                    elif point_type.lower() == 'xp':
                        # For XP, use xp_total from top level
                        current_points = int(user_points_data.get('xp_total', 0))
                    
                    # Check if user has enough points
                    if current_points < points_required:
                        return jsonify({
                            'success': False,
                            'error': f'{points_required} {point_type} points required (you have {current_points})'
                        }), 400
            except Exception as e:
                # If we can't get points, log but don't block (graceful degradation)
                print(f"Warning: Could not check points requirement: {e}")
                # For now, allow claiming if level requirement is met
                # This maintains backward compatibility
        
        # Claim the reward
        db.session.execute(
            text("""INSERT INTO user_rewards (user_id, reward_id, claimed_at)
               VALUES (:user_id, :reward_id, :claimed_at)"""),
            {
                'user_id': user_id,
                'reward_id': reward_id,
                'claimed_at': datetime.utcnow()
            }
        )
        
        # Apply reward data (stat points, themes, etc.)
        reward_data = {}
        if reward[7]:  # reward_data
            try:
                reward_data = json.loads(reward[7])
            except:
                pass
        
        # Apply stat points if any
        if 'stat_points' in reward_data and level_info:
            new_points = level_info['available_stat_points'] + reward_data['stat_points']
            db.session.execute(
                text("UPDATE player_levels SET available_stat_points = :points WHERE user_id = :user_id"),
                {'points': new_points, 'user_id': user_id}
            )
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Reward claimed successfully',
            'reward_data': reward_data
        })
    except Exception as e:
        db.session.rollback()
        print(f"Error claiming reward: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@hunters_game_bp.route('/api/game/hunters/xp-history', methods=['GET'])
def get_xp_history():
    """Get XP history for a user"""
    user_id = _resolve_uid()
    source = request.args.get('source')
    limit = request.args.get('limit', type=int, default=50)
    
    try:
        query = "SELECT * FROM xp_history WHERE user_id = :user_id"
        params = {'user_id': user_id}
        
        if source:
            query += " AND source = :source"
            params['source'] = source
        
        query += " ORDER BY created_at DESC LIMIT :limit"
        params['limit'] = limit
        
        result = db.session.execute(text(query), params)
        rows = result.fetchall()
        
        history = []
        for row in rows:
            metadata = {}
            if row[5]:  # metadata
                try:
                    metadata = json.loads(row[5])
                except:
                    pass
            
            history.append({
                'id': row[0],
                'xp_amount': row[2],
                'source': row[3],
                'action_type': row[4],
                'metadata': metadata,
                'level_before': row[6],
                'level_after': row[7],
                'created_at': row[8].isoformat() if row[8] else None
            })
        
        return jsonify({
            'success': True,
            'history': history
        })
    except Exception as e:
        print(f"Error getting XP history: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# Award XP function for unified points system
def award_xp(user_id: str, points: Dict, **kwargs) -> Dict:
    """Award XP and points to unified points system.

    Optional kwargs: xp_source, xp_action_type (for xp_history rows; defaults
    preserve legacy agent_trigger / points_awarded behavior).
    """
    xp_source = kwargs.get('xp_source') or 'agent_trigger'
    xp_action_type = kwargs.get('xp_action_type') or 'points_awarded'
    try:
        if not db:
            return {
                'success': False,
                'error': 'Database not available'
            }
        
        # Get current level info
        level_info = get_user_level_info(user_id)
        if not level_info:
            return {
                'success': False,
                'error': 'Could not get level info'
            }
        
        # Calculate XP to award
        xp_amount = points.get('xp', 0)
        generation_points = points.get('generation_points', 0)
        battle_points = points.get('battle_points', 0)
        
        # Update XP
        new_xp = level_info['current_xp'] + xp_amount
        new_total_xp = level_info['total_xp'] + xp_amount
        
        # Calculate level
        level = level_info['current_level']
        xp_for_next = 1000 * (level ** 1.5)  # Exponential leveling
        
        level_up = False
        new_level = level
        
        while new_xp >= xp_for_next:
            new_xp -= xp_for_next
            new_level += 1
            level_up = True
            xp_for_next = 1000 * (new_level ** 1.5)
        
        # Update database
        db.session.execute(
            text("""UPDATE player_levels 
               SET current_xp = :xp, total_xp = :total_xp, current_level = :level
               WHERE user_id = :user_id"""),
            {
                'xp': new_xp,
                'total_xp': new_total_xp,
                'level': new_level,
                'user_id': user_id
            }
        )
        
        # Record in XP history
        db.session.execute(
            text("""INSERT INTO xp_history 
               (user_id, xp_amount, source, action_type, level_before, level_after)
               VALUES (:user_id, :xp_amount, :source, :action_type, :level_before, :level_after)"""),
            {
                'user_id': user_id,
                'xp_amount': xp_amount,
                'source': xp_source,
                'action_type': xp_action_type,
                'level_before': level,
                'level_after': new_level
            }
        )
        
        db.session.commit()
        
        if level_up:
            try:
                from backend.services.activity_events_service import emit
                emit(
                    "hunter_level_up",
                    user_id=user_id,
                    channel="game",
                    text=f"Level {new_level}",
                    payload={"level": new_level, "xp_awarded": xp_amount},
                )
            except Exception:
                pass

        try:
            from backend.services.ai_user_controller import on_user_activity
            on_user_activity(user_id, "xp_earned", {"amount": xp_amount, "level": new_level, "leveled_up": level_up})
        except Exception:
            pass

        # Record agent activity for the XP award; agents follow user action and win with them
        try:
            from backend.services.agent_db_service import agent_db_service
            from backend.services.user_agent_skills import user_agent_skills
            _skills_data = user_agent_skills.get_user_skills(user_id)
            _assigned = _skills_data.get('assigned_agents', [])
            _agent = next((a for a in _assigned if 'learning' in a or 'battle' in a), _assigned[0] if _assigned else None)
            if _agent:
                _action = 'level_up' if level_up else 'skill_execution'
                agent_db_service.record_agent_activity(
                    user_id=user_id, agent_id=_agent,
                    action=_action, skill='award_xp',
                    xp_gained=xp_amount,
                    points_gained=generation_points + battle_points,
                    metadata={'level': new_level, 'level_up': level_up}
                )
                # Agent followed user action; when user levels up, agent wins with them (nice and easy)
                agent_db_service.record_user_action_followed(
                    user_id=user_id, agent_id=_agent,
                    user_action='xp_earned',
                    win=level_up,
                    xp_on_win=25,
                    points_on_win=5.0,
                    metadata={'xp_amount': xp_amount, 'new_level': new_level},
                )
        except Exception:
            pass

        return {
            'success': True,
            'xp_awarded': xp_amount,
            'total_xp': new_total_xp,
            'level': new_level,
            'leveled_up': level_up,
            'generation_points': generation_points,
            'battle_points': battle_points
        }
        
    except Exception as e:
        if db:
            db.session.rollback()
        return {
            'success': False,
            'error': str(e)
        }


# Additional stub endpoints (implement as needed)
@hunters_game_bp.route('/api/game/hunters/profile', methods=['GET'])
def get_profile():
    """Get complete player profile"""
    user_id = _resolve_uid()
    level_info = get_user_level_info(user_id)
    
    return jsonify({
        'success': True,
        'profile': {
            'user_id': user_id,
            'leveling': level_info
        }
    })


@hunters_game_bp.route('/api/game/hunters/stats', methods=['GET'])
def get_stats():
    """Get player stats"""
    user_id = _resolve_uid()
    level_info = get_user_level_info(user_id)
    
    if level_info:
        return jsonify({
            'success': True,
            'stats': {
                'creativity': level_info['stat_creativity'],
                'efficiency': level_info['stat_efficiency'],
                'quality': level_info['stat_quality'],
                'social': level_info['stat_social'],
                'knowledge': level_info['stat_knowledge']
            },
            'available_stat_points': level_info['available_stat_points']
        })
    else:
        return jsonify({
            'success': False,
            'error': 'Failed to get stats'
        }), 500


@hunters_game_bp.route('/api/game/hunters/specials', methods=['GET'])
def get_hunters_specials():
    """Get specials for hunters game (run_verification, run_dna_test, view_star_map)."""
    specials = ["run_verification", "run_dna_test", "view_star_map"]
    return jsonify({"success": True, "specials": specials})


@hunters_game_bp.route('/api/game/hunters/rulebook', methods=['GET'])
def get_hunters_rulebook():
    """Get Rulebook V.2 with 19 theme-based spells, sectored."""
    p = os.path.join(_BASE_DIR, "data", "hunters_rulebook_v2.json")
    if os.path.exists(p):
        with open(p, "r", encoding="utf-8") as f:
            data = json.load(f)
        return jsonify({"success": True, "rulebook": data})
    return jsonify({"success": False, "error": "Rulebook not found"}), 404


@hunters_game_bp.route('/api/game/hunters/stories', methods=['GET'])
def get_hunters_stories():
    """Get Hunters stories (campaigns, one-shots): Winter Wedding, time reversal, medieval, power combos."""
    p = os.path.join(_BASE_DIR, "data", "hunters_stories.json")
    if os.path.exists(p):
        try:
            with open(p, "r", encoding="utf-8") as f:
                data = json.load(f)
            return jsonify({"success": True, "stories": data})
        except Exception as e:
            return jsonify({"success": False, "error": str(e)}), 500
    return jsonify({"success": False, "error": "Stories not found"}), 404


@hunters_game_bp.route('/api/game/hunters/effect-clusters', methods=['GET'])
def get_effect_clusters():
    """Effect clusters to enhance Trophy Hunters game."""
    clusters = {
        "galactic": ["view_star_map", "proxima_b_beacon", "sirius_b_pulse", "earth_b_shield", "starmap25_investigate", "starmap25_view"],
        "verification": ["run_verification", "run_dna_test", "integrity_scan"],
        "combat": ["trophy_strike", "hunter_fury", "precision_shot"],
        "support": ["heal_trophy", "buff_creativity", "buff_knowledge"],
        "utility": ["clickthrough", "extend_session", "checkpoint", "aggregator_fill", "geo_reference", "speaker_ruler"],
        "medieval": ["winter_wedding_aura", "contract_seal", "jarls_fury", "skald_chant"],
        "time_reversal": ["rewind_turn", "narrative_rewind", "checkpoint"],
        "power_combos": ["contract_seal_jarls_fury", "poison_revealed_son_smuggled", "infiltrator_knight_berserker"],
    }
    return jsonify({"success": True, "effect_clusters": clusters})


@hunters_game_bp.route('/api/game/hunters/award-game-points', methods=['POST'])
def award_game_points():
    """Award game_points to unified points system (Trophy Hunters game)."""
    try:
        data = request.get_json() or {}
        user_id = _resolve_uid()
        amount = float(data.get('amount', data.get('points', 0)))
        source = data.get('source', 'hunters_game')
        meta = data.get('metadata', {})
        if amount <= 0:
            return jsonify({'success': True, 'user_id': user_id, 'amount': 0, 'message': 'No-op'}), 200
        from backend.services.unified_points_database import unified_points_db
        r = unified_points_db.add_points(user_id, 'game_points', amount, source=source, metadata=meta)
        try:
            from backend.services.unified_points_sync import unified_points_sync_device
            unified_points_sync_device.record_domain_sync('game')
        except Exception:
            pass
        return jsonify(r), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


def _get_geo_ref(user_id: str):
    """Get latest geo_ref for user: tries agent_geo_refs (DB), then user location service (file)."""
    if db:
        try:
            r = db.session.execute(
                text("SELECT latitude, longitude, geo_ref FROM agent_geo_refs WHERE user_id = :uid ORDER BY updated_at DESC LIMIT 1"),
                {"uid": user_id},
            )
            row = r.fetchone()
            if row:
                return {"latitude": row[0], "longitude": row[1], "geo_ref": row[2]}
        except Exception:
            pass
    try:
        from backend.services.user_location_service import user_location_service
        loc = user_location_service.get_location(user_id)
        if loc and (loc.get("latitude") is not None or loc.get("geo_ref")):
            return {"latitude": loc.get("latitude"), "longitude": loc.get("longitude"), "geo_ref": loc.get("geo_ref") or ""}
    except Exception:
        pass
    return None


@hunters_game_bp.route('/api/game/hunters/geo-ref', methods=['GET'])
def get_geo_ref():
    """Get GPS/geo reference for user (profile)."""
    user_id = _resolve_uid()
    g = _get_geo_ref(user_id)
    return jsonify({"success": True, "user_id": user_id, "geo_ref": g}), 200


@hunters_game_bp.route('/api/game/hunters/geo-ref', methods=['POST'])
def upsert_geo_ref():
    """Upsert GPS/geo reference for user (profile). Writes to DB when available and to user location service."""
    try:
        data = request.get_json() or {}
        user_id = data.get('user_id', _resolve_uid())
        lat = data.get('latitude')
        lon = data.get('longitude')
        geo_ref = data.get('geo_ref', '')
        # Always update the new user location system (file-backed)
        try:
            from backend.services.user_location_service import user_location_service
            user_location_service.update_location(
                user_id, latitude=lat, longitude=lon, geo_ref=geo_ref or None, source="manual"
            )
        except Exception:
            pass
        if db:
            db.session.execute(
                text("""
                    INSERT INTO agent_geo_refs (user_id, latitude, longitude, geo_ref, updated_at)
                    VALUES (:uid, :lat, :lon, :gr, CURRENT_TIMESTAMP)
                """),
                {"uid": user_id, "lat": lat, "lon": lon, "gr": geo_ref or ""},
            )
            db.session.commit()
        return jsonify({"success": True, "user_id": user_id, "geo_ref": _get_geo_ref(user_id)}), 200
    except Exception as e:
        if db:
            db.session.rollback()
        return jsonify({"success": False, "error": str(e)}), 500


@hunters_game_bp.route('/api/game/hunters/profiling', methods=['GET'])
def get_hunters_profiling():
    """Profiling for hunters game: agent_tech, specials, geo_ref."""
    user_id = _resolve_uid()
    level_info = get_user_level_info(user_id) if db else None
    specials = ['run_verification', 'run_dna_test', 'view_star_map']
    geo_ref = _get_geo_ref(user_id)
    return jsonify({
        'success': True,
        'user_id': user_id,
        'profiling': {
            'agent_tech_enabled': True,
            'specials': specials,
            'level_info': level_info,
            'geo_ref': geo_ref,
        },
    })


def _snapshot_points_subset(user_id: str) -> Dict:
    """Slice of unified points for Game ↔ Battle bridge (no heavy systems dump)."""
    out: Dict = {
        'xp_total': 0,
        'level': 1,
        'coins': 0,
        'battle_points': 0,
        'game_points': 0,
        'activity_points': 0,
        'trophy_points': 0,
    }
    try:
        from backend.services.unified_points_database import unified_points_db
        if not unified_points_db or not hasattr(unified_points_db, 'get_all_points'):
            return out
        res = unified_points_db.get_all_points(user_id)
        if not isinstance(res, dict) or not res.get('success'):
            return out
        payload = res.get('points')
        if not isinstance(payload, dict):
            return out

        def _gi(key: str, default: int = 0) -> int:
            try:
                return int(float(payload.get(key, default) or default))
            except (TypeError, ValueError):
                return default

        out['xp_total'] = _gi('xp_total', 0)
        out['level'] = max(1, _gi('level', 1))
        out['coins'] = _gi('coins', 0)
        out['battle_points'] = _gi('battle_points', 0)
        out['game_points'] = _gi('game_points', 0)
        out['activity_points'] = _gi('activity_points', 0)
        out['trophy_points'] = _gi('trophy_points', 0)
    except Exception:
        pass
    return out


def _derive_game_battle_persona(level_info: Optional[Dict], battle_stats: Dict, points_subset: Dict) -> Dict:
    """Lightweight playstyle fingerprint from hunter stat allocation + arena outcomes."""
    li = level_info or {}
    c = int(li.get('stat_creativity') or 0)
    e = int(li.get('stat_efficiency') or 0)
    q = int(li.get('stat_quality') or 0)
    soc = int(li.get('stat_social') or 0)
    k = int(li.get('stat_knowledge') or 0)
    pairs = [
        ('Creative duelist', c),
        ('Efficiency tactician', e),
        ('Quality marksman', q),
        ('Social rally captain', soc),
        ('Knowledge archivist', k),
    ]
    pairs.sort(key=lambda x: -x[1])
    primary = pairs[0][0] if pairs and pairs[0][1] > 0 else 'Balanced newcomer'

    bs = battle_stats or {}
    total_b = int(bs.get('total_battles') or 0)
    wr = float(bs.get('win_rate') or 0)
    bp = int(bs.get('battle_points') or 0)
    if total_b < 2:
        arena = 'Arena cadet — a few skirmishes will sharpen your battle card.'
    elif wr >= 58.0:
        arena = 'Bold arena tempo — wins trending above noise.'
    elif wr <= 38.0 and total_b >= 4:
        arena = 'Measured learner — losses traded for matchup intel.'
    else:
        arena = 'Steady competitor — even win profile.'

    gp = int((points_subset or {}).get('game_points') or 0)
    hxp = int((points_subset or {}).get('xp_total') or 0)
    readiness = min(100, int(wr) + min(35, max(0, bp // 15)) + min(25, max(0, gp // 120)))

    return {
        'archetype': primary,
        'arena_voice': arena,
        'signals': {
            'creativity': c,
            'efficiency': e,
            'quality': q,
            'social': soc,
            'knowledge': k,
        },
        'readiness_score': readiness,
        'cross_link_hint': 'Trophy hunts and quests advance hunter XP; quick battles add battle points and bonus hunter XP.',
        'hunter_xp_track': hxp,
        'game_points_track': gp,
    }


@hunters_game_bp.route('/api/game/hunters/battle-bridge-snapshot', methods=['GET'])
def battle_bridge_snapshot():
    """Unified snapshot for Game + Battle pages: hunter row, battle row, points slice, derived persona."""
    user_id = _resolve_uid()
    level_info = get_user_level_info(user_id)
    pts = _snapshot_points_subset(user_id)
    battle: Dict = {}
    try:
        from backend.routes.battle_routes import _get_battle_stats
        battle = _get_battle_stats(user_id) or {}
    except Exception:
        battle = {}
    persona = _derive_game_battle_persona(level_info, battle, pts)
    hunter_stats = None
    if level_info:
        hunter_stats = {
            'creativity': level_info.get('stat_creativity', 0),
            'efficiency': level_info.get('stat_efficiency', 0),
            'quality': level_info.get('stat_quality', 0),
            'social': level_info.get('stat_social', 0),
            'knowledge': level_info.get('stat_knowledge', 0),
            'available_stat_points': level_info.get('available_stat_points', 0),
        }
    lab_prog = {
        'researched_count': 0, 'total': 25, 'researched_ids': [], 'bonuses_claimed': 0,
        'lab_tier': 'Novice', 'exploration_count': 0, 'explore_ready': True, 'explore_cooldown_remaining_sec': 0,
    }
    try:
        from backend.routes.lab_routes import lab_public_summary
        lab_prog = lab_public_summary(user_id)
    except Exception:
        pass
    return jsonify({
        'success': True,
        'user_id': user_id,
        'hunter': {
            'level': level_info.get('current_level', 1) if level_info else 1,
            'title': level_info.get('title', 'Novice Hunter') if level_info else 'Novice Hunter',
            'total_xp': level_info.get('total_xp', 0) if level_info else 0,
            'stats': hunter_stats,
        },
        'battle': battle,
        'points': pts,
        'persona': persona,
        'lab_chapter2': lab_prog,
        'lab_progress': lab_prog,
    }), 200


@hunters_game_bp.route('/api/game/competitive-loops', methods=['GET'])
def game_competitive_loops():
    """Seasonal competitive loop summary: reset clock, weekly challenges, retention cohort, reward previews."""
    try:
        user_id = _resolve_uid()
        pts = _snapshot_points_subset(user_id)
        level_info = get_user_level_info(user_id)
        today = date.today()
        week_start = today - timedelta(days=today.weekday())
        next_reset = week_start + timedelta(days=7)
        season_id = request.args.get('season_id') or f"season-{today.year}-w{today.isocalendar().week:02d}"
        battle = {}
        try:
            from backend.routes.battle_routes import _get_battle_stats
            battle = _get_battle_stats(user_id) or {}
        except Exception:
            battle = {}

        xp_total = int(pts.get('xp_total') or 0)
        game_points = int(pts.get('game_points') or 0)
        battle_points = int(pts.get('battle_points') or 0)
        trophy_points = int(pts.get('trophy_points') or 0)
        total_battles = int(battle.get('wins', 0) or 0) + int(battle.get('losses', 0) or 0)
        level = int((level_info or {}).get('current_level') or pts.get('level') or 1)

        weekly_challenges = [
            {
                "id": "weekly_xp_1000",
                "name": "Earn 1,000 XP",
                "progress": min(xp_total, 1000),
                "target": 1000,
                "reward_preview": {"xp_total": 250, "game_points": 50},
            },
            {
                "id": "weekly_battle_3",
                "name": "Run 3 Battles",
                "progress": min(total_battles, 3),
                "target": 3,
                "reward_preview": {"battle_points": 120, "xp_total": 200},
            },
            {
                "id": "weekly_starmap_push",
                "name": "Push Star Map Progress",
                "progress": min(game_points // 100, 5),
                "target": 5,
                "reward_preview": {"game_points": 150, "trophy_points": 25},
            },
        ]
        for challenge in weekly_challenges:
            challenge["progress_percent"] = min(100, int((challenge["progress"] / challenge["target"]) * 100))
            challenge["completed"] = challenge["progress"] >= challenge["target"]

        if xp_total >= 10000 or total_battles >= 10:
            cohort = "core_competitor"
        elif xp_total >= 2500 or total_battles >= 3:
            cohort = "returning_player"
        elif xp_total > 0 or game_points > 0:
            cohort = "activated_player"
        else:
            cohort = "new_player"

        reward_previews = [
            {"id": "next_level", "label": "Next Level Bonus", "unlock_hint": f"Reach level {level + 1}", "preview": {"stats_points": 1, "xp_boost": "small"}},
            {"id": "season_rank", "label": "Season Rank Push", "unlock_hint": "Climb weekly leaderboard", "preview": {"battle_points": 75, "badge": "weekly contender"}},
            {"id": "starmap_route", "label": "Star Map Route Cache", "unlock_hint": "Invest, build, and secure systems", "preview": {"game_points": 120, "mn2_bonus": "eligible via Star Map crypto"}},
        ]

        season_score = xp_total + (game_points * 2) + (battle_points * 3) + (trophy_points * 4) + (total_battles * 50)
        return jsonify({
            "success": True,
            "user_id": user_id,
            "season": {
                "id": season_id,
                "week_start": week_start.isoformat(),
                "next_reset": next_reset.isoformat(),
                "score": season_score,
                "leaderboard_hint": "/api/battle/season/%s/leaderboard" % season_id,
            },
            "retention": {
                "cohort": cohort,
                "signals": {
                    "xp_total": xp_total,
                    "game_points": game_points,
                    "battle_count": total_battles,
                    "level": level,
                },
            },
            "weekly_challenges": weekly_challenges,
            "reward_previews": reward_previews,
            "generated_at": datetime.utcnow().isoformat() + "Z",
        }), 200
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@hunters_game_bp.route('/api/game/hunters/aggregator-fulfill', methods=['GET'])
def aggregator_fulfill():
    """Fulfill API: return missing/default Hunter game data (rewards, profile, rulebook refs)."""
    user_id = _resolve_uid()
    rulebook_path = os.path.join(_BASE_DIR, "data", "hunters_rulebook_v2.json")
    rulebook = {}
    if os.path.exists(rulebook_path):
        try:
            with open(rulebook_path, "r", encoding="utf-8") as f:
                rulebook = json.load(f)
        except Exception:
            pass
    star_map_path = os.path.join(_BASE_DIR, "data", "star_map.json")
    star_map = {"stars": [], "specials": ["run_verification", "run_dna_test", "view_star_map"]}
    if os.path.exists(star_map_path):
        try:
            with open(star_map_path, "r", encoding="utf-8") as f:
                star_map = json.load(f)
        except Exception:
            pass
    level_info = get_user_level_info(user_id) if db else None
    geo_ref = _get_geo_ref(user_id)
    default_rewards = [
        {"id": "d1", "name": "First Trophy", "type": "level", "level_required": 1, "icon": "🏆"},
        {"id": "d2", "name": "Star Map Viewer", "type": "points", "points_required": 10, "point_type": "game_points", "icon": "🌟"},
        {"id": "d3", "name": "Verification Pro", "type": "points", "points_required": 25, "point_type": "game_points", "icon": "✔️"},
    ]
    walkthroughs = {}
    guides_data = {}
    stories_ref = {}
    walk_path = os.path.join(_BASE_DIR, "data", "game_walkthroughs.json")
    guides_path = os.path.join(_BASE_DIR, "data", "game_guides.json")
    stories_path = os.path.join(_BASE_DIR, "data", "hunters_stories.json")
    if os.path.exists(walk_path):
        try:
            with open(walk_path, "r", encoding="utf-8") as f:
                walkthroughs = json.load(f)
        except Exception:
            pass
    if os.path.exists(guides_path):
        try:
            with open(guides_path, "r", encoding="utf-8") as f:
                guides_data = json.load(f)
        except Exception:
            pass
    if os.path.exists(stories_path):
        try:
            with open(stories_path, "r", encoding="utf-8") as f:
                stories_ref = json.load(f)
        except Exception:
            pass
    return jsonify({
        "success": True,
        "user_id": user_id,
        "fulfill": {
            "default_rewards": default_rewards,
            "rulebook_ref": rulebook,
            "star_map_ref": {"stars": star_map.get("stars", [])[:7], "specials": star_map.get("specials", [])},
            "level_info": level_info,
            "geo_ref": geo_ref,
            "specials": ["run_verification", "run_dna_test", "view_star_map"],
            "walkthroughs_ref": walkthroughs,
            "guides_ref": guides_data,
            "stories_ref": stories_ref,
        },
    }), 200


@hunters_game_bp.route('/api/game/hunters/walkthroughs', methods=['GET'])
def get_walkthroughs():
    """Get game walkthroughs (play by the rulebook)."""
    p = os.path.join(_BASE_DIR, "data", "game_walkthroughs.json")
    if os.path.exists(p):
        try:
            with open(p, "r", encoding="utf-8") as f:
                data = json.load(f)
            return jsonify({"success": True, "walkthroughs": data}), 200
        except Exception:
            pass
    return jsonify({"success": False, "error": "Walkthroughs not found"}), 404


@hunters_game_bp.route('/api/game/hunters/guides', methods=['GET'])
def get_guides():
    """Get game guides (rulebook-aligned)."""
    p = os.path.join(_BASE_DIR, "data", "game_guides.json")
    if os.path.exists(p):
        try:
            with open(p, "r", encoding="utf-8") as f:
                data = json.load(f)
            return jsonify({"success": True, "guides": data}), 200
        except Exception:
            pass
    return jsonify({"success": False, "error": "Guides not found"}), 404


@hunters_game_bp.route('/api/game/hunters/leaderboard', methods=['GET'])
def get_leaderboard():
    """Get leaderboard"""
    category = request.args.get('category', 'level')
    limit = request.args.get('limit', type=int, default=100)
    
    try:
        if category == 'level':
            query = "SELECT user_id, current_level, total_xp, title FROM player_levels ORDER BY current_level DESC, total_xp DESC LIMIT :limit"
        elif category == 'xp':
            query = "SELECT user_id, current_level, total_xp, title FROM player_levels ORDER BY total_xp DESC LIMIT :limit"
        else:
            query = "SELECT user_id, current_level, total_xp, title FROM player_levels ORDER BY current_level DESC LIMIT :limit"
        
        result = db.session.execute(text(query), {'limit': limit})
        rows = result.fetchall()
        
        leaderboard = []
        for rank, row in enumerate(rows, 1):
            leaderboard.append({
                'rank': rank,
                'user_id': row[0],
                'level': row[1],
                'total_xp': row[2],
                'title': row[3]
            })
        
        return jsonify({
            'success': True,
            'leaderboard': leaderboard
        })
    except Exception as e:
        print(f"Error getting leaderboard: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# --- Nexus arc (data/nexus_arc_levels.json + logs/hunter_nexus_claims) ---


@hunters_game_bp.route("/api/game/hunters/nexus-levels", methods=["GET"])
def nexus_levels_public():
    """Full arc definition for the game client (story, gates, seasons)."""
    try:
        import backend.services.nexus_arc_service as nas

        data = nas.load_nexus_levels_file()
        return jsonify({"success": True, "data": data}), 200
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@hunters_game_bp.route("/api/game/hunters/nexus-state", methods=["GET"])
def nexus_state():
    """Claimed levels + streak, faction, co-op, daily challenge, copilot, trophy echo, shop flags."""
    try:
        import backend.services.nexus_arc_service as nas

        user_id = _resolve_uid()
        doc = nas.load_user_doc(user_id)
        doc = nas.update_streak_on_visit(doc)
        nas.save_user_doc(user_id, doc)

        rewards = nas.build_level_rewards()
        claimed = list(doc.get("claimed") or [])
        order = list(rewards.keys())
        levels = nas.load_nexus_levels_file().get("levels") or []
        today = date.today().isoformat()
        daily = nas.daily_challenge_for_today(user_id)
        copilot = nas.copilot_suggestion(claimed, levels)
        fg = doc.get("faction")
        if fg and "nx_11" in claimed and "nx_12" not in claimed:
            for lv in levels:
                if lv.get("id") != "nx_12":
                    continue
                gates = lv.get("gates") or {}
                if fg in gates:
                    g = gates[fg] or {}
                    gt = g.get("type")
                    if gt == "tab":
                        copilot = {"next_tab": str(g.get("tab")), "reason": "Your path (%s) needs this tab once." % fg}
                    elif gt == "battle_total_min":
                        copilot = {"next_tab": "battle", "reason": "Vanguard: at least one battle on record."}
                    elif gt == "friends_min":
                        copilot = {"next_tab": "social", "reason": "Weaver: add allies until the gate clears."}
                break

        fc = nas.friends_count(user_id)
        bt = nas.battle_total(user_id)

        return jsonify(
            {
                "success": True,
                "user_id": user_id,
                "claimed": claimed,
                "level_ids": order,
                "version": 2,
                "faction": doc.get("faction"),
                "streak_days": int(doc.get("streak_count") or 0),
                "friends_count": fc,
                "battle_total": bt,
                "co_op_progress_pct": min(100, int(100 * fc / 3)) if fc else 0,
                "daily_challenge": daily,
                "daily_bonus_claimed": doc.get("daily_director_redeemed_date") == today,
                "trophy_echo": nas.trophy_story_echo(),
                "copilot": copilot,
                "world_phase": 2 if "nx_10" in claimed else 1,
                "shop_bundle_ch5": "nx_05" in claimed,
                "shop_bundle_ch10": "nx_10" in claimed,
                "shop_bundle_s2": "nx_20" in claimed,
            }
        ), 200
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@hunters_game_bp.route("/api/game/hunters/nexus-blurbs", methods=["GET"])
def nexus_blurbs():
    """Per-level narrative blurbs: OpenAI when configured, else deterministic templates."""
    try:
        import backend.services.nexus_arc_service as nas

        user_id = _resolve_uid()
        ids_raw = (request.args.get("ids") or "").strip()
        level_ids = [x.strip() for x in ids_raw.split(",") if x.strip()]
        if not level_ids:
            data = nas.load_nexus_levels_file()
            level_ids = [str(lv.get("id")) for lv in (data.get("levels") or [])[:12]]
        play_seed = request.args.get("play_seed") or "0"
        mood = request.args.get("mood") or "reflective"
        use_llm = request.args.get("llm", "1").lower() in ("1", "true", "yes")
        result = nas.build_blurbs(user_id, level_ids, play_seed, mood, use_llm)
        return jsonify({"success": True, "user_id": user_id, **result}), 200
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@hunters_game_bp.route("/api/game/hunters/nexus-faction", methods=["POST"])
def nexus_set_faction():
    """Branching paths: pathfinder | vanguard | weaver."""
    try:
        import backend.services.nexus_arc_service as nas

        data = request.get_json() or {}
        user_id = _resolve_uid()
        fac = (data.get("faction") or "").strip().lower()
        if fac not in ("pathfinder", "vanguard", "weaver"):
            return jsonify({"success": False, "error": "invalid_faction"}), 400
        doc = nas.load_user_doc(user_id)
        doc["faction"] = fac
        nas.save_user_doc(user_id, doc)
        return jsonify({"success": True, "user_id": user_id, "faction": fac}), 200
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@hunters_game_bp.route("/api/game/hunters/nexus-daily-complete", methods=["POST"])
def nexus_daily_complete():
    """Daily director bonus: once per calendar day (+20 XP, +15 game_points)."""
    try:
        import backend.services.nexus_arc_service as nas
        from backend.services.unified_points_database import unified_points_db

        user_id = _resolve_uid()
        doc = nas.load_user_doc(user_id)
        today = date.today().isoformat()
        if doc.get("daily_director_redeemed_date") == today:
            return jsonify({"success": True, "already": True, "user_id": user_id}), 200
        doc["daily_director_redeemed_date"] = today
        nas.save_user_doc(user_id, doc)
        meta = {"source": "nexus_daily_director", "day": today}
        unified_points_db.add_points(user_id, "xp_total", 20.0, "nexus_daily", meta)
        unified_points_db.add_points(user_id, "game_points", 15.0, "nexus_daily", meta)
        try:
            from backend.services.unified_points_sync import unified_points_sync_device

            unified_points_sync_device.record_domain_sync("game")
        except Exception:
            pass
        return jsonify({"success": True, "user_id": user_id, "awarded": {"xp_total": 20, "game_points": 15}}), 200
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@hunters_game_bp.route("/api/game/hunters/nexus-claim", methods=["POST"])
def nexus_claim():
    """Claim one Nexus level: xp_total + game_points; sequential; idempotent."""
    try:
        import backend.services.nexus_arc_service as nas
        from backend.services.unified_points_database import unified_points_db

        data = request.get_json() or {}
        user_id = _resolve_uid()
        level_id = (data.get("level_id") or "").strip()
        rewards = nas.build_level_rewards()
        if level_id not in rewards:
            return jsonify({"success": False, "error": "unknown_level", "level_id": level_id}), 400

        doc = nas.load_user_doc(user_id)
        claimed = list(doc.get("claimed") or [])
        if level_id in claimed:
            return jsonify(
                {
                    "success": True,
                    "already_claimed": True,
                    "user_id": user_id,
                    "level_id": level_id,
                    "claimed": claimed,
                }
            ), 200

        order = list(rewards.keys())
        idx = order.index(level_id)
        if idx > 0:
            prev_id = order[idx - 1]
            if prev_id not in claimed:
                return jsonify(
                    {
                        "success": False,
                        "error": "previous_level_required",
                        "required_level_id": prev_id,
                    }
                ), 400

        cfg = rewards[level_id]
        xp_amt = int(cfg.get("xp", 0))
        gp_amt = int(cfg.get("game_points", 0))
        meta = {"level_id": level_id, "arc": "nexus", **(data.get("metadata") or {})}

        rx = unified_points_db.add_points(user_id, "xp_total", float(xp_amt), "nexus_arc", meta)
        rg = unified_points_db.add_points(user_id, "game_points", float(gp_amt), "nexus_arc", meta)

        claimed.append(level_id)
        doc["claimed"] = claimed
        nas.save_user_doc(user_id, doc)
        try:
            from backend.services.unified_points_sync import unified_points_sync_device

            unified_points_sync_device.record_domain_sync("game")
        except Exception:
            pass

        return jsonify(
            {
                "success": True,
                "user_id": user_id,
                "level_id": level_id,
                "awarded": {"xp_total": xp_amt, "game_points": gp_amt},
                "results": {"xp": rx, "game_points": rg},
                "claimed": claimed,
            }
        ), 200
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500
