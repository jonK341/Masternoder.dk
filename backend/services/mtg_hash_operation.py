"""
MTG Hash Operation System - Bank/Boks with 2400€ Minimum
Integration with Clips and Movies
"""
from datetime import datetime
from typing import Dict, List, Optional, Any
from collections import defaultdict
import hashlib
import json

class MTGHashOperation:
    """MTG Hash Operation System with Bank/Boks"""
    
    def __init__(self):
        self.user_banks = defaultdict(lambda: {'balance': 0.0, 'transactions': []})  # {user_id: bank_data}
        self.user_boks = defaultdict(lambda: {'value': 0.0, 'items': []})  # {user_id: boks_data}
        self.hash_operations = defaultdict(list)  # {user_id: [operation_data]}
        self.minimum_requirement = 2400.0  # Minimum 2400€
        self.clips_movies_queue = defaultdict(list)  # {user_id: [clip/movie_data]}
    
    def execute_operation(
        self,
        user_id: str,
        operation_type: str,
        amount: float,
        hash_value: Optional[str] = None
    ) -> Dict[str, Any]:
        """Execute MTG hash operation"""
        operation_id = f"mtg_op_{datetime.utcnow().timestamp()}"
        
        # Generate hash if not provided
        if not hash_value:
            hash_value = self._generate_hash(user_id, operation_type, amount)
        
        operation = {
            'operation_id': operation_id,
            'user_id': user_id,
            'operation_type': operation_type,
            'amount': amount,
            'hash': hash_value,
            'timestamp': datetime.utcnow().isoformat(),
            'status': 'pending'
        }
        
        # Execute based on operation type
        if operation_type == 'deposit':
            result = self._deposit_to_bank(user_id, amount)
        elif operation_type == 'withdraw':
            result = self._withdraw_from_bank(user_id, amount)
        elif operation_type == 'boks_purchase':
            result = self._purchase_boks(user_id, amount)
        elif operation_type == 'boks_sell':
            result = self._sell_boks(user_id, amount)
        elif operation_type == 'hash_generate':
            result = self._generate_hash_operation(user_id, amount, hash_value)
        else:
            return {'success': False, 'error': 'Invalid operation type'}
        
        if result.get('success'):
            operation['status'] = 'completed'
            self.hash_operations[user_id].append(operation)
            
            # Check if minimum requirement met
            total_value = self.get_total_value(user_id)
            if total_value >= self.minimum_requirement:
                # Unlock next clips and movie
                self._unlock_clips_movie(user_id)
            
            return {
                'success': True,
                'operation': operation,
                'bank_balance': self.user_banks[user_id]['balance'],
                'boks_value': self.user_boks[user_id]['value'],
                'total_value': total_value,
                'minimum_met': total_value >= self.minimum_requirement
            }
        else:
            operation['status'] = 'failed'
            operation['error'] = result.get('error')
            return {
                'success': False,
                'error': result.get('error'),
                'operation': operation
            }
    
    def _deposit_to_bank(self, user_id: str, amount: float) -> Dict[str, Any]:
        """Deposit to bank"""
        if amount <= 0:
            return {'success': False, 'error': 'Amount must be positive'}
        
        self.user_banks[user_id]['balance'] += amount
        self.user_banks[user_id]['transactions'].append({
            'type': 'deposit',
            'amount': amount,
            'timestamp': datetime.utcnow().isoformat()
        })
        
        return {'success': True}
    
    def _withdraw_from_bank(self, user_id: str, amount: float) -> Dict[str, Any]:
        """Withdraw from bank"""
        if amount <= 0:
            return {'success': False, 'error': 'Amount must be positive'}
        
        if self.user_banks[user_id]['balance'] < amount:
            return {'success': False, 'error': 'Insufficient bank balance'}
        
        self.user_banks[user_id]['balance'] -= amount
        self.user_banks[user_id]['transactions'].append({
            'type': 'withdraw',
            'amount': amount,
            'timestamp': datetime.utcnow().isoformat()
        })
        
        return {'success': True}
    
    def _purchase_boks(self, user_id: str, amount: float) -> Dict[str, Any]:
        """Purchase boks items"""
        if amount <= 0:
            return {'success': False, 'error': 'Amount must be positive'}
        
        if self.user_banks[user_id]['balance'] < amount:
            return {'success': False, 'error': 'Insufficient bank balance'}
        
        # Deduct from bank
        self.user_banks[user_id]['balance'] -= amount
        
        # Add to boks
        self.user_boks[user_id]['value'] += amount
        self.user_boks[user_id]['items'].append({
            'item_id': f"boks_item_{datetime.utcnow().timestamp()}",
            'purchase_price': amount,
            'purchase_date': datetime.utcnow().isoformat()
        })
        
        return {'success': True}
    
    def _sell_boks(self, user_id: str, amount: float) -> Dict[str, Any]:
        """Sell boks items"""
        if amount <= 0:
            return {'success': False, 'error': 'Amount must be positive'}
        
        if self.user_boks[user_id]['value'] < amount:
            return {'success': False, 'error': 'Insufficient boks value'}
        
        # Remove from boks
        self.user_boks[user_id]['value'] -= amount
        
        # Add to bank
        self.user_banks[user_id]['balance'] += amount
        
        return {'success': True}
    
    def _generate_hash_operation(self, user_id: str, amount: float, hash_value: str) -> Dict[str, Any]:
        """Generate hash operation"""
        # Hash operation generates value
        generated_value = amount * 0.1  # 10% of amount as generated value
        
        # Split between bank and boks
        bank_portion = generated_value * 0.6
        boks_portion = generated_value * 0.4
        
        self.user_banks[user_id]['balance'] += bank_portion
        self.user_boks[user_id]['value'] += boks_portion
        
        return {'success': True, 'generated_value': generated_value}
    
    def _generate_hash(self, user_id: str, operation_type: str, amount: float) -> str:
        """Generate hash for operation"""
        data = f"{user_id}_{operation_type}_{amount}_{datetime.utcnow().timestamp()}"
        return hashlib.sha256(data.encode()).hexdigest()[:16]
    
    def get_total_value(self, user_id: str) -> float:
        """Get total value (bank + boks)"""
        return self.user_banks[user_id]['balance'] + self.user_boks[user_id]['value']
    
    def get_status(self, user_id: str) -> Dict[str, Any]:
        """Get MTG operation status"""
        bank_balance = self.user_banks[user_id]['balance']
        boks_value = self.user_boks[user_id]['value']
        total_value = self.get_total_value(user_id)
        minimum_met = total_value >= self.minimum_requirement
        progress_percent = min((total_value / self.minimum_requirement) * 100, 100)
        
        return {
            'success': True,
            'bank_balance': bank_balance,
            'boks_value': boks_value,
            'total_value': total_value,
            'minimum_requirement': self.minimum_requirement,
            'minimum_met': minimum_met,
            'progress_percent': progress_percent,
            'remaining': max(0, self.minimum_requirement - total_value)
        }
    
    def _unlock_clips_movie(self, user_id: str) -> Dict[str, Any]:
        """Unlock next clips and movie when minimum met"""
        if user_id not in self.clips_movies_queue:
            self.clips_movies_queue[user_id] = []
        
        # Add clips and movie to queue
        clips_movie = {
            'id': f"clips_movie_{datetime.utcnow().timestamp()}",
            'type': 'unlocked',
            'unlocked_at': datetime.utcnow().isoformat(),
            'clips': [
                {'clip_id': f"clip_1_{datetime.utcnow().timestamp()}", 'status': 'ready'},
                {'clip_id': f"clip_2_{datetime.utcnow().timestamp()}", 'status': 'ready'},
                {'clip_id': f"clip_3_{datetime.utcnow().timestamp()}", 'status': 'ready'}
            ],
            'movie': {
                'movie_id': f"movie_{datetime.utcnow().timestamp()}",
                'status': 'ready'
            }
        }
        
        self.clips_movies_queue[user_id].append(clips_movie)
        
        return {
            'success': True,
            'clips_movie': clips_movie
        }
    
    def get_clips_movie(self, user_id: str) -> Dict[str, Any]:
        """Get next clips and movie"""
        queue = self.clips_movies_queue.get(user_id, [])
        
        return {
            'success': True,
            'clips_movies': queue,
            'total_available': len(queue)
        }


# Global instance
mtg_hash_operation = MTGHashOperation()

