"""
Enhanced Generator Logic
Additional intelligence and XP tracking for video generation
"""

from flask import Blueprint, request, jsonify, session
from typing import Dict, Any
from datetime import datetime
import uuid

generator_enhanced_bp = Blueprint('generator_enhanced', __name__)

def get_user_id():
    """Get user ID from session"""
    if 'user_id' not in session:
        session['user_id'] = str(uuid.uuid4())
    return session['user_id']

@generator_enhanced_bp.route('/api/generator/calculate-xp-bonus', methods=['POST'])
@generator_enhanced_bp.route('/vidgenerator/api/generator/calculate-xp-bonus', methods=['POST'])
def calculate_xp_bonus():
    """Calculate XP bonus based on generation parameters"""
    try:
        data = request.get_json() or {}
        user_id = get_user_id()
        
        prompt = data.get('prompt', '')
        theme = data.get('theme', 'matrix')
        duration = data.get('duration', 10)
        quality_score = data.get('quality_score', 0.8)
        
        # Base XP calculation
        base_xp = 100
        
        # Prompt complexity bonus
        prompt_length = len(prompt.split())
        if prompt_length > 100:
            complexity_multiplier = 1.5
        elif prompt_length > 50:
            complexity_multiplier = 1.3
        elif prompt_length > 20:
            complexity_multiplier = 1.1
        else:
            complexity_multiplier = 1.0
        
        # Theme bonus (from hunters game)
        theme_multipliers = {
            'matrix': 1.5,
            'cyberpunk': 1.3,
            'sci-fi': 1.2,
            'nature': 1.0,
            'mtg': 1.4,
            'halo4': 1.6,
            'wwii': 1.1,
            'fantasy': 1.3,
            'horror': 1.7,
            'comedy': 0.9,
            'romance': 1.0,
            'action': 1.5
        }
        theme_multiplier = theme_multipliers.get(theme, 1.0)
        
        # Duration bonus
        duration_multiplier = min(1.0 + (duration / 100), 2.0)  # Max 2x for long videos
        
        # Quality bonus
        quality_multiplier = 0.5 + (quality_score * 0.5)  # 0.5x to 1.0x based on quality
        
        # Calculate total XP
        total_xp = int(base_xp * complexity_multiplier * theme_multiplier * duration_multiplier * quality_multiplier)
        
        return jsonify({
            'success': True,
            'xp_calculation': {
                'base_xp': base_xp,
                'complexity_multiplier': complexity_multiplier,
                'theme_multiplier': theme_multiplier,
                'duration_multiplier': duration_multiplier,
                'quality_multiplier': quality_multiplier,
                'total_xp': total_xp
            }
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@generator_enhanced_bp.route('/api/generator/generation-intelligence', methods=['POST'])
@generator_enhanced_bp.route('/vidgenerator/api/generator/generation-intelligence', methods=['POST'])
def get_generation_intelligence():
    """Get intelligence for generation (themes, suggestions, etc.)"""
    try:
        data = request.get_json() or {}
        prompt = data.get('prompt', '')
        user_id = get_user_id()
        
        # Get user's generation history for suggestions
        try:
            from src.db.models import Documentary
            from src.db.models import db
            
            user_generations = Documentary.query.filter_by(
                user_id=user_id,
                status='completed'
            ).order_by(Documentary.created_at.desc()).limit(10).all()
            
            recent_themes = [doc.theme for doc in user_generations if doc.theme]
            favorite_theme = max(set(recent_themes), key=recent_themes.count) if recent_themes else 'matrix'
        except:
            favorite_theme = 'matrix'
            user_generations = []
        
        # Theme suggestions based on prompt
        theme_suggestions = []
        prompt_lower = prompt.lower()
        
        if any(word in prompt_lower for word in ['war', 'battle', 'soldier', 'military']):
            theme_suggestions.append({'theme': 'wwii', 'confidence': 0.9, 'reason': 'Military/war keywords detected'})
        if any(word in prompt_lower for word in ['space', 'alien', 'planet', 'future', 'sci']):
            theme_suggestions.append({'theme': 'sci-fi', 'confidence': 0.9, 'reason': 'Sci-fi keywords detected'})
        if any(word in prompt_lower for word in ['nature', 'animal', 'wildlife', 'forest', 'ocean']):
            theme_suggestions.append({'theme': 'nature', 'confidence': 0.9, 'reason': 'Nature keywords detected'})
        if any(word in prompt_lower for word in ['matrix', 'code', 'digital', 'hacker']):
            theme_suggestions.append({'theme': 'matrix', 'confidence': 0.9, 'reason': 'Matrix keywords detected'})
        
        return jsonify({
            'success': True,
            'intelligence': {
                'favorite_theme': favorite_theme,
                'theme_suggestions': theme_suggestions[:3],  # Top 3
                'generation_count': len(user_generations),
                'prompt_analysis': {
                    'length': len(prompt.split()),
                    'complexity': 'high' if len(prompt.split()) > 50 else 'medium' if len(prompt.split()) > 20 else 'low'
                }
            }
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

def register_generator_enhanced_routes(app):
    """Register enhanced generator routes"""
    app.register_blueprint(generator_enhanced_bp, url_prefix='')
    app.register_blueprint(generator_enhanced_bp, url_prefix='/vidgenerator', name='generator_enhanced_with_prefix')
    print("[Routes] Enhanced generator routes registered", flush=True)

