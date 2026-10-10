"""
Real-time Events System
Live events, time-limited challenges, event notifications
"""
import uuid
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from collections import defaultdict


class GameEvent:
    """Represents a game event"""
    
    def __init__(self, event_id: str, name: str, description: str, event_type: str,
                 start_time: datetime, end_time: datetime, rewards: Dict = None):
        self.id = event_id
        self.name = name
        self.description = description
        self.type = event_type  # double_xp, special_challenge, tournament, seasonal
        self.start_time = start_time
        self.end_time = end_time
        self.rewards = rewards or {}
        self.participants = []
        self.status = 'upcoming'  # upcoming, active, ended
        self.notifications_sent = False
    
    def to_dict(self):
        """Convert to dictionary"""
        now = datetime.utcnow()
        if now < self.start_time:
            status = 'upcoming'
            time_until = str(self.start_time - now)
        elif now <= self.end_time:
            status = 'active'
            time_until = str(self.end_time - now)
        else:
            status = 'ended'
            time_until = None
        
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'type': self.type,
            'start_time': self.start_time.isoformat(),
            'end_time': self.end_time.isoformat(),
            'status': status,
            'time_until': time_until,
            'rewards': self.rewards,
            'participants_count': len(self.participants)
        }


class EventsSystem:
    """Manages real-time events"""
    
    def __init__(self):
        """Initialize events system"""
        self.events = {}
        self.user_events = defaultdict(list)  # {user_id: [event_ids]}
        self.event_notifications = defaultdict(list)  # {user_id: [notifications]}
        self._initialize_default_events()
    
    def _initialize_default_events(self):
        """Initialize default events"""
        # Daily Double XP Event
        daily_double_xp = GameEvent(
            str(uuid.uuid4()),
            'Double XP Day',
            'Earn double XP on all activities today!',
            'double_xp',
            datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0),
            datetime.utcnow().replace(hour=23, minute=59, second=59, microsecond=999999),
            {'xp_multiplier': 2.0}
        )
        self.events[daily_double_xp.id] = daily_double_xp
        
        # Weekly Special Challenge
        weekly_challenge = GameEvent(
            str(uuid.uuid4()),
            'Weekly Mega Challenge',
            'Complete special weekly challenges for exclusive rewards!',
            'special_challenge',
            datetime.utcnow().replace(hour=12, minute=0, second=0, microsecond=0),
            datetime.utcnow() + timedelta(days=7),
            {'bonus_xp': 500, 'currency': 200}
        )
        self.events[weekly_challenge.id] = weekly_challenge
    
    def create_event(self, name: str, description: str, event_type: str,
                    start_time: datetime, end_time: datetime, rewards: Dict = None) -> Dict[str, Any]:
        """Create a new event"""
        event_id = str(uuid.uuid4())
        event = GameEvent(event_id, name, description, event_type, start_time, end_time, rewards)
        self.events[event_id] = event
        
        return {
            'success': True,
            'event_id': event_id,
            'event': event.to_dict()
        }
    
    def get_active_events(self) -> List[Dict]:
        """Get all active events"""
        now = datetime.utcnow()
        active = []
        
        for event in self.events.values():
            if event.start_time <= now <= event.end_time:
                event.status = 'active'
                active.append(event.to_dict())
            elif now < event.start_time:
                event.status = 'upcoming'
                active.append(event.to_dict())
        
        active.sort(key=lambda e: e['start_time'])
        return active
    
    def get_upcoming_events(self, limit: int = 5) -> List[Dict]:
        """Get upcoming events"""
        now = datetime.utcnow()
        upcoming = []
        
        for event in self.events.values():
            if now < event.start_time:
                upcoming.append(event.to_dict())
        
        upcoming.sort(key=lambda e: e['start_time'])
        return upcoming[:limit]
    
    def join_event(self, event_id: str, user_id: str) -> Dict[str, Any]:
        """Join an event"""
        event = self.events.get(event_id)
        if not event:
            return {'success': False, 'error': 'Event not found'}
        
        now = datetime.utcnow()
        if now < event.start_time:
            return {'success': False, 'error': 'Event has not started yet'}
        if now > event.end_time:
            return {'success': False, 'error': 'Event has ended'}
        
        if user_id not in event.participants:
            event.participants.append(user_id)
        
        if event_id not in self.user_events[user_id]:
            self.user_events[user_id].append(event_id)
        
        return {
            'success': True,
            'event': event.to_dict()
        }
    
    def get_user_events(self, user_id: str) -> List[Dict]:
        """Get events user is participating in"""
        event_ids = self.user_events.get(user_id, [])
        events = []
        
        for event_id in event_ids:
            event = self.events.get(event_id)
            if event:
                events.append(event.to_dict())
        
        return events
    
    def add_notification(self, user_id: str, message: str, notification_type: str = 'info',
                        event_id: str = None) -> Dict[str, Any]:
        """Add a notification for user"""
        notification = {
            'id': str(uuid.uuid4()),
            'message': message,
            'type': notification_type,  # info, success, warning, error, event
            'event_id': event_id,
            'created_at': datetime.utcnow().isoformat(),
            'read': False
        }
        
        self.event_notifications[user_id].append(notification)
        
        # Keep only last 50 notifications
        if len(self.event_notifications[user_id]) > 50:
            self.event_notifications[user_id] = self.event_notifications[user_id][-50:]
        
        return notification
    
    def get_notifications(self, user_id: str, unread_only: bool = False) -> List[Dict]:
        """Get user notifications"""
        notifications = self.event_notifications.get(user_id, [])
        
        if unread_only:
            notifications = [n for n in notifications if not n.get('read', False)]
        
        notifications.sort(key=lambda n: n['created_at'], reverse=True)
        return notifications
    
    def mark_notification_read(self, user_id: str, notification_id: str) -> Dict[str, Any]:
        """Mark notification as read"""
        notifications = self.event_notifications.get(user_id, [])
        
        for notification in notifications:
            if notification['id'] == notification_id:
                notification['read'] = True
                return {'success': True, 'notification': notification}
        
        return {'success': False, 'error': 'Notification not found'}
    
    def get_event_leaderboard(self, event_id: str, limit: int = 20) -> List[Dict]:
        """Get event leaderboard"""
        event = self.events.get(event_id)
        if not event:
            return []
        
        # This would integrate with actual player stats
        # For now, return participant list
        leaderboard = []
        for user_id in event.participants:
            leaderboard.append({
                'user_id': user_id,
                'score': 0,  # Would calculate from event participation
                'rank': 0
            })
        
        return leaderboard[:limit]


# Global instance
events_system = EventsSystem()

