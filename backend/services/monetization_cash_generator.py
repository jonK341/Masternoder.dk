"""
Monetization Cash Generator - "Hvordan vrider du kluden til cash på Masternoder.dk?"
How to turn content/resources into cash on Masternoder.dk
"""
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from decimal import Decimal
import uuid

class MonetizationCashGenerator:
    """
    Cash Generation System
    Turns content, resources, and activities into cash
    """
    
    def __init__(self):
        self.cash_sources = {
            'content_creation': {
                'name': 'Content Creation',
                'base_rate': Decimal('0.10'),  # per view
                'multiplier': Decimal('1.0')
            },
            'affiliate_links': {
                'name': 'Affiliate Links',
                'base_rate': Decimal('0.05'),  # per click
                'multiplier': Decimal('1.5')
            },
            'node_generation': {
                'name': 'Node Generation',
                'base_rate': Decimal('0.20'),  # per hour
                'multiplier': Decimal('2.0')
            },
            'automation': {
                'name': 'Automation',
                'base_rate': Decimal('0.15'),  # per task
                'multiplier': Decimal('1.8')
            },
            'battle_victories': {
                'name': 'Battle Victories',
                'base_rate': Decimal('1.00'),  # per victory
                'multiplier': Decimal('3.0')
            },
            'tech_tree_research': {
                'name': 'Tech Tree Research',
                'base_rate': Decimal('0.50'),  # per research
                'multiplier': Decimal('2.5')
            }
        }
        
        self.user_cash = {}  # user_id -> cash_amount
        self.cash_history = {}  # user_id -> [cash_events]
        self.top_earners = []  # Top 50 earners
    
    def generate_cash(self, user_id: str, source: str, amount: Decimal = None, 
                     metadata: Dict = None) -> Dict[str, Any]:
        """Generate cash from a source"""
        if source not in self.cash_sources:
            return {'success': False, 'error': 'Invalid cash source'}
        
        source_config = self.cash_sources[source]
        
        if amount is None:
            amount = source_config['base_rate'] * source_config['multiplier']
        
        # Add to user cash
        if user_id not in self.user_cash:
            self.user_cash[user_id] = Decimal('0')
        
        self.user_cash[user_id] += amount
        
        # Record in history
        if user_id not in self.cash_history:
            self.cash_history[user_id] = []
        
        self.cash_history[user_id].append({
            'id': str(uuid.uuid4()),
            'source': source,
            'amount': float(amount),
            'timestamp': datetime.utcnow().isoformat(),
            'metadata': metadata or {}
        })
        
        # Update top earners
        self._update_top_earners()
        
        return {
            'success': True,
            'user_id': user_id,
            'source': source,
            'amount': float(amount),
            'total_cash': float(self.user_cash[user_id]),
            'timestamp': datetime.utcnow().isoformat()
        }
    
    def _update_top_earners(self):
        """Update top 50 earners list"""
        sorted_users = sorted(
            self.user_cash.items(),
            key=lambda x: x[1],
            reverse=True
        )[:50]
        
        self.top_earners = [
            {
                'rank': idx + 1,
                'user_id': user_id,
                'total_cash': float(cash),
                'is_top_6': idx < 6
            }
            for idx, (user_id, cash) in enumerate(sorted_users)
        ]
    
    def get_top_50(self) -> List[Dict[str, Any]]:
        """Get top 50 earners"""
        self._update_top_earners()
        return self.top_earners
    
    def get_top_6(self) -> List[Dict[str, Any]]:
        """Get top 6 earners (special frame)"""
        top_50 = self.get_top_50()
        return [user for user in top_50 if user['is_top_6']]
    
    def get_user_cash(self, user_id: str) -> Dict[str, Any]:
        """Get user cash status"""
        total_cash = float(self.user_cash.get(user_id, Decimal('0')))
        
        # Calculate rank
        rank = None
        for idx, user in enumerate(self.top_earners):
            if user['user_id'] == user_id:
                rank = idx + 1
                break
        
        return {
            'success': True,
            'user_id': user_id,
            'total_cash': total_cash,
            'rank': rank,
            'is_top_6': rank is not None and rank <= 6,
            'cash_history': self.cash_history.get(user_id, [])[-10:]  # Last 10
        }

# Global instance
monetization_cash_generator = MonetizationCashGenerator()

