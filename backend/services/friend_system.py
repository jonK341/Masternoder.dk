"""
Friend System
Manages user friendships, friend requests, and friend activities
"""
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import json
import os

try:
    from backend.services.enhanced_user_profile_json import enhanced_user_profile_json
except ImportError:
    enhanced_user_profile_json = None


class FriendSystem:
    """System for managing user friendships"""
    
    def __init__(self, data_dir: str = 'data/friends'):
        self.data_dir = data_dir
        os.makedirs(data_dir, exist_ok=True)
        
        # In-memory storage
        self.friendships = {}  # user_id -> [friend_ids]
        self.friend_requests = {}  # user_id -> [request_data]
        self.blocked_users = {}  # user_id -> [blocked_user_ids]
    
    def send_friend_request(self, from_user_id: str, to_user_id: str, message: str = '') -> Dict[str, Any]:
        """
        Send a friend request
        
        Args:
            from_user_id: User sending the request
            to_user_id: User receiving the request
            message: Optional message
            
        Returns:
            Request result
        """
        if from_user_id == to_user_id:
            return {
                'success': False,
                'error': 'Cannot send friend request to yourself'
            }
        
        # Check if already friends
        if self.are_friends(from_user_id, to_user_id):
            return {
                'success': False,
                'error': 'Already friends'
            }
        
        # Check if already blocked
        if self.is_blocked(from_user_id, to_user_id):
            return {
                'success': False,
                'error': 'User is blocked'
            }
        
        # Check if request already exists
        if self.has_pending_request(from_user_id, to_user_id):
            return {
                'success': False,
                'error': 'Friend request already sent'
            }
        
        # Create request
        request_data = {
            'from_user_id': from_user_id,
            'to_user_id': to_user_id,
            'message': message,
            'status': 'pending',
            'created_at': datetime.utcnow().isoformat()
        }
        
        # Store request
        if to_user_id not in self.friend_requests:
            self.friend_requests[to_user_id] = []
        self.friend_requests[to_user_id].append(request_data)
        
        # Save to file
        self._save_friend_requests(to_user_id)
        
        return {
            'success': True,
            'request': request_data,
            'message': 'Friend request sent'
        }
    
    def accept_friend_request(self, user_id: str, from_user_id: str) -> Dict[str, Any]:
        """
        Accept a friend request
        
        Args:
            user_id: User accepting the request
            from_user_id: User who sent the request
            
        Returns:
            Acceptance result
        """
        # Find and remove request
        if user_id not in self.friend_requests:
            return {
                'success': False,
                'error': 'No friend request found'
            }
        
        request = None
        for req in self.friend_requests[user_id]:
            if req['from_user_id'] == from_user_id and req['status'] == 'pending':
                request = req
                break
        
        if not request:
            return {
                'success': False,
                'error': 'Friend request not found'
            }
        
        # Mark as accepted
        request['status'] = 'accepted'
        request['accepted_at'] = datetime.utcnow().isoformat()
        
        # Add friendship
        self._add_friendship(from_user_id, user_id)
        
        # Remove from pending requests
        self.friend_requests[user_id] = [r for r in self.friend_requests[user_id] if r != request]
        self._save_friend_requests(user_id)
        
        return {
            'success': True,
            'message': 'Friend request accepted',
            'friendship': {
                'user1_id': from_user_id,
                'user2_id': user_id,
                'created_at': request['accepted_at']
            }
        }
    
    def reject_friend_request(self, user_id: str, from_user_id: str) -> Dict[str, Any]:
        """Reject a friend request"""
        if user_id not in self.friend_requests:
            return {
                'success': False,
                'error': 'No friend request found'
            }
        
        # Remove request
        self.friend_requests[user_id] = [
            r for r in self.friend_requests[user_id]
            if not (r['from_user_id'] == from_user_id and r['status'] == 'pending')
        ]
        self._save_friend_requests(user_id)
        
        return {
            'success': True,
            'message': 'Friend request rejected'
        }
    
    def remove_friend(self, user_id: str, friend_id: str) -> Dict[str, Any]:
        """Remove a friend"""
        if not self.are_friends(user_id, friend_id):
            return {
                'success': False,
                'error': 'Not friends'
            }
        
        # Remove friendship
        if user_id in self.friendships:
            self.friendships[user_id] = [f for f in self.friendships[user_id] if f != friend_id]
        if friend_id in self.friendships:
            self.friendships[friend_id] = [f for f in self.friendships[friend_id] if f != user_id]
        
        # Save
        self._save_friendships(user_id)
        self._save_friendships(friend_id)
        
        return {
            'success': True,
            'message': 'Friend removed'
        }
    
    def get_friends(self, user_id: str) -> List[str]:
        """Get list of friend IDs"""
        return self.friendships.get(user_id, [])
    
    def get_friend_requests(self, user_id: str) -> List[Dict[str, Any]]:
        """Get pending friend requests for a user"""
        return [
            r for r in self.friend_requests.get(user_id, [])
            if r['status'] == 'pending'
        ]
    
    def get_sent_requests(self, user_id: str) -> List[Dict[str, Any]]:
        """Get friend requests sent by a user"""
        sent = []
        for to_user_id, requests in self.friend_requests.items():
            for req in requests:
                if req['from_user_id'] == user_id and req['status'] == 'pending':
                    sent.append(req)
        return sent
    
    def are_friends(self, user1_id: str, user2_id: str) -> bool:
        """Check if two users are friends"""
        return (
            user2_id in self.friendships.get(user1_id, []) or
            user1_id in self.friendships.get(user2_id, [])
        )
    
    def has_pending_request(self, from_user_id: str, to_user_id: str) -> bool:
        """Check if there's a pending request between users"""
        if to_user_id not in self.friend_requests:
            return False
        
        for req in self.friend_requests[to_user_id]:
            if req['from_user_id'] == from_user_id and req['status'] == 'pending':
                return True
        return False
    
    def block_user(self, user_id: str, blocked_user_id: str) -> Dict[str, Any]:
        """Block a user"""
        if user_id == blocked_user_id:
            return {
                'success': False,
                'error': 'Cannot block yourself'
            }
        
        if user_id not in self.blocked_users:
            self.blocked_users[user_id] = []
        
        if blocked_user_id not in self.blocked_users[user_id]:
            self.blocked_users[user_id].append(blocked_user_id)
        
        # Remove friendship if exists
        if self.are_friends(user_id, blocked_user_id):
            self.remove_friend(user_id, blocked_user_id)
        
        return {
            'success': True,
            'message': 'User blocked'
        }
    
    def unblock_user(self, user_id: str, blocked_user_id: str) -> Dict[str, Any]:
        """Unblock a user"""
        if user_id in self.blocked_users:
            self.blocked_users[user_id] = [
                u for u in self.blocked_users[user_id] if u != blocked_user_id
            ]
        
        return {
            'success': True,
            'message': 'User unblocked'
        }
    
    def is_blocked(self, user1_id: str, user2_id: str) -> bool:
        """Check if user1 has blocked user2"""
        return user2_id in self.blocked_users.get(user1_id, [])
    
    def get_friend_activity(self, user_id: str, limit: int = 20) -> List[Dict[str, Any]]:
        """Get activity feed from friends"""
        friends = self.get_friends(user_id)
        activity = []
        
        # This would integrate with activity tracking
        # For now, return empty list
        return activity[:limit]
    
    def _add_friendship(self, user1_id: str, user2_id: str):
        """Add friendship between two users"""
        if user1_id not in self.friendships:
            self.friendships[user1_id] = []
        if user2_id not in self.friendships[user1_id]:
            self.friendships[user1_id].append(user2_id)
        
        if user2_id not in self.friendships:
            self.friendships[user2_id] = []
        if user1_id not in self.friendships[user2_id]:
            self.friendships[user2_id].append(user1_id)
        
        # Save
        self._save_friendships(user1_id)
        self._save_friendships(user2_id)
    
    def _save_friendships(self, user_id: str):
        """Save friendships to file"""
        try:
            file_path = os.path.join(self.data_dir, f'{user_id}_friends.json')
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump({
                    'user_id': user_id,
                    'friends': self.friendships.get(user_id, []),
                    'updated_at': datetime.utcnow().isoformat()
                }, f, indent=2)
        except Exception as e:
            print(f"[FriendSystem] Error saving friendships for {user_id}: {e}", flush=True)
    
    def _save_friend_requests(self, user_id: str):
        """Save friend requests to file"""
        try:
            file_path = os.path.join(self.data_dir, f'{user_id}_requests.json')
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump({
                    'user_id': user_id,
                    'requests': self.friend_requests.get(user_id, []),
                    'updated_at': datetime.utcnow().isoformat()
                }, f, indent=2)
        except Exception as e:
            print(f"[FriendSystem] Error saving requests for {user_id}: {e}", flush=True)


# Global instance
friend_system = FriendSystem()
