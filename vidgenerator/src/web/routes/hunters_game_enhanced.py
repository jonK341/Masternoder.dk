"""
Enhanced Hunters Game with Defense Mechanisms Integration
Includes psychological defense mechanisms, skills, and enemy websites
"""
from flask import Blueprint, jsonify, request
from datetime import datetime
import json
import random

from src.services.defense_mechanisms.defense_engine import (
    DefenseMechanismsEngine,
    DefenseMechanism,
    SkillType,
    EnemyType
)
from src.services.themes.theme_definitions import theme_definitions

hunters_game_enhanced_bp = Blueprint('hunters_game_enhanced', __name__)

# Game state storage (in production, use database)
game_states = {}
defense_engine = DefenseMechanismsEngine()

class EnhancedHuntersGame:
    """Enhanced Hunters Game with defense mechanisms"""
    
    def __init__(self):
        # Use hardcoded theme definitions
        all_themes = theme_definitions.get_all_themes()
        self.themes = {
            key: {
                'xp_multiplier': theme['xp_multiplier'],
                'difficulty': theme['difficulty'],
                'color': theme['color'],
                'defense_bonus': theme['defense_bonus'],
                'name': theme['name'],
                'display_name': theme['display_name'],
                'description': theme['description'],
                'icon': theme['icon'],
                'recommended_skills': theme['recommended_skills'],
                'enemy_resistance': theme['enemy_resistance'],
                'hack_bonus': theme['hack_bonus'],
                'special_abilities': theme['special_abilities'],
                'story_elements': theme['story_elements'],
                'generation_prompts': theme['generation_prompts']
            }
            for key, theme in all_themes.items()
        }
    
    def calculate_enhanced_xp(
        self,
        theme: str,
        base_xp: int,
        defense_mechanism: DefenseMechanism,
        skill_levels: dict,
        enemy_type: EnemyType,
        success: bool = True
    ) -> dict:
        """Calculate XP with defense mechanisms"""
        theme_data = self.themes.get(theme, {'xp_multiplier': 1.0, 'defense_bonus': 1.0})
        theme_multiplier = theme_data['xp_multiplier']
        defense_bonus = theme_data.get('defense_bonus', 1.0)
        
        # Calculate defense points
        defense_result = defense_engine.calculate_defense_points(
            mechanism=defense_mechanism,
            base_points=float(base_xp),
            skill_levels=skill_levels,
            enemy_threat=enemy_type,
            time_factor=1.0
        )
        
        # Apply theme multiplier and success factor
        success_multiplier = 1.0 if success else 0.5
        final_xp = defense_result['final_points'] * theme_multiplier * defense_bonus * success_multiplier
        
        return {
            'base_xp': base_xp,
            'theme_multiplier': theme_multiplier,
            'defense_points': defense_result['final_points'],
            'defense_bonus': defense_bonus,
            'success_multiplier': success_multiplier,
            'final_xp': round(final_xp, 2),
            'defense_breakdown': defense_result
        }
    
    def get_theme_bonus(self, theme: str) -> dict:
        """Get theme-specific bonuses"""
        theme_data = self.themes.get(theme, {})
        if not theme_data:
            # Fallback to theme definitions
            theme_def = theme_definitions.get_theme(theme)
            if theme_def:
                return {
                    'xp_multiplier': theme_def['xp_multiplier'],
                    'difficulty': theme_def['difficulty'],
                    'color': theme_def['color'],
                    'defense_bonus': theme_def['defense_bonus']
                }
        return theme_data

# Initialize game
enhanced_hunters_game = EnhancedHuntersGame()

@hunters_game_enhanced_bp.route('/api/game/hunters-enhanced/start', methods=['POST'])
def start_enhanced_hunters_game():
    """Start enhanced hunters game with defense mechanisms"""
    try:
        data = request.get_json() or {}
        user_id = data.get('user_id', 'anonymous')
        theme = data.get('theme', 'matrix')
        
        # Get user skills (default to 50 if not provided)
        skill_levels = {
            SkillType.LOGIC: float(data.get('logic_skill', 50.0)),
            SkillType.ORGANIZATION: float(data.get('organization_skill', 50.0)),
            SkillType.SOCIAL: float(data.get('social_skill', 50.0)),
            SkillType.TECHNICAL: float(data.get('technical_skill', 50.0)),
            SkillType.STRATEGIC: float(data.get('strategic_skill', 50.0)),
            SkillType.PSYCHOLOGICAL: float(data.get('psychological_skill', 50.0)),
        }
        
        game_state = {
            'user_id': user_id,
            'theme': theme,
            'level': 1,
            'xp': 0,
            'total_xp': 0,
            'hunts_completed': 0,
            'defense_actions': [],
            'hack_actions': [],
            'skill_levels': {k.value: v for k, v in skill_levels.items()},
            'started_at': datetime.now().isoformat(),
            'theme_bonus': enhanced_hunters_game.get_theme_bonus(theme)
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

@hunters_game_enhanced_bp.route('/api/game/hunters-enhanced/complete-hunt', methods=['POST'])
def complete_enhanced_hunt():
    """Complete a hunt with defense mechanisms"""
    try:
        data = request.get_json() or {}
        user_id = data.get('user_id', 'anonymous')
        base_xp = data.get('base_xp', 100)
        success = data.get('success', True)
        mechanism_str = data.get('defense_mechanism', 'sublimation')
        enemy_str = data.get('enemy_type', 'competitor')
        
        if user_id not in game_states:
            return jsonify({
                'success': False,
                'error': 'Game not started'
            }), 400
        
        game_state = game_states[user_id]
        theme = game_state.get('theme', 'matrix')
        
        # Convert skill levels back to SkillType enum
        skill_dict = game_state.get('skill_levels', {})
        skill_levels = {
            SkillType.LOGIC: float(skill_dict.get('logic', 50.0)),
            SkillType.ORGANIZATION: float(skill_dict.get('organization', 50.0)),
            SkillType.SOCIAL: float(skill_dict.get('social', 50.0)),
            SkillType.TECHNICAL: float(skill_dict.get('technical', 50.0)),
            SkillType.STRATEGIC: float(skill_dict.get('strategic', 50.0)),
            SkillType.PSYCHOLOGICAL: float(skill_dict.get('psychological', 50.0)),
        }
        
        # Get enums
        mechanism = DefenseMechanism(mechanism_str)
        enemy_type = EnemyType(enemy_str)
        
        # Calculate enhanced XP
        xp_result = enhanced_hunters_game.calculate_enhanced_xp(
            theme=theme,
            base_xp=base_xp,
            defense_mechanism=mechanism,
            skill_levels=skill_levels,
            enemy_type=enemy_type,
            success=success
        )
        
        xp_earned = int(xp_result['final_xp'])
        
        # Store defense action
        defense_action = {
            'mechanism': mechanism_str,
            'enemy_type': enemy_str,
            'final_points': xp_result['defense_points'],
            'timestamp': datetime.now().isoformat()
        }
        game_state['defense_actions'].append(defense_action)
        
        # Update game state
        game_state['xp'] += xp_earned
        game_state['total_xp'] += xp_earned
        game_state['hunts_completed'] += 1
        
        # Level up check (every 1000 XP)
        new_level = (game_state['total_xp'] // 1000) + 1
        leveled_up = new_level > game_state['level']
        if leveled_up:
            game_state['level'] = new_level
        
        # Recalculate total points
        total_points = defense_engine.calculate_total_user_points(
            defense_actions=game_state['defense_actions'],
            hack_actions=game_state['hack_actions'],
            base_xp=0.0
        )
        
        return jsonify({
            'success': True,
            'xp_earned': xp_earned,
            'total_xp': game_state['total_xp'],
            'level': game_state['level'],
            'leveled_up': leveled_up,
            'xp_breakdown': xp_result,
            'total_points_breakdown': total_points,
            'game_state': game_state
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@hunters_game_enhanced_bp.route('/api/game/hunters-enhanced/enemies', methods=['GET'])
def get_enemy_websites():
    """Get enemy websites for hunters game"""
    try:
        enemies = defense_engine.get_enemy_websites()
        return jsonify({
            'success': True,
            'enemies': enemies
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@hunters_game_enhanced_bp.route('/api/game/hunters-enhanced/recalculate', methods=['POST'])
def recalculate_all_points():
    """Recalculate all points mathematically"""
    try:
        data = request.get_json() or {}
        user_id = data.get('user_id', 'anonymous')
        
        if user_id not in game_states:
            return jsonify({
                'success': False,
                'error': 'Game not started'
            }), 400
        
        game_state = game_states[user_id]
        
        # Recalculate all points
        total_points = defense_engine.calculate_total_user_points(
            defense_actions=game_state.get('defense_actions', []),
            hack_actions=game_state.get('hack_actions', []),
            base_xp=0.0
        )
        
        # Update game state
        game_state['total_xp'] = total_points['total_points']
        game_state['level'] = total_points['level']
        
        return jsonify({
            'success': True,
            'recalculated_points': total_points,
            'updated_game_state': game_state
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

