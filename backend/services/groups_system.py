"""
Groups System - User Groups Management
Group creation, membership, and collaboration
"""
from typing import Dict, Any, Optional, List
from datetime import datetime
from collections import defaultdict
import uuid

try:
    from backend.services.unified_points_database import UnifiedPointsDatabase
    from backend.services.point_connection_system import PointConnectionSystem
    unified_points_db = UnifiedPointsDatabase()
    point_connection = PointConnectionSystem()
except ImportError:
    unified_points_db = None
    point_connection = None


class GroupsSystem:
    """
    Groups System
    - Group creation and management
    - Membership management
    - Group activities and collaboration
    - Group points and achievements
    """
    
    def __init__(self):
        self.groups = {}  # {group_id: group_data}
        self.group_members = defaultdict(set)  # {group_id: {user_ids}}
        self.group_activities = defaultdict(list)  # {group_id: [activity_data]}
        self.user_groups = defaultdict(set)  # {user_id: {group_ids}}
    
    def create_group(self, creator_id: str, group_name: str, group_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new group"""
        group_id = str(uuid.uuid4())
        
        group = {
            'group_id': group_id,
            'group_name': group_name,
            'creator_id': creator_id,
            'description': group_data.get('description', ''),
            'group_type': group_data.get('group_type', 'general'),  # general, quest, battle, research
            'privacy': group_data.get('privacy', 'public'),  # public, private, invite_only
            'max_members': group_data.get('max_members', 50),
            'created_at': datetime.utcnow().isoformat(),
            'status': 'active',
            'group_points': 0,
            'level': 1,
            'metadata': group_data.get('metadata', {})
        }
        
        self.groups[group_id] = group
        self.group_members[group_id].add(creator_id)
        self.user_groups[creator_id].add(group_id)
        
        return {
            'success': True,
            'group_id': group_id,
            'group': group
        }
    
    def join_group(self, user_id: str, group_id: str) -> Dict[str, Any]:
        """Join a group"""
        if group_id not in self.groups:
            return {'success': False, 'error': 'Group not found'}
        
        group = self.groups[group_id]
        
        # Check if already member
        if user_id in self.group_members[group_id]:
            return {'success': False, 'error': 'Already a member'}
        
        # Check max members
        if len(self.group_members[group_id]) >= group.get('max_members', 50):
            return {'success': False, 'error': 'Group is full'}
        
        # Add member
        self.group_members[group_id].add(user_id)
        self.user_groups[user_id].add(group_id)
        
        # Record activity
        self.group_activities[group_id].append({
            'type': 'member_joined',
            'user_id': user_id,
            'timestamp': datetime.utcnow().isoformat()
        })
        
        return {
            'success': True,
            'group_id': group_id,
            'user_id': user_id,
            'member_count': len(self.group_members[group_id])
        }
    
    def leave_group(self, user_id: str, group_id: str) -> Dict[str, Any]:
        """Leave a group"""
        if group_id not in self.groups:
            return {'success': False, 'error': 'Group not found'}
        
        if user_id not in self.group_members[group_id]:
            return {'success': False, 'error': 'Not a member'}
        
        # Remove member
        self.group_members[group_id].discard(user_id)
        self.user_groups[user_id].discard(group_id)
        
        # Record activity
        self.group_activities[group_id].append({
            'type': 'member_left',
            'user_id': user_id,
            'timestamp': datetime.utcnow().isoformat()
        })
        
        return {
            'success': True,
            'group_id': group_id,
            'user_id': user_id
        }
    
    def get_group(self, group_id: str) -> Dict[str, Any]:
        """Get group information"""
        if group_id not in self.groups:
            return {'success': False, 'error': 'Group not found'}
        
        group = self.groups[group_id].copy()
        group['member_count'] = len(self.group_members[group_id])
        group['members'] = list(self.group_members[group_id])
        
        return {
            'success': True,
            'group': group
        }
    
    def get_user_groups(self, user_id: str) -> Dict[str, Any]:
        """Get all groups a user belongs to"""
        group_ids = list(self.user_groups.get(user_id, set()))
        groups = []
        
        for group_id in group_ids:
            if group_id in self.groups:
                group = self.groups[group_id].copy()
                group['member_count'] = len(self.group_members[group_id])
                groups.append(group)
        
        return {
            'success': True,
            'user_id': user_id,
            'groups': groups,
            'total_groups': len(groups)
        }
    
    def add_group_activity(self, group_id: str, activity_type: str, 
                          user_id: str, activity_data: Dict[str, Any]) -> Dict[str, Any]:
        """Add activity to group"""
        if group_id not in self.groups:
            return {'success': False, 'error': 'Group not found'}
        
        activity = {
            'activity_id': str(uuid.uuid4()),
            'type': activity_type,
            'user_id': user_id,
            'timestamp': datetime.utcnow().isoformat(),
            'data': activity_data
        }
        
        self.group_activities[group_id].append(activity)
        
        # Keep only last 100 activities
        if len(self.group_activities[group_id]) > 100:
            self.group_activities[group_id] = self.group_activities[group_id][-100:]
        
        return {
            'success': True,
            'activity_id': activity['activity_id'],
            'activity': activity
        }
    
    def get_group_activities(self, group_id: str, limit: int = 50) -> Dict[str, Any]:
        """Get group activities"""
        if group_id not in self.groups:
            return {'success': False, 'error': 'Group not found'}
        
        activities = self.group_activities.get(group_id, [])
        recent_activities = activities[-limit:] if len(activities) > limit else activities
        
        return {
            'success': True,
            'group_id': group_id,
            'activities': recent_activities,
            'total_activities': len(activities)
        }
    
    def add_group_points(self, group_id: str, points: int, source: str = 'activity') -> Dict[str, Any]:
        """Add points to group"""
        if group_id not in self.groups:
            return {'success': False, 'error': 'Group not found'}
        
        self.groups[group_id]['group_points'] = self.groups[group_id].get('group_points', 0) + points
        
        # Calculate level based on points (1000 points per level)
        new_level = (self.groups[group_id]['group_points'] // 1000) + 1
        self.groups[group_id]['level'] = new_level
        
        return {
            'success': True,
            'group_id': group_id,
            'points_added': points,
            'total_points': self.groups[group_id]['group_points'],
            'level': new_level
        }


# Global instance
groups_system = GroupsSystem()

