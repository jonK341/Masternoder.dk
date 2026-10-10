"""
178 Systems Leaderboard Service
Leaderboards for all 178 point systems with achievements
"""
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from collections import defaultdict
import json

try:
    from backend.services.leaderboard_cache import leaderboard_cache
except ImportError:
    leaderboard_cache = None

class Leaderboard178Systems:
    """
    Leaderboard system for all 178 point systems
    Includes achievements and rankings
    """
    
    # Map system_id to unified_point_counter field names
    SYSTEM_FIELD_MAPPING = {
        'xp': 'xp_total',
        'battle': 'battle_points',
        'activity': 'activity_points',  # Will sum multiple activity fields
        'chat': 'chat_points',
        'theme': 'theme_points_total',
        'trophy': 'trophy_points',
        'trophies': 'trophy_points',
        'generation': 'generations_total',
        'reward': 'reward_points',  # Sum of various reward fields
        'social': 'social_points_total',
        'achievement': 'achievement_points',
        'stats': 'stats_points_total',
        'coins': 'coins',
        'credits': 'credits',
        'tokens': 'tokens',
    }
    
    def __init__(self):
        """Initialize leaderboard system"""
        self.cache = {}
        self.cache_ttl = 300  # 5 minutes
    
    def get_leaderboard(self, system_id: str, limit: int = 100, 
                       timeframe: str = 'all') -> Dict[str, Any]:
        """
        Get leaderboard for a specific point system
        
        Args:
            system_id: Point system identifier
            limit: Number of entries to return
            timeframe: 'all', 'daily', 'weekly', 'monthly'
            
        Returns:
            Leaderboard data with rankings
        """
        # Try to get from cache first
        if leaderboard_cache:
            cached = leaderboard_cache.get_cached_leaderboard(system_id, timeframe, limit)
            if cached:
                return {
                    'success': True,
                    'system_id': system_id,
                    'timeframe': timeframe,
                    'total_entries': len(cached),
                    'leaderboard': cached,
                    'updated_at': datetime.utcnow().isoformat(),
                    'cached': True
                }
        
        try:
            from backend.services.unified_point_counter import unified_point_counter
            from src.db.models import db, UserProfile
            
            # Get timeframe filter
            time_filter = self._get_timeframe_filter(timeframe)
            
            # Optimized: Query users with pagination support
            # Only load users that might be in top N (estimate: load 2x limit for safety)
            query_limit = min(limit * 2, 1000)  # Cap at 1000 for performance
            
            users = UserProfile.query.filter(
                UserProfile.preferences.isnot(None)
            ).limit(query_limit).all()
            
            rankings = []
            for user in users:
                try:
                    # Get user points (cached if possible)
                    all_points = unified_point_counter.get_all_points(user.user_id)
                    
                    # Get system-specific points using field mapping
                    points = self._get_system_points(system_id, all_points)
                    
                    if points > 0:
                        # Enhanced entry with intelligence from agents, service worker, skill sets, and rewards
                        entry = {
                            'user_id': user.user_id,
                            'username': user.username or f'User_{user.user_id[:8]}',
                            'points': points,
                            'rank': 0  # Will be set after sorting
                        }
                        
                        # Add aggregated intelligence
                        intelligence = self._get_user_intelligence(user.user_id, all_points)
                        entry.update(intelligence)
                        
                        rankings.append(entry)
                except Exception as e:
                    continue
            
            # Sort by points descending
            rankings.sort(key=lambda x: x['points'], reverse=True)
            
            # Assign ranks
            for i, entry in enumerate(rankings[:limit]):
                entry['rank'] = i + 1
                # Handle ties
                if i > 0 and entry['points'] == rankings[i-1]['points']:
                    entry['rank'] = rankings[i-1]['rank']
            
            result = {
                'success': True,
                'system_id': system_id,
                'timeframe': timeframe,
                'total_entries': len(rankings),
                'leaderboard': rankings[:limit],
                'updated_at': datetime.utcnow().isoformat(),
                'cached': False
            }
            
            # Cache the result
            if leaderboard_cache:
                leaderboard_cache.cache_leaderboard(
                    system_id, timeframe, limit, rankings[:limit]
                )
            
            return result
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'leaderboard': []
            }
    
    def get_user_rank(self, user_id: str, system_id: str) -> Dict[str, Any]:
        """Get user's rank in a specific system"""
        leaderboard = self.get_leaderboard(system_id, limit=10000)
        
        if not leaderboard.get('success'):
            return {'rank': None, 'total_players': 0}
        
        # Find user in leaderboard
        for entry in leaderboard['leaderboard']:
            if entry['user_id'] == user_id:
                return {
                    'rank': entry['rank'],
                    'points': entry['points'],
                    'total_players': leaderboard['total_entries'],
                    'percentile': (1 - (entry['rank'] / leaderboard['total_entries'])) * 100 if leaderboard['total_entries'] > 0 else 0
                }
        
        return {'rank': None, 'total_players': leaderboard['total_entries']}
    
    def get_all_systems_leaderboard(self, limit: int = 100) -> Dict[str, Any]:
        """Get combined leaderboard across all systems"""
        # Try cache first
        if leaderboard_cache:
            cached = leaderboard_cache.get_cached_leaderboard('all', 'all', limit)
            if cached:
                return {
                    'success': True,
                    'total_entries': len(cached),
                    'leaderboard': cached,
                    'updated_at': datetime.utcnow().isoformat(),
                    'cached': True
                }
        
        try:
            from backend.services.unified_point_counter import unified_point_counter
            from src.db.models import db, UserProfile
            
            # Optimized: Limit query to reasonable number
            query_limit = min(limit * 3, 2000)  # Load more for accurate totals, but cap it
            
            users = UserProfile.query.filter(
                UserProfile.preferences.isnot(None)
            ).limit(query_limit).all()
            
            total_scores = defaultdict(int)
            user_data = {}
            
            for user in users:
                try:
                    all_points = unified_point_counter.get_all_points(user.user_id)
                    total = sum([v for k, v in all_points.items() if isinstance(v, (int, float)) and k.endswith('_points')])
                    total_scores[user.user_id] = total
                    user_data[user.user_id] = {
                        'username': user.username or f'User_{user.user_id[:8]}',
                        'user_id': user.user_id
                    }
                except:
                    continue
            
            # Sort by total score
            sorted_users = sorted(total_scores.items(), key=lambda x: x[1], reverse=True)
            
            rankings = []
            for i, (user_id, total) in enumerate(sorted_users[:limit]):
                # Enhanced entry with intelligence
                entry = {
                    'rank': i + 1,
                    'user_id': user_id,
                    'username': user_data[user_id]['username'],
                    'total_points': total,
                    'points': total  # Alias for consistency
                }
                
                # Add aggregated intelligence
                try:
                    all_points = unified_point_counter.get_all_points(user_id)
                    intelligence = self._get_user_intelligence(user_id, all_points)
                    entry.update(intelligence)
                except:
                    pass  # Continue without intelligence if error
                
                rankings.append(entry)
            
            result = {
                'success': True,
                'total_entries': len(sorted_users),
                'leaderboard': rankings,
                'updated_at': datetime.utcnow().isoformat(),
                'cached': False
            }
            
            # Cache the result
            if leaderboard_cache:
                leaderboard_cache.cache_leaderboard('all', 'all', limit, rankings)
            
            return result
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'leaderboard': []
            }
    
    def _get_system_points(self, system_id: str, all_points: Dict[str, Any]) -> int:
        """
        Get points for a specific system using field mapping
        Handles special cases like activity (sum of multiple fields)
        """
        # Check direct mapping first
        if system_id in self.SYSTEM_FIELD_MAPPING:
            field_name = self.SYSTEM_FIELD_MAPPING[system_id]
            if system_id == 'activity':
                # Activity points: sum of multiple activity-related fields
                activity_points = all_points.get('activity_points', 0) or 0
                videos_created = (all_points.get('videos_created', 0) or 0) * 10
                videos_watched = (all_points.get('videos_watched', 0) or 0) * 5
                videos_shared = (all_points.get('videos_shared', 0) or 0) * 15
                time_points = (all_points.get('time_played', 0) or 0) // 60  # 1 point per minute
                return activity_points + videos_created + videos_watched + videos_shared + time_points
            elif system_id == 'reward':
                # Reward points: sum of various reward fields
                reward_points = all_points.get('reward_points', 0) or 0
                achievement_points = all_points.get('achievement_points', 0) or 0
                milestone_points = all_points.get('milestone_points', 0) or 0
                trophy_points = all_points.get('trophy_points', 0) or 0
                return reward_points + achievement_points + milestone_points + trophy_points
            else:
                return all_points.get(field_name, 0) or 0
        
        # Fallback: try {system_id}_points format
        fallback_field = f'{system_id}_points'
        if fallback_field in all_points:
            return all_points.get(fallback_field, 0) or 0
        
        # Try without _points suffix
        if system_id in all_points:
            value = all_points.get(system_id)
            if isinstance(value, (int, float)):
                return int(value) or 0
        
        return 0
    
    def _get_user_intelligence(self, user_id: str, all_points: Dict[str, Any]) -> Dict[str, Any]:
        """
        Aggregate intelligence from agents, service worker, skill sets, and rewards
        Returns comprehensive user intelligence data
        """
        intelligence = {
            'agent_data': {},
            'service_worker_stats': {},
            'skill_sets': [],
            'rewards': {},
            'aggregated_score': 0
        }
        
        # 1. Agent Data (skills, levels, activities, performance)
        try:
            from src.db.models import Agent
            agents = Agent.query.filter_by(user_id=user_id).limit(10).all()
            
            if agents:
                agent_data = []
                total_agent_points = 0
                total_agent_level = 0
                total_agent_skills = 0
                
                for agent in agents:
                    try:
                        agent_info = {
                            'agent_id': agent.agent_id if hasattr(agent, 'agent_id') else str(agent.id),
                            'agent_name': agent.agent_name if hasattr(agent, 'agent_name') else 'Unknown',
                            'agent_type': agent.agent_type if hasattr(agent, 'agent_type') else 'general',
                            'level_system_1': getattr(agent, 'level_system_1', 1),
                            'level_system_2': getattr(agent, 'level_system_2', 1),
                            'level_system_3': getattr(agent, 'level_system_3', 1),
                            'total_tasks_completed': getattr(agent, 'total_tasks_completed', 0),
                            'total_skills_learned': getattr(agent, 'total_skills_learned', 0),
                            'total_points_earned': getattr(agent, 'total_points_earned', 0),
                            'video_generation_count': getattr(agent, 'video_generation_count', 0)
                        }
                        
                        # Try to get skills from JSON fields
                        try:
                            top50_skills = json.loads(getattr(agent, 'top50_skills', '[]')) if hasattr(agent, 'top50_skills') and getattr(agent, 'top50_skills') else []
                            if isinstance(top50_skills, list):
                                agent_info['skills'] = top50_skills[:10]  # Top 10 skills
                                total_agent_skills += len(top50_skills)
                        except:
                            agent_info['skills'] = []
                        
                        total_agent_points += agent_info['total_points_earned']
                        total_agent_level += (agent_info['level_system_1'] + agent_info['level_system_2'] + agent_info['level_system_3']) // 3
                        agent_data.append(agent_info)
                    except Exception as e:
                        continue
                
                intelligence['agent_data'] = {
                    'agents': agent_data,
                    'total_agents': len(agent_data),
                    'total_agent_points': total_agent_points,
                    'average_agent_level': total_agent_level // len(agent_data) if agent_data else 0,
                    'total_agent_skills': total_agent_skills,
                    'total_tasks_completed': sum(a.get('total_tasks_completed', 0) for a in agent_data)
                }
        except Exception as e:
            logger.debug(f"Agent data not available for user {user_id}: {e}", exc_info=False)
        
        # 2. Service Worker Stats (activity tracking, engagement)
        try:
            service_worker_stats = {}
            
            # Get activity data from activity_points_system
            try:
                from backend.services.activity_points_system import ActivityPointsSystem
                activity_system = ActivityPointsSystem()
                if hasattr(activity_system, 'visitor_data') and user_id in activity_system.visitor_data:
                    visitor = activity_system.visitor_data[user_id]
                    service_worker_stats.update({
                        'total_activities': visitor.get('total_activities', 0),
                        'total_time_spent': visitor.get('total_time_spent', 0),
                        'session_count': visitor.get('session_count', 1),
                        'activity_types': dict(visitor.get('activity_types', {}))
                    })
            except:
                pass  # Activity system not available
            
            # Also get from unified points
            service_worker_stats.update({
                'videos_created': all_points.get('videos_created', 0),
                'videos_watched': all_points.get('videos_watched', 0),
                'videos_shared': all_points.get('videos_shared', 0),
                'time_played': all_points.get('time_played', 0),
                'login_streak': all_points.get('login_streak', 0),
                'daily_logins': all_points.get('daily_logins', 0)
            })
            
            intelligence['service_worker_stats'] = service_worker_stats
        except Exception as e:
            logger.debug(f"Service worker stats not available for user {user_id}: {e}", exc_info=False)
        
        # 3. Skill Sets (battle skills, agent skills, etc.)
        try:
            skill_sets = []
            
            # Agent Battle Skills
            try:
                from backend.services.agent_battle_skills import agent_battle_skills
                if hasattr(agent_battle_skills, 'get_user_skills'):
                    battle_skills = agent_battle_skills.get_user_skills(user_id)
                    if battle_skills.get('success') and battle_skills.get('skills'):
                        skill_sets.append({
                            'type': 'battle_skills',
                            'name': 'Battle Skills',
                            'skills': battle_skills['skills'],
                            'count': battle_skills.get('total', 0)
                        })
            except Exception as e:
                logger.debug(f"Battle skills not available for user {user_id}: {e}", exc_info=False)
            
            # Agent Enhanced Skills
            try:
                from backend.services.agent_enhanced_skills import agent_enhanced_skills
                if hasattr(agent_enhanced_skills, 'get_user_skills'):
                    enhanced_skills = agent_enhanced_skills.get_user_skills(user_id)
                    if enhanced_skills.get('success') and enhanced_skills.get('skills'):
                        skill_sets.append({
                            'type': 'enhanced_skills',
                            'name': 'Enhanced Skills',
                            'skills': enhanced_skills['skills'],
                            'count': enhanced_skills.get('total', 0)
                        })
            except Exception as e:
                logger.debug(f"Enhanced skills not available for user {user_id}: {e}", exc_info=False)
            
            intelligence['skill_sets'] = skill_sets
        except Exception as e:
            logger.debug(f"Skill sets not available for user {user_id}: {e}", exc_info=False)
        
        # 4. Rewards (pending and claimed)
        try:
            from backend.services.rewards_system_v2 import rewards_system_v2
            if rewards_system_v2 and hasattr(rewards_system_v2, 'get_user_rewards'):
                user_rewards = rewards_system_v2.get_user_rewards(user_id, include_history=False)
                if user_rewards.get('success'):
                    intelligence['rewards'] = {
                        'pending_count': len(user_rewards.get('pending_rewards', [])),
                        'total_claimed': len(user_rewards.get('reward_history', [])),
                        'statistics': user_rewards.get('statistics', {})
                    }
        except Exception as e:
            logger.debug(f"Rewards not available for user {user_id}: {e}", exc_info=False)
        
        # Calculate aggregated score (intelligence score)
        aggregated_score = 0
        aggregated_score += intelligence['agent_data'].get('total_agent_points', 0) * 0.3
        aggregated_score += intelligence['service_worker_stats'].get('total_activities', 0) * 2
        aggregated_score += intelligence['service_worker_stats'].get('time_played', 0) // 60  # 1 point per minute
        aggregated_score += sum(s.get('count', 0) for s in intelligence['skill_sets']) * 50
        aggregated_score += intelligence['rewards'].get('total_claimed', 0) * 25
        aggregated_score += intelligence['rewards'].get('pending_count', 0) * 10
        
        intelligence['aggregated_score'] = int(aggregated_score)
        
        return intelligence
    
    def _get_timeframe_filter(self, timeframe: str):
        """Get timeframe filter for database queries"""
        now = datetime.utcnow()
        if timeframe == 'daily':
            return now - timedelta(days=1)
        elif timeframe == 'weekly':
            return now - timedelta(weeks=1)
        elif timeframe == 'monthly':
            return now - timedelta(days=30)
        else:
            return None


# Global instance
leaderboard_178_systems = Leaderboard178Systems()

