"""
Point History Tracking System
Tracks all point changes with timestamps, sources, and metadata
"""
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import json
import os
from collections import defaultdict

class PointHistoryTracking:
    """Tracks point history with detailed metadata"""
    
    def __init__(self, storage_dir: str = "data/point_history"):
        self.storage_dir = storage_dir
        os.makedirs(storage_dir, exist_ok=True)
        
        # In-memory cache for recent history
        self.recent_history = defaultdict(list)  # user_id -> [history entries]
        self.max_cache_size = 1000
    
    def record_point_change(self, user_id: str, point_type: str, 
                           amount: float, source: str,
                           metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        """Record a point change in history"""
        entry = {
            'entry_id': f"{user_id}_{datetime.utcnow().timestamp()}_{point_type}",
            'user_id': user_id,
            'point_type': point_type,
            'amount': amount,
            'source': source,
            'metadata': metadata or {},
            'timestamp': datetime.utcnow().isoformat(),
            'date': datetime.utcnow().date().isoformat()
        }
        
        # Add to cache
        if user_id not in self.recent_history:
            self.recent_history[user_id] = []
        self.recent_history[user_id].append(entry)
        
        # Limit cache size
        if len(self.recent_history[user_id]) > self.max_cache_size:
            self.recent_history[user_id] = self.recent_history[user_id][-self.max_cache_size:]
        
        # Save to file
        self._save_to_file(user_id, entry)
        
        return {
            'success': True,
            'entry': entry
        }
    
    def get_point_history(self, user_id: str, 
                         point_type: Optional[str] = None,
                         start_date: Optional[str] = None,
                         end_date: Optional[str] = None,
                         limit: int = 100) -> Dict[str, Any]:
        """Get point history for a user"""
        # Load from cache and file
        history = self._load_user_history(user_id)
        
        # Filter by point type
        if point_type:
            history = [h for h in history if h.get('point_type') == point_type]
        
        # Filter by date range
        if start_date:
            history = [h for h in history if h.get('date') >= start_date]
        if end_date:
            history = [h for h in history if h.get('date') <= end_date]
        
        # Sort by timestamp (newest first)
        history.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
        
        # Limit results
        history = history[:limit]
        
        return {
            'success': True,
            'user_id': user_id,
            'total_entries': len(history),
            'history': history
        }
    
    def get_point_statistics(self, user_id: str,
                            point_type: Optional[str] = None,
                            days: int = 30) -> Dict[str, Any]:
        """Get point statistics for a user"""
        cutoff_date = (datetime.utcnow() - timedelta(days=days)).date().isoformat()
        history = self._load_user_history(user_id)
        
        # Filter by date and point type
        if point_type:
            history = [h for h in history if h.get('point_type') == point_type and h.get('date') >= cutoff_date]
        else:
            history = [h for h in history if h.get('date') >= cutoff_date]
        
        # Calculate statistics
        total_earned = sum(h.get('amount', 0) for h in history if h.get('amount', 0) > 0)
        total_spent = abs(sum(h.get('amount', 0) for h in history if h.get('amount', 0) < 0))
        net_change = total_earned - total_spent
        
        # Group by source
        by_source = defaultdict(float)
        for h in history:
            source = h.get('source', 'unknown')
            by_source[source] += h.get('amount', 0)
        
        # Group by day
        by_day = defaultdict(float)
        for h in history:
            day = h.get('date', '')
            by_day[day] += h.get('amount', 0)
        
        return {
            'success': True,
            'user_id': user_id,
            'period_days': days,
            'total_entries': len(history),
            'total_earned': total_earned,
            'total_spent': total_spent,
            'net_change': net_change,
            'by_source': dict(by_source),
            'by_day': dict(by_day),
            'average_per_day': net_change / days if days > 0 else 0
        }
    
    def _save_to_file(self, user_id: str, entry: Dict[str, Any]):
        """Save history entry to file"""
        file_path = os.path.join(self.storage_dir, f"{user_id}_history.json")
        
        # Load existing history
        history = []
        if os.path.exists(file_path):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    history = json.load(f)
            except:
                history = []
        
        # Add new entry
        history.append(entry)
        
        # Keep only last 10000 entries per user
        if len(history) > 10000:
            history = history[-10000:]
        
        # Save
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(history, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Error saving point history: {e}")
    
    def _load_user_history(self, user_id: str) -> List[Dict[str, Any]]:
        """Load user history from cache and file"""
        # Start with cache
        history = list(self.recent_history.get(user_id, []))
        
        # Load from file
        file_path = os.path.join(self.storage_dir, f"{user_id}_history.json")
        if os.path.exists(file_path):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    file_history = json.load(f)
                    # Merge and deduplicate
                    existing_ids = {h.get('entry_id') for h in history}
                    for h in file_history:
                        if h.get('entry_id') not in existing_ids:
                            history.append(h)
            except Exception as e:
                print(f"Error loading point history: {e}")
        
        return history

# Global instance
point_history_tracking = PointHistoryTracking()

