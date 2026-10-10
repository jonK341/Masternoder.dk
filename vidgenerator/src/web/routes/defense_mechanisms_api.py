"""
Defense Mechanisms API Routes
Handles all defense mechanism calculations, points, and integration
"""
from flask import Blueprint, request, jsonify
from datetime import datetime
import json

from src.services.defense_mechanisms.defense_engine import (
    DefenseMechanismsEngine,
    DefenseMechanism,
    SkillType,
    EnemyType,
    HackType
)

def register_defense_mechanisms_routes(app):
    """Register defense mechanisms API routes"""
    
    engine = DefenseMechanismsEngine()
    
    @app.route('/api/defense/calculate', methods=['POST'])
    @app.route('/vidgenerator/api/defense/calculate', methods=['POST'])
    def calculate_defense_points():
        """Calculate defense mechanism points"""
        try:
            data = request.get_json() or {}
            
            mechanism_str = data.get('mechanism', 'denial')
            mechanism = DefenseMechanism(mechanism_str)
            
            base_points = float(data.get('base_points', 100.0))
            
            skill_levels = {
                SkillType.LOGIC: float(data.get('logic_skill', 50.0)),
                SkillType.ORGANIZATION: float(data.get('organization_skill', 50.0)),
                SkillType.SOCIAL: float(data.get('social_skill', 50.0)),
                SkillType.TECHNICAL: float(data.get('technical_skill', 50.0)),
                SkillType.STRATEGIC: float(data.get('strategic_skill', 50.0)),
                SkillType.PSYCHOLOGICAL: float(data.get('psychological_skill', 50.0)),
            }
            
            enemy_str = data.get('enemy_type', 'competitor')
            enemy_type = EnemyType(enemy_str)
            
            time_factor = float(data.get('time_factor', 1.0))
            
            result = engine.calculate_defense_points(
                mechanism=mechanism,
                base_points=base_points,
                skill_levels=skill_levels,
                enemy_threat=enemy_type,
                time_factor=time_factor
            )
            
            return jsonify({
                'success': True,
                'result': result
            })
        except Exception as e:
            return jsonify({
                'success': False,
                'error': str(e)
            }), 400
    
    @app.route('/api/defense/hack', methods=['POST'])
    @app.route('/vidgenerator/api/defense/hack', methods=['POST'])
    def calculate_hack_points():
        """Calculate hack/scam points"""
        try:
            data = request.get_json() or {}
            
            hack_str = data.get('hack_type', 'phishing')
            hack_type = HackType(hack_str)
            
            success_rate = float(data.get('success_rate', 0.5))
            
            skill_levels = {
                SkillType.TECHNICAL: float(data.get('technical_skill', 50.0)),
                SkillType.STRATEGIC: float(data.get('strategic_skill', 50.0)),
                SkillType.SOCIAL: float(data.get('social_skill', 50.0)),
            }
            
            enemy_str = data.get('target_enemy', 'competitor')
            enemy_type = EnemyType(enemy_str)
            
            result = engine.calculate_hack_points(
                hack_type=hack_type,
                success_rate=success_rate,
                skill_levels=skill_levels,
                target_enemy=enemy_type
            )
            
            return jsonify({
                'success': True,
                'result': result
            })
        except Exception as e:
            return jsonify({
                'success': False,
                'error': str(e)
            }), 400
    
    @app.route('/api/defense/recalculate', methods=['POST'])
    @app.route('/vidgenerator/api/defense/recalculate', methods=['POST'])
    def recalculate_all_points():
        """Recalculate all user points from scratch"""
        try:
            data = request.get_json() or {}
            user_id = data.get('user_id')
            
            # Get user's defense actions and hack actions from database
            # This would typically come from the database
            defense_actions = data.get('defense_actions', [])
            hack_actions = data.get('hack_actions', [])
            base_xp = float(data.get('base_xp', 0.0))
            
            result = engine.calculate_total_user_points(
                defense_actions=defense_actions,
                hack_actions=hack_actions,
                base_xp=base_xp
            )
            
            return jsonify({
                'success': True,
                'result': result
            })
        except Exception as e:
            return jsonify({
                'success': False,
                'error': str(e)
            }), 400
    
    @app.route('/api/defense/enemies', methods=['GET'])
    @app.route('/vidgenerator/api/defense/enemies', methods=['GET'])
    def get_enemy_websites():
        """Get list of enemy websites"""
        try:
            enemies = engine.get_enemy_websites()
            return jsonify({
                'success': True,
                'enemies': enemies
            })
        except Exception as e:
            return jsonify({
                'success': False,
                'error': str(e)
            }), 400
    
    @app.route('/api/defense/hacks', methods=['GET'])
    @app.route('/vidgenerator/api/defense/hacks', methods=['GET'])
    def get_available_hacks():
        """Get list of available hacks and scams"""
        try:
            hacks = engine.get_available_hacks()
            return jsonify({
                'success': True,
                'hacks': hacks
            })
        except Exception as e:
            return jsonify({
                'success': False,
                'error': str(e)
            }), 400
    
    @app.route('/api/defense/mechanisms', methods=['GET'])
    @app.route('/vidgenerator/api/defense/mechanisms', methods=['GET'])
    def get_defense_mechanisms():
        """Get list of all defense mechanisms"""
        try:
            mechanisms = [
                {
                    'value': mech.value,
                    'name': mech.value.replace('_', ' ').title(),
                    'multiplier': engine.base_multipliers.get(mech, 1.0)
                }
                for mech in DefenseMechanism
            ]
            return jsonify({
                'success': True,
                'mechanisms': mechanisms
            })
        except Exception as e:
            return jsonify({
                'success': False,
                'error': str(e)
            }), 400

