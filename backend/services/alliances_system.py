"""
Alliances System - Clan alliances for coordinated warfare
"""
import uuid
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from collections import defaultdict


class Alliance:
    """Represents an alliance"""
    
    def __init__(self, alliance_id: str, name: str, leader_id: str, alliance_type: str = 'defensive'):
        self.id = alliance_id
        self.name = name
        self.leader_id = leader_id
        self.type = alliance_type  # defensive, offensive, trade, neutral
        self.clans = [leader_id]  # List of clan IDs
        self.created_at = datetime.utcnow()
        self.total_wars = 0
        self.wars_won = 0
        self.territories = []
        self.resources = {
            'gold': 0,
            'materials': 0,
            'energy': 0
        }
    
    def to_dict(self):
        """Convert to dictionary"""
        return {
            'id': self.id,
            'name': self.name,
            'leader_id': self.leader_id,
            'type': self.type,
            'clans': self.clans,
            'clans_count': len(self.clans),
            'created_at': self.created_at.isoformat(),
            'total_wars': self.total_wars,
            'wars_won': self.wars_won,
            'territories': self.territories,
            'resources': self.resources
        }


class AllianceWar:
    """Represents an alliance war"""
    
    def __init__(self, war_id: str, alliance1_id: str, alliance2_id: str):
        self.id = war_id
        self.alliance1_id = alliance1_id
        self.alliance2_id = alliance2_id
        self.status = 'active'  # active, ended
        self.alliance1_score = 0
        self.alliance2_score = 0
        self.started_at = datetime.utcnow()
        self.ends_at = datetime.utcnow() + timedelta(days=7)
        self.winner_id = None
    
    def to_dict(self):
        """Convert to dictionary"""
        return {
            'id': self.id,
            'alliance1_id': self.alliance1_id,
            'alliance2_id': self.alliance2_id,
            'status': self.status,
            'alliance1_score': self.alliance1_score,
            'alliance2_score': self.alliance2_score,
            'started_at': self.started_at.isoformat(),
            'ends_at': self.ends_at.isoformat(),
            'winner_id': self.winner_id
        }


class AlliancesSystem:
    """Manages alliances between clans"""
    
    def __init__(self):
        self.alliances = {}  # {alliance_id: Alliance}
        self.clan_alliances = {}  # {clan_id: alliance_id}
        self.wars = {}  # {war_id: AllianceWar}
        self.alliance_wars = defaultdict(list)  # {alliance_id: [war_ids]}
    
    def create_alliance(self, name: str, leader_clan_id: str, alliance_type: str = 'defensive') -> Dict[str, Any]:
        """Create a new alliance"""
        alliance_id = str(uuid.uuid4())
        alliance = Alliance(alliance_id, name, leader_clan_id, alliance_type)
        self.alliances[alliance_id] = alliance
        self.clan_alliances[leader_clan_id] = alliance_id
        
        return {
            'success': True,
            'alliance_id': alliance_id,
            'alliance': alliance.to_dict()
        }
    
    def join_alliance(self, alliance_id: str, clan_id: str) -> Dict[str, Any]:
        """Join an alliance"""
        alliance = self.alliances.get(alliance_id)
        if not alliance:
            return {'success': False, 'error': 'Alliance not found'}
        
        if clan_id in alliance.clans:
            return {'success': False, 'error': 'Already in alliance'}
        
        if clan_id in self.clan_alliances:
            return {'success': False, 'error': 'Clan already in an alliance'}
        
        alliance.clans.append(clan_id)
        self.clan_alliances[clan_id] = alliance_id
        
        return {
            'success': True,
            'alliance': alliance.to_dict()
        }
    
    def leave_alliance(self, alliance_id: str, clan_id: str) -> Dict[str, Any]:
        """Leave an alliance"""
        alliance = self.alliances.get(alliance_id)
        if not alliance:
            return {'success': False, 'error': 'Alliance not found'}
        
        if clan_id not in alliance.clans:
            return {'success': False, 'error': 'Not in alliance'}
        
        if clan_id == alliance.leader_id:
            return {'success': False, 'error': 'Leader cannot leave alliance'}
        
        alliance.clans.remove(clan_id)
        if clan_id in self.clan_alliances:
            del self.clan_alliances[clan_id]
        
        return {
            'success': True,
            'alliance': alliance.to_dict()
        }
    
    def get_user_alliances(self, clan_id: str) -> List[Dict]:
        """Get all alliances for a clan"""
        alliance_id = self.clan_alliances.get(clan_id)
        if alliance_id:
            alliance = self.alliances.get(alliance_id)
            if alliance:
                return [alliance.to_dict()]
        return []
    
    def declare_war(self, alliance1_id: str, alliance2_id: str) -> Dict[str, Any]:
        """Declare war between two alliances"""
        if alliance1_id == alliance2_id:
            return {'success': False, 'error': 'Cannot declare war on yourself'}
        
        alliance1 = self.alliances.get(alliance1_id)
        alliance2 = self.alliances.get(alliance2_id)
        
        if not alliance1 or not alliance2:
            return {'success': False, 'error': 'Alliance not found'}
        
        war_id = str(uuid.uuid4())
        war = AllianceWar(war_id, alliance1_id, alliance2_id)
        self.wars[war_id] = war
        self.alliance_wars[alliance1_id].append(war_id)
        self.alliance_wars[alliance2_id].append(war_id)
        
        alliance1.total_wars += 1
        alliance2.total_wars += 1
        
        return {
            'success': True,
            'war_id': war_id,
            'war': war.to_dict()
        }
    
    def get_alliance_wars(self, alliance_id: str) -> List[Dict]:
        """Get wars for an alliance"""
        war_ids = self.alliance_wars.get(alliance_id, [])
        wars = []
        for war_id in war_ids:
            war = self.wars.get(war_id)
            if war:
                wars.append(war.to_dict())
        return wars


# Global instance
alliances_system = AlliancesSystem()

