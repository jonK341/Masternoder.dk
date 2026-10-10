"""
Theme Points System - Track and award theme points
"""
from datetime import datetime
from typing import Dict, List, Optional, Any
from collections import defaultdict
import json


class ThemePointsSystem:
    """Manages theme points tracking and awards"""
    
    def __init__(self):
        self.user_theme_points = defaultdict(dict)  # {user_id: {theme: points}}
        self.theme_leaderboards = defaultdict(list)  # {theme: [user_entries]}
        self.theme_stats = defaultdict(dict)  # {theme: {total_points, total_users, etc}}
    
    def award_theme_points(self, user_id: str, theme: str, points: int, 
                          source: str = 'general') -> Dict[str, Any]:
        """Award theme points to user"""
        if user_id not in self.user_theme_points:
            self.user_theme_points[user_id] = {}
        
        if theme not in self.user_theme_points[user_id]:
            self.user_theme_points[user_id][theme] = 0
        
        self.user_theme_points[user_id][theme] += points
        
        # Update theme stats
        if theme not in self.theme_stats:
            self.theme_stats[theme] = {
                'total_points': 0,
                'total_users': 0,
                'average_points': 0
            }
        
        self.theme_stats[theme]['total_points'] += points
        
        # Update leaderboard
        self._update_leaderboard(theme, user_id, self.user_theme_points[user_id][theme])
        
        return {
            'success': True,
            'user_id': user_id,
            'theme': theme,
            'points_awarded': points,
            'total_points': self.user_theme_points[user_id][theme],
            'source': source
        }
    
    def get_user_theme_points(self, user_id: str) -> Dict[str, Any]:
        """Get all theme points for user"""
        if user_id not in self.user_theme_points:
            self.user_theme_points[user_id] = {}
        
        total_points = sum(self.user_theme_points[user_id].values())
        
        return {
            'success': True,
            'user_id': user_id,
            'theme_points': dict(self.user_theme_points[user_id]),
            'total_theme_points': total_points,
            'themes_count': len(self.user_theme_points[user_id])
        }
    
    def get_theme_leaderboard(self, theme: str, limit: int = 10) -> Dict[str, Any]:
        """Get leaderboard for specific theme"""
        if theme not in self.theme_leaderboards:
            return {
                'success': True,
                'theme': theme,
                'leaderboard': [],
                'total_users': 0
            }
        
        leaderboard = sorted(
            self.theme_leaderboards[theme],
            key=lambda x: x['points'],
            reverse=True
        )[:limit]
        
        return {
            'success': True,
            'theme': theme,
            'leaderboard': leaderboard,
            'total_users': len(self.theme_leaderboards[theme])
        }
    
    def get_all_theme_stats(self) -> Dict[str, Any]:
        """Get stats for all themes"""
        # Recalculate stats
        for theme in self.theme_stats.keys():
            users_with_theme = sum(
                1 for user_points in self.user_theme_points.values()
                if theme in user_points and user_points[theme] > 0
            )
            total = self.theme_stats[theme]['total_points']
            avg = total / users_with_theme if users_with_theme > 0 else 0
            
            self.theme_stats[theme]['total_users'] = users_with_theme
            self.theme_stats[theme]['average_points'] = round(avg, 2)
        
        return {
            'success': True,
            'themes': dict(self.theme_stats),
            'total_themes': len(self.theme_stats)
        }
    
    def _update_leaderboard(self, theme: str, user_id: str, points: int):
        """Update theme leaderboard"""
        if theme not in self.theme_leaderboards:
            self.theme_leaderboards[theme] = []
        
        # Find existing entry
        existing = next(
            (entry for entry in self.theme_leaderboards[theme] if entry['user_id'] == user_id),
            None
        )
        
        if existing:
            existing['points'] = points
            existing['updated_at'] = datetime.utcnow().isoformat()
        else:
            self.theme_leaderboards[theme].append({
                'user_id': user_id,
                'points': points,
                'rank': 0,
                'updated_at': datetime.utcnow().isoformat()
            })


# Global instance
theme_points_system = ThemePointsSystem()

