"""
Debugger Profile Routes
Profile and unified points integration for debugger site
"""
from flask import Blueprint, request, jsonify
from backend.services.unified_points_database import unified_points_db
from backend.services.user_profile import user_profile
from typing import Dict, Optional
import os

debugger_profile_bp = Blueprint('debugger_profile', __name__)


@debugger_profile_bp.route('/api/debugger/profile/points', methods=['GET'])
def get_profile_points():
    """Get user profile with unified points"""
    try:
        user_id = request.args.get('user_id', 'default_user')
        
        # Get all points
        points_result = unified_points_db.get_all_points(user_id)
        
        if not points_result.get('success'):
            return jsonify({
                'success': False,
                'error': 'Failed to get points'
            }), 500
        
        points = points_result.get('points', {})
        
        # Get profile data
        try:
            profile_data = user_profile.get_user_profile(user_id)
        except:
            profile_data = {}
        
        return jsonify({
            'success': True,
            'user_id': user_id,
            'points': points,
            'profile': profile_data,
            'summary': {
                'level': points.get('level', 1),
                'xp_total': points.get('xp_total', 0),
                'coins': points.get('coins', 0),
                'credits': points.get('credits', 0),
                'battle_points': points.get('battle_points', 0),
                'social_points': points.get('social_points', 0)
            }
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@debugger_profile_bp.route('/api/debugger/profile/add-points', methods=['POST'])
def add_profile_points():
    """Add points to user profile"""
    try:
        data = request.get_json() or {}
        user_id = data.get('user_id', 'default_user')
        point_type = data.get('point_type', 'xp')
        amount = float(data.get('amount', 0))
        source = data.get('source', 'debugger')
        
        if amount == 0:
            return jsonify({
                'success': False,
                'error': 'Amount must be greater than 0'
            }), 400
        
        result = unified_points_db.add_points(
            user_id=user_id,
            point_type=point_type,
            amount=amount,
            source=source,
            metadata={'debugger_action': 'manual_add'}
        )
        
        return jsonify(result)
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@debugger_profile_bp.route('/api/debugger/profile/stats', methods=['GET'])
def get_profile_stats():
    """Get comprehensive profile statistics"""
    try:
        user_id = request.args.get('user_id', 'default_user')
        
        # Get points
        points_result = unified_points_db.get_all_points(user_id)
        points = points_result.get('points', {}) if points_result.get('success') else {}
        
        # Calculate stats
        stats = {
            'user_id': user_id,
            'level': points.get('level', 1),
            'xp_total': points.get('xp_total', 0),
            'xp_to_next_level': (points.get('level', 1) * 1000) - (points.get('xp_total', 0) % 1000),
            'total_points': sum([
                points.get('coins', 0),
                points.get('credits', 0),
                points.get('battle_points', 0),
                points.get('social_points', 0),
                points.get('knowledge_points', 0)
            ]),
            'point_breakdown': {
                'coins': points.get('coins', 0),
                'credits': points.get('credits', 0),
                'battle_points': points.get('battle_points', 0),
                'social_points': points.get('social_points', 0),
                'knowledge_points': points.get('knowledge_points', 0),
                'trophy_points': points.get('trophy_points', 0),
                'dna_manipulation_points': points.get('dna_manipulation_points', 0),
                'dna_cloning_points': points.get('dna_cloning_points', 0)
            },
            'achievements': {
                'achievements_earned': points.get('achievements_earned', 0),
                'milestones_reached': points.get('milestones_reached', 0)
            },
            'systems': points.get('systems', {})
        }
        
        return jsonify({
            'success': True,
            'stats': stats
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@debugger_profile_bp.route('/api/debugger/profile/agent-points', methods=['GET'])
def get_agent_points():
    """Get points earned by agents"""
    try:
        agent_id = request.args.get('agent_id', 'agent_manager')
        
        # Try to import and use AgentPointCreator with fallback
        try:
            from backend.services.agent_point_creator import AgentPointCreator
            point_creator = AgentPointCreator()
            
            # Get agent value created
            try:
                agent_value = point_creator.get_agent_value_created(agent_id)
            except:
                agent_value = {}
        except (ImportError, Exception) as e:
            # Fallback if import fails
            print(f"[WARN] Could not import AgentPointCreator: {e}")
            agent_value = {
                'points_awarded': {},
                'value_created': 0,
                'total_actions': 0
            }
        
        return jsonify({
            'success': True,
            'agent_id': agent_id,
            'points': agent_value.get('points_awarded', {}),
            'value_created': agent_value.get('value_created', 0),
            'total_actions': agent_value.get('total_actions', 0)
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
