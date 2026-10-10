"""
Theme Game Routes
A gamified experience with integrated monetization
Separate from stats page - dedicated game experience
"""

from flask import Blueprint, render_template, jsonify, request, session
from typing import Dict, Any
from datetime import datetime, timedelta
import json

from src.db.models import db, Documentary

theme_game_bp = Blueprint('theme_game', __name__)


@theme_game_bp.route('/theme-game')
@theme_game_bp.route('/game')
def theme_game_page():
    """Theme Game page - main game experience"""
    try:
        return render_template('theme_game/index.html')
    except Exception as e:
        return f"Error loading theme game page: {str(e)}", 500


@theme_game_bp.route('/api/theme-game/profile')
def get_game_profile():
    """Get user's game profile"""
    try:
        user_id = session.get('user_id', 'anonymous')
        
        # Get user's game data
        profile = {
            'user_id': user_id,
            'level': 1,
            'xp': 0,
            'coins': 0,  # Virtual currency
            'premium_coins': 0,  # Premium currency (purchased)
            'themes_unlocked': ['matrix'],
            'achievements': [],
            'quests_active': [],
            'inventory': [],
            'subscription_tier': 'free',
            'power_ups': [],
            'streak': 0,
            'total_earnings': 0  # Total coins earned
        }
        
        return jsonify({
            'success': True,
            'profile': profile
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@theme_game_bp.route('/api/theme-game/quests')
def get_quests():
    """Get available quests"""
    try:
        user_id = session.get('user_id', 'anonymous')
        
        quests = [
            {
                'id': 'daily_generation',
                'name': 'Daily Generation',
                'description': 'Generate 1 video today',
                'type': 'daily',
                'reward': {'coins': 100, 'xp': 50},
                'premium_reward': {'premium_coins': 10},  # Premium users get extra
                'progress': 0,
                'target': 1,
                'unlocked': True
            },
            {
                'id': 'theme_master',
                'name': 'Theme Master',
                'description': 'Use 3 different themes',
                'type': 'weekly',
                'reward': {'coins': 500, 'xp': 200},
                'premium_reward': {'premium_coins': 50},
                'progress': 0,
                'target': 3,
                'unlocked': True
            },
            {
                'id': 'quality_seeker',
                'name': 'Quality Seeker',
                'description': 'Generate video with 0.9+ quality',
                'type': 'special',
                'reward': {'coins': 1000, 'xp': 500},
                'premium_reward': {'premium_coins': 100, 'power_up': 'quality_boost'},
                'progress': 0,
                'target': 1,
                'unlocked': True
            }
        ]
        
        return jsonify({
            'success': True,
            'quests': quests
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@theme_game_bp.route('/api/theme-game/shop')
def get_shop():
    """Get game shop items"""
    try:
        shop_items = {
            'power_ups': [
                {
                    'id': 'quality_boost',
                    'name': 'Quality Boost',
                    'description': 'Next 3 videos get +20% quality',
                    'price': {'coins': 500},
                    'premium_price': {'premium_coins': 50},
                    'duration': 3,  # Uses
                    'type': 'power_up'
                },
                {
                    'id': 'speed_boost',
                    'name': 'Speed Boost',
                    'description': '2x faster generation for 24h',
                    'price': {'coins': 300},
                    'premium_price': {'premium_coins': 30},
                    'duration': 24,  # Hours
                    'type': 'power_up'
                },
                {
                    'id': 'extra_clips',
                    'name': 'Extra Clips',
                    'description': '+5 clips on next generation',
                    'price': {'coins': 400},
                    'premium_price': {'premium_coins': 40},
                    'duration': 1,
                    'type': 'power_up'
                }
            ],
            'themes': [
                {
                    'id': 'mtg',
                    'name': 'Magic the Gathering',
                    'description': 'Unlock MTG theme',
                    'price': {'coins': 2000},
                    'premium_price': {'premium_coins': 200},
                    'type': 'theme',
                    'premium_only': False
                },
                {
                    'id': 'halo4',
                    'name': 'Halo 4',
                    'description': 'Unlock Halo 4 theme',
                    'price': {'coins': 2000},
                    'premium_price': {'premium_coins': 200},
                    'type': 'theme',
                    'premium_only': False
                },
                {
                    'id': 'exclusive_theme_1',
                    'name': 'Exclusive Theme Pack',
                    'description': 'Premium exclusive themes',
                    'price': {'premium_coins': 500},
                    'type': 'theme',
                    'premium_only': True
                }
            ],
            'subscriptions': [
                {
                    'id': 'pro_monthly',
                    'name': 'Pro Monthly',
                    'description': 'Unlock all features, earn 2x coins',
                    'price': {'real_money': 29.99},
                    'benefits': ['2x_coin_earnings', 'unlimited_videos', 'all_themes', 'priority_processing'],
                    'type': 'subscription'
                },
                {
                    'id': 'pro_annual',
                    'name': 'Pro Annual',
                    'description': 'Best value - 2 months free',
                    'price': {'real_money': 299.99},
                    'benefits': ['2x_coin_earnings', 'unlimited_videos', 'all_themes', 'priority_processing', 'exclusive_themes'],
                    'type': 'subscription',
                    'discount': '2 months free'
                }
            ],
            'premium_currency': [
                {
                    'id': 'premium_coins_100',
                    'name': '100 Premium Coins',
                    'description': 'Premium currency pack',
                    'price': {'real_money': 4.99},
                    'coins': 100,
                    'type': 'currency',
                    'bonus': 0
                },
                {
                    'id': 'premium_coins_500',
                    'name': '500 Premium Coins',
                    'description': 'Best value - 20% bonus',
                    'price': {'real_money': 19.99},
                    'coins': 600,  # 500 + 100 bonus
                    'type': 'currency',
                    'bonus': 100
                },
                {
                    'id': 'premium_coins_1000',
                    'name': '1000 Premium Coins',
                    'description': 'Mega pack - 30% bonus',
                    'price': {'real_money': 34.99},
                    'coins': 1300,  # 1000 + 300 bonus
                    'type': 'currency',
                    'bonus': 300
                }
            ]
        }
        
        return jsonify({
            'success': True,
            'shop': shop_items
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@theme_game_bp.route('/api/theme-game/purchase', methods=['POST'])
def purchase_item():
    """Purchase item from shop"""
    try:
        data = request.get_json()
        user_id = session.get('user_id', 'anonymous')
        item_id = data.get('item_id')
        payment_method = data.get('payment_method', 'coins')  # 'coins', 'premium_coins', 'real_money'
        
        # In production, this would:
        # 1. Validate payment
        # 2. Process transaction
        # 3. Update user inventory
        # 4. Log transaction
        
        return jsonify({
            'success': True,
            'message': 'Purchase successful',
            'item_id': item_id,
            'payment_method': payment_method
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@theme_game_bp.route('/api/theme-game/leaderboard')
def get_leaderboard():
    """Get game leaderboard"""
    try:
        leaderboard = [
            {'rank': 1, 'username': 'Player1', 'level': 50, 'xp': 50000, 'coins': 100000},
            {'rank': 2, 'username': 'Player2', 'level': 45, 'xp': 45000, 'coins': 90000},
            {'rank': 3, 'username': 'Player3', 'level': 40, 'xp': 40000, 'coins': 80000}
        ]
        
        return jsonify({
            'success': True,
            'leaderboard': leaderboard
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@theme_game_bp.route('/api/theme-game/complete-quest', methods=['POST'])
def complete_quest():
    """Complete a quest and award rewards"""
    try:
        data = request.get_json()
        user_id = session.get('user_id', 'anonymous')
        quest_id = data.get('quest_id')
        
        # Award rewards
        rewards = {
            'coins': 100,
            'xp': 50,
            'premium_coins': 10  # Premium users
        }
        
        return jsonify({
            'success': True,
            'rewards': rewards,
            'message': 'Quest completed!'
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


def register_theme_game_routes(app):
    """Register theme game routes"""
    app.register_blueprint(theme_game_bp, url_prefix='/vidgenerator')
    print("[Routes] Theme Game routes registered")

