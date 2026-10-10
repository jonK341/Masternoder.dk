"""
Social Features System
Friends, guilds, teams, and social interactions
"""
import uuid
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from collections import defaultdict


class FriendRequest:
    """Represents a friend request"""
    
    def __init__(self, request_id: str, from_user_id: str, to_user_id: str):
        self.id = request_id
        self.from_user_id = from_user_id
        self.to_user_id = to_user_id
        self.status = 'pending'  # pending, accepted, rejected
        self.created_at = datetime.utcnow()
        self.responded_at = None
    
    def to_dict(self):
        """Convert to dictionary"""
        return {
            'id': self.id,
            'from_user_id': self.from_user_id,
            'to_user_id': self.to_user_id,
            'status': self.status,
            'created_at': self.created_at.isoformat(),
            'responded_at': self.responded_at.isoformat() if self.responded_at else None
        }


class Guild:
    """Represents a guild/team"""
    
    def __init__(self, guild_id: str, name: str, leader_id: str, description: str = ''):
        self.id = guild_id
        self.name = name
        self.leader_id = leader_id
        self.description = description
        self.members = [leader_id]
        self.max_members = 50
        self.level = 1
        self.total_xp = 0
        self.created_at = datetime.utcnow()
        self.settings = {
            'public': True,
            'auto_accept': False,
            'min_level': 1
        }
    
    def to_dict(self):
        """Convert to dictionary"""
        return {
            'id': self.id,
            'name': self.name,
            'leader_id': self.leader_id,
            'description': self.description,
            'members_count': len(self.members),
            'max_members': self.max_members,
            'level': self.level,
            'total_xp': self.total_xp,
            'created_at': self.created_at.isoformat(),
            'settings': self.settings
        }


class SocialSystem:
    """Manages social features"""
    
    def __init__(self):
        """Initialize social system"""
        self.friends = defaultdict(set)  # {user_id: {friend_ids}}
        self.friend_requests = {}  # {request_id: FriendRequest}
        self.user_friend_requests = defaultdict(list)  # {user_id: [request_ids]}
        self.guilds = {}  # {guild_id: Guild}
        self.user_guilds = {}  # {user_id: guild_id}
        self.guild_requests = defaultdict(list)  # {guild_id: [user_ids]}
    
    def send_friend_request(self, from_user_id: str, to_user_id: str) -> Dict[str, Any]:
        """Send a friend request"""
        if from_user_id == to_user_id:
            return {'success': False, 'error': 'Cannot friend yourself'}
        
        # Check if already friends
        if to_user_id in self.friends[from_user_id]:
            return {'success': False, 'error': 'Already friends'}
        
        # Check if request already exists
        for req in self.friend_requests.values():
            if (req.from_user_id == from_user_id and req.to_user_id == to_user_id and 
                req.status == 'pending'):
                return {'success': False, 'error': 'Friend request already sent'}
        
        request_id = str(uuid.uuid4())
        request = FriendRequest(request_id, from_user_id, to_user_id)
        self.friend_requests[request_id] = request
        self.user_friend_requests[to_user_id].append(request_id)
        
        return {
            'success': True,
            'request_id': request_id,
            'request': request.to_dict()
        }
    
    def respond_to_friend_request(self, request_id: str, user_id: str, 
                                 accept: bool) -> Dict[str, Any]:
        """Respond to a friend request"""
        request = self.friend_requests.get(request_id)
        if not request:
            return {'success': False, 'error': 'Request not found'}
        
        if request.to_user_id != user_id:
            return {'success': False, 'error': 'Not your request'}
        
        if request.status != 'pending':
            return {'success': False, 'error': 'Request already responded to'}
        
        request.status = 'accepted' if accept else 'rejected'
        request.responded_at = datetime.utcnow()
        
        if accept:
            # Add as friends
            self.friends[request.from_user_id].add(request.to_user_id)
            self.friends[request.to_user_id].add(request.from_user_id)
        
        return {
            'success': True,
            'request': request.to_dict(),
            'friends': list(self.friends[user_id])
        }
    
    def get_friends(self, user_id: str) -> List[str]:
        """Get list of friends"""
        return list(self.friends.get(user_id, set()))
    
    def get_friend_requests(self, user_id: str) -> Dict[str, List[Dict]]:
        """Get friend requests for user"""
        incoming = []
        outgoing = []
        
        for request in self.friend_requests.values():
            if request.to_user_id == user_id and request.status == 'pending':
                incoming.append(request.to_dict())
            elif request.from_user_id == user_id and request.status == 'pending':
                outgoing.append(request.to_dict())
        
        return {
            'incoming': incoming,
            'outgoing': outgoing
        }
    
    def remove_friend(self, user_id: str, friend_id: str) -> Dict[str, Any]:
        """Remove a friend"""
        if friend_id in self.friends[user_id]:
            self.friends[user_id].discard(friend_id)
            self.friends[friend_id].discard(user_id)
            return {'success': True, 'message': 'Friend removed'}
        return {'success': False, 'error': 'Not friends'}
    
    def create_guild(self, name: str, leader_id: str, description: str = '') -> Dict[str, Any]:
        """Create a new guild"""
        # Check if user is already in a guild
        if leader_id in self.user_guilds:
            return {'success': False, 'error': 'Already in a guild'}
        
        guild_id = str(uuid.uuid4())
        guild = Guild(guild_id, name, leader_id, description)
        self.guilds[guild_id] = guild
        self.user_guilds[leader_id] = guild_id
        
        return {
            'success': True,
            'guild_id': guild_id,
            'guild': guild.to_dict()
        }
    
    def join_guild(self, guild_id: str, user_id: str) -> Dict[str, Any]:
        """Join a guild"""
        guild = self.guilds.get(guild_id)
        if not guild:
            return {'success': False, 'error': 'Guild not found'}
        
        if user_id in self.user_guilds:
            return {'success': False, 'error': 'Already in a guild'}
        
        if len(guild.members) >= guild.max_members:
            return {'success': False, 'error': 'Guild is full'}
        
        if guild.settings.get('auto_accept', False):
            guild.members.append(user_id)
            self.user_guilds[user_id] = guild_id
            return {
                'success': True,
                'guild': guild.to_dict()
            }
        else:
            # Add to request queue
            if user_id not in self.guild_requests[guild_id]:
                self.guild_requests[guild_id].append(user_id)
            return {
                'success': True,
                'pending': True,
                'message': 'Request sent to guild leader'
            }
    
    def get_user_guild(self, user_id: str) -> Optional[Dict]:
        """Get user's guild"""
        guild_id = self.user_guilds.get(user_id)
        if guild_id:
            guild = self.guilds.get(guild_id)
            if guild:
                return guild.to_dict()
        return None
    
    def get_guild_members(self, guild_id: str) -> List[str]:
        """Get guild members"""
        guild = self.guilds.get(guild_id)
        if guild:
            return guild.members
        return []
    
    def leave_guild(self, user_id: str, guild_id: str) -> Dict[str, Any]:
        """Leave a guild"""
        guild = self.guilds.get(guild_id)
        if not guild:
            return {'success': False, 'error': 'Guild not found'}
        
        if user_id not in guild.members:
            return {'success': False, 'error': 'You are not a member of this guild'}
        
        if user_id == guild.leader_id:
            return {'success': False, 'error': 'Leader cannot leave guild. Transfer leadership first.'}
        
        guild.members.remove(user_id)
        return {'success': True, 'message': 'Left guild successfully'}
    
    def invite_to_guild(self, user_id: str, guild_id: str, invitee_id: str) -> Dict[str, Any]:
        """Invite a user to join a guild"""
        guild = self.guilds.get(guild_id)
        if not guild:
            return {'success': False, 'error': 'Guild not found'}
        
        if user_id not in guild.members:
            return {'success': False, 'error': 'You must be a member to invite others'}
        
        if invitee_id in guild.members:
            return {'success': False, 'error': 'User is already a member'}
        
        if len(guild.members) >= guild.max_members:
            return {'success': False, 'error': 'Guild is full'}
        
        # Add to guild requests
        if invitee_id not in self.guild_requests[guild_id]:
            self.guild_requests[guild_id].append(invitee_id)
        
        return {'success': True, 'message': f'Invitation sent to {invitee_id}'}
    
    def kick_from_guild(self, user_id: str, guild_id: str, member_id: str) -> Dict[str, Any]:
        """Kick a member from a guild"""
        guild = self.guilds.get(guild_id)
        if not guild:
            return {'success': False, 'error': 'Guild not found'}
        
        if user_id != guild.leader_id:
            return {'success': False, 'error': 'Only the leader can kick members'}
        
        if member_id not in guild.members:
            return {'success': False, 'error': 'User is not a member of this guild'}
        
        if member_id == guild.leader_id:
            return {'success': False, 'error': 'Cannot kick the leader'}
        
        guild.members.remove(member_id)
        return {'success': True, 'message': f'{member_id} has been removed from the guild'}
    
    def get_guild_leaderboard(self, limit: int = 20) -> List[Dict]:
        """Get guild leaderboard"""
        guilds = list(self.guilds.values())
        guilds.sort(key=lambda g: g.total_xp, reverse=True)
        return [g.to_dict() for g in guilds[:limit]]
    
    def get_social_stats(self, user_id: str) -> Dict[str, Any]:
        """Get social statistics for user"""
        friends = self.get_friends(user_id)
        guild = self.get_user_guild(user_id)
        requests = self.get_friend_requests(user_id)
        
        return {
            'friends_count': len(friends),
            'friends': friends[:10],  # First 10 friends
            'guild': guild,
            'friend_requests': {
                'incoming_count': len(requests['incoming']),
                'outgoing_count': len(requests['outgoing'])
            }
        }


# Global instance
social_system = SocialSystem()

