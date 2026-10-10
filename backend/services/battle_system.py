"""
Battle System - Clan vs Clan battles
"""
from datetime import datetime
from typing import Dict, List, Optional, Any
import random

class BattleSystem:
    """Manages clan battles and competitions"""
    
    def __init__(self):
        self.battles = {}  # battle_id -> battle_data
        self.clans = {}  # clan_id -> clan_data
        self.battle_history = []  # List of completed battles
    
    def create_clan(self, clan_id: str, name: str, leader_id: str, description: str = "") -> Dict[str, Any]:
        """Create a new clan"""
        clan = {
            'id': clan_id,
            'name': name,
            'leader_id': leader_id,
            'description': description,
            'members': [leader_id],
            'created_at': datetime.utcnow().isoformat(),
            'total_wins': 0,
            'total_losses': 0,
            'total_draws': 0,
            'trophies': 0,
            'power': 0  # Combined power of all members
        }
        self.clans[clan_id] = clan
        return clan
    
    def join_clan(self, clan_id: str, user_id: str) -> bool:
        """Add a user to a clan"""
        if clan_id not in self.clans:
            return False
        if user_id not in self.clans[clan_id]['members']:
            self.clans[clan_id]['members'].append(user_id)
        return True
    
    def leave_clan(self, clan_id: str, user_id: str) -> bool:
        """Remove a user from a clan"""
        if clan_id not in self.clans:
            return False
        if user_id in self.clans[clan_id]['members']:
            self.clans[clan_id]['members'].remove(user_id)
        return True
    
    def calculate_clan_power(self, clan_id: str) -> int:
        """Calculate total power of a clan based on member stats"""
        if clan_id not in self.clans:
            return 0
        
        # This would integrate with the game system to get member stats
        # For now, return a base power
        member_count = len(self.clans[clan_id]['members'])
        return member_count * 100 + self.clans[clan_id]['trophies'] * 10
    
    def create_battle(self, clan1_id: str, clan2_id: str, battle_type: str = 'standard') -> Dict[str, Any]:
        """Create a new battle between two clans - auto-creates clans if they don't exist"""
        # Auto-create clans if they don't exist
        if clan1_id not in self.clans:
            self.create_clan(clan1_id, f"Clan {clan1_id}", f"leader_{clan1_id}", f"Auto-created clan {clan1_id}")
        if clan2_id not in self.clans:
            self.create_clan(clan2_id, f"Clan {clan2_id}", f"leader_{clan2_id}", f"Auto-created clan {clan2_id}")
        
        battle_id = f"battle_{datetime.utcnow().timestamp()}"
        battle = {
            'id': battle_id,
            'clan1_id': clan1_id,
            'clan2_id': clan2_id,
            'clan1_name': self.clans[clan1_id]['name'],
            'clan2_name': self.clans[clan2_id]['name'],
            'battle_type': battle_type,
            'status': 'active',
            'created_at': datetime.utcnow().isoformat(),
            'clan1_score': 0,
            'clan2_score': 0,
            'clan1_power': self.calculate_clan_power(clan1_id),
            'clan2_power': self.calculate_clan_power(clan2_id),
            'winner': None,
            'rewards': {}
        }
        
        self.battles[battle_id] = battle
        return {'success': True, 'battle': battle}
    
    def create_quick_battle(self, user_id: str, difficulty: str = 'balanced', battle_type: str = 'quick') -> Dict[str, Any]:
        """Create a quick battle without requiring clans - perfect for instant battles"""
        # Create temporary clans for quick battle
        clan1_id = f"quick_clan_{user_id}_{datetime.utcnow().timestamp()}"
        clan2_id = f"quick_opponent_{datetime.utcnow().timestamp()}"
        
        # Create player clan
        self.create_clan(clan1_id, f"Player {user_id}", user_id, "Quick battle player clan")
        self.join_clan(clan1_id, user_id)
        
        # Create opponent clan with AI
        opponent_name = f"AI Opponent {difficulty.title()}"
        self.create_clan(clan2_id, opponent_name, f"ai_{difficulty}", f"AI opponent for {difficulty} battle")
        
        # Set opponent power based on difficulty
        difficulty_power = {
            'easy': 50,
            'balanced': 100,
            'hard': 200,
            'extreme': 500
        }
        self.clans[clan2_id]['power'] = difficulty_power.get(difficulty, 100)
        self.clans[clan2_id]['trophies'] = difficulty_power.get(difficulty, 100) // 10
        
        battle_id = f"quick_battle_{datetime.utcnow().timestamp()}"
        battle = {
            'id': battle_id,
            'clan1_id': clan1_id,
            'clan2_id': clan2_id,
            'clan1_name': self.clans[clan1_id]['name'],
            'clan2_name': self.clans[clan2_id]['name'],
            'battle_type': battle_type,
            'difficulty': difficulty,
            'status': 'active',
            'created_at': datetime.utcnow().isoformat(),
            'clan1_score': 0,
            'clan2_score': 0,
            'clan1_power': self.calculate_clan_power(clan1_id),
            'clan2_power': self.calculate_clan_power(clan2_id),
            'winner': None,
            'rewards': {
                'experience': difficulty_power.get(difficulty, 100),
                'gold': difficulty_power.get(difficulty, 100) // 2
            },
            'is_quick_battle': True,
            'user_id': user_id
        }
        
        self.battles[battle_id] = battle
        return {'success': True, 'battle': battle}
    
    def submit_battle_action(self, battle_id: str, clan_id: str, user_id: str, action_type: str, value: int = 1) -> Dict[str, Any]:
        """Submit an action in a battle (e.g., video generation, quality score)"""
        if battle_id not in self.battles:
            return {'success': False, 'error': 'Battle not found'}
        
        battle = self.battles[battle_id]
        if battle['status'] != 'active':
            return {'success': False, 'error': 'Battle is not active'}
        
        # Determine which clan the user belongs to
        if battle['clan1_id'] == clan_id:
            battle['clan1_score'] += value
        elif battle['clan2_id'] == clan_id:
            battle['clan2_score'] += value
        else:
            return {'success': False, 'error': 'User not in participating clan'}
        
        return {'success': True, 'battle': battle}
    
    def end_battle(self, battle_id: str) -> Dict[str, Any]:
        """End a battle and determine winner"""
        if battle_id not in self.battles:
            return {'success': False, 'error': 'Battle not found'}
        
        battle = self.battles[battle_id]
        if battle['status'] != 'active':
            return {'success': False, 'error': 'Battle already ended'}
        
        clan1_score = battle['clan1_score']
        clan2_score = battle['clan2_score']
        
        # Determine winner
        if clan1_score > clan2_score:
            winner_id = battle['clan1_id']
            loser_id = battle['clan2_id']
            battle['winner'] = battle['clan1_id']
            self.clans[battle['clan1_id']]['total_wins'] += 1
            self.clans[battle['clan2_id']]['total_losses'] += 1
        elif clan2_score > clan1_score:
            winner_id = battle['clan2_id']
            loser_id = battle['clan1_id']
            battle['winner'] = battle['clan2_id']
            self.clans[battle['clan2_id']]['total_wins'] += 1
            self.clans[battle['clan1_id']]['total_losses'] += 1
        else:
            # Draw
            battle['winner'] = None
            self.clans[battle['clan1_id']]['total_draws'] += 1
            self.clans[battle['clan2_id']]['total_draws'] += 1
        
        # Calculate rewards
        base_reward = 100
        if battle['winner']:
            trophy_reward = 10
            self.clans[battle['winner']]['trophies'] += trophy_reward
            battle['rewards'] = {
                'winner': {
                    'trophies': trophy_reward,
                    'xp': base_reward * 2,
                    'credits': base_reward
                },
                'loser': {
                    'trophies': 0,
                    'xp': base_reward,
                    'credits': base_reward // 2
                }
            }
        else:
            battle['rewards'] = {
                'clan1': {
                    'trophies': 5,
                    'xp': base_reward,
                    'credits': base_reward // 2
                },
                'clan2': {
                    'trophies': 5,
                    'xp': base_reward,
                    'credits': base_reward // 2
                }
            }
        
        battle['status'] = 'completed'
        battle['ended_at'] = datetime.utcnow().isoformat()
        
        # Move to history
        self.battle_history.append(battle)
        del self.battles[battle_id]
        
        return {'success': True, 'battle': battle}
    
    def get_clan_info(self, clan_id: str) -> Optional[Dict[str, Any]]:
        """Get information about a clan"""
        return self.clans.get(clan_id)
    
    def get_active_battles(self) -> List[Dict[str, Any]]:
        """Get all active battles"""
        return [battle for battle in self.battles.values() if battle['status'] == 'active']
    
    def get_battle_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent battle history"""
        return self.battle_history[-limit:]
    
    def get_leaderboard(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get clan leaderboard sorted by trophies"""
        clans = list(self.clans.values())
        clans.sort(key=lambda x: x['trophies'], reverse=True)
        return clans[:limit]


# Global instance
battle_system = BattleSystem()
