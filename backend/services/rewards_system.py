"""
Rewards System - Quest rewards, social network discovery, dependencies, upgrades
"""
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from collections import defaultdict

class RewardsSystem:
    """Rewards system for quest rewards, social discovery, dependencies, upgrades"""
    
    def __init__(self):
        self.user_rewards = defaultdict(list)  # {user_id: [reward_data]}
        self.pending_rewards = defaultdict(list)  # {user_id: [pending_reward_data]}
        self.reward_history = defaultdict(list)  # {user_id: [history_data]}
        self.reward_categories = {
            'mission': {'name': 'Mission Rewards', 'icon': '🎯', 'color': 'var(--primary)'},
            'quest': {'name': 'Quest Rewards', 'icon': '📅', 'color': '#ffaa00'},
            'social': {'name': 'Social Network Discovery', 'icon': '👥', 'color': '#44ff44'},
            'dependency': {'name': 'Dependencies', 'icon': '⚙️', 'color': '#8888ff'},
            'upgrade': {'name': 'Upgrades', 'icon': '🚀', 'color': '#ff8888'}
        }
    
    def add_reward(
        self,
        user_id: str,
        category: str,
        reward_type: str,
        amount: int,
        description: str = "",
        source: str = ""
    ) -> Dict[str, Any]:
        """Add a reward to user"""
        reward = {
            'reward_id': f"reward_{datetime.utcnow().timestamp()}",
            'user_id': user_id,
            'category': category,
            'reward_type': reward_type,  # 'points', 'trophies', 'items', 'cards'
            'amount': amount,
            'description': description,
            'source': source,
            'status': 'pending',
            'created_at': datetime.utcnow().isoformat()
        }
        
        self.pending_rewards[user_id].append(reward)
        
        return {
            'success': True,
            'reward': reward
        }
    
    def claim_reward(self, user_id: str, reward_id: str) -> Dict[str, Any]:
        """Claim a pending reward"""
        pending = [r for r in self.pending_rewards[user_id] if r['reward_id'] == reward_id]
        
        if not pending:
            return {'success': False, 'error': 'Reward not found'}
        
        reward = pending[0]
        reward['status'] = 'claimed'
        reward['claimed_at'] = datetime.utcnow().isoformat()
        
        # Move to history
        self.pending_rewards[user_id].remove(reward)
        self.reward_history[user_id].append(reward)
        self.user_rewards[user_id].append(reward)
        
        return {
            'success': True,
            'reward': reward
        }
    
    def claim_all_rewards(self, user_id: str) -> Dict[str, Any]:
        """Claim all pending rewards"""
        claimed = []
        
        for reward in self.pending_rewards[user_id][:]:
            reward['status'] = 'claimed'
            reward['claimed_at'] = datetime.utcnow().isoformat()
            self.pending_rewards[user_id].remove(reward)
            self.reward_history[user_id].append(reward)
            self.user_rewards[user_id].append(reward)
            claimed.append(reward)
        
        return {
            'success': True,
            'claimed_count': len(claimed),
            'rewards': claimed
        }
    
    def get_user_rewards(self, user_id: str) -> Dict[str, Any]:
        """Get user's rewards"""
        pending = self.pending_rewards.get(user_id, [])
        history = self.reward_history.get(user_id, [])[-50:]  # Last 50
        
        # Calculate totals
        total_points = sum(r['amount'] for r in self.user_rewards.get(user_id, []) if r['reward_type'] == 'points')
        total_trophies = sum(r['amount'] for r in self.user_rewards.get(user_id, []) if r['reward_type'] == 'trophies')
        
        # Group by category
        category_totals = defaultdict(int)
        for reward in self.user_rewards.get(user_id, []):
            category_totals[reward['category']] += reward['amount']
        
        return {
            'success': True,
            'pending_rewards': pending,
            'reward_history': history,
            'total_points': total_points,
            'total_trophies': total_trophies,
            'pending_count': len(pending),
            'category_totals': dict(category_totals)
        }
    
    def add_mission_reward(self, user_id: str, mission_id: str, points: int, trophies: int) -> Dict[str, Any]:
        """Add reward from mission completion"""
        return self.add_reward(
            user_id=user_id,
            category='mission',
            reward_type='points',
            amount=points,
            description=f'Mission completion: {mission_id}',
            source=mission_id
        )
    
    def add_quest_reward(self, user_id: str, quest_id: str, points: int, trophies: int) -> Dict[str, Any]:
        """Add reward from quest completion"""
        rewards = []
        
        if points > 0:
            rewards.append(self.add_reward(
                user_id=user_id,
                category='quest',
                reward_type='points',
                amount=points,
                description=f'Quest completion: {quest_id}',
                source=quest_id
            )['reward'])
        
        if trophies > 0:
            rewards.append(self.add_reward(
                user_id=user_id,
                category='quest',
                reward_type='trophies',
                amount=trophies,
                description=f'Quest completion: {quest_id}',
                source=quest_id
            )['reward'])
        
        return {
            'success': True,
            'rewards': rewards
        }
    
    def add_social_discovery_reward(self, user_id: str, discovery_type: str, amount: int) -> Dict[str, Any]:
        """Add reward from social network discovery"""
        return self.add_reward(
            user_id=user_id,
            category='social',
            reward_type='points',
            amount=amount,
            description=f'Social network discovery: {discovery_type}',
            source='social_network'
        )
    
    def add_dependency_reward(self, user_id: str, dependency_name: str, amount: int) -> Dict[str, Any]:
        """Add reward from operator dependency updates"""
        return self.add_reward(
            user_id=user_id,
            category='dependency',
            reward_type='points',
            amount=amount,
            description=f'Dependency update: {dependency_name}',
            source='operator'
        )
    
    def add_upgrade_reward(self, user_id: str, upgrade_name: str, amount: int) -> Dict[str, Any]:
        """Add reward from development and deployment upgrades"""
        return self.add_reward(
            user_id=user_id,
            category='upgrade',
            reward_type='points',
            amount=amount,
            description=f'Upgrade: {upgrade_name}',
            source='development'
        )


# Global instance
rewards_system = RewardsSystem()

