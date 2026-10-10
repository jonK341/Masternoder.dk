"""
Time Lock Security System
Prevents manipulation of DNA and microstructures
"""
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
import hashlib
import logging

logger = logging.getLogger(__name__)

class TimeLockSecurity:
    """
    Time Lock Security System
    Creates cryptographic time locks to prevent manipulation
    """
    
    def __init__(self):
        self.time_locks = {}
        self.protected_structures = {}
        self.lock_history = []
    
    def create_time_lock(self, structure_id: str, structure_type: str,
                        data: Any, unlock_time: Optional[datetime] = None) -> Dict[str, Any]:
        """
        Create a time lock for a structure (DNA, microstructure, etc.)
        """
        # Generate hash of data
        data_hash = self._hash_data(data)
        
        # Create lock
        lock_id = f"timelock_{structure_id}_{datetime.utcnow().timestamp()}"
        
        # Default unlock time: 24 hours from now
        if unlock_time is None:
            unlock_time = datetime.utcnow() + timedelta(hours=24)
        
        time_lock = {
            'lock_id': lock_id,
            'structure_id': structure_id,
            'structure_type': structure_type,
            'data_hash': data_hash,
            'created_at': datetime.utcnow().isoformat(),
            'unlock_time': unlock_time.isoformat(),
            'locked': True,
            'attempts': 0,
            'max_attempts': 3
        }
        
        self.time_locks[lock_id] = time_lock
        self.protected_structures[structure_id] = {
            'lock_id': lock_id,
            'structure_type': structure_type,
            'protected_at': datetime.utcnow().isoformat()
        }
        
        self.lock_history.append({
            'action': 'created',
            'lock_id': lock_id,
            'structure_id': structure_id,
            'timestamp': datetime.utcnow().isoformat()
        })
        
        return {'success': True, 'time_lock': time_lock}
    
    def verify_time_lock(self, structure_id: str, data: Any) -> Dict[str, Any]:
        """
        Verify time lock is valid and data hasn't been tampered
        """
        if structure_id not in self.protected_structures:
            return {'success': False, 'error': 'Structure not protected'}
        
        lock_id = self.protected_structures[structure_id]['lock_id']
        time_lock = self.time_locks.get(lock_id)
        
        if not time_lock:
            return {'success': False, 'error': 'Time lock not found'}
        
        # Check if locked
        if time_lock['locked']:
            unlock_time = datetime.fromisoformat(time_lock['unlock_time'])
            if datetime.utcnow() < unlock_time:
                return {
                    'success': False,
                    'error': 'Time lock still active',
                    'unlock_time': time_lock['unlock_time'],
                    'remaining_time': str(unlock_time - datetime.utcnow())
                }
        
        # Verify data hash
        current_hash = self._hash_data(data)
        if current_hash != time_lock['data_hash']:
            time_lock['attempts'] += 1
            if time_lock['attempts'] >= time_lock['max_attempts']:
                return {
                    'success': False,
                    'error': 'Data tampering detected! Maximum attempts exceeded.',
                    'security_alert': True
                }
            return {
                'success': False,
                'error': 'Data hash mismatch - possible tampering',
                'attempts': time_lock['attempts']
            }
        
        return {
            'success': True,
            'verified': True,
            'structure_id': structure_id,
            'lock_id': lock_id
        }
    
    def unlock_structure(self, structure_id: str, 
                        authorization: str) -> Dict[str, Any]:
        """
        Unlock a structure (requires authorization)
        """
        if structure_id not in self.protected_structures:
            return {'success': False, 'error': 'Structure not protected'}
        
        lock_id = self.protected_structures[structure_id]['lock_id']
        time_lock = self.time_locks.get(lock_id)
        
        if not time_lock:
            return {'success': False, 'error': 'Time lock not found'}
        
        # Check authorization (simplified - would use proper auth in production)
        if authorization != 'authorized':
            return {'success': False, 'error': 'Unauthorized'}
        
        # Unlock
        time_lock['locked'] = False
        time_lock['unlocked_at'] = datetime.utcnow().isoformat()
        
        self.lock_history.append({
            'action': 'unlocked',
            'lock_id': lock_id,
            'structure_id': structure_id,
            'timestamp': datetime.utcnow().isoformat()
        })
        
        return {'success': True, 'unlocked': True, 'lock_id': lock_id}
    
    def _hash_data(self, data: Any) -> str:
        """Generate hash of data"""
        data_str = str(data)
        return hashlib.sha256(data_str.encode()).hexdigest()
    
    def protect_dna_sequence(self, dna_id: str, sequence: str) -> Dict[str, Any]:
        """
        Protect a DNA sequence with time lock
        """
        return self.create_time_lock(dna_id, 'dna', sequence)
    
    def protect_microstructure(self, structure_id: str, structure_data: Dict) -> Dict[str, Any]:
        """
        Protect a microstructure with time lock
        """
        return self.create_time_lock(structure_id, 'microstructure', structure_data)

# Global instance
time_lock_security = TimeLockSecurity()

