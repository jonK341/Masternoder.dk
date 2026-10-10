"""
Calendar Rewards API
Handles reward claiming for calendar appointments
"""

from flask import Blueprint, request, jsonify, session
from typing import Dict, Any
from datetime import datetime

from src.services.calendar.monetization_calendar import get_monetization_calendar

calendar_rewards_bp = Blueprint('calendar_rewards', __name__)


@calendar_rewards_bp.route('/api/stats/claim-reward', methods=['POST'])
def claim_reward():
    """Claim reward for a calendar appointment"""
    try:
        data = request.get_json()
        user_id = session.get('user_id', 'anonymous')
        date_str = data.get('date')
        appointment_title = data.get('appointment_title')
        
        # Get monetization calendar
        monetization_cal = get_monetization_calendar()
        
        # Get milestone/event for this date
        milestone = monetization_cal.get_milestone_by_date(date_str)
        event = monetization_cal.get_event_by_date(dateStr)
        
        appointment = milestone or event
        
        if not appointment:
            return jsonify({
                'success': False,
                'error': 'Appointment not found'
            }), 404
        
        # Get user tier (would be from database in production)
        user_tier = session.get('subscription_tier', 'free')
        
        # Calculate reward
        reward = monetization_cal.calculate_reward(appointment, user_tier)
        
        # Award XP for calendar claim
        try:
            from src.services.behavioral_tracking.xp_system import XPSystem
            xp_system = XPSystem()
            
            # Base XP for claiming calendar reward
            base_xp = 50
            # Bonus XP based on tier
            tier_multipliers = {
                'free': 1.0,
                'premium': 1.5,
                'pro': 2.0
            }
            xp_awarded = int(base_xp * tier_multipliers.get(user_tier, 1.0))
            
            # Award XP
            xp_result = xp_system.award_xp(
                user_id=user_id,
                amount=xp_awarded,
                action_type='calendar_reward',
                metadata={
                    'date': date_str,
                    'appointment_title': appointment_title,
                    'tier': user_tier
                }
            )
            
            # Add XP to reward
            if 'xp' not in reward:
                reward['xp'] = 0
            reward['xp'] += xp_awarded
            reward['xp_details'] = {
                'base': base_xp,
                'multiplier': tier_multipliers.get(user_tier, 1.0),
                'total': xp_awarded,
                'new_total': xp_result.get('new_total_xp', 0),
                'level_up': xp_result.get('leveled_up', False)
            }
        except Exception as e:
            print(f"[CalendarRewards] Could not award XP: {e}")
            reward['xp'] = reward.get('xp', 0)
        
        # In production, this would:
        # 1. Check if reward already claimed
        # 2. Award currency/XP to user (DONE)
        # 3. Unlock badges/features
        # 4. Apply discounts
        # 5. Log transaction
        
        return jsonify({
            'success': True,
            'rewards': reward,
            'message': 'Reward claimed successfully!'
        })
        
    except Exception as e:
        print(f"[CalendarRewards] Error: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@calendar_rewards_bp.route('/api/stats/monetization-milestones')
def get_monetization_milestones():
    """Get all monetization milestones"""
    try:
        monetization_cal = get_monetization_calendar()
        milestones = monetization_cal.get_monetization_appointments()
        
        return jsonify({
            'success': True,
            'milestones': milestones
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


def register_calendar_rewards_routes(app):
    """Register calendar rewards routes"""
    app.register_blueprint(calendar_rewards_bp, url_prefix='/vidgenerator')
    print("[Routes] Calendar rewards routes registered")

