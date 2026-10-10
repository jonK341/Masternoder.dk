"""
Error Hash Tracking System - Track errors with hash values for analytics
"""
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from collections import defaultdict
import hashlib
import json
import traceback


class ErrorHashTracking:
    """Track errors with hash values for deduplication and analytics"""
    
    def __init__(self):
        self.error_hashes = defaultdict(dict)  # {error_hash: error_data}
        self.error_history = defaultdict(list)  # {endpoint: [errors]}
        self.error_counts = defaultdict(int)  # {error_hash: count}
        self.error_timestamps = defaultdict(list)  # {error_hash: [timestamps]}
        self.total_errors = 0
        self.total_requests = 0
    
    def track_error(self, endpoint: str, error: Exception, 
                   context: Dict[str, Any] = None, user_id: str = None) -> Dict[str, Any]:
        """Track an error and generate hash"""
        try:
            # Create error signature
            error_message = str(error)
            error_type = type(error).__name__
            error_traceback = traceback.format_exc()
            
            # Create hash from error signature
            error_signature = f"{endpoint}:{error_type}:{error_message}"
            error_hash = hashlib.sha256(error_signature.encode()).hexdigest()
            
            # Store error data
            error_data = {
                'error_hash': error_hash,
                'endpoint': endpoint,
                'error_type': error_type,
                'error_message': error_message,
                'error_traceback': error_traceback[:500],  # First 500 chars
                'context': context or {},
                'user_id': user_id,
                'timestamp': datetime.utcnow().isoformat(),
                'count': 1
            }
            
            # Update counts
            if error_hash in self.error_hashes:
                self.error_hashes[error_hash]['count'] += 1
                self.error_hashes[error_hash]['last_occurrence'] = datetime.utcnow().isoformat()
            else:
                self.error_hashes[error_hash] = error_data
                self.error_hashes[error_hash]['first_occurrence'] = datetime.utcnow().isoformat()
                self.error_hashes[error_hash]['last_occurrence'] = datetime.utcnow().isoformat()
            
            self.error_counts[error_hash] += 1
            self.error_timestamps[error_hash].append(datetime.utcnow().isoformat())
            self.error_history[endpoint].append(error_data)
            self.total_errors += 1
            
            # Keep only last 1000 timestamps per error
            if len(self.error_timestamps[error_hash]) > 1000:
                self.error_timestamps[error_hash] = self.error_timestamps[error_hash][-1000:]
            
            return {
                'success': True,
                'error_hash': error_hash,
                'error_data': error_data
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f'Failed to track error: {str(e)}'
            }
    
    def get_error_analytics(self, limit: int = 100) -> Dict[str, Any]:
        """Get error analytics with hash tracking"""
        # Group errors by endpoint
        endpoint_errors = defaultdict(list)
        endpoint_counts = defaultdict(int)
        
        for error_hash, error_data in self.error_hashes.items():
            endpoint = error_data['endpoint']
            count = error_data['count']
            endpoint_errors[endpoint].append({
                'error_hash': error_hash,
                'error_type': error_data['error_type'],
                'error_message': error_data['error_message'],
                'count': count,
                'first_occurrence': error_data.get('first_occurrence'),
                'last_occurrence': error_data.get('last_occurrence')
            })
            endpoint_counts[endpoint] += count
        
        # Create endpoint stats
        endpoint_stats = []
        for endpoint, errors in endpoint_errors.items():
            total_errors = endpoint_counts[endpoint]
            endpoint_stats.append({
                'endpoint': endpoint,
                'error_count': total_errors,
                'unique_errors': len(errors),
                'errors': sorted(errors, key=lambda x: x['count'], reverse=True)[:10]  # Top 10 per endpoint
            })
        
        # Sort by error count
        endpoint_stats.sort(key=lambda x: x['error_count'], reverse=True)
        
        # Get top errors by hash
        top_errors = sorted(
            self.error_hashes.items(),
            key=lambda x: x[1]['count'],
            reverse=True
        )[:limit]
        
        return {
            'success': True,
            'total_errors': self.total_errors,
            'total_requests': self.total_requests,
            'unique_errors': len(self.error_hashes),
            'overall_error_rate': (self.total_errors / self.total_requests * 100) if self.total_requests > 0 else 0,
            'by_endpoint': endpoint_stats[:20],  # Top 20 endpoints
            'by_hash': [
                {
                    'error_hash': error_hash,
                    'endpoint': data['endpoint'],
                    'error_type': data['error_type'],
                    'error_message': data['error_message'][:100],  # First 100 chars
                    'count': data['count'],
                    'first_occurrence': data.get('first_occurrence'),
                    'last_occurrence': data.get('last_occurrence')
                }
                for error_hash, data in top_errors
            ],
            'timestamp': datetime.utcnow().isoformat()
        }
    
    def get_error_by_hash(self, error_hash: str) -> Dict[str, Any]:
        """Get error details by hash"""
        if error_hash not in self.error_hashes:
            return {
                'success': False,
                'error': 'Error hash not found'
            }
        
        error_data = self.error_hashes[error_hash].copy()
        error_data['occurrence_count'] = len(self.error_timestamps.get(error_hash, []))
        error_data['recent_occurrences'] = self.error_timestamps.get(error_hash, [])[-10:]  # Last 10
        
        return {
            'success': True,
            'error': error_data
        }
    
    def clear_old_errors(self, days: int = 30) -> Dict[str, Any]:
        """Clear errors older than specified days"""
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        cutoff_iso = cutoff_date.isoformat()
        
        cleared_count = 0
        hashes_to_remove = []
        
        for error_hash, error_data in self.error_hashes.items():
            last_occurrence = error_data.get('last_occurrence')
            if last_occurrence and last_occurrence < cutoff_iso:
                hashes_to_remove.append(error_hash)
                cleared_count += error_data['count']
        
        for error_hash in hashes_to_remove:
            del self.error_hashes[error_hash]
            if error_hash in self.error_counts:
                del self.error_counts[error_hash]
            if error_hash in self.error_timestamps:
                del self.error_timestamps[error_hash]
        
        # Update total_errors count
        self.total_errors = sum(data.get('count', 0) for data in self.error_hashes.values())
        
        return {
            'success': True,
            'cleared_count': cleared_count,
            'hashes_removed': len(hashes_to_remove),
            'remaining_errors': len(self.error_hashes)
        }
    
    def clear_all_errors(self) -> Dict[str, Any]:
        """Clear all errors (reset error tracking)"""
        total_cleared = self.total_errors
        hash_count = len(self.error_hashes)
        
        self.error_hashes.clear()
        self.error_history.clear()
        self.error_counts.clear()
        self.error_timestamps.clear()
        self.total_errors = 0
        
        return {
            'success': True,
            'cleared_count': total_cleared,
            'hashes_removed': hash_count,
            'message': 'All errors cleared'
        }
    
    def fix_error_tracking_issues(self) -> Dict[str, Any]:
        """Fix common error tracking issues"""
        fixes_applied = []
        
        # Fix 1: Remove invalid error hashes
        invalid_hashes = []
        for error_hash, error_data in list(self.error_hashes.items()):
            if not isinstance(error_data, dict) or 'endpoint' not in error_data:
                invalid_hashes.append(error_hash)
                fixes_applied.append(f'Removed invalid error hash: {error_hash[:16]}...')
        
        for error_hash in invalid_hashes:
            if error_hash in self.error_hashes:
                del self.error_hashes[error_hash]
            if error_hash in self.error_counts:
                del self.error_counts[error_hash]
            if error_hash in self.error_timestamps:
                del self.error_timestamps[error_hash]
        
        # Fix 2: Sync error counts
        for error_hash in list(self.error_hashes.keys()):
            if error_hash not in self.error_counts:
                self.error_counts[error_hash] = self.error_hashes[error_hash].get('count', 1)
                fixes_applied.append(f'Synced count for hash: {error_hash[:16]}...')
        
        # Fix 3: Recalculate total_errors
        old_total = self.total_errors
        self.total_errors = sum(data.get('count', 0) for data in self.error_hashes.values())
        if old_total != self.total_errors:
            fixes_applied.append(f'Recalculated total_errors: {old_total} -> {self.total_errors}')
        
        # Fix 4: Clean up empty endpoints
        empty_endpoints = [ep for ep, errors in self.error_history.items() if not errors]
        for ep in empty_endpoints:
            del self.error_history[ep]
            fixes_applied.append(f'Removed empty endpoint history: {ep}')
        
        return {
            'success': True,
            'fixes_applied': fixes_applied,
            'total_fixes': len(fixes_applied),
            'remaining_errors': len(self.error_hashes),
            'total_errors': self.total_errors
        }
    
    def increment_request_count(self):
        """Increment total request count"""
        self.total_requests += 1


# Global instance
error_hash_tracking = ErrorHashTracking()

