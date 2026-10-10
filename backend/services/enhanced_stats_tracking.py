"""
Enhanced Stats Tracking & Counting System
Comprehensive statistics tracking with real-time updates, upgrades, and detailed counting
"""
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from collections import defaultdict
from sqlalchemy import func, and_, or_


class EnhancedStatsTracker:
    """Enhanced statistics tracking with comprehensive counting and upgrades"""
    
    def __init__(self):
        """Initialize enhanced stats tracker"""
        self.stat_snapshots = defaultdict(list)  # {user_id: [snapshots]}
        self.stat_upgrades = defaultdict(list)  # {user_id: [upgrades]}
        self.counting_cache = defaultdict(dict)  # {user_id: {metric: count}}
        self.last_update = defaultdict(datetime)  # {user_id: timestamp}
        
    def get_comprehensive_counts(self, user_id: str) -> Dict[str, Any]:
        """
        Get comprehensive counting statistics for a user
        
        Returns detailed counts for:
        - Videos (total, by category, by quality, by date)
        - Achievements & Milestones
        - XP & Level progression
        - Stats points
        - Game activities
        """
        try:
            from src.db.models import db, Documentary, MovieClip
            from backend.services.hunters_leveling_system import hunters_leveling_system
            from backend.services.game_achievements import game_achievement_system
            
            counts = {
                'videos': self._count_videos(user_id),
                'achievements': self._count_achievements(user_id),
                'milestones': self._count_milestones(user_id),
                'xp_progression': self._count_xp_progression(user_id),
                'stats_points': self._count_stats_points(user_id),
                'game_activities': self._count_game_activities(user_id),
                'quality_stats': self._count_quality_stats(user_id),
                'category_breakdown': self._count_category_breakdown(user_id),
                'time_breakdown': self._count_time_breakdown(user_id),
                'leveling_stats': self._count_leveling_stats(user_id)
            }
            
            # Cache the counts
            self.counting_cache[user_id] = counts
            self.last_update[user_id] = datetime.utcnow()
            
            return counts
            
        except Exception as e:
            print(f"[EnhancedStats] Error getting comprehensive counts: {e}")
            return self._get_empty_counts()
    
    def _count_videos(self, user_id: str) -> Dict[str, Any]:
        """Count video-related statistics"""
        try:
            from src.db.models import db, Documentary
            
            total = Documentary.query.filter_by(status='completed').count()
            
            # By category
            categories = ['underholdning', 'porn', 'rettigheder']
            by_category = {}
            for cat in categories:
                count = Documentary.query.filter_by(
                    status='completed',
                    category_name=cat
                ).count()
                by_category[cat] = count
            
            # By quality level
            quality_levels = {
                'ultra': Documentary.query.filter(
                    Documentary.status == 'completed',
                    Documentary.quality_score >= 0.95
                ).count(),
                'premium': Documentary.query.filter(
                    Documentary.status == 'completed',
                    Documentary.quality_score >= 0.85,
                    Documentary.quality_score < 0.95
                ).count(),
                'high': Documentary.query.filter(
                    Documentary.status == 'completed',
                    Documentary.quality_score >= 0.75,
                    Documentary.quality_score < 0.85
                ).count(),
                'medium': Documentary.query.filter(
                    Documentary.status == 'completed',
                    Documentary.quality_score >= 0.60,
                    Documentary.quality_score < 0.75
                ).count(),
                'low': Documentary.query.filter(
                    Documentary.status == 'completed',
                    Documentary.quality_score < 0.60,
                    Documentary.quality_score.isnot(None)
                ).count()
            }
            
            # By date ranges
            now = datetime.utcnow()
            date_ranges = {
                'today': Documentary.query.filter(
                    Documentary.status == 'completed',
                    func.date(Documentary.created_at) == now.date()
                ).count(),
                'this_week': Documentary.query.filter(
                    Documentary.status == 'completed',
                    Documentary.created_at >= now - timedelta(days=7)
                ).count(),
                'this_month': Documentary.query.filter(
                    Documentary.status == 'completed',
                    Documentary.created_at >= now - timedelta(days=30)
                ).count(),
                'this_year': Documentary.query.filter(
                    Documentary.status == 'completed',
                    Documentary.created_at >= now - timedelta(days=365)
                ).count()
            }
            
            return {
                'total': total,
                'by_category': by_category,
                'by_quality': quality_levels,
                'by_date': date_ranges,
                'average_quality': self._get_average_quality(),
                'total_duration': self._get_total_duration()
            }
        except Exception as e:
            print(f"[EnhancedStats] Error counting videos: {e}")
            return {'total': 0, 'by_category': {}, 'by_quality': {}, 'by_date': {}}
    
    def _count_achievements(self, user_id: str) -> Dict[str, Any]:
        """Count achievement statistics"""
        try:
            from backend.services.game_achievements import game_achievement_system
            
            if not game_achievement_system:
                return {'total': 0, 'earned': 0, 'percentage': 0}
            
            achievements = game_achievement_system.get_user_achievements(user_id)
            total = len(achievements)
            earned = sum(1 for ach in achievements if ach.get('earned', False))
            percentage = (earned / total * 100) if total > 0 else 0
            
            # Count by type
            by_type = defaultdict(int)
            for ach in achievements:
                ach_type = ach.get('type', 'general')
                by_type[ach_type] += 1
                if ach.get('earned', False):
                    by_type[f'{ach_type}_earned'] += 1
            
            return {
                'total': total,
                'earned': earned,
                'remaining': total - earned,
                'percentage': round(percentage, 2),
                'by_type': dict(by_type),
                'total_points_earned': sum(
                    ach.get('points', 0) for ach in achievements if ach.get('earned', False)
                )
            }
        except Exception as e:
            print(f"[EnhancedStats] Error counting achievements: {e}")
            return {'total': 0, 'earned': 0, 'percentage': 0}
    
    def _count_milestones(self, user_id: str) -> Dict[str, Any]:
        """Count milestone statistics"""
        try:
            from backend.services.game_achievements import game_achievement_system
            
            if not game_achievement_system:
                return {'total': 0, 'reached': 0, 'percentage': 0}
            
            milestones = game_achievement_system.get_user_milestones(user_id)
            total = len(milestones)
            reached = sum(1 for mil in milestones if mil.get('reached', False))
            percentage = (reached / total * 100) if total > 0 else 0
            
            return {
                'total': total,
                'reached': reached,
                'remaining': total - reached,
                'percentage': round(percentage, 2),
                'total_points_earned': sum(
                    mil.get('points', 0) for mil in milestones if mil.get('reached', False)
                )
            }
        except Exception as e:
            print(f"[EnhancedStats] Error counting milestones: {e}")
            return {'total': 0, 'reached': 0, 'percentage': 0}
    
    def _count_xp_progression(self, user_id: str) -> Dict[str, Any]:
        """Count XP and progression statistics"""
        try:
            from backend.services.hunters_leveling_system import hunters_leveling_system
            
            if not hunters_leveling_system:
                return {'total_xp': 0, 'current_xp': 0, 'level': 1}
            
            profile = hunters_leveling_system.get_player_profile(user_id)
            leveling = profile.get('leveling', {})
            
            # Get XP history from profile (if available)
            xp_history = profile.get('xp_history', [])
            
            # Calculate XP by source
            xp_by_source = defaultdict(int)
            for entry in xp_history:
                source = entry.get('source', 'unknown')
                xp_amount = entry.get('xp_awarded', 0)
                xp_by_source[source] += xp_amount
            
            # Calculate daily/weekly/monthly XP
            now = datetime.utcnow()
            xp_today = sum(
                e.get('xp_awarded', 0) for e in xp_history
                if datetime.fromisoformat(e.get('timestamp', now.isoformat())) >= now.replace(hour=0, minute=0, second=0)
            ) if xp_history else 0
            xp_this_week = sum(
                e.get('xp_awarded', 0) for e in xp_history
                if datetime.fromisoformat(e.get('timestamp', now.isoformat())) >= now - timedelta(days=7)
            ) if xp_history else 0
            xp_this_month = sum(
                e.get('xp_awarded', 0) for e in xp_history
                if datetime.fromisoformat(e.get('timestamp', now.isoformat())) >= now - timedelta(days=30)
            ) if xp_history else 0
            
            return {
                'total_xp': leveling.get('total_xp', 0),
                'current_xp': leveling.get('current_xp', 0),
                'level': leveling.get('current_level', 1),
                'xp_to_next_level': leveling.get('xp_to_next_level', 0),
                'level_progress': leveling.get('level_progress', 0),
                'by_source': dict(xp_by_source),
                'recent': {
                    'today': xp_today,
                    'this_week': xp_this_week,
                    'this_month': xp_this_month
                },
                'total_entries': len(xp_history)
            }
        except Exception as e:
            print(f"[EnhancedStats] Error counting XP progression: {e}")
            return {'total_xp': 0, 'current_xp': 0, 'level': 1}
    
    def _count_stats_points(self, user_id: str) -> Dict[str, Any]:
        """Count stats points statistics"""
        try:
            from backend.services.hunters_leveling_system import hunters_leveling_system
            
            if not hunters_leveling_system:
                return {'total': 0, 'available': 0, 'allocated': {}}
            
            profile = hunters_leveling_system.get_player_profile(user_id)
            stats = profile.get('stats', {})
            
            allocated = {
                'creativity': stats.get('stat_creativity', 0),
                'efficiency': stats.get('stat_efficiency', 0),
                'quality': stats.get('stat_quality', 0),
                'social': stats.get('stat_social', 0),
                'knowledge': stats.get('stat_knowledge', 0)
            }
            
            total_allocated = sum(allocated.values())
            total_earned = profile.get('total_stats_points', 0)
            available = profile.get('available_stat_points', 0)
            
            return {
                'total_earned': total_earned,
                'available': available,
                'allocated': allocated,
                'total_allocated': total_allocated,
                'total_capacity': total_earned + total_allocated
            }
        except Exception as e:
            print(f"[EnhancedStats] Error counting stats points: {e}")
            return {'total': 0, 'available': 0, 'allocated': {}}
    
    def _count_game_activities(self, user_id: str) -> Dict[str, Any]:
        """Count game activity statistics"""
        try:
            from backend.services.hunters_leveling_system import hunters_leveling_system
            from backend.services.daily_challenges import daily_challenges
            
            activities = {
                'challenges_completed': 0,
                'battles_won': 0,
                'battles_lost': 0,
                'total_battles': 0,
                'prestige_count': 0
            }
            
            # Get challenge completion count
            try:
                from backend.services.daily_challenges import DailyChallenges
                daily_challenges = DailyChallenges()
                daily_chs = daily_challenges.get_daily_challenges(user_id)
                weekly_chs = daily_challenges.get_weekly_challenges(user_id)
                activities['challenges_completed'] = sum(
                    1 for ch in (daily_chs.get('challenges', []) + weekly_chs.get('challenges', []))
                    if ch.get('completed', False)
                )
            except Exception as e:
                print(f"[EnhancedStats] Error counting challenges: {e}")
            
            # Get battle stats
            try:
                from backend.services.battle_system import battle_system
                if battle_system:
                    battle_stats = battle_system.get_player_battle_stats(user_id)
                    activities['battles_won'] = battle_stats.get('wins', 0)
                    activities['battles_lost'] = battle_stats.get('losses', 0)
                    activities['total_battles'] = battle_stats.get('total_battles', 0)
            except Exception as e:
                print(f"[EnhancedStats] Error counting battles: {e}")
            
            # Get prestige count
            try:
                if hunters_leveling_system:
                    profile = hunters_leveling_system.get_player_profile(user_id)
                    activities['prestige_count'] = profile.get('leveling', {}).get('prestige_level', 0)
            except Exception as e:
                print(f"[EnhancedStats] Error counting prestige: {e}")
            
            return activities
        except Exception as e:
            print(f"[EnhancedStats] Error counting game activities: {e}")
            return {}
    
    def _count_quality_stats(self, user_id: str) -> Dict[str, Any]:
        """Count quality-related statistics"""
        try:
            from src.db.models import db, Documentary
            
            # Quality distribution
            quality_scores = db.session.query(Documentary.quality_score).filter(
                Documentary.status == 'completed',
                Documentary.quality_score.isnot(None),
                Documentary.quality_score > 0
            ).all()
            
            if not quality_scores:
                return {
                    'average': 0.0,
                    'highest': 0.0,
                    'lowest': 0.0,
                    'a_plus_count': 0,
                    'distribution': {}
                }
            
            scores = [float(score[0]) for score in quality_scores]
            
            # A+ quality count (>= 0.95)
            a_plus_count = Documentary.query.filter(
                Documentary.status == 'completed',
                or_(
                    Documentary.quality_score >= 0.95,
                    Documentary.quality_meets_a_plus == True
                )
            ).count()
            
            return {
                'average': round(sum(scores) / len(scores), 3),
                'highest': round(max(scores), 3),
                'lowest': round(min(scores), 3),
                'median': round(sorted(scores)[len(scores) // 2], 3),
                'a_plus_count': a_plus_count,
                'a_plus_percentage': round((a_plus_count / len(scores) * 100), 2) if scores else 0,
                'total_scored': len(scores)
            }
        except Exception as e:
            print(f"[EnhancedStats] Error counting quality stats: {e}")
            return {'average': 0.0, 'highest': 0.0, 'lowest': 0.0}
    
    def _count_category_breakdown(self, user_id: str) -> Dict[str, Any]:
        """Count category breakdown statistics"""
        try:
            from src.db.models import db, Documentary
            
            categories = ['underholdning', 'porn', 'rettigheder']
            breakdown = {}
            
            for cat in categories:
                count = Documentary.query.filter_by(
                    status='completed',
                    category_name=cat
                ).count()
                
                # Get average quality for this category
                avg_quality = db.session.query(
                    func.avg(Documentary.quality_score)
                ).filter(
                    Documentary.status == 'completed',
                    Documentary.category_name == cat,
                    Documentary.quality_score.isnot(None)
                ).scalar()
                
                breakdown[cat] = {
                    'count': count,
                    'average_quality': round(float(avg_quality), 3) if avg_quality else 0.0
                }
            
            total = sum(b['count'] for b in breakdown.values())
            for cat in breakdown:
                breakdown[cat]['percentage'] = round(
                    (breakdown[cat]['count'] / total * 100) if total > 0 else 0, 2
                )
            
            return breakdown
        except Exception as e:
            print(f"[EnhancedStats] Error counting category breakdown: {e}")
            return {}
    
    def _count_time_breakdown(self, user_id: str) -> Dict[str, Any]:
        """Count time-based breakdown statistics"""
        try:
            from src.db.models import Documentary
            
            now = datetime.utcnow()
            
            # Get creation dates
            docs = Documentary.query.filter_by(status='completed').all()
            
            by_hour = defaultdict(int)
            by_day_of_week = defaultdict(int)
            by_month = defaultdict(int)
            
            for doc in docs:
                if doc.created_at:
                    by_hour[doc.created_at.hour] += 1
                    by_day_of_week[doc.created_at.weekday()] += 1
                    by_month[doc.created_at.strftime('%Y-%m')] += 1
            
            return {
                'by_hour': dict(sorted(by_hour.items())),
                'by_day_of_week': {
                    'Monday': by_day_of_week[0],
                    'Tuesday': by_day_of_week[1],
                    'Wednesday': by_day_of_week[2],
                    'Thursday': by_day_of_week[3],
                    'Friday': by_day_of_week[4],
                    'Saturday': by_day_of_week[5],
                    'Sunday': by_day_of_week[6]
                },
                'by_month': dict(sorted(by_month.items()))
            }
        except Exception as e:
            print(f"[EnhancedStats] Error counting time breakdown: {e}")
            return {}
    
    def _count_leveling_stats(self, user_id: str) -> Dict[str, Any]:
        """Count leveling and progression statistics"""
        try:
            from backend.services.hunters_leveling_system import hunters_leveling_system
            
            if not hunters_leveling_system:
                return {'level': 1, 'tier': 'Novice'}
            
            profile = hunters_leveling_system.get_player_profile(user_id)
            leveling = profile.get('leveling', {})
            
            level = leveling.get('current_level', 1)
            
            # Determine tier
            if level <= 10:
                tier = 'Novice'
            elif level <= 25:
                tier = 'Apprentice'
            elif level <= 50:
                tier = 'Expert'
            elif level <= 100:
                tier = 'Master'
            else:
                tier = 'Legend'
            
            return {
                'level': level,
                'tier': tier,
                'title': leveling.get('title', 'Novice Hunter'),
                'prestige_level': leveling.get('prestige_level', 0),
                'total_levels_gained': level - 1,
                'next_level': level + 1,
                'xp_to_next': leveling.get('xp_to_next_level', 0),
                'progress_percentage': round(leveling.get('level_progress', 0) * 100, 2)
            }
        except Exception as e:
            print(f"[EnhancedStats] Error counting leveling stats: {e}")
            return {'level': 1, 'tier': 'Novice'}
    
    def _get_average_quality(self) -> float:
        """Get average quality score"""
        try:
            from src.db.models import db, Documentary
            
            avg = db.session.query(
                func.avg(Documentary.quality_score)
            ).filter(
                Documentary.status == 'completed',
                Documentary.quality_score.isnot(None),
                Documentary.quality_score > 0
            ).scalar()
            
            return round(float(avg), 3) if avg else 0.0
        except:
            return 0.0
    
    def _get_total_duration(self) -> int:
        """Get total duration in seconds"""
        try:
            from src.db.models import db, Documentary
            
            total = db.session.query(
                func.sum(Documentary.duration)
            ).filter_by(status='completed').scalar()
            
            return int(total) if total else 0
        except:
            return 0
    
    def _get_empty_counts(self) -> Dict[str, Any]:
        """Return empty counts structure"""
        return {
            'videos': {'total': 0},
            'achievements': {'total': 0, 'earned': 0},
            'milestones': {'total': 0, 'reached': 0},
            'xp_progression': {'total_xp': 0, 'level': 1},
            'stats_points': {'total': 0, 'available': 0},
            'game_activities': {},
            'quality_stats': {'average': 0.0},
            'category_breakdown': {},
            'time_breakdown': {},
            'leveling_stats': {'level': 1}
        }
    
    def record_stat_update(self, user_id: str, stat_type: str, value: Any, metadata: Dict = None):
        """Record a stat update for tracking"""
        snapshot = {
            'timestamp': datetime.utcnow().isoformat(),
            'stat_type': stat_type,
            'value': value,
            'metadata': metadata or {}
        }
        
        self.stat_snapshots[user_id].append(snapshot)
        
        # Keep only last 500 snapshots per user
        if len(self.stat_snapshots[user_id]) > 500:
            self.stat_snapshots[user_id] = self.stat_snapshots[user_id][-500:]
    
    def get_stat_upgrades(self, user_id: str) -> List[Dict[str, Any]]:
        """Get stat upgrade history for a user"""
        return self.stat_upgrades.get(user_id, [])
    
    def record_stat_upgrade(self, user_id: str, upgrade_type: str, old_value: Any, new_value: Any, cost: int = 0):
        """Record a stat upgrade"""
        upgrade = {
            'timestamp': datetime.utcnow().isoformat(),
            'upgrade_type': upgrade_type,
            'old_value': old_value,
            'new_value': new_value,
            'improvement': new_value - old_value if isinstance(new_value, (int, float)) else None,
            'cost': cost
        }
        
        self.stat_upgrades[user_id].append(upgrade)
        
        # Keep only last 100 upgrades per user
        if len(self.stat_upgrades[user_id]) > 100:
            self.stat_upgrades[user_id] = self.stat_upgrades[user_id][-100:]


# Global instance
enhanced_stats_tracker = EnhancedStatsTracker()

