"""
User Agent Skills Service
Manages agent skill assignment and progression for users
"""
import os
import json
from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta, timezone

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

class UserAgentSkills:
    """Service for managing user agent skills"""
    
    def __init__(self, base_dir: Optional[str] = None):
        self.base_dir = base_dir or BASE_DIR
        self.data_dir = os.path.join(self.base_dir, 'logs', 'user_agent_skills')
        os.makedirs(self.data_dir, exist_ok=True)
        
        # Load agent skillset system
        try:
            from backend.services.agent_skillset import agent_skillset
            self.agent_skillset = agent_skillset
        except:
            self.agent_skillset = None
    
    def assign_initial_skills(self, user_id: str, scraped_info: Dict) -> Dict:
        """Assign initial agent skills based on scraped information"""
        assigned_skills = {
            'user_id': user_id,
            'assigned_agents': [],
            'skills': [],
            'skill_path': 'balanced',  # balanced, creator, battle, social, analytics
            'assigned_at': datetime.now().isoformat()
        }
        
        # Analyze scraped info to determine skill path
        behavior_pattern = scraped_info.get('behavior', {}).get('behavior_pattern', 'balanced')
        preferences = scraped_info.get('preferences', {}).get('content_interests', [])
        device_type = scraped_info.get('device', {}).get('device_type', 'desktop')
        
        # Determine skill path
        if 'creator' in behavior_pattern or 'generate' in str(preferences).lower():
            assigned_skills['skill_path'] = 'creator'
            assigned_skills['assigned_agents'] = ['content_generator_agent', 'learning_agent']
            assigned_skills['skills'] = [
                {'agent_id': 'content_generator_agent', 'skill': 'generate_video', 'level': 1},
                {'agent_id': 'content_generator_agent', 'skill': 'generate_image', 'level': 1},
                {'agent_id': 'content_generator_agent', 'skill': 'create_template', 'level': 1},
                {'agent_id': 'content_generator_agent', 'skill': 'ai_assist_task', 'level': 1},
                {'agent_id': 'learning_agent', 'skill': 'ai_follow_user_action', 'level': 1},
                {'agent_id': 'learning_agent', 'skill': 'ai_nice_and_easy', 'level': 1},
            ]
        elif 'battle' in behavior_pattern or 'battle' in str(preferences).lower():
            assigned_skills['skill_path'] = 'battle'
            assigned_skills['assigned_agents'] = ['battle_strategy_agent', 'learning_agent']
            assigned_skills['skills'] = [
                {'agent_id': 'battle_strategy_agent', 'skill': 'analyze_battle', 'level': 1},
                {'agent_id': 'battle_strategy_agent', 'skill': 'create_strategy', 'level': 1},
                {'agent_id': 'battle_strategy_agent', 'skill': 'optimize_tactics', 'level': 1},
                {'agent_id': 'battle_strategy_agent', 'skill': 'ai_win_with_user', 'level': 1},
                {'agent_id': 'learning_agent', 'skill': 'ai_follow_user_action', 'level': 1},
                {'agent_id': 'learning_agent', 'skill': 'ai_nice_and_easy', 'level': 1},
            ]
        elif 'social' in behavior_pattern or 'social' in str(preferences).lower():
            assigned_skills['skill_path'] = 'social'
            assigned_skills['assigned_agents'] = ['social_engagement_agent', 'learning_agent']
            assigned_skills['skills'] = [
                {'agent_id': 'social_engagement_agent', 'skill': 'manage_friends', 'level': 1},
                {'agent_id': 'social_engagement_agent', 'skill': 'coordinate_events', 'level': 1},
                {'agent_id': 'social_engagement_agent', 'skill': 'build_community', 'level': 1},
                {'agent_id': 'social_engagement_agent', 'skill': 'ai_suggest_next', 'level': 1},
                {'agent_id': 'learning_agent', 'skill': 'ai_follow_user_action', 'level': 1},
            ]
        elif 'analytics' in behavior_pattern or 'stats' in str(preferences).lower():
            assigned_skills['skill_path'] = 'analytics'
            assigned_skills['assigned_agents'] = ['analytics_agent', 'ai_intelligence_agent']
            assigned_skills['skills'] = [
                {'agent_id': 'analytics_agent', 'skill': 'analyze_user_behavior', 'level': 1},
                {'agent_id': 'analytics_agent', 'skill': 'track_metrics', 'level': 1},
                {'agent_id': 'analytics_agent', 'skill': 'generate_reports', 'level': 1},
                {'agent_id': 'analytics_agent', 'skill': 'ai_auto_optimize', 'level': 1},
                {'agent_id': 'ai_intelligence_agent', 'skill': 'pattern_recognition', 'level': 1},
                {'agent_id': 'ai_intelligence_agent', 'skill': 'ai_suggest_next', 'level': 1},
            ]
        elif 'ai' in behavior_pattern or 'assist' in str(preferences).lower():
            assigned_skills['skill_path'] = 'ai'
            assigned_skills['assigned_agents'] = ['content_generator_agent', 'ai_intelligence_agent', 'learning_agent']
            assigned_skills['skills'] = [
                {'agent_id': 'content_generator_agent', 'skill': 'generate_video', 'level': 1},
                {'agent_id': 'ai_intelligence_agent', 'skill': 'intelligence_aggregation', 'level': 1},
                {'agent_id': 'ai_intelligence_agent', 'skill': 'pattern_recognition', 'level': 1},
                {'agent_id': 'learning_agent', 'skill': 'learn_from_data', 'level': 1},
                {'agent_id': 'learning_agent', 'skill': 'ai_follow_user_action', 'level': 1},
                {'agent_id': 'learning_agent', 'skill': 'ai_nice_and_easy', 'level': 1},
            ]
        else:
            # Balanced path — content, analytics, learning, reporter (broadcast + knowledge-sharing ingredients); 10 skills
            assigned_skills['skill_path'] = 'balanced'
            assigned_skills['assigned_agents'] = [
                'content_generator_agent', 'analytics_agent', 'learning_agent', 'reporter_agent',
            ]
            assigned_skills['skills'] = [
                {'agent_id': 'content_generator_agent', 'skill': 'generate_video', 'level': 1},
                {'agent_id': 'content_generator_agent', 'skill': 'ai_assist_task', 'level': 1},
                {'agent_id': 'analytics_agent', 'skill': 'track_metrics', 'level': 1},
                {'agent_id': 'analytics_agent', 'skill': 'analyze_user_behavior', 'level': 1},
                {'agent_id': 'analytics_agent', 'skill': 'ai_suggest_next', 'level': 1},
                {'agent_id': 'learning_agent', 'skill': 'ai_follow_user_action', 'level': 1},
                {'agent_id': 'learning_agent', 'skill': 'ai_win_with_user', 'level': 1},
                {'agent_id': 'learning_agent', 'skill': 'ai_nice_and_easy', 'level': 1},
                {'agent_id': 'reporter_agent', 'skill': 'broadcast', 'level': 1},
                {'agent_id': 'reporter_agent', 'skill': 'news_report_ingredients', 'level': 1},
            ]
        
        # Save assigned skills
        self.save_user_skills(user_id, assigned_skills)
        
        # Add to agent skillset system if available
        if self.agent_skillset:
            for skill_data in assigned_skills['skills']:
                agent_id = skill_data['agent_id']
                skill_name = skill_data['skill']
                # Add user as test_player in skillset system
                player_id = f"user_{user_id}"
                self.agent_skillset.add_skill(player_id, skill_name, agent_type='test_players')
        
        return assigned_skills
    
    def get_user_skills(self, user_id: str) -> Dict:
        """Get all skills for a user. Seeds assigned agents for new users (balanced path) when none exist."""
        file_path = os.path.join(self.data_dir, f"{user_id}.json")
        
        if os.path.exists(file_path):
            try:
                with open(file_path, 'r') as f:
                    return json.load(f)
            except Exception:
                pass
        
        # New user: seed assigned agents (balanced path) so agent_db_service has agents to work with
        try:
            return self.assign_initial_skills(user_id, {})
        except Exception:
            pass
        return {
            'user_id': user_id,
            'assigned_agents': [],
            'skills': [],
            'skill_path': 'balanced'
        }
    
    def save_user_skills(self, user_id: str, skills_data: Dict) -> bool:
        """Save user skills to file"""
        try:
            file_path = os.path.join(self.data_dir, f"{user_id}.json")
            skills_data['updated_at'] = datetime.now().isoformat()
            
            with open(file_path, 'w') as f:
                json.dump(skills_data, f, indent=2)
            
            return True
        except Exception as e:
            print(f"Error saving user skills: {e}")
            return False
    
    def add_skill(self, user_id: str, agent_id: str, skill_name: str, level: int = 1) -> bool:
        """Add a skill to user"""
        skills_data = self.get_user_skills(user_id)
        
        # Check if skill already exists
        existing_skill = None
        for skill in skills_data.get('skills', []):
            if skill.get('agent_id') == agent_id and skill.get('skill') == skill_name:
                existing_skill = skill
                break
        
        if existing_skill:
            # Update level if higher
            if level > existing_skill.get('level', 1):
                existing_skill['level'] = level
        else:
            # Add new skill
            skills_data.setdefault('skills', []).append({
                'agent_id': agent_id,
                'skill': skill_name,
                'level': level,
                'unlocked_at': datetime.now().isoformat()
            })
        
        # Update assigned agents list
        if agent_id not in skills_data.get('assigned_agents', []):
            skills_data.setdefault('assigned_agents', []).append(agent_id)
        
        return self.save_user_skills(user_id, skills_data)
    
    def level_up_skill(self, user_id: str, skill_name: str, experience: int = 100) -> Dict:
        """Level up a skill with experience"""
        skills_data = self.get_user_skills(user_id)
        
        # Find skill
        skill_found = False
        for skill in skills_data.get('skills', []):
            if skill.get('skill') == skill_name:
                skill_found = True
                current_level = skill.get('level', 1)
                current_xp = skill.get('experience', 0) + experience
                
                # Calculate new level (100 XP per level)
                new_level = min((current_xp // 100) + 1, 10)  # Max level 10
                
                skill['experience'] = current_xp
                skill['level'] = new_level
                skill['last_used_at'] = datetime.now().isoformat()
                skill['usage_count'] = skill.get('usage_count', 0) + 1
                
                leveled_up = new_level > current_level
                
                self.save_user_skills(user_id, skills_data)
                
                return {
                    'success': True,
                    'skill': skill_name,
                    'old_level': current_level,
                    'new_level': new_level,
                    'experience': current_xp,
                    'leveled_up': leveled_up
                }
        
        if not skill_found:
            return {
                'success': False,
                'error': f'Skill {skill_name} not found for user {user_id}'
            }
    
    def get_skill_stats(self, user_id: str) -> Dict:
        """Get skill statistics for a user"""
        skills_data = self.get_user_skills(user_id)
        
        stats = {
            'user_id': user_id,
            'total_skills': len(skills_data.get('skills', [])),
            'total_agents': len(skills_data.get('assigned_agents', [])),
            'skill_path': skills_data.get('skill_path', 'balanced'),
            'skills_by_level': {},
            'skills_by_agent': {},
            'total_experience': 0,
            'average_level': 0
        }
        
        total_level = 0
        for skill in skills_data.get('skills', []):
            level = skill.get('level', 1)
            agent_id = skill.get('agent_id', 'unknown')
            experience = skill.get('experience', 0)
            
            stats['skills_by_level'][level] = stats['skills_by_level'].get(level, 0) + 1
            stats['skills_by_agent'][agent_id] = stats['skills_by_agent'].get(agent_id, 0) + 1
            stats['total_experience'] += experience
            total_level += level
        
        if stats['total_skills'] > 0:
            stats['average_level'] = round(total_level / stats['total_skills'], 2)
        
        return stats
    
    def recommend_skills(self, user_id: str, user_behavior: Dict) -> List[Dict]:
        """Recommend skills based on user behavior"""
        recommendations = []
        
        # Analyze behavior to recommend skills
        if user_behavior.get('content_created', 0) > 5:
            recommendations.append({
                'agent_id': 'content_generator_agent',
                'skill': 'optimize_content',
                'reason': 'You create a lot of content'
            })
        
        if user_behavior.get('battle_participations', 0) > 3:
            recommendations.append({
                'agent_id': 'battle_strategy_agent',
                'skill': 'predict_outcome',
                'reason': 'You participate in battles frequently'
            })
        
        if user_behavior.get('social_interactions', 0) > 10:
            recommendations.append({
                'agent_id': 'social_engagement_agent',
                'skill': 'facilitate_discussions',
                'reason': 'You are very social'
            })
        
        return recommendations

    def grant_full_agent_access(
        self,
        user_id: str,
        include_unique_skills: bool = True,
        include_battle_skills: bool = True,
    ) -> Dict:
        """
        Grant full access to all agent skills for a user.
        This is used for premium/full onboarding flows.
        """
        if not self.agent_skillset:
            return {'success': False, 'error': 'agent_skillset_unavailable'}

        all_skillsets = self.agent_skillset.get_all_skillsets()
        agents = (all_skillsets or {}).get('agents', {}) or {}
        skills_data = self.get_user_skills(user_id)

        existing_pairs = {
            (s.get('agent_id'), s.get('skill'))
            for s in skills_data.get('skills', [])
            if isinstance(s, dict)
        }
        assigned_agents = set(skills_data.get('assigned_agents', []))
        added = 0

        for agent_id, agent_data in agents.items():
            assigned_agents.add(agent_id)
            base_skills = list(agent_data.get('skills', []) or [])
            unique_profiles = list(agent_data.get('unique_skill_profiles', []) or [])
            battle_profiles = list(agent_data.get('battle_skill_profiles', []) or [])

            # Keep baseline skills unless explicitly filtered by flags.
            selected_skills = []
            for skill_name in base_skills:
                is_unique = '_unique_' in str(skill_name)
                is_battle = '_battle_' in str(skill_name)
                if is_unique and not include_unique_skills:
                    continue
                if is_battle and not include_battle_skills:
                    continue
                selected_skills.append(skill_name)

            # Ensure profile-defined skills are included.
            if include_unique_skills:
                selected_skills.extend([p.get('skill_name') for p in unique_profiles if p.get('skill_name')])
            if include_battle_skills:
                selected_skills.extend([p.get('skill_name') for p in battle_profiles if p.get('skill_name')])

            for skill_name in selected_skills:
                key = (agent_id, skill_name)
                if not skill_name or key in existing_pairs:
                    continue
                skills_data.setdefault('skills', []).append({
                    'agent_id': agent_id,
                    'skill': skill_name,
                    'level': 1,
                    'unlocked_at': datetime.now().isoformat(),
                })
                existing_pairs.add(key)
                added += 1

        skills_data['assigned_agents'] = sorted(list(assigned_agents))
        skills_data['skill_path'] = 'full_system'
        self.save_user_skills(user_id, skills_data)

        return {
            'success': True,
            'user_id': user_id,
            'skills_added': added,
            'total_skills': len(skills_data.get('skills', [])),
            'total_agents': len(skills_data.get('assigned_agents', [])),
            'mode': 'full_agent_access',
        }

    def maintenance_inactive_user_skills(
        self,
        max_batch: int = 10,
        inactive_days: Optional[int] = None,
        dry_run: bool = False,
    ) -> Dict[str, Any]:
        """
        Reevaluate per-user skills files: if both file age and agent activity are older than
        USER_SKILLS_INACTIVE_DAYS (default 120), remove the JSON so the next get_user_skills()
        can re-seed (balanced path). Processes at most max_batch files per run (default 10).
        """
        days = inactive_days
        if days is None:
            try:
                days = int(os.environ.get('USER_SKILLS_INACTIVE_DAYS', '120'))
            except ValueError:
                days = 120
        threshold = datetime.now(timezone.utc) - timedelta(days=days)
        removed: List[str] = []
        skipped: List[str] = []

        try:
            from backend.services.agent_db_service import agent_db_service
        except Exception:
            agent_db_service = None  # type: ignore

        def _parse_iso(s: Optional[str]) -> Optional[datetime]:
            if not s:
                return None
            try:
                raw = str(s).strip().replace(' ', 'T', 1)
                if raw.endswith('Z'):
                    raw = raw[:-1] + '+00:00'
                dt = datetime.fromisoformat(raw)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                return dt
            except Exception:
                return None

        try:
            names = sorted(
                f for f in os.listdir(self.data_dir) if f.endswith('.json')
            )
        except Exception:
            return {'success': False, 'error': 'cannot_list_data_dir', 'removed': [], 'skipped': []}

        for fname in names:
            if len(removed) >= max_batch:
                break
            user_id = fname[:-5]
            path = os.path.join(self.data_dir, fname)
            try:
                mtime = datetime.fromtimestamp(os.path.getmtime(path), tz=timezone.utc)
            except Exception:
                mtime = threshold

            data: Dict = {}
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
            except Exception:
                skipped.append(user_id)
                continue

            updated_at = _parse_iso(data.get('updated_at'))
            last_skill_use: Optional[datetime] = None
            for sk in data.get('skills') or []:
                if isinstance(sk, dict) and sk.get('last_used_at'):
                    t = _parse_iso(sk.get('last_used_at'))
                    if t and (last_skill_use is None or t > last_skill_use):
                        last_skill_use = t

            last_activity = None
            if agent_db_service:
                try:
                    last_activity = agent_db_service.get_user_last_activity_at(user_id)
                    if last_activity and last_activity.tzinfo is None:
                        last_activity = last_activity.replace(tzinfo=timezone.utc)
                except Exception:
                    pass

            ref_times = [t for t in (updated_at, last_skill_use, mtime, last_activity) if t is not None]
            newest = max(ref_times) if ref_times else mtime

            if newest >= threshold:
                skipped.append(user_id)
                continue

            if dry_run:
                removed.append(user_id + ' (dry_run)')
                continue
            try:
                os.remove(path)
                removed.append(user_id)
            except Exception:
                skipped.append(user_id)

        return {
            'success': True,
            'inactive_days': days,
            'threshold_utc': threshold.isoformat(),
            'dry_run': dry_run,
            'removed': removed,
            'skipped_count': len(skipped),
        }

# Global instance
user_agent_skills = UserAgentSkills()
