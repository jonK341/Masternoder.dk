"""
Chat Points System
Awards points for chatting and messaging activities
"""

from typing import Dict, Any, Optional
from datetime import datetime
import json

try:
    from src.services.behavioral_tracking.xp_system import XPSystem
    xp_system = XPSystem()
except ImportError:
    xp_system = None


class ChatPointsSystem:
    """Manages points awarded for chat activities"""
    
    def __init__(self):
        self.point_rewards = {
            'send_message': 1,  # 1 point per message
            'first_message': 10,  # Bonus for first message
            'message_streak': 5,  # Bonus for consecutive days
            'helpful_message': 5,  # Bonus for helpful/quality messages
            'long_message': 2,  # Bonus for longer messages (>100 chars)
            'daily_chat': 20,  # Bonus for chatting daily
            'weekly_chat': 50,  # Bonus for chatting weekly
            'monthly_chat': 200  # Bonus for chatting monthly
        }
    
    def award_chat_points(
        self,
        user_id: str,
        action_type: str,
        message_length: int = 0,
        metadata: Dict = None
    ) -> Dict[str, Any]:
        """Award points for chat activity"""
        if not xp_system:
            return {'points_awarded': 0, 'total_chat_points': 0}
        
        if metadata is None:
            metadata = {}
        
        result = {
            'points_awarded': 0,
            'total_chat_points': 0,
            'bonuses': []
        }
        
        try:
            profile = xp_system.get_user_profile(user_id)
            behavioral = profile.get('behavioral', {})
            chat_stats = behavioral.get('chat_stats', {})
            
            # Base points for sending message
            if action_type == 'send_message':
                base_points = self.point_rewards.get('send_message', 1)
                result['points_awarded'] += base_points
                
                # First message bonus
                total_messages = chat_stats.get('total_messages', 0)
                if total_messages == 0:
                    bonus = self.point_rewards.get('first_message', 10)
                    result['points_awarded'] += bonus
                    result['bonuses'].append({'type': 'first_message', 'points': bonus})
                
                # Long message bonus
                if message_length > 100:
                    bonus = self.point_rewards.get('long_message', 2)
                    result['points_awarded'] += bonus
                    result['bonuses'].append({'type': 'long_message', 'points': bonus})
                
                # Update chat stats
                chat_stats['total_messages'] = total_messages + 1
                chat_stats['last_message_time'] = datetime.now().isoformat()
                
                # Check for streaks
                streak_bonus = self._check_message_streak(user_id, chat_stats)
                if streak_bonus > 0:
                    result['points_awarded'] += streak_bonus
                    result['bonuses'].append({'type': 'message_streak', 'points': streak_bonus})
            
            # Update total chat points
            current_chat_points = chat_stats.get('total_chat_points', 0)
            new_chat_points = current_chat_points + result['points_awarded']
            chat_stats['total_chat_points'] = new_chat_points
            result['total_chat_points'] = new_chat_points
            
            # Check for daily/weekly/monthly bonuses
            daily_bonus = self._check_daily_bonus(user_id, chat_stats)
            if daily_bonus > 0:
                result['points_awarded'] += daily_bonus
                result['total_chat_points'] += daily_bonus
                result['bonuses'].append({'type': 'daily_chat', 'points': daily_bonus})
            
            # Update behavioral stats
            behavioral['chat_stats'] = chat_stats
            profile['behavioral'] = behavioral
            
            # Save profile
            xp_system.save_user_profile(user_id, profile)
            
            # Also award regular XP for chat activity
            xp_metadata = {
                'action_type': action_type,
                'message_length': message_length,
                'chat_points_awarded': result['points_awarded'],
                **metadata
            }
            xp_awarded = xp_system.track_action(
                user_id=user_id,
                action_type='chat_activity',
                metadata=xp_metadata
            )
            
            print(f"[ChatPoints] User {user_id} earned {result['points_awarded']} chat points (total: {result['total_chat_points']})")
            if result['bonuses']:
                for bonus in result['bonuses']:
                    print(f"  - {bonus['type']}: +{bonus['points']} points")
            
            return result
        except Exception as e:
            print(f"[ChatPoints] Error awarding chat points: {e}")
            import traceback
            traceback.print_exc()
            return result
    
    def _check_message_streak(self, user_id: str, chat_stats: Dict) -> int:
        """Check for message streak bonus"""
        try:
            last_message_time = chat_stats.get('last_message_time')
            if not last_message_time:
                return 0
            
            current_streak = chat_stats.get('current_streak', 0)
            streak_days = chat_stats.get('streak_days', [])
            
            today = datetime.now().date().isoformat()
            
            # Check if already counted today
            if today in streak_days:
                return 0
            
            # Check if consecutive day
            yesterday = (datetime.now().date() - datetime.timedelta(days=1)).isoformat()
            if yesterday in streak_days or current_streak == 0:
                # New or continuing streak
                current_streak += 1
                streak_days.append(today)
                
                # Keep only last 30 days
                if len(streak_days) > 30:
                    streak_days = streak_days[-30:]
                
                chat_stats['current_streak'] = current_streak
                chat_stats['streak_days'] = streak_days
                
                # Award streak bonus every 3 days
                if current_streak % 3 == 0:
                    return self.point_rewards.get('message_streak', 5)
            else:
                # Streak broken, reset
                chat_stats['current_streak'] = 1
                chat_stats['streak_days'] = [today]
            
            return 0
        except Exception as e:
            print(f"[ChatPoints] Error checking streak: {e}")
            return 0
    
    def _check_daily_bonus(self, user_id: str, chat_stats: Dict) -> int:
        """Check for daily/weekly/monthly chat bonuses"""
        try:
            today = datetime.now().date().isoformat()
            daily_chats = chat_stats.get('daily_chats', {})
            
            # Check if already awarded today
            if today in daily_chats:
                return 0
            
            # Mark as chatted today
            daily_chats[today] = True
            
            # Count consecutive days
            consecutive_days = len([d for d in sorted(daily_chats.keys()) if d >= (datetime.now().date() - datetime.timedelta(days=30)).isoformat()])
            
            # Daily bonus (first message of the day)
            bonus = self.point_rewards.get('daily_chat', 20)
            
            # Weekly bonus (7 consecutive days)
            if consecutive_days >= 7 and consecutive_days % 7 == 0:
                bonus += self.point_rewards.get('weekly_chat', 50)
            
            # Monthly bonus (30 consecutive days)
            if consecutive_days >= 30 and consecutive_days % 30 == 0:
                bonus += self.point_rewards.get('monthly_chat', 200)
            
            # Keep only last 90 days
            cutoff_date = (datetime.now().date() - datetime.timedelta(days=90)).isoformat()
            daily_chats = {k: v for k, v in daily_chats.items() if k >= cutoff_date}
            
            chat_stats['daily_chats'] = daily_chats
            
            return bonus
        except Exception as e:
            print(f"[ChatPoints] Error checking daily bonus: {e}")
            return 0
    
    def get_chat_points(self, user_id: str) -> Dict[str, Any]:
        """Get user's chat points and stats"""
        if not xp_system:
            return {'total_chat_points': 0, 'stats': {}}
        
        try:
            profile = xp_system.get_user_profile(user_id)
            behavioral = profile.get('behavioral', {})
            chat_stats = behavioral.get('chat_stats', {})
            
            return {
                'total_chat_points': chat_stats.get('total_chat_points', 0),
                'total_messages': chat_stats.get('total_messages', 0),
                'current_streak': chat_stats.get('current_streak', 0),
                'daily_chats': len(chat_stats.get('daily_chats', {})),
                'last_message_time': chat_stats.get('last_message_time')
            }
        except Exception as e:
            print(f"[ChatPoints] Error getting chat points: {e}")
            return {'total_chat_points': 0, 'stats': {}}


# Global instance
chat_points_system = ChatPointsSystem()

