"""
Enhanced Progress Data System
Aggressive data tracking with calculator integration
"""
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import logging
import json

logger = logging.getLogger(__name__)

class EnhancedProgressData:
    """Tracks detailed progress with analytics and predictions"""
    
    def __init__(self):
        self.user_progress = {}  # user_id -> progress_data
        self.leveling_analytics = {}  # user_id -> leveling_data
        self.point_accumulation = {}  # user_id -> point_history
        self.achievement_predictions = {}  # user_id -> predictions
        self.performance_benchmarks = {}  # user_id -> benchmarks
        self.competitive_rankings = {}  # category -> rankings
    
    def track_progress(self, user_id: str, progress_type: str, value: float,
                      metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        """Track detailed progress"""
        if user_id not in self.user_progress:
            self.user_progress[user_id] = {
                'total_activities': 0,
                'progress_by_type': {},
                'daily_progress': {},
                'weekly_progress': {},
                'monthly_progress': {},
                'all_time_high': {},
                'streaks': {},
                'trends': {}
            }
        
        progress_data = self.user_progress[user_id]
        progress_data['total_activities'] += 1
        
        # Track by type
        if progress_type not in progress_data['progress_by_type']:
            progress_data['progress_by_type'][progress_type] = {
                'count': 0,
                'total_value': 0,
                'average': 0,
                'max_value': 0,
                'min_value': float('inf')
            }
        
        type_data = progress_data['progress_by_type'][progress_type]
        type_data['count'] += 1
        type_data['total_value'] += value
        type_data['average'] = type_data['total_value'] / type_data['count']
        type_data['max_value'] = max(type_data['max_value'], value)
        type_data['min_value'] = min(type_data['min_value'], value)
        
        # Daily tracking
        today = datetime.utcnow().date().isoformat()
        if today not in progress_data['daily_progress']:
            progress_data['daily_progress'][today] = {}
        
        if progress_type not in progress_data['daily_progress'][today]:
            progress_data['daily_progress'][today][progress_type] = 0
        
        progress_data['daily_progress'][today][progress_type] += value
        
        # Update all-time high
        if progress_type not in progress_data['all_time_high']:
            progress_data['all_time_high'][progress_type] = value
        else:
            progress_data['all_time_high'][progress_type] = max(
                progress_data['all_time_high'][progress_type], value
            )
        
        return {
            'success': True,
            'user_id': user_id,
            'progress_type': progress_type,
            'value': value,
            'summary': type_data
        }
    
    def calculate_leveling_analytics(self, user_id: str) -> Dict[str, Any]:
        """Calculate detailed leveling analytics"""
        try:
            from backend.services.unified_points_database import unified_points_db
            
            user_points = unified_points_db.get_user_points(user_id)
            total_points = sum(user_points.values()) if user_points else 0
            
            # Calculate level (simplified formula)
            level = int(total_points ** 0.5 / 10) + 1
            
            # Calculate progress to next level
            current_level_xp = (level - 1) ** 2 * 100
            next_level_xp = level ** 2 * 100
            progress = (total_points - current_level_xp) / (next_level_xp - current_level_xp) * 100
            
            # Calculate leveling rate
            if user_id not in self.leveling_analytics:
                self.leveling_analytics[user_id] = {
                    'levels_gained': [],
                    'leveling_times': [],
                    'average_leveling_time': 0
                }
            
            analytics = self.leveling_analytics[user_id]
            
            # Estimate time to next level
            recent_activities = self.user_progress.get(user_id, {}).get('total_activities', 0)
            if recent_activities > 0:
                points_per_activity = total_points / recent_activities
                points_needed = next_level_xp - total_points
                estimated_activities = points_needed / points_per_activity if points_per_activity > 0 else 0
            else:
                estimated_activities = 0
            
            return {
                'user_id': user_id,
                'current_level': level,
                'total_points': total_points,
                'current_level_xp': current_level_xp,
                'next_level_xp': next_level_xp,
                'progress_percentage': min(100, max(0, progress)),
                'points_to_next_level': max(0, next_level_xp - total_points),
                'estimated_activities_to_level': int(estimated_activities),
                'leveling_rate': analytics.get('average_leveling_time', 0)
            }
        except Exception as e:
            logger.error(f"Error calculating leveling analytics: {e}")
            return {'error': str(e)}
    
    def generate_point_accumulation_graph(self, user_id: str, days: int = 30) -> Dict[str, Any]:
        """Generate point accumulation graph data"""
        if user_id not in self.point_accumulation:
            self.point_accumulation[user_id] = []
        
        accumulation = self.point_accumulation[user_id]
        
        # Get recent data
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        recent_data = [
            entry for entry in accumulation
            if datetime.fromisoformat(entry['timestamp']) >= cutoff_date
        ]
        
        # Group by day
        daily_totals = {}
        for entry in recent_data:
            date = entry['timestamp'][:10]  # YYYY-MM-DD
            if date not in daily_totals:
                daily_totals[date] = 0
            daily_totals[date] += entry['points']
        
        # Create graph data
        graph_data = [
            {'date': date, 'points': points}
            for date, points in sorted(daily_totals.items())
        ]
        
        return {
            'user_id': user_id,
            'days': days,
            'data_points': len(graph_data),
            'graph_data': graph_data,
            'total_points': sum(d['points'] for d in graph_data),
            'average_daily': sum(d['points'] for d in graph_data) / len(graph_data) if graph_data else 0
        }
    
    def predict_achievements(self, user_id: str) -> Dict[str, Any]:
        """Predict upcoming achievements"""
        try:
            from backend.services.unified_points_database import unified_points_db
            
            user_points = unified_points_db.get_user_points(user_id)
            
            predictions = []
            
            # Predict based on current progress
            for point_type, current_value in user_points.items():
                # Predict milestones (100, 500, 1000, 2500, 5000, 10000)
                milestones = [100, 500, 1000, 2500, 5000, 10000]
                
                for milestone in milestones:
                    if current_value < milestone:
                        # Calculate estimated time
                        progress_data = self.user_progress.get(user_id, {})
                        type_data = progress_data.get('progress_by_type', {}).get(point_type, {})
                        
                        if type_data.get('average', 0) > 0:
                            points_needed = milestone - current_value
                            estimated_activities = points_needed / type_data['average']
                            
                            predictions.append({
                                'point_type': point_type,
                                'milestone': milestone,
                                'current_value': current_value,
                                'points_needed': points_needed,
                                'estimated_activities': int(estimated_activities),
                                'estimated_days': int(estimated_activities / max(1, type_data.get('count', 1) / 30))
                            })
                        break
            
            # Sort by estimated time
            predictions.sort(key=lambda x: x.get('estimated_days', 999))
            
            return {
                'user_id': user_id,
                'predictions': predictions[:10],  # Top 10
                'total_predictions': len(predictions)
            }
        except Exception as e:
            logger.error(f"Error predicting achievements: {e}")
            return {'error': str(e)}
    
    def calculate_performance_benchmarks(self, user_id: str) -> Dict[str, Any]:
        """Calculate performance benchmarks"""
        progress_data = self.user_progress.get(user_id, {})
        
        benchmarks = {
            'daily_average': 0,
            'weekly_average': 0,
            'monthly_average': 0,
            'consistency_score': 0,
            'improvement_rate': 0,
            'peak_performance': {}
        }
        
        # Calculate daily average
        daily_data = progress_data.get('daily_progress', {})
        if daily_data:
            recent_days = list(daily_data.values())[-7:]  # Last 7 days
            daily_totals = [sum(day.values()) for day in recent_days]
            benchmarks['daily_average'] = sum(daily_totals) / len(daily_totals) if daily_totals else 0
        
        # Calculate consistency (variance)
        if len(daily_totals) > 1:
            mean = benchmarks['daily_average']
            variance = sum((x - mean) ** 2 for x in daily_totals) / len(daily_totals)
            std_dev = variance ** 0.5
            benchmarks['consistency_score'] = max(0, 100 - (std_dev / mean * 100)) if mean > 0 else 0
        
        # Calculate improvement rate
        if len(daily_totals) >= 2:
            first_half = sum(daily_totals[:len(daily_totals)//2]) / (len(daily_totals)//2)
            second_half = sum(daily_totals[len(daily_totals)//2:]) / (len(daily_totals) - len(daily_totals)//2)
            benchmarks['improvement_rate'] = ((second_half - first_half) / first_half * 100) if first_half > 0 else 0
        
        # Peak performance
        all_time_high = progress_data.get('all_time_high', {})
        benchmarks['peak_performance'] = all_time_high
        
        return {
            'user_id': user_id,
            'benchmarks': benchmarks
        }
    
    def get_competitive_rankings(self, category: str = 'all') -> Dict[str, Any]:
        """Get competitive rankings"""
        try:
            from backend.services.unified_points_database import unified_points_db
            
            # Get all users (simplified - in production, use proper query)
            # For now, return structure
            rankings = {
                'category': category,
                'top_users': [],
                'user_rank': None,
                'total_participants': 0
            }
            
            return {
                'success': True,
                'rankings': rankings
            }
        except Exception as e:
            logger.error(f"Error getting rankings: {e}")
            return {'error': str(e)}
    
    def add_point_entry(self, user_id: str, point_type: str, points: float):
        """Add point entry to accumulation history"""
        if user_id not in self.point_accumulation:
            self.point_accumulation[user_id] = []
        
        self.point_accumulation[user_id].append({
            'timestamp': datetime.utcnow().isoformat(),
            'point_type': point_type,
            'points': points
        })
        
        # Keep only last 1000 entries
        if len(self.point_accumulation[user_id]) > 1000:
            self.point_accumulation[user_id] = self.point_accumulation[user_id][-1000:]

enhanced_progress_data = EnhancedProgressData()
