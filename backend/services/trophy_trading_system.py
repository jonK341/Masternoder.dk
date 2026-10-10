"""
Trophy Trading System - Trade trophies between users
Includes careful processing and rate limiting
"""
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from collections import defaultdict
import time
import random

class TrophyTradingSystem:
    """Trophy trading system with careful processing"""
    
    def __init__(self):
        self.trades = {}  # {trade_id: trade_data}
        self.trade_offers = {}  # {offer_id: offer_data}
        self.user_trade_history = defaultdict(list)  # {user_id: [trade_ids]}
        self.trade_rates = {}  # {trophy_id: current_rate}
        self.processing_queue = []  # Queue for careful processing
        self.last_processing_time = {}  # {user_id: timestamp}
        self.processing_delay = 2.0  # 2 seconds delay for careful thinking
        self.drug_items = {}  # Special items like "Speed.Hash"
        self._initialize_drug_items()
    
    def _initialize_drug_items(self):
        """Initialize special drug items"""
        self.drug_items = {
            'speed_hash': {
                'id': 'speed_hash',
                'name': 'Speed.Hash',
                'description': 'Enhances processing speed but requires careful thinking',
                'effect': 'processing_speed',
                'multiplier': 1.5,
                'trade_value': 100,
                'rarity': 'rare'
            },
            'careful_thought': {
                'id': 'careful_thought',
                'name': 'Careful Thought',
                'description': 'Slows processing for better decisions',
                'effect': 'careful_thinking',
                'multiplier': 0.7,
                'trade_value': 150,
                'rarity': 'uncommon'
            }
        }
    
    def create_trade_offer(
        self,
        from_user_id: str,
        to_user_id: str,
        offering_trophies: List[str],
        requesting_trophies: List[str],
        message: str = ""
    ) -> Dict[str, Any]:
        """Create a trade offer - careful processing"""
        # Rate limiting - slow and careful
        if from_user_id in self.last_processing_time:
            time_since = time.time() - self.last_processing_time[from_user_id]
            if time_since < self.processing_delay:
                wait_time = self.processing_delay - time_since
                return {
                    'success': False,
                    'error': f'Please think carefully. Wait {wait_time:.1f} seconds before trading again.'
                }
        
        offer_id = f"offer_{datetime.utcnow().timestamp()}"
        
        offer = {
            'offer_id': offer_id,
            'from_user_id': from_user_id,
            'to_user_id': to_user_id,
            'offering_trophies': offering_trophies,
            'requesting_trophies': requesting_trophies,
            'message': message,
            'status': 'pending',
            'created_at': datetime.utcnow().isoformat(),
            'expires_at': (datetime.utcnow() + timedelta(days=7)).isoformat()
        }
        
        self.trade_offers[offer_id] = offer
        self.last_processing_time[from_user_id] = time.time()
        
        return {
            'success': True,
            'offer': offer,
            'message': 'Trade offer created. Please review carefully before accepting.'
        }
    
    def accept_trade_offer(self, offer_id: str, user_id: str) -> Dict[str, Any]:
        """Accept a trade offer - careful processing"""
        if offer_id not in self.trade_offers:
            return {'success': False, 'error': 'Trade offer not found'}
        
        offer = self.trade_offers[offer_id]
        
        if offer['to_user_id'] != user_id:
            return {'success': False, 'error': 'Not authorized to accept this offer'}
        
        if offer['status'] != 'pending':
            return {'success': False, 'error': 'Trade offer already processed'}
        
        # Rate limiting
        if user_id in self.last_processing_time:
            time_since = time.time() - self.last_processing_time[user_id]
            if time_since < self.processing_delay:
                wait_time = self.processing_delay - time_since
                return {
                    'success': False,
                    'error': f'Please think carefully. Wait {wait_time:.1f} seconds before accepting.'
                }
        
        # Process trade carefully
        trade_id = f"trade_{datetime.utcnow().timestamp()}"
        
        trade = {
            'trade_id': trade_id,
            'offer_id': offer_id,
            'from_user_id': offer['from_user_id'],
            'to_user_id': offer['to_user_id'],
            'trophies_exchanged': {
                'from': offer['offering_trophies'],
                'to': offer['requesting_trophies']
            },
            'status': 'completed',
            'completed_at': datetime.utcnow().isoformat()
        }
        
        self.trades[trade_id] = trade
        self.user_trade_history[offer['from_user_id']].append(trade_id)
        self.user_trade_history[offer['to_user_id']].append(trade_id)
        
        offer['status'] = 'accepted'
        offer['accepted_at'] = datetime.utcnow().isoformat()
        
        self.last_processing_time[user_id] = time.time()
        
        return {
            'success': True,
            'trade': trade,
            'message': 'Trade completed successfully. Think carefully about your next move.'
        }
    
    def get_trade_offers(self, user_id: str) -> Dict[str, Any]:
        """Get trade offers for a user"""
        incoming = [o for o in self.trade_offers.values() if o['to_user_id'] == user_id and o['status'] == 'pending']
        outgoing = [o for o in self.trade_offers.values() if o['from_user_id'] == user_id and o['status'] == 'pending']
        
        return {
            'success': True,
            'incoming_offers': incoming,
            'outgoing_offers': outgoing
        }
    
    def get_trade_history(self, user_id: str, limit: int = 20) -> Dict[str, Any]:
        """Get trade history for a user"""
        trade_ids = self.user_trade_history.get(user_id, [])[-limit:]
        trades = [self.trades[tid] for tid in trade_ids if tid in self.trades]
        
        return {
            'success': True,
            'trades': trades
        }


class CollectibleCardSystem:
    """Collectible card/item system with valuation (like Sol Ring)"""
    
    def __init__(self):
        self.cards = {}  # {card_id: card_data}
        self.user_collections = defaultdict(list)  # {user_id: [card_ids]}
        self.card_definitions = self._initialize_card_definitions()
        self.valuation_history = defaultdict(list)  # {card_id: [valuation_data]}
        self.market_prices = {}  # {card_id: current_price}
    
    def _initialize_card_definitions(self) -> Dict[str, Dict[str, Any]]:
        """Initialize card definitions"""
        return {
            'sol_ring_alpha': {
                'id': 'sol_ring_alpha',
                'name': 'Sol Ring Alpha',
                'description': 'Legendary artifact - multiplies value over time',
                'rarity': 'mythic',
                'base_price': 105,  # USD
                'current_price': 900,  # EUR
                'multiplier': 10.0,
                'years_to_multiply': 5,
                'played_copies': True,
                'category': 'artifact',
                'icon': '💍'
            },
            'jons_thing': {
                'id': 'jons_thing',
                'name': "Jon's Thing",
                'description': 'Special collectible with exponential growth',
                'rarity': 'legendary',
                'base_price': 50,
                'current_price': 500,
                'multiplier': 10.0,
                'years_to_multiply': 5,
                'played_copies': True,
                'category': 'special',
                'icon': '⚡'
            }
        }
    
    def create_card(self, card_type: str, user_id: str) -> Dict[str, Any]:
        """Create a collectible card for a user"""
        if card_type not in self.card_definitions:
            return {'success': False, 'error': 'Card type not found'}
        
        card_def = self.card_definitions[card_type]
        card_id = f"{card_type}_{datetime.utcnow().timestamp()}"
        
        card = {
            'card_id': card_id,
            'card_type': card_type,
            'name': card_def['name'],
            'description': card_def['description'],
            'rarity': card_def['rarity'],
            'purchase_price': card_def['base_price'],
            'current_value': card_def['current_price'],
            'multiplier': card_def['multiplier'],
            'purchased_at': datetime.utcnow().isoformat(),
            'owner_id': user_id,
            'played_copies': card_def.get('played_copies', False),
            'icon': card_def.get('icon', '🃏')
        }
        
        self.cards[card_id] = card
        self.user_collections[user_id].append(card_id)
        
        # Initialize valuation
        self.valuation_history[card_id].append({
            'timestamp': datetime.utcnow().isoformat(),
            'value': card_def['base_price'],
            'currency': 'USD'
        })
        
        self.market_prices[card_id] = card_def['current_price']
        
        return {
            'success': True,
            'card': card,
            'message': f"Card created: {card_def['name']}"
        }
    
    def calculate_future_value(self, card_id: str, years: int = 10) -> Dict[str, Any]:
        """Calculate future value based on multiplier"""
        if card_id not in self.cards:
            return {'success': False, 'error': 'Card not found'}
        
        card = self.cards[card_id]
        base_price = card['purchase_price']
        multiplier = card['multiplier']
        years_to_multiply = card.get('years_to_multiply', 5)
        
        # Calculate value growth
        growth_rate = (multiplier ** (1 / years_to_multiply)) - 1
        future_value = base_price * ((1 + growth_rate) ** years)
        
        return {
            'success': True,
            'current_value': card['current_value'],
            'future_value_5_years': base_price * multiplier,
            'future_value_10_years': future_value,
            'growth_rate': growth_rate * 100,
            'multiplier': multiplier
        }
    
    def get_user_collection(self, user_id: str) -> Dict[str, Any]:
        """Get user's card collection"""
        card_ids = self.user_collections.get(user_id, [])
        cards = [self.cards[cid] for cid in card_ids if cid in self.cards]
        
        total_value = sum(card['current_value'] for card in cards)
        
        return {
            'success': True,
            'cards': cards,
            'total_value': total_value,
            'count': len(cards)
        }
    
    def trade_card(self, from_user_id: str, to_user_id: str, card_id: str, price: float) -> Dict[str, Any]:
        """Trade a card between users"""
        if card_id not in self.cards:
            return {'success': False, 'error': 'Card not found'}
        
        card = self.cards[card_id]
        
        if card['owner_id'] != from_user_id:
            return {'success': False, 'error': 'Not authorized to trade this card'}
        
        # Transfer ownership
        card['owner_id'] = to_user_id
        card['traded_at'] = datetime.utcnow().isoformat()
        card['trade_price'] = price
        
        # Update collections
        if card_id in self.user_collections[from_user_id]:
            self.user_collections[from_user_id].remove(card_id)
        self.user_collections[to_user_id].append(card_id)
        
        # Update valuation
        self.valuation_history[card_id].append({
            'timestamp': datetime.utcnow().isoformat(),
            'value': price,
            'currency': 'EUR',
            'trade': True
        })
        
        self.market_prices[card_id] = price
        
        return {
            'success': True,
            'card': card,
            'message': f"Card traded for {price}€"
        }


# Global instances
trophy_trading_system = TrophyTradingSystem()
collectible_card_system = CollectibleCardSystem()

