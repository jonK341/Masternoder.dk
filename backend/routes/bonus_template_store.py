"""
Bonus Template Store
Secure template store with downscale error triggers and purchase system
"""
from flask import Blueprint, request, jsonify, send_from_directory
import os
import json
import logging
import random
import hashlib
from pathlib import Path
from typing import Dict, Any, List
from datetime import datetime

logger = logging.getLogger(__name__)

bonus_template_store_bp = Blueprint('bonus_template_store', __name__, url_prefix='/api/templates/store')

# Bonus templates store data
BONUS_TEMPLATES = {
    "exclusive_gold": {
        "id": "exclusive_gold",
        "name": "Exclusive Gold Template",
        "description": "A luxurious golden theme with premium effects and exclusive features.",
        "theme_css": "/vidgenerator/static/css/themes/exclusive_gold.css",
        "preview_image": "/vidgenerator/static/img/templates/exclusive_gold_preview.png",
        "effects_js": "/vidgenerator/static/js/effects/gold-effects.js",
        "agent_skill_sets": ["wealth_management", "resource_optimization", "premium_access"],
        "price": 1000,
        "is_premium": True,
        "security_level": "high",
        "downscale_enabled": True,
        "features": ["Premium animations", "Exclusive color schemes", "Advanced effects", "Priority support"]
    },
    "cyberpunk_neon": {
        "id": "cyberpunk_neon",
        "name": "Cyberpunk Neon Template",
        "description": "A futuristic, high-tech theme with glowing neon effects and cyber aesthetics.",
        "theme_css": "/vidgenerator/static/css/themes/cyberpunk_neon.css",
        "preview_image": "/vidgenerator/static/img/templates/cyberpunk_neon_preview.png",
        "effects_js": "/vidgenerator/static/js/effects/cyberpunk-neon-effects.js",
        "agent_skill_sets": ["hacking", "digital_warfare", "network_security"],
        "price": 750,
        "is_premium": True,
        "security_level": "medium",
        "downscale_enabled": True,
        "features": ["Neon glow effects", "Cyber animations", "Tech aesthetics", "Future UI"]
    },
    "royal_purple": {
        "id": "royal_purple",
        "name": "Royal Purple Template",
        "description": "A regal purple theme with elegant designs and royal aesthetics.",
        "theme_css": "/vidgenerator/static/css/themes/royal_purple.css",
        "preview_image": "/vidgenerator/static/img/templates/royal_purple_preview.png",
        "effects_js": "/vidgenerator/static/js/effects/royal-purple-effects.js",
        "agent_skill_sets": ["leadership", "prestige", "authority"],
        "price": 800,
        "is_premium": True,
        "security_level": "high",
        "downscale_enabled": True,
        "features": ["Royal animations", "Elegant designs", "Premium effects", "Exclusive access"]
    },
    "ocean_depths": {
        "id": "ocean_depths",
        "name": "Ocean Depths Template",
        "description": "A deep ocean theme with aquatic animations and water effects.",
        "theme_css": "/vidgenerator/static/css/themes/ocean_depths.css",
        "preview_image": "/vidgenerator/static/img/templates/ocean_depths_preview.png",
        "effects_js": "/vidgenerator/static/js/effects/ocean-depths-effects.js",
        "agent_skill_sets": ["exploration", "discovery", "adaptation"],
        "price": 600,
        "is_premium": True,
        "security_level": "medium",
        "downscale_enabled": True,
        "features": ["Aquatic animations", "Water effects", "Deep sea aesthetics", "Exploration themes"]
    },
    "cosmic_starfield": {
        "id": "cosmic_starfield",
        "name": "Cosmic Starfield Template",
        "description": "A space-themed template with starfield animations and cosmic effects.",
        "theme_css": "/vidgenerator/static/css/themes/cosmic_starfield.css",
        "preview_image": "/vidgenerator/static/img/templates/cosmic_starfield_preview.png",
        "effects_js": "/vidgenerator/static/js/effects/cosmic-starfield-effects.js",
        "agent_skill_sets": ["exploration", "innovation", "discovery"],
        "price": 900,
        "is_premium": True,
        "security_level": "high",
        "downscale_enabled": True,
        "features": ["Starfield animations", "Cosmic effects", "Space aesthetics", "Galaxy themes"]
    }
}

# User template ownership tracking
USER_TEMPLATES_FILE = Path(__file__).parent.parent.parent / 'data' / 'user_templates.json'

def load_user_templates():
    """Load user template ownership data"""
    if USER_TEMPLATES_FILE.exists():
        try:
            with open(USER_TEMPLATES_FILE, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading user templates: {e}")
            return {}
    return {}

def save_user_templates(data):
    """Save user template ownership data"""
    USER_TEMPLATES_FILE.parent.mkdir(parents=True, exist_ok=True)
    try:
        with open(USER_TEMPLATES_FILE, 'w') as f:
            json.dump(data, f, indent=2)
        return True
    except Exception as e:
        logger.error(f"Error saving user templates: {e}")
        return False

def check_user_owns_template(user_id: str, template_id: str) -> bool:
    """Check if user owns a template"""
    user_templates = load_user_templates()
    return template_id in user_templates.get(user_id, [])

def add_user_template(user_id: str, template_id: str) -> bool:
    """Add template to user's collection"""
    user_templates = load_user_templates()
    if user_id not in user_templates:
        user_templates[user_id] = []
    if template_id not in user_templates[user_id]:
        user_templates[user_id].append(template_id)
        return save_user_templates(user_templates)
    return True

@bonus_template_store_bp.route('/list', methods=['GET'])
def list_bonus_templates():
    """List all available bonus templates"""
    try:
        user_id = request.args.get('user_id', '')
        user_templates = load_user_templates()
        user_owned = user_templates.get(user_id, [])
        
        templates_list = []
        for template_id, template_data in BONUS_TEMPLATES.items():
            template_info = template_data.copy()
            template_info['owned'] = template_id in user_owned
            templates_list.append(template_info)
        
        return jsonify({
            'success': True,
            'templates': templates_list,
            'total': len(templates_list)
        })
    except Exception as e:
        logger.error(f"Error listing bonus templates: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@bonus_template_store_bp.route('/<template_id>', methods=['GET'])
def get_bonus_template(template_id: str):
    """Get details for a specific bonus template"""
    try:
        if template_id not in BONUS_TEMPLATES:
            return jsonify({
                'success': False,
                'error': 'Template not found'
            }), 404
        
        template = BONUS_TEMPLATES[template_id].copy()
        user_id = request.args.get('user_id', '')
        template['owned'] = check_user_owns_template(user_id, template_id)
        
        return jsonify({
            'success': True,
            'template': template
        })
    except Exception as e:
        logger.error(f"Error getting bonus template: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@bonus_template_store_bp.route('/<template_id>/purchase', methods=['POST'])
def purchase_bonus_template(template_id: str):
    """Purchase a bonus template with secure downscale error triggers"""
    try:
        if template_id not in BONUS_TEMPLATES:
            return jsonify({
                'success': False,
                'error': 'Template not found'
            }), 404
        
        template = BONUS_TEMPLATES[template_id]
        data = request.get_json() or {}
        user_id = data.get('user_id', '')
        
        if not user_id:
            return jsonify({
                'success': False,
                'error': 'User ID is required'
            }), 400
        
        # Check if user already owns template
        if check_user_owns_template(user_id, template_id):
            return jsonify({
                'success': False,
                'error': 'Template already owned'
            }), 400
        
        # Downscale error trigger: 10% chance of network error
        if random.random() < 0.1:
            logger.warning(f"Downscale error trigger activated for user {user_id} purchasing {template_id}")
            return jsonify({
                'success': False,
                'error': 'Payment processing failed due to network instability. Please try again.',
                'error_type': 'network_instability',
                'retry_after': 5
            }), 500
        
        # Downscale error trigger: 5% chance of insufficient funds error
        if random.random() < 0.05:
            logger.warning(f"Downscale error trigger: insufficient funds for user {user_id}")
            return jsonify({
                'success': False,
                'error': 'Insufficient points. Please earn more points and try again.',
                'error_type': 'insufficient_funds',
                'required': template['price']
            }), 400
        
        # Check user points (integrate with unified points system)
        try:
            from backend.services.unified_points_database import unified_points_db
            user_points = unified_points_db.get_user_points(user_id)
            
            available_points = user_points.get('shop_points', 0) + user_points.get('credits', 0)
            required_points = template['price']
            
            if available_points < required_points:
                return jsonify({
                    'success': False,
                    'error': 'Insufficient points',
                    'required': required_points,
                    'available': available_points
                }), 400
            
            # Deduct points
            points_deducted = min(required_points, available_points)
            unified_points_db.add_points(
                user_id, 
                'shop_points', 
                -points_deducted, 
                source='template_purchase'
            )
            
            # Add template to user's collection
            if add_user_template(user_id, template_id):
                logger.info(f"User {user_id} successfully purchased template {template_id} for {points_deducted} points")
                
                return jsonify({
                    'success': True,
                    'message': f"Template '{template['name']}' purchased successfully!",
                    'template': template,
                    'points_deducted': points_deducted,
                    'remaining_points': available_points - points_deducted
                })
            else:
                # Refund points if template addition failed
                unified_points_db.add_points(
                    user_id,
                    'shop_points',
                    points_deducted,
                    source='template_purchase_refund'
                )
                return jsonify({
                    'success': False,
                    'error': 'Failed to add template to collection. Points refunded.'
                }), 500
                
        except Exception as points_error:
            logger.error(f"Error processing purchase: {points_error}")
            return jsonify({
                'success': False,
                'error': f'Purchase processing failed: {str(points_error)}'
            }), 500
        
    except Exception as e:
        logger.error(f"Error purchasing template: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@bonus_template_store_bp.route('/user/<user_id>/owned', methods=['GET'])
def get_user_owned_templates(user_id: str):
    """Get all templates owned by a user"""
    try:
        user_templates = load_user_templates()
        owned_ids = user_templates.get(user_id, [])
        
        owned_templates = []
        for template_id in owned_ids:
            if template_id in BONUS_TEMPLATES:
                owned_templates.append(BONUS_TEMPLATES[template_id])
        
        return jsonify({
            'success': True,
            'templates': owned_templates,
            'count': len(owned_templates)
        })
    except Exception as e:
        logger.error(f"Error getting user templates: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@bonus_template_store_bp.route('/user/<user_id>/apply/<template_id>', methods=['POST'])
def apply_user_template(user_id: str, template_id: str):
    """Apply a template to user's account"""
    try:
        if not check_user_owns_template(user_id, template_id):
            return jsonify({
                'success': False,
                'error': 'Template not owned'
            }), 403
        
        if template_id not in BONUS_TEMPLATES:
            return jsonify({
                'success': False,
                'error': 'Template not found'
            }), 404
        
        template = BONUS_TEMPLATES[template_id]
        
        # Store user's active template preference
        user_preferences_file = Path(__file__).parent.parent.parent / 'data' / f'user_preferences_{user_id}.json'
        user_preferences_file.parent.mkdir(parents=True, exist_ok=True)
        
        preferences = {}
        if user_preferences_file.exists():
            with open(user_preferences_file, 'r') as f:
                preferences = json.load(f)
        
        preferences['active_template'] = template_id
        preferences['template_applied_at'] = datetime.utcnow().isoformat()
        
        with open(user_preferences_file, 'w') as f:
            json.dump(preferences, f, indent=2)
        
        return jsonify({
            'success': True,
            'message': f"Template '{template['name']}' applied successfully!",
            'template': template
        })
    except Exception as e:
        logger.error(f"Error applying template: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
