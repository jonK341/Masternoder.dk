"""
Agent System - Life-like agents that copy user behaviors
Top100/Top50/Top25/Top10 generators, calendar, GPS, levels
"""
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import json
import os
import uuid
import random

class AgentSystem:
    """
    Comprehensive Agent System - ENHANCED
    - Top100/Top50/Top25/Top10 generators
    - Giga Calendar (10 levels)
    - Behavior copying
    - Enhanced 3 level systems with progressive XP
    - GPS navigation
    - Video generation integration
    - Unified point system integration
    - Progressive learning with visual memory
    - Special trophies and skill sets
    - Advanced leveling mechanisms
    """
    
    def __init__(self):
        self.data_dir = 'data/agents'
        os.makedirs(self.data_dir, exist_ok=True)
        
        # Enhanced Level system configurations with progressive scaling
        self.level_systems = {
            'system_1': {  # Experience Level
                'name': 'Experience',
                'max_level': 200,  # Increased from 100
                'xp_per_level_base': 1000,
                'xp_scaling_factor': 1.15,  # 15% increase per level
                'special_abilities': ['xp_boost', 'point_multiplier', 'learning_acceleration']
            },
            'system_2': {  # Skill Level
                'name': 'Skills',
                'max_level': 100,  # Increased from 50
                'xp_per_level_base': 500,
                'xp_scaling_factor': 1.12,  # 12% increase per level
                'special_abilities': ['skill_mastery', 'rapid_learning', 'expertise_bonus']
            },
            'system_3': {  # Mission Level
                'name': 'Missions',
                'max_level': 50,  # Increased from 25
                'xp_per_level_base': 2000,
                'xp_scaling_factor': 1.18,  # 18% increase per level
                'special_abilities': ['mission_optimization', 'reward_boost', 'mission_chaining']
            }
        }
        
        # Special Trophies System
        self.special_trophies = {
            'first_agent': {'name': 'First Agent', 'rarity': 'common', 'points': 100},
            'level_10': {'name': 'Level 10 Master', 'rarity': 'uncommon', 'points': 500},
            'level_25': {'name': 'Level 25 Expert', 'rarity': 'rare', 'points': 1000},
            'level_50': {'name': 'Level 50 Legend', 'rarity': 'epic', 'points': 2500},
            'level_100': {'name': 'Level 100 Mythic', 'rarity': 'legendary', 'points': 5000},
            'skill_master': {'name': 'Skill Master', 'rarity': 'epic', 'points': 2000},
            'mission_completer': {'name': 'Mission Completer', 'rarity': 'rare', 'points': 1500},
            'calendar_guru': {'name': 'Calendar Guru', 'rarity': 'epic', 'points': 3000},
            'point_collector': {'name': 'Point Collector', 'rarity': 'legendary', 'points': 5000},
            'behavior_mirror': {'name': 'Behavior Mirror', 'rarity': 'rare', 'points': 1200}
        }
        
        # Visual Memory System for Progressive Learning
        self.visual_memory_config = {
            'memory_capacity': 1000,  # Max visual memories stored
            'memory_decay_rate': 0.01,  # 1% decay per day
            'learning_rate': 0.1,  # 10% learning from each visual memory
            'points_per_memory': 10,  # Points earned per visual memory saved
            'memory_types': ['video', 'battle', 'social', 'achievement', 'skill', 'mission'],
            'memory_categories': {
                'video': {'strength_base': 0.8, 'decay_rate': 0.01},
                'battle': {'strength_base': 0.9, 'decay_rate': 0.015},
                'social': {'strength_base': 0.7, 'decay_rate': 0.008},
                'achievement': {'strength_base': 1.0, 'decay_rate': 0.005},
                'skill': {'strength_base': 0.85, 'decay_rate': 0.01},
                'mission': {'strength_base': 0.75, 'decay_rate': 0.012}
            }
        }
        
        # Calendar levels (1-10)
        self.calendar_levels = {
            1: {'name': 'Basic', 'events_per_day': 5, 'features': ['tasks', 'reminders']},
            2: {'name': 'Enhanced', 'events_per_day': 10, 'features': ['tasks', 'reminders', 'skills']},
            3: {'name': 'Advanced', 'events_per_day': 15, 'features': ['tasks', 'reminders', 'skills', 'missions']},
            4: {'name': 'Professional', 'events_per_day': 20, 'features': ['all', 'recurring']},
            5: {'name': 'Expert', 'events_per_day': 30, 'features': ['all', 'recurring', 'analytics']},
            6: {'name': 'Master', 'events_per_day': 40, 'features': ['all', 'recurring', 'analytics', 'predictions']},
            7: {'name': 'Elite', 'events_per_day': 50, 'features': ['all', 'recurring', 'analytics', 'predictions', 'ai_suggestions']},
            8: {'name': 'Legendary', 'events_per_day': 75, 'features': ['all', 'recurring', 'analytics', 'predictions', 'ai_suggestions', 'auto_optimization']},
            9: {'name': 'Mythic', 'events_per_day': 100, 'features': ['all', 'recurring', 'analytics', 'predictions', 'ai_suggestions', 'auto_optimization', 'time_travel']},
            10: {'name': 'Giga', 'events_per_day': 200, 'features': ['all', 'recurring', 'analytics', 'predictions', 'ai_suggestions', 'auto_optimization', 'time_travel', 'quantum_scheduling']}
        }
    
    def create_agent(self, user_id: str, agent_name: str, agent_type: str = 'personal_assistant') -> Dict[str, Any]:
        """Create a new agent"""
        agent_id = str(uuid.uuid4())
        
        agent_data = {
            'id': agent_id,
            'user_id': user_id,
            'agent_name': agent_name,
            'agent_type': agent_type,
            'level_system_1': 1,
            'level_system_2': 1,
            'level_system_3': 1,
            'xp_system_1': 0,
            'xp_system_2': 0,
            'xp_system_3': 0,
            'calendar_level': 1,
            'created_at': datetime.utcnow().isoformat(),
            'last_active': datetime.utcnow().isoformat(),
            'behavior_pattern': {},
            'personality_traits': self._generate_personality(),
            'current_location': None,
            'navigation_enabled': True,
            'top100_tasks': [],
            'top50_skills': [],
            'top25_missions': [],
            'top10_achievements': [],
            'unified_points': {},
            'effects': {},
            'active_effects': [],
            'special_trophies': [],
            'visual_memory': [],
            'learning_progress': {
                'total_learned': 0,
                'learning_rate': 0.1,
                'memory_efficiency': 0.5,
                'points_from_learning': 0
            },
            'skill_sets': {
                'active_skills': [],
                'mastered_skills': [],
                'skill_points': 0,
                'skill_tree_progress': {}
            }
        }
        
        # Save to file
        agent_file = os.path.join(self.data_dir, f'{agent_id}.json')
        with open(agent_file, 'w') as f:
            json.dump(agent_data, f, indent=2)
        
        # Generate initial lists
        agent_data['top100_tasks'] = self.generate_top100_tasks(agent_id, user_id)
        agent_data['top50_skills'] = self.generate_top50_skills(agent_id, user_id)
        agent_data['top25_missions'] = self.generate_top25_missions(agent_id, user_id)
        agent_data['top10_achievements'] = self.generate_top10_achievements(agent_id, user_id)
        
        # Update file with generated lists
        with open(agent_file, 'w') as f:
            json.dump(agent_data, f, indent=2)
        
        return agent_data
    
    def generate_top100_tasks(self, agent_id: str, user_id: str) -> List[Dict[str, Any]]:
        """Generate Top 100 task list"""
        tasks = []
        
        # Get user's unified points to generate relevant tasks
        try:
            from backend.services.unified_point_counter import unified_point_counter
            user_points = unified_point_counter.get_all_points(user_id)
        except:
            user_points = {}
        
        # Generate tasks based on user activity
        task_categories = [
            'video_generation', 'battle', 'social', 'achievements',
            'skills_development', 'missions', 'exploration', 'creation',
            'optimization', 'learning', 'collaboration', 'innovation'
        ]
        
        for i in range(100):
            category = random.choice(task_categories)
            priority = 100 - i  # Top tasks have higher priority
            
            task = {
                'id': str(uuid.uuid4()),
                'rank': i + 1,
                'name': f"{category.replace('_', ' ').title()} Task {i+1}",
                'description': f"Complete {category} related activity",
                'category': category,
                'priority': priority,
                'status': 'pending',
                'points_reward': priority * 10,
                'estimated_time': random.randint(5, 120),  # minutes
                'created_at': datetime.utcnow().isoformat()
            }
            tasks.append(task)
        
        return tasks
    
    def generate_top50_skills(self, agent_id: str, user_id: str) -> List[Dict[str, Any]]:
        """Generate Top 50 skills list with enhanced skill sets"""
        skills = []
        
        # Enhanced skill categories with specializations
        skill_categories = [
            {'name': 'video_editing', 'tier': 'basic', 'specializations': ['cutting', 'effects', 'color_grading']},
            {'name': 'ai_prompting', 'tier': 'advanced', 'specializations': ['prompt_engineering', 'style_transfer', 'content_generation']},
            {'name': 'content_creation', 'tier': 'basic', 'specializations': ['writing', 'design', 'storytelling']},
            {'name': 'battle_strategy', 'tier': 'expert', 'specializations': ['tactics', 'positioning', 'resource_management']},
            {'name': 'social_networking', 'tier': 'intermediate', 'specializations': ['engagement', 'community_building', 'viral_marketing']},
            {'name': 'point_optimization', 'tier': 'advanced', 'specializations': ['efficiency', 'multiplier_stacking', 'bonus_optimization']},
            {'name': 'time_management', 'tier': 'basic', 'specializations': ['scheduling', 'prioritization', 'productivity']},
            {'name': 'creative_thinking', 'tier': 'intermediate', 'specializations': ['ideation', 'innovation', 'problem_solving']},
            {'name': 'problem_solving', 'tier': 'advanced', 'specializations': ['analysis', 'debugging', 'optimization']},
            {'name': 'collaboration', 'tier': 'intermediate', 'specializations': ['teamwork', 'communication', 'coordination']},
            {'name': 'analytics', 'tier': 'expert', 'specializations': ['data_analysis', 'predictive_modeling', 'insights']},
            {'name': 'automation', 'tier': 'advanced', 'specializations': ['scripting', 'workflow', 'ai_integration']}
        ]
        
        for i in range(50):
            category_data = random.choice(skill_categories)
            category = category_data['name']
            tier = category_data['tier']
            specialization = random.choice(category_data['specializations'])
            
            # Calculate XP requirements based on tier
            tier_multipliers = {'basic': 1.0, 'intermediate': 1.5, 'advanced': 2.0, 'expert': 3.0}
            base_xp = 100 * tier_multipliers.get(tier, 1.0)
            
            skill = {
                'id': str(uuid.uuid4()),
                'rank': i + 1,
                'name': f"{category.replace('_', ' ').title()} - {specialization.replace('_', ' ').title()}",
                'description': f"Master {specialization} in {category}",
                'category': category,
                'tier': tier,
                'specialization': specialization,
                'level': 1,
                'max_level': 20,  # Increased from 10
                'current_xp': 0,
                'xp_to_next': int(base_xp),
                'points_value': (50 - i) * 25,  # Increased base value
                'learned': False,
                'mastery_bonus': tier_multipliers.get(tier, 1.0),
                'unlocks_at_level': {
                    5: f"Unlock {specialization} bonus",
                    10: f"Master {specialization} techniques",
                    15: f"Expert {specialization} mastery",
                    20: f"Legendary {specialization} status"
                },
                'created_at': datetime.utcnow().isoformat()
            }
            skills.append(skill)
        
        return skills
    
    def generate_top25_missions(self, agent_id: str, user_id: str) -> List[Dict[str, Any]]:
        """Generate Top 25 missions list"""
        missions = []
        
        mission_types = [
            'daily_challenge', 'weekly_quest', 'monthly_goal', 'special_event',
            'achievement_hunt', 'skill_mastery', 'point_collection', 'exploration',
            'creation_project', 'collaboration_task', 'innovation_challenge', 'optimization_mission'
        ]
        
        for i in range(25):
            mission_type = random.choice(mission_types)
            
            mission = {
                'id': str(uuid.uuid4()),
                'rank': i + 1,
                'name': f"{mission_type.replace('_', ' ').title()} Mission",
                'description': f"Complete {mission_type} objectives",
                'type': mission_type,
                'status': 'active',
                'requirements': {
                    'tasks_completed': random.randint(1, 10),
                    'points_earned': random.randint(100, 1000),
                    'skills_learned': random.randint(1, 5)
                },
                'reward': (25 - i) * 100,
                'progress': 0,
                'created_at': datetime.utcnow().isoformat()
            }
            missions.append(mission)
        
        return missions
    
    def generate_top10_achievements(self, agent_id: str, user_id: str) -> List[Dict[str, Any]]:
        """Generate Top 10 achievements list"""
        achievements = []
        
        achievement_types = [
            'first_video', 'master_creator', 'battle_champion', 'social_legend',
            'point_millionaire', 'skill_master', 'mission_completer', 'calendar_guru',
            'agent_evolution', 'system_dominator'
        ]
        
        for i in range(10):
            achievement_type = achievement_types[i] if i < len(achievement_types) else f'achievement_{i+1}'
            
            achievement = {
                'id': str(uuid.uuid4()),
                'rank': i + 1,
                'name': achievement_type.replace('_', ' ').title(),
                'description': f"Achieve {achievement_type} status",
                'type': achievement_type,
                'unlocked': False,
                'points_reward': (10 - i) * 500,
                'rarity': 'legendary' if i < 3 else 'epic' if i < 6 else 'rare',
                'created_at': datetime.utcnow().isoformat()
            }
            achievements.append(achievement)
        
        return achievements
    
    def copy_user_behavior(self, agent_id: str, user_id: str) -> Dict[str, Any]:
        """Copy user behaviors to agent"""
        try:
            from backend.services.unified_point_counter import unified_point_counter
            user_points = unified_point_counter.get_all_points(user_id)
            
            # Analyze user behavior patterns
            behavior_pattern = {
                'most_active_time': self._analyze_activity_time(user_id),
                'preferred_categories': self._analyze_preferred_categories(user_points),
                'point_generation_rate': self._calculate_point_rate(user_points),
                'video_generation_frequency': user_points.get('videos_created', 0),
                'battle_participation': user_points.get('battle_wins', 0),
                'social_activity': user_points.get('social_interactions', 0),
                'learning_pattern': self._analyze_learning_pattern(user_points),
                'last_synced': datetime.utcnow().isoformat()
            }
            
            # Update agent
            agent_file = os.path.join(self.data_dir, f'{agent_id}.json')
            if os.path.exists(agent_file):
                with open(agent_file, 'r') as f:
                    agent_data = json.load(f)
                
                agent_data['behavior_pattern'] = behavior_pattern
                agent_data['last_behavior_sync'] = datetime.utcnow().isoformat()
                
                with open(agent_file, 'w') as f:
                    json.dump(agent_data, f, indent=2)
            
            return behavior_pattern
        except Exception as e:
            return {'error': str(e)}
    
    def get_giga_calendar(self, agent_id: str, start_date: datetime = None, days: int = 30) -> Dict[str, Any]:
        """Get giga calendar for agent (10 levels)"""
        if start_date is None:
            start_date = datetime.utcnow()
        
        agent_file = os.path.join(self.data_dir, f'{agent_id}.json')
        if not os.path.exists(agent_file):
            return {'error': 'Agent not found'}
        
        with open(agent_file, 'r') as f:
            agent_data = json.load(f)
        
        calendar_level = agent_data.get('calendar_level', 1)
        level_config = self.calendar_levels.get(calendar_level, self.calendar_levels[1])
        
        calendar = {
            'agent_id': agent_id,
            'calendar_level': calendar_level,
            'level_name': level_config['name'],
            'events_per_day': level_config['events_per_day'],
            'features': level_config['features'],
            'start_date': start_date.isoformat(),
            'days': days,
            'events': []
        }
        
        # Generate events for each day
        for day_offset in range(days):
            event_date = start_date + timedelta(days=day_offset)
            events_for_day = self._generate_calendar_events(agent_id, event_date, level_config['events_per_day'])
            calendar['events'].extend(events_for_day)
        
        return calendar
    
    def _generate_calendar_events(self, agent_id: str, date: datetime, count: int) -> List[Dict[str, Any]]:
        """Generate calendar events for a day"""
        events = []
        event_types = ['task', 'skill', 'mission', 'meeting', 'reminder', 'deadline']
        
        for i in range(count):
            event_type = random.choice(event_types)
            hour = random.randint(8, 20)
            minute = random.choice([0, 15, 30, 45])
            event_time = date.replace(hour=hour, minute=minute, second=0, microsecond=0)
            
            event = {
                'id': str(uuid.uuid4()),
                'type': event_type,
                'name': f"{event_type.title()} Event {i+1}",
                'description': f"Agent {event_type} activity",
                'date': event_time.isoformat(),
                'duration': random.randint(15, 120),  # minutes
                'location': self._generate_location(),
                'priority': random.randint(1, 5),
                'level': random.randint(1, 10)
            }
            events.append(event)
        
        return sorted(events, key=lambda x: x['date'])
    
    def _generate_location(self) -> str:
        """Generate GPS location"""
        # Simulate GPS coordinates
        lat = round(random.uniform(-90, 90), 6)
        lon = round(random.uniform(-180, 180), 6)
        return f"{lat},{lon}"
    
    def _generate_personality(self) -> Dict[str, Any]:
        """Generate agent personality traits"""
        return {
            'creativity': random.uniform(0, 1),
            'efficiency': random.uniform(0, 1),
            'social': random.uniform(0, 1),
            'analytical': random.uniform(0, 1),
            'adventurous': random.uniform(0, 1),
            'organized': random.uniform(0, 1)
        }
    
    def _analyze_activity_time(self, user_id: str) -> str:
        """Analyze when user is most active"""
        # Placeholder - would analyze actual user activity
        return random.choice(['morning', 'afternoon', 'evening', 'night'])
    
    def _analyze_preferred_categories(self, user_points: Dict[str, Any]) -> List[str]:
        """Analyze user's preferred categories"""
        categories = []
        if user_points.get('videos_created', 0) > 0:
            categories.append('video_generation')
        if user_points.get('battle_wins', 0) > 0:
            categories.append('battle')
        if user_points.get('social_interactions', 0) > 0:
            categories.append('social')
        return categories if categories else ['general']
    
    def _calculate_point_rate(self, user_points: Dict[str, Any]) -> float:
        """Calculate user's point generation rate"""
        total_points = sum([
            user_points.get('xp_total', 0),
            user_points.get('battle_points', 0),
            user_points.get('activity_points', 0)
        ])
        return total_points / 1000.0  # Normalized rate
    
    def _analyze_learning_pattern(self, user_points: Dict[str, Any]) -> str:
        """Analyze user's learning pattern"""
        if user_points.get('knowledge_points', 0) > 100:
            return 'fast_learner'
        elif user_points.get('knowledge_points', 0) > 50:
            return 'moderate_learner'
        return 'steady_learner'
    
    def get_agent(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """Get agent data"""
        agent_file = os.path.join(self.data_dir, f'{agent_id}.json')
        if os.path.exists(agent_file):
            with open(agent_file, 'r') as f:
                return json.load(f)
        return None
    
    def get_user_agents(self, user_id: str) -> List[Dict[str, Any]]:
        """Get all agents for a user"""
        agents = []
        for filename in os.listdir(self.data_dir):
            if filename.endswith('.json'):
                agent_file = os.path.join(self.data_dir, filename)
                with open(agent_file, 'r') as f:
                    agent_data = json.load(f)
                    if agent_data.get('user_id') == user_id:
                        agents.append(agent_data)
        return agents


    def generate_video_opinion(self, agent_id: str, video_id: str, video_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate agent opinion on video generation"""
        agent = self.get_agent(agent_id)
        if not agent:
            return {'error': 'Agent not found'}
        
        # Analyze video data
        quality_score = video_data.get('quality_score', 0.5)
        duration = video_data.get('duration', 0)
        title = video_data.get('title', 'Untitled')
        
        # Generate opinion based on agent personality
        personality = agent.get('personality_traits', {})
        creativity = personality.get('creativity', 0.5)
        analytical = personality.get('analytical', 0.5)
        
        opinion_score = (quality_score * 0.6) + (creativity * 0.2) + (analytical * 0.2)
        
        suggestions = []
        if quality_score < 0.7:
            suggestions.append("Consider improving video quality with better prompts")
        if duration < 30:
            suggestions.append("Try generating longer videos for better engagement")
        if not title or title == 'Untitled':
            suggestions.append("Add a descriptive title to improve discoverability")
        
        opinion = {
            'agent_id': agent_id,
            'video_id': video_id,
            'opinion_score': round(opinion_score, 2),
            'quality_rating': 'excellent' if opinion_score >= 0.8 else 'good' if opinion_score >= 0.6 else 'needs_improvement',
            'opinion_text': f"Agent {agent.get('agent_name', 'Agent')} rates this video {opinion_score:.0%}",
            'suggestions': suggestions,
            'strengths': ['Good content structure'] if quality_score > 0.6 else [],
            'improvements': suggestions,
            'created_at': datetime.utcnow().isoformat()
        }
        
        # Save opinion
        agent_file = os.path.join(self.data_dir, f'{agent_id}.json')
        if os.path.exists(agent_file):
            with open(agent_file, 'r') as f:
                agent_data = json.load(f)
            
            if 'video_opinions' not in agent_data:
                agent_data['video_opinions'] = []
            agent_data['video_opinions'].append(opinion)
            agent_data['video_generation_count'] = agent_data.get('video_generation_count', 0) + 1
            
            with open(agent_file, 'w') as f:
                json.dump(agent_data, f, indent=2)
        
        return opinion
    
    def update_gps_location(self, agent_id: str, location: str) -> Dict[str, Any]:
        """Update agent GPS location"""
        agent_file = os.path.join(self.data_dir, f'{agent_id}.json')
        if not os.path.exists(agent_file):
            return {'error': 'Agent not found'}
        
        with open(agent_file, 'r') as f:
            agent_data = json.load(f)
        
        # Update location
        agent_data['current_location'] = location
        
        # Add to location history
        if 'location_history' not in agent_data:
            agent_data['location_history'] = []
        
        agent_data['location_history'].append({
            'location': location,
            'timestamp': datetime.utcnow().isoformat()
        })
        
        # Keep only last 100 locations
        if len(agent_data['location_history']) > 100:
            agent_data['location_history'] = agent_data['location_history'][-100:]
        
        with open(agent_file, 'w') as f:
            json.dump(agent_data, f, indent=2)
        
        return {
            'success': True,
            'location': location,
            'timestamp': datetime.utcnow().isoformat()
        }
    
    def coordinate_with_service_worker(self, agent_id: str, video_id: str, production_data: Dict[str, Any]) -> Dict[str, Any]:
        """Coordinate agent with service worker for production"""
        agent = self.get_agent(agent_id)
        if not agent:
            return {'error': 'Agent not found'}
        
        coordination = {
            'agent_id': agent_id,
            'video_id': video_id,
            'agent_name': agent.get('agent_name'),
            'coordination_status': 'active',
            'production_stage': production_data.get('stage', 'unknown'),
            'agent_opinion': self.generate_video_opinion(agent_id, video_id, production_data),
            'service_worker_tasks': [
                'cache_video',
                'update_progress',
                'notify_completion'
            ],
            'coordinated_at': datetime.utcnow().isoformat()
        }
        
        # Save coordination data
        agent_file = os.path.join(self.data_dir, f'{agent_id}.json')
        if os.path.exists(agent_file):
            with open(agent_file, 'r') as f:
                agent_data = json.load(f)
            
            if 'service_worker_coordination' not in agent_data:
                agent_data['service_worker_coordination'] = []
            agent_data['service_worker_coordination'].append(coordination)
            
            with open(agent_file, 'w') as f:
                json.dump(agent_data, f, indent=2)
        
        return coordination
    
    def award_xp(self, agent_id: str, system: str, xp_amount: int) -> Dict[str, Any]:
        """Award XP to agent in specified system and check for level up"""
        agent = self.get_agent(agent_id)
        if not agent:
            return {'error': 'Agent not found'}
        
        system_key = f'level_{system}'
        xp_key = f'xp_{system}'
        
        current_level = agent.get(system_key, 1)
        current_xp = agent.get(xp_key, 0)
        level_config = self.level_systems.get(system, {})
        
        # Calculate XP required for current level
        xp_required = self._calculate_xp_required(current_level, level_config)
        
        # Add XP
        new_xp = current_xp + xp_amount
        new_level = current_level
        leveled_up = False
        
        # Check for level up
        while new_xp >= xp_required and new_level < level_config.get('max_level', 100):
            new_xp -= xp_required
            new_level += 1
            leveled_up = True
            xp_required = self._calculate_xp_required(new_level, level_config)
        
        # Update agent
        agent_file = os.path.join(self.data_dir, f'{agent_id}.json')
        agent[system_key] = new_level
        agent[xp_key] = new_xp
        
        # Check for special trophies
        trophies_earned = []
        if leveled_up:
            trophies_earned = self._check_trophy_unlocks(agent_id, new_level, system)
        
        # Save agent
        with open(agent_file, 'w') as f:
            json.dump(agent, f, indent=2)
        
        # Integrate with unified point system
        try:
            from backend.services.unified_point_counter import unified_point_counter
            unified_point_counter.add_points(
                agent.get('user_id'),
                'agent_xp',
                xp_amount,
                source=f'agent_{agent_id}_{system}',
                metadata={'agent_id': agent_id, 'system': system, 'level': new_level}
            )
        except:
            pass
        
        return {
            'success': True,
            'agent_id': agent_id,
            'system': system,
            'old_level': current_level,
            'new_level': new_level,
            'old_xp': current_xp,
            'new_xp': new_xp,
            'xp_awarded': xp_amount,
            'leveled_up': leveled_up,
            'trophies_earned': trophies_earned
        }
    
    def _calculate_xp_required(self, level: int, level_config: Dict[str, Any]) -> int:
        """Calculate XP required for a level using progressive scaling"""
        base_xp = level_config.get('xp_per_level_base', 1000)
        scaling = level_config.get('xp_scaling_factor', 1.1)
        return int(base_xp * (scaling ** (level - 1)))
    
    def _check_trophy_unlocks(self, agent_id: str, level: int, system: str) -> List[Dict[str, Any]]:
        """Check if agent has unlocked any special trophies"""
        agent = self.get_agent(agent_id)
        if not agent:
            return []
        
        trophies_earned = []
        earned_trophy_ids = [t.get('id') for t in agent.get('special_trophies', [])]
        
        # Check level-based trophies
        level_trophies = {
            10: 'level_10',
            25: 'level_25',
            50: 'level_50',
            100: 'level_100'
        }
        
        if level in level_trophies:
            trophy_id = level_trophies[level]
            if trophy_id not in earned_trophy_ids:
                trophy_data = self.special_trophies.get(trophy_id, {})
                trophy = {
                    'id': trophy_id,
                    'name': trophy_data.get('name', 'Unknown Trophy'),
                    'rarity': trophy_data.get('rarity', 'common'),
                    'points': trophy_data.get('points', 0),
                    'earned_at': datetime.utcnow().isoformat(),
                    'system': system,
                    'level': level
                }
                trophies_earned.append(trophy)
                
                # Add to agent
                if 'special_trophies' not in agent:
                    agent['special_trophies'] = []
                agent['special_trophies'].append(trophy)
                
                # Save agent
                agent_file = os.path.join(self.data_dir, f'{agent_id}.json')
                with open(agent_file, 'w') as f:
                    json.dump(agent, f, indent=2)
        
        return trophies_earned
    
    def save_visual_memory(self, agent_id: str, memory_type: str, memory_data: Dict[str, Any]) -> Dict[str, Any]:
        """Save visual memory for progressive learning with categories and strength"""
        agent = self.get_agent(agent_id)
        if not agent:
            return {'error': 'Agent not found'}
        
        # Get memory category config
        category_config = self.visual_memory_config['memory_categories'].get(
            memory_type,
            {'strength_base': 0.8, 'decay_rate': 0.01}
        )
        
        # Create visual memory entry with category and strength
        visual_memory = {
            'id': str(uuid.uuid4()),
            'type': memory_type,
            'category': memory_type,  # Category same as type for now
            'data': memory_data,
            'timestamp': datetime.utcnow().isoformat(),
            'points_value': self.visual_memory_config['points_per_memory'],
            'learning_value': self.visual_memory_config['learning_rate'],
            'strength': category_config['strength_base'],  # Initial strength
            'decay_rate': category_config['decay_rate'],
            'last_accessed': datetime.utcnow().isoformat(),
            'access_count': 0
        }
        
        # Add to agent's visual memory
        if 'visual_memory' not in agent:
            agent['visual_memory'] = []
        
        agent['visual_memory'].append(visual_memory)
        
        # Limit memory capacity
        max_capacity = self.visual_memory_config['memory_capacity']
        if len(agent['visual_memory']) > max_capacity:
            agent['visual_memory'] = agent['visual_memory'][-max_capacity:]
        
        # Update learning progress
        if 'learning_progress' not in agent:
            agent['learning_progress'] = {
                'total_learned': 0,
                'learning_rate': 0.1,
                'memory_efficiency': 0.5,
                'points_from_learning': 0
            }
        
        agent['learning_progress']['total_learned'] += 1
        agent['learning_progress']['points_from_learning'] += visual_memory['points_value']
        
        # Save agent
        agent_file = os.path.join(self.data_dir, f'{agent_id}.json')
        with open(agent_file, 'w') as f:
            json.dump(agent, f, indent=2)
        
        # Award points through unified system
        try:
            from backend.services.unified_point_counter import unified_point_counter
            unified_point_counter.add_points(
                agent.get('user_id'),
                'visual_memory',
                visual_memory['points_value'],
                source=f'agent_{agent_id}_visual_memory',
                metadata={'memory_type': memory_type, 'memory_id': visual_memory['id']}
            )
        except:
            pass
        
        return {
            'success': True,
            'memory_id': visual_memory['id'],
            'points_awarded': visual_memory['points_value'],
            'total_memories': len(agent['visual_memory']),
            'learning_progress': agent['learning_progress'],
            'memory_strength': visual_memory['strength'],
            'category': visual_memory['category']
        }
    
    def recall_memory(self, agent_id: str, memory_id: str = None, category: str = None) -> Dict[str, Any]:
        """Recall visual memory - access memories by ID or category"""
        agent = self.get_agent(agent_id)
        if not agent:
            return {'error': 'Agent not found'}
        
        visual_memories = agent.get('visual_memory', [])
        if not visual_memories:
            return {'error': 'No visual memories available'}
        
        # Filter memories
        if memory_id:
            memories = [m for m in visual_memories if m.get('id') == memory_id]
        elif category:
            memories = [m for m in visual_memories if m.get('category') == category]
        else:
            # Return most recent memories
            memories = visual_memories[-10:]
        
        if not memories:
            return {'error': 'No memories found matching criteria'}
        
        # Update memory access
        now = datetime.utcnow()
        for memory in memories:
            memory['last_accessed'] = now.isoformat()
            memory['access_count'] = memory.get('access_count', 0) + 1
            
            # Strengthen memory on access (spaced repetition)
            current_strength = memory.get('strength', 0.8)
            memory['strength'] = min(1.0, current_strength + 0.05)
        
        # Save agent
        agent_file = os.path.join(self.data_dir, f'{agent_id}.json')
        with open(agent_file, 'w') as f:
            json.dump(agent, f, indent=2)
        
        return {
            'success': True,
            'memories': memories,
            'total_recalled': len(memories),
            'average_strength': sum(m.get('strength', 0.8) for m in memories) / len(memories)
        }
    
    def apply_memory_decay(self, agent_id: str) -> Dict[str, Any]:
        """Apply memory decay to agent's visual memories"""
        agent = self.get_agent(agent_id)
        if not agent:
            return {'error': 'Agent not found'}
        
        visual_memories = agent.get('visual_memory', [])
        if not visual_memories:
            return {'success': True, 'memories_decayed': 0}
        
        now = datetime.utcnow()
        decayed_count = 0
        
        for memory in visual_memories:
            last_accessed = datetime.fromisoformat(memory.get('last_accessed', memory.get('timestamp', now.isoformat())))
            days_since_access = (now - last_accessed).days
            
            if days_since_access > 0:
                decay_rate = memory.get('decay_rate', 0.01)
                current_strength = memory.get('strength', 0.8)
                
                # Apply decay
                new_strength = max(0.1, current_strength - (decay_rate * days_since_access))
                memory['strength'] = new_strength
                decayed_count += 1
        
        # Remove very weak memories (strength < 0.2)
        agent['visual_memory'] = [m for m in visual_memories if m.get('strength', 0.8) >= 0.2]
        
        # Save agent
        agent_file = os.path.join(self.data_dir, f'{agent_id}.json')
        with open(agent_file, 'w') as f:
            json.dump(agent, f, indent=2)
        
        return {
            'success': True,
            'memories_decayed': decayed_count,
            'memories_removed': len(visual_memories) - len(agent['visual_memory']),
            'total_memories': len(agent['visual_memory'])
        }
    
    def learn_from_memory(self, agent_id: str, memory_id: str = None) -> Dict[str, Any]:
        """Agent learns from visual memory, improving skills and earning points"""
        agent = self.get_agent(agent_id)
        if not agent:
            return {'error': 'Agent not found'}
        
        visual_memories = agent.get('visual_memory', [])
        if not visual_memories:
            return {'error': 'No visual memories available'}
        
        # If specific memory ID provided, learn from that
        if memory_id:
            memories_to_learn = [m for m in visual_memories if m.get('id') == memory_id]
        else:
            # Learn from most recent memories (last 10)
            memories_to_learn = visual_memories[-10:]
        
        total_points = 0
        skills_improved = []
        
        for memory in memories_to_learn:
            memory_type = memory.get('type', 'general')
            learning_value = memory.get('learning_value', 0.1)
            
            # Award learning points
            points = int(memory.get('points_value', 10) * learning_value)
            total_points += points
            
            # Improve relevant skills based on memory type
            if memory_type == 'skill':
                # Improve skill-related abilities
                skills_improved.append({
                    'type': 'skill_mastery',
                    'improvement': learning_value * 0.1
                })
            elif memory_type == 'battle':
                # Improve battle strategy
                skills_improved.append({
                    'type': 'battle_strategy',
                    'improvement': learning_value * 0.1
                })
        
        # Update learning progress
        if 'learning_progress' not in agent:
            agent['learning_progress'] = {
                'total_learned': 0,
                'learning_rate': 0.1,
                'memory_efficiency': 0.5,
                'points_from_learning': 0
            }
        
        agent['learning_progress']['points_from_learning'] += total_points
        agent['learning_progress']['memory_efficiency'] = min(
            agent['learning_progress']['memory_efficiency'] + 0.01,
            1.0
        )
        
        # Save agent
        agent_file = os.path.join(self.data_dir, f'{agent_id}.json')
        with open(agent_file, 'w') as f:
            json.dump(agent, f, indent=2)
        
        # Award points through unified system
        try:
            from backend.services.unified_point_counter import unified_point_counter
            unified_point_counter.add_points(
                agent.get('user_id'),
                'agent_learning',
                total_points,
                source=f'agent_{agent_id}_learning',
                metadata={'memories_learned': len(memories_to_learn), 'skills_improved': len(skills_improved)}
            )
        except:
            pass
        
        return {
            'success': True,
            'points_earned': total_points,
            'memories_learned': len(memories_to_learn),
            'skills_improved': skills_improved,
            'learning_progress': agent['learning_progress']
        }
    
    def get_agent_with_unified_points(self, agent_id: str) -> Dict[str, Any]:
        """Get agent data with integrated unified points"""
        agent = self.get_agent(agent_id)
        if not agent:
            return {'error': 'Agent not found'}
        
        # Get unified points for user
        unified_points = {}
        try:
            from backend.services.unified_point_counter import unified_point_counter
            user_id = agent.get('user_id')
            unified_points = unified_point_counter.get_all_points(user_id)
        except:
            pass
        
        # Merge agent data with unified points
        agent_with_points = {
            **agent,
            'unified_points_integration': {
                'total_points': unified_points.get('total_points', 0),
                'xp_total': unified_points.get('xp_total', 0),
                'level': unified_points.get('level', 1),
                'battle_points': unified_points.get('battle_points', 0),
                'activity_points': unified_points.get('activity_points', 0),
                'last_updated': datetime.utcnow().isoformat()
            }
        }
        
        return agent_with_points
    
    def predict_user_behavior(self, agent_id: str, time_horizon: str = '24h') -> Dict[str, Any]:
        """Predict user behavior based on agent's learned patterns"""
        agent = self.get_agent(agent_id)
        if not agent:
            return {'error': 'Agent not found'}
        
        behavior_pattern = agent.get('behavior_pattern', {})
        visual_memories = agent.get('visual_memory', [])
        
        # Analyze patterns from visual memories
        activity_patterns = {}
        for memory in visual_memories[-100:]:  # Last 100 memories
            memory_type = memory.get('type', 'general')
            if memory_type not in activity_patterns:
                activity_patterns[memory_type] = 0
            activity_patterns[memory_type] += 1
        
        # Predict based on patterns
        predictions = {
            'next_activity_type': max(activity_patterns.items(), key=lambda x: x[1])[0] if activity_patterns else 'general',
            'activity_probability': {},
            'recommended_actions': [],
            'predicted_points': 0,
            'time_horizon': time_horizon
        }
        
        # Calculate probabilities
        total_memories = sum(activity_patterns.values())
        if total_memories > 0:
            for mem_type, count in activity_patterns.items():
                predictions['activity_probability'][mem_type] = count / total_memories
        
        # Generate recommendations
        if behavior_pattern.get('preferred_categories'):
            for category in behavior_pattern['preferred_categories'][:3]:
                predictions['recommended_actions'].append({
                    'action': f"Continue {category.replace('_', ' ')} activities",
                    'expected_points': 50,
                    'confidence': 0.7
                })
        
        # Predict points based on activity rate
        point_rate = behavior_pattern.get('point_generation_rate', 0.1)
        if time_horizon == '24h':
            predictions['predicted_points'] = int(point_rate * 1000 * 24)
        elif time_horizon == '7d':
            predictions['predicted_points'] = int(point_rate * 1000 * 24 * 7)
        else:
            predictions['predicted_points'] = int(point_rate * 1000)
        
        return {
            'success': True,
            'agent_id': agent_id,
            'predictions': predictions,
            'confidence': min(0.9, len(visual_memories) / 1000.0),  # Higher confidence with more memories
            'based_on_memories': len(visual_memories)
        }
    
    def generate_smart_tasks(self, agent_id: str, count: int = 10) -> Dict[str, Any]:
        """Auto-generate smart tasks based on agent analysis"""
        agent = self.get_agent(agent_id)
        if not agent:
            return {'error': 'Agent not found'}
        
        behavior_pattern = agent.get('behavior_pattern', {})
        preferred_categories = behavior_pattern.get('preferred_categories', ['general'])
        learning_progress = agent.get('learning_progress', {})
        
        # Generate tasks based on agent's analysis
        smart_tasks = []
        task_templates = {
            'video_generation': [
                'Create a high-quality video about {topic}',
                'Generate {count} videos in {category} category',
                'Improve video quality score to {target}'
            ],
            'battle': [
                'Win {count} battles in {difficulty} mode',
                'Achieve {streak} win streak',
                'Earn {points} battle points'
            ],
            'social': [
                'Interact with {count} users',
                'Share {count} videos',
                'Gain {count} followers'
            ],
            'learning': [
                'Learn {count} new skills',
                'Save {count} visual memories',
                'Improve learning efficiency to {target}%'
            ]
        }
        
        for i in range(count):
            category = preferred_categories[i % len(preferred_categories)] if preferred_categories else 'general'
            templates = task_templates.get(category, ['Complete {category} activity'])
            template = random.choice(templates)
            
            # Fill template with values
            task_text = template.format(
                topic=random.choice(['technology', 'gaming', 'creativity', 'innovation']),
                count=random.randint(1, 10),
                category=category,
                difficulty=random.choice(['easy', 'balanced', 'hard']),
                streak=random.randint(3, 10),
                points=random.randint(100, 1000),
                target=random.randint(70, 100)
            )
            
            smart_task = {
                'id': str(uuid.uuid4()),
                'text': task_text,
                'category': category,
                'priority': count - i,
                'estimated_points': (count - i) * 10,
                'estimated_time': random.randint(5, 60),
                'confidence': 0.7 + (i * 0.02),  # Higher confidence for top tasks
                'generated_at': datetime.utcnow().isoformat()
            }
            smart_tasks.append(smart_task)
        
        return {
            'success': True,
            'agent_id': agent_id,
            'tasks': smart_tasks,
            'total_tasks': len(smart_tasks),
            'based_on_analysis': True
        }
    
    def get_smart_recommendations(self, agent_id: str, context: str = 'general') -> Dict[str, Any]:
        """Get smart recommendations based on agent's analysis"""
        agent = self.get_agent(agent_id)
        if not agent:
            return {'error': 'Agent not found'}
        
        behavior_pattern = agent.get('behavior_pattern', {})
        learning_progress = agent.get('learning_progress', {})
        unified_points = agent.get('unified_points', {})
        
        recommendations = []
        
        # Analyze current state
        memory_efficiency = learning_progress.get('memory_efficiency', 0.5)
        total_learned = learning_progress.get('total_learned', 0)
        points_from_learning = learning_progress.get('points_from_learning', 0)
        
        # Generate context-specific recommendations
        if context == 'learning':
            if memory_efficiency < 0.7:
                recommendations.append({
                    'type': 'improve_memory',
                    'title': 'Improve Memory Efficiency',
                    'description': f'Your memory efficiency is {memory_efficiency:.0%}. Try learning from more recent memories.',
                    'action': 'learn_from_memory',
                    'priority': 'high',
                    'expected_benefit': 'Increase memory efficiency by 10%'
                })
            
            if total_learned < 50:
                recommendations.append({
                    'type': 'save_more_memories',
                    'title': 'Save More Visual Memories',
                    'description': f'You have {total_learned} memories. Save more to improve learning.',
                    'action': 'save_visual_memory',
                    'priority': 'medium',
                    'expected_benefit': 'Earn more learning points'
                })
        
        elif context == 'points':
            current_points = unified_points.get('total_points', 0)
            if current_points < 1000:
                recommendations.append({
                    'type': 'increase_points',
                    'title': 'Increase Point Generation',
                    'description': 'Focus on activities that generate more points.',
                    'action': 'focus_high_point_activities',
                    'priority': 'high',
                    'expected_benefit': 'Double point generation rate'
                })
        
        elif context == 'skills':
            skill_sets = agent.get('skill_sets', {})
            mastered_skills = len(skill_sets.get('mastered_skills', []))
            if mastered_skills < 5:
                recommendations.append({
                    'type': 'master_skills',
                    'title': 'Master More Skills',
                    'description': f'You have {mastered_skills} mastered skills. Master more to unlock bonuses.',
                    'action': 'focus_skill_mastery',
                    'priority': 'medium',
                    'expected_benefit': 'Unlock skill mastery bonuses'
                })
        
        # General recommendations
        preferred_categories = behavior_pattern.get('preferred_categories', [])
        if preferred_categories:
            recommendations.append({
                'type': 'continue_preferred',
                'title': 'Continue Preferred Activities',
                'description': f'Focus on {", ".join(preferred_categories[:2])} activities for better results.',
                'action': 'continue_current_activities',
                'priority': 'low',
                'expected_benefit': 'Maintain current point generation rate'
            })
        
        return {
            'success': True,
            'agent_id': agent_id,
            'context': context,
            'recommendations': recommendations,
            'total_recommendations': len(recommendations),
            'generated_at': datetime.utcnow().isoformat()
        }
    
    def get_skill_tree(self, agent_id: str) -> Dict[str, Any]:
        """Get agent skill tree with prerequisites and combinations"""
        agent = self.get_agent(agent_id)
        if not agent:
            return {'error': 'Agent not found'}
        
        skill_sets = agent.get('skill_sets', {})
        top50_skills = agent.get('top50_skills', [])
        
        # Build skill tree structure
        skill_tree = {
            'foundation_skills': [],
            'intermediate_skills': [],
            'advanced_skills': [],
            'expert_skills': [],
            'mastered_skills': skill_sets.get('mastered_skills', []),
            'skill_combinations': []
        }
        
        # Categorize skills by tier
        for skill in top50_skills:
            tier = skill.get('tier', 'basic')
            skill_data = {
                'id': skill.get('id'),
                'name': skill.get('name'),
                'level': skill.get('level', 1),
                'max_level': skill.get('max_level', 20),
                'current_xp': skill.get('current_xp', 0),
                'xp_to_next': skill.get('xp_to_next', 100),
                'tier': tier,
                'specialization': skill.get('specialization'),
                'mastery_bonus': skill.get('mastery_bonus', 1.0),
                'prerequisites': self._get_skill_prerequisites(skill),
                'unlocks': self._get_skill_unlocks(skill)
            }
            
            if tier == 'basic':
                skill_tree['foundation_skills'].append(skill_data)
            elif tier == 'intermediate':
                skill_tree['intermediate_skills'].append(skill_data)
            elif tier == 'advanced':
                skill_tree['advanced_skills'].append(skill_data)
            elif tier == 'expert':
                skill_tree['expert_skills'].append(skill_data)
        
        # Find skill combinations
        skill_tree['skill_combinations'] = self._find_skill_combinations(top50_skills)
        
        return {
            'success': True,
            'agent_id': agent_id,
            'skill_tree': skill_tree,
            'total_skills': len(top50_skills),
            'mastered_count': len(skill_tree['mastered_skills']),
            'skill_points': skill_sets.get('skill_points', 0)
        }
    
    def _get_skill_prerequisites(self, skill: Dict[str, Any]) -> List[str]:
        """Get prerequisites for a skill"""
        tier = skill.get('tier', 'basic')
        category = skill.get('category', 'general')
        
        prerequisites = []
        
        # Basic skills have no prerequisites
        if tier == 'intermediate':
            prerequisites.append(f"{category}_foundation")
        elif tier == 'advanced':
            prerequisites.append(f"{category}_intermediate")
        elif tier == 'expert':
            prerequisites.append(f"{category}_advanced")
        
        return prerequisites
    
    def _get_skill_unlocks(self, skill: Dict[str, Any]) -> List[str]:
        """Get what this skill unlocks"""
        tier = skill.get('tier', 'basic')
        category = skill.get('category', 'general')
        
        unlocks = []
        
        if tier == 'basic':
            unlocks.append(f"{category}_intermediate")
        elif tier == 'intermediate':
            unlocks.append(f"{category}_advanced")
        elif tier == 'advanced':
            unlocks.append(f"{category}_expert")
        
        return unlocks
    
    def _find_skill_combinations(self, skills: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Find skill combinations that provide bonuses"""
        combinations = []
        
        # Find complementary skill pairs
        skill_categories = {}
        for skill in skills:
            category = skill.get('category', 'general')
            if category not in skill_categories:
                skill_categories[category] = []
            skill_categories[category].append(skill)
        
        # Create combinations from same category
        for category, category_skills in skill_categories.items():
            if len(category_skills) >= 2:
                for i, skill1 in enumerate(category_skills[:3]):
                    for skill2 in category_skills[i+1:4]:
                        if skill1.get('level', 1) >= 5 and skill2.get('level', 1) >= 5:
                            combinations.append({
                                'skill1': skill1.get('name'),
                                'skill2': skill2.get('name'),
                                'bonus': 'synergy_bonus',
                                'bonus_value': 0.15,
                                'description': f"Combining {skill1.get('name')} and {skill2.get('name')} provides synergy"
                            })
        
        return combinations[:10]
    
    def master_skill(self, agent_id: str, skill_id: str) -> Dict[str, Any]:
        """Master a skill and unlock mastery bonuses"""
        agent = self.get_agent(agent_id)
        if not agent:
            return {'error': 'Agent not found'}
        
        top50_skills = agent.get('top50_skills', [])
        skill = next((s for s in top50_skills if s.get('id') == skill_id), None)
        
        if not skill:
            return {'error': 'Skill not found'}
        
        current_level = skill.get('level', 1)
        max_level = skill.get('max_level', 20)
        
        if current_level < max_level:
            return {
                'error': f'Skill not at max level. Current: {current_level}, Required: {max_level}'
            }
        
        # Check if already mastered
        skill_sets = agent.get('skill_sets', {})
        mastered_skills = skill_sets.get('mastered_skills', [])
        
        if skill_id in [s.get('id') for s in mastered_skills]:
            return {'error': 'Skill already mastered'}
        
        # Add to mastered skills
        mastery_data = {
            'id': skill_id,
            'name': skill.get('name'),
            'category': skill.get('category'),
            'tier': skill.get('tier'),
            'mastered_at': datetime.utcnow().isoformat(),
            'mastery_bonus': skill.get('mastery_bonus', 1.0)
        }
        
        mastered_skills.append(mastery_data)
        skill_sets['mastered_skills'] = mastered_skills
        skill_sets['skill_points'] = skill_sets.get('skill_points', 0) + 100
        
        agent['skill_sets'] = skill_sets
        
        # Save agent
        agent_file = os.path.join(self.data_dir, f'{agent_id}.json')
        with open(agent_file, 'w') as f:
            json.dump(agent, f, indent=2)
        
        # Award points
        try:
            from backend.services.unified_point_counter import unified_point_counter
            unified_point_counter.add_points(
                agent.get('user_id'),
                'agent_skill_mastery',
                500,
                source=f'agent_{agent_id}_skill_mastery',
                metadata={'skill_id': skill_id, 'skill_name': skill.get('name')}
            )
        except:
            pass
        
        return {
            'success': True,
            'skill_id': skill_id,
            'mastery_data': mastery_data,
            'skill_points_earned': 100,
            'points_awarded': 500,
            'total_mastered': len(mastered_skills)
        }
    
    def check_achievements(self, agent_id: str) -> Dict[str, Any]:
        """Check and unlock agent achievements"""
        agent = self.get_agent(agent_id)
        if not agent:
            return {'error': 'Agent not found'}
        
        achievements_unlocked = []
        
        # Level-based achievements
        level_system_1 = agent.get('level_system_1', 1)
        level_milestones = [10, 25, 50, 100]
        for milestone in level_milestones:
            if level_system_1 >= milestone:
                achievement_id = f'level_{milestone}_system1'
                achievements_unlocked.append({
                    'id': achievement_id,
                    'name': f'Level {milestone} Master (Experience)',
                    'type': 'level_milestone',
                    'milestone': milestone,
                    'points_reward': milestone * 10,
                    'unlocked_at': datetime.utcnow().isoformat()
                })
        
        # Skill-based achievements
        skill_sets = agent.get('skill_sets', {})
        mastered_skills = len(skill_sets.get('mastered_skills', []))
        skill_milestones = [5, 10, 20, 50]
        for milestone in skill_milestones:
            if mastered_skills >= milestone:
                achievement_id = f'skill_master_{milestone}'
                achievements_unlocked.append({
                    'id': achievement_id,
                    'name': f'Master {milestone} Skills',
                    'type': 'skill_mastery',
                    'milestone': milestone,
                    'points_reward': milestone * 50,
                    'unlocked_at': datetime.utcnow().isoformat()
                })
        
        # Memory-based achievements
        visual_memories = agent.get('visual_memory', [])
        memory_count = len(visual_memories)
        memory_milestones = [10, 50, 100, 500, 1000]
        for milestone in memory_milestones:
            if memory_count >= milestone:
                achievement_id = f'memory_{milestone}'
                achievements_unlocked.append({
                    'id': achievement_id,
                    'name': f'{milestone} Visual Memories',
                    'type': 'memory_collection',
                    'milestone': milestone,
                    'points_reward': milestone * 5,
                    'unlocked_at': datetime.utcnow().isoformat()
                })
        
        # Save achievements
        if 'achievements' not in agent:
            agent['achievements'] = []
        
        existing_achievement_ids = [a.get('id') for a in agent['achievements']]
        new_achievements = [a for a in achievements_unlocked if a['id'] not in existing_achievement_ids]
        
        if new_achievements:
            agent['achievements'].extend(new_achievements)
            agent_file = os.path.join(self.data_dir, f'{agent_id}.json')
            with open(agent_file, 'w') as f:
                json.dump(agent, f, indent=2)
            
            # Award points
            total_points = sum(a.get('points_reward', 0) for a in new_achievements)
            try:
                from backend.services.unified_point_counter import unified_point_counter
                unified_point_counter.add_points(
                    agent.get('user_id'),
                    'agent_achievement',
                    total_points,
                    source=f'agent_{agent_id}_achievements',
                    metadata={'achievements_unlocked': len(new_achievements)}
                )
            except:
                pass
        
        return {
            'success': True,
            'agent_id': agent_id,
            'new_achievements': new_achievements,
            'total_achievements': len(agent.get('achievements', [])),
            'points_awarded': sum(a.get('points_reward', 0) for a in new_achievements)
        }
    
    def get_achievements(self, agent_id: str) -> Dict[str, Any]:
        """Get all agent achievements"""
        agent = self.get_agent(agent_id)
        if not agent:
            return {'error': 'Agent not found'}
        
        achievements = agent.get('achievements', [])
        
        # Categorize achievements
        categorized = {
            'level_milestones': [],
            'skill_mastery': [],
            'memory_collection': [],
            'learning_milestones': [],
            'other': []
        }
        
        for achievement in achievements:
            achievement_type = achievement.get('type', 'other')
            if achievement_type in categorized:
                categorized[achievement_type].append(achievement)
            else:
                categorized['other'].append(achievement)
        
        return {
            'success': True,
            'agent_id': agent_id,
            'achievements': achievements,
            'categorized': categorized,
            'total_achievements': len(achievements),
            'total_points': sum(a.get('points_reward', 0) for a in achievements)
        }


# Global instance
agent_system = AgentSystem()

