"""
Guild/Clan System
Manages guilds, members, and guild activities
"""
from typing import Dict, Any, List, Optional
from datetime import datetime
import json
import os
import uuid

try:
    from backend.services.enhanced_user_profile_json import enhanced_user_profile_json
    from backend.services.unified_point_counter import unified_point_counter
except ImportError:
    enhanced_user_profile_json = None
    unified_point_counter = None


class GuildSystem:
    """System for managing guilds/clans"""
    
    def __init__(self, data_dir: str = 'data/guilds'):
        self.data_dir = data_dir
        os.makedirs(data_dir, exist_ok=True)
        
        # In-memory storage
        self.guilds = {}  # guild_id -> guild_data
        self.user_guilds = {}  # user_id -> guild_id
        self.guild_members = {}  # guild_id -> [member_data]
        self.guild_requests = {}  # guild_id -> [request_data]
    
    def create_guild(self, creator_id: str, name: str, description: str = '', 
                    tag: str = '', privacy: str = 'public') -> Dict[str, Any]:
        """
        Create a new guild
        
        Args:
            creator_id: User creating the guild
            name: Guild name
            description: Guild description
            tag: Guild tag (short identifier)
            privacy: 'public' or 'private'
            
        Returns:
            Guild creation result
        """
        # Validate name
        if not name or len(name) < 3 or len(name) > 50:
            return {
                'success': False,
                'error': 'Guild name must be between 3 and 50 characters'
            }
        
        # Check if user already in a guild
        if creator_id in self.user_guilds:
            return {
                'success': False,
                'error': 'You are already in a guild'
            }
        
        # Generate guild ID
        guild_id = f"guild_{uuid.uuid4().hex[:12]}"
        
        # Create guild
        guild_data = {
            'guild_id': guild_id,
            'name': name,
            'description': description,
            'tag': tag or name[:4].upper(),
            'privacy': privacy,
            'creator_id': creator_id,
            'created_at': datetime.utcnow().isoformat(),
            'member_count': 1,
            'max_members': 50,
            'level': 1,
            'points': 0,
            'trophies': 0
        }
        
        self.guilds[guild_id] = guild_data
        
        # Add creator as leader
        self.user_guilds[creator_id] = guild_id
        self.guild_members[guild_id] = [{
            'user_id': creator_id,
            'role': 'leader',
            'joined_at': datetime.utcnow().isoformat(),
            'contribution': 0
        }]
        
        # Save
        self._save_guild(guild_id)
        
        return {
            'success': True,
            'guild': guild_data,
            'message': 'Guild created successfully'
        }
    
    def join_guild(self, user_id: str, guild_id: str) -> Dict[str, Any]:
        """
        Join a guild
        
        Args:
            user_id: User joining
            guild_id: Guild to join
            
        Returns:
            Join result
        """
        if guild_id not in self.guilds:
            return {
                'success': False,
                'error': 'Guild not found'
            }
        
        guild = self.guilds[guild_id]
        
        # Check if already in a guild
        if user_id in self.user_guilds:
            return {
                'success': False,
                'error': 'You are already in a guild'
            }
        
        # Check if guild is full
        if guild['member_count'] >= guild['max_members']:
            return {
                'success': False,
                'error': 'Guild is full'
            }
        
        # Check privacy
        if guild['privacy'] == 'private':
            # Check if there's a pending request
            if not self._has_pending_request(user_id, guild_id):
                return {
                    'success': False,
                    'error': 'Guild is private. Request to join first.'
                }
        
        # Add member
        self.user_guilds[user_id] = guild_id
        if guild_id not in self.guild_members:
            self.guild_members[guild_id] = []
        
        self.guild_members[guild_id].append({
            'user_id': user_id,
            'role': 'member',
            'joined_at': datetime.utcnow().isoformat(),
            'contribution': 0
        })
        
        guild['member_count'] += 1
        
        # Save
        self._save_guild(guild_id)
        
        return {
            'success': True,
            'message': 'Joined guild successfully',
            'guild': guild
        }
    
    def leave_guild(self, user_id: str) -> Dict[str, Any]:
        """Leave current guild"""
        if user_id not in self.user_guilds:
            return {
                'success': False,
                'error': 'Not in a guild'
            }
        
        guild_id = self.user_guilds[user_id]
        guild = self.guilds[guild_id]
        
        # Check if leader
        member = next((m for m in self.guild_members[guild_id] if m['user_id'] == user_id), None)
        if member and member['role'] == 'leader':
            # Leader leaving - disband or transfer leadership
            if guild['member_count'] == 1:
                # Disband guild
                return self.disband_guild(guild_id, user_id)
            else:
                return {
                    'success': False,
                    'error': 'Leader must transfer leadership before leaving'
                }
        
        # Remove member
        del self.user_guilds[user_id]
        self.guild_members[guild_id] = [
            m for m in self.guild_members[guild_id] if m['user_id'] != user_id
        ]
        guild['member_count'] -= 1
        
        # Save
        self._save_guild(guild_id)
        
        return {
            'success': True,
            'message': 'Left guild successfully'
        }
    
    def disband_guild(self, guild_id: str, leader_id: str) -> Dict[str, Any]:
        """Disband a guild (leader only)"""
        if guild_id not in self.guilds:
            return {
                'success': False,
                'error': 'Guild not found'
            }
        
        guild = self.guilds[guild_id]
        
        # Verify leader
        member = next((m for m in self.guild_members[guild_id] if m['user_id'] == leader_id), None)
        if not member or member['role'] != 'leader':
            return {
                'success': False,
                'error': 'Only leader can disband guild'
            }
        
        # Remove all members
        for member in self.guild_members[guild_id]:
            if member['user_id'] in self.user_guilds:
                del self.user_guilds[member['user_id']]
        
        # Remove guild
        del self.guilds[guild_id]
        del self.guild_members[guild_id]
        
        # Delete file
        try:
            file_path = os.path.join(self.data_dir, f'{guild_id}.json')
            if os.path.exists(file_path):
                os.remove(file_path)
        except:
            pass
        
        return {
            'success': True,
            'message': 'Guild disbanded'
        }
    
    def get_guild(self, guild_id: str) -> Optional[Dict[str, Any]]:
        """Get guild information"""
        return self.guilds.get(guild_id)
    
    def get_user_guild(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user's current guild"""
        if user_id not in self.user_guilds:
            return None
        
        guild_id = self.user_guilds[user_id]
        return self.get_guild(guild_id)
    
    def get_guild_members(self, guild_id: str) -> List[Dict[str, Any]]:
        """Get guild members"""
        return self.guild_members.get(guild_id, [])
    
    def get_guild_leaderboard(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get guild leaderboard sorted by points"""
        guilds_list = list(self.guilds.values())
        guilds_list.sort(key=lambda g: g.get('points', 0), reverse=True)
        return guilds_list[:limit]
    
    def add_guild_points(self, guild_id: str, points: int, user_id: str) -> Dict[str, Any]:
        """Add points to guild (from member contribution)"""
        if guild_id not in self.guilds:
            return {
                'success': False,
                'error': 'Guild not found'
            }
        
        guild = self.guilds[guild_id]
        guild['points'] = guild.get('points', 0) + points
        
        # Update member contribution
        for member in self.guild_members[guild_id]:
            if member['user_id'] == user_id:
                member['contribution'] = member.get('contribution', 0) + points
                break
        
        # Save
        self._save_guild(guild_id)
        
        return {
            'success': True,
            'guild_points': guild['points']
        }
    
    def _has_pending_request(self, user_id: str, guild_id: str) -> bool:
        """Check if user has pending request to join guild"""
        if guild_id not in self.guild_requests:
            return False
        
        for req in self.guild_requests[guild_id]:
            if req['user_id'] == user_id and req['status'] == 'pending':
                return True
        return False
    
    def _save_guild(self, guild_id: str):
        """Save guild to file"""
        try:
            file_path = os.path.join(self.data_dir, f'{guild_id}.json')
            guild_data = {
                'guild': self.guilds[guild_id],
                'members': self.guild_members.get(guild_id, []),
                'updated_at': datetime.utcnow().isoformat()
            }
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(guild_data, f, indent=2)
        except Exception as e:
            print(f"[GuildSystem] Error saving guild {guild_id}: {e}", flush=True)


# Global instance
guild_system = GuildSystem()
