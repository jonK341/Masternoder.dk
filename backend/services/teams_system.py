"""
Teams System - Temporary and permanent teams for battles
"""
import uuid
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from collections import defaultdict


class Team:
    """Represents a team"""
    
    def __init__(self, team_id: str, name: str, leader_id: str, team_type: str = 'temporary', max_members: int = 5):
        self.id = team_id
        self.name = name
        self.leader_id = leader_id
        self.type = team_type  # temporary, permanent, tournament
        self.members = [leader_id]
        self.max_members = max_members
        self.created_at = datetime.utcnow()
        self.expires_at = None
        if team_type == 'temporary':
            self.expires_at = datetime.utcnow() + timedelta(hours=24)
        self.rating = 1000
        self.wins = 0
        self.losses = 0
    
    def to_dict(self):
        """Convert to dictionary"""
        return {
            'id': self.id,
            'name': self.name,
            'leader_id': self.leader_id,
            'type': self.type,
            'members': self.members,
            'members_count': len(self.members),
            'max_members': self.max_members,
            'created_at': self.created_at.isoformat(),
            'expires_at': self.expires_at.isoformat() if self.expires_at else None,
            'rating': self.rating,
            'wins': self.wins,
            'losses': self.losses
        }


class TeamsSystem:
    """Manages teams for battles"""
    
    def __init__(self):
        self.teams = {}  # {team_id: Team}
        self.user_teams = defaultdict(list)  # {user_id: [team_ids]}
        self.team_requests = defaultdict(list)  # {team_id: [user_ids]}
    
    def create_team(self, name: str, leader_id: str, team_type: str = 'temporary', max_members: int = 5) -> Dict[str, Any]:
        """Create a new team"""
        team_id = str(uuid.uuid4())
        team = Team(team_id, name, leader_id, team_type, max_members)
        self.teams[team_id] = team
        self.user_teams[leader_id].append(team_id)
        
        return {
            'success': True,
            'team_id': team_id,
            'team': team.to_dict()
        }
    
    def join_team(self, team_id: str, user_id: str) -> Dict[str, Any]:
        """Join a team"""
        team = self.teams.get(team_id)
        if not team:
            return {'success': False, 'error': 'Team not found'}
        
        if user_id in team.members:
            return {'success': False, 'error': 'Already in team'}
        
        if len(team.members) >= team.max_members:
            return {'success': False, 'error': 'Team is full'}
        
        team.members.append(user_id)
        self.user_teams[user_id].append(team_id)
        
        return {
            'success': True,
            'team': team.to_dict()
        }
    
    def leave_team(self, team_id: str, user_id: str) -> Dict[str, Any]:
        """Leave a team"""
        team = self.teams.get(team_id)
        if not team:
            return {'success': False, 'error': 'Team not found'}
        
        if user_id not in team.members:
            return {'success': False, 'error': 'Not in team'}
        
        if user_id == team.leader_id:
            return {'success': False, 'error': 'Leader cannot leave team'}
        
        team.members.remove(user_id)
        if team_id in self.user_teams[user_id]:
            self.user_teams[user_id].remove(team_id)
        
        return {
            'success': True,
            'team': team.to_dict()
        }
    
    def delete_team(self, team_id: str, user_id: str) -> Dict[str, Any]:
        """Delete a team"""
        team = self.teams.get(team_id)
        if not team:
            return {'success': False, 'error': 'Team not found'}
        
        if team.leader_id != user_id:
            return {'success': False, 'error': 'Only leader can delete team'}
        
        # Remove team from all users
        for member_id in team.members:
            if team_id in self.user_teams[member_id]:
                self.user_teams[member_id].remove(team_id)
        
        del self.teams[team_id]
        
        return {'success': True, 'message': 'Team deleted'}
    
    def get_user_teams(self, user_id: str) -> List[Dict]:
        """Get all teams for a user"""
        team_ids = self.user_teams.get(user_id, [])
        teams = []
        for team_id in team_ids:
            team = self.teams.get(team_id)
            if team:
                teams.append(team.to_dict())
        return teams
    
    def find_team_matches(self, team_id: str, min_rating_diff: int = 200) -> List[Dict]:
        """Find matching teams for battle"""
        team = self.teams.get(team_id)
        if not team:
            return []
        
        matches = []
        for other_team in self.teams.values():
            if other_team.id == team_id:
                continue
            
            if other_team.type != team.type:
                continue
            
            rating_diff = abs(other_team.rating - team.rating)
            if rating_diff <= min_rating_diff:
                matches.append({
                    'match_id': str(uuid.uuid4()),
                    'opponent_team_id': other_team.id,
                    'opponent_team_name': other_team.name,
                    'opponent_members_count': len(other_team.members),
                    'rating': other_team.rating,
                    'rating_diff': rating_diff
                })
        
        # Sort by rating difference (closest first)
        matches.sort(key=lambda x: x['rating_diff'])
        return matches[:5]  # Return top 5 matches


# Global instance
teams_system = TeamsSystem()

