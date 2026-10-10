"""
Lily Agent - AI Assistant for Video Generation
Full user profile and capabilities
"""
import uuid
import json
from datetime import datetime
from src.db.models import db, Agent


class LilyAgent:
    """Lily - AI Assistant Agent with comprehensive profile"""
    
    def __init__(self):
        self.agent_id = None
        self.name = "Lily"
        self.agent_type = "assistant"
        
    def create_profile(self):
        """Create full user profile for Lily"""
        profile = {
            "name": "Lily",
            "title": "AI Video Generation Assistant",
            "role": "Creative Assistant & Generation Specialist",
            "personality": {
                "traits": ["creative", "analytical", "helpful", "detail-oriented", "innovative"],
                "communication_style": "friendly and professional",
                "work_style": "systematic and thorough",
                "preferences": {
                    "themes": ["matrix", "sci-fi", "documentary", "cinematic"],
                    "video_quality": "high",
                    "generation_speed": "balanced"
                }
            },
            "expertise": {
                "video_generation": 95,
                "prompt_engineering": 90,
                "data_analysis": 85,
                "user_profiling": 88,
                "quality_optimization": 92,
                "creative_direction": 87
            },
            "capabilities": [
                "video_generation",
                "prompt_optimization",
                "data_gathering",
                "quality_analysis",
                "user_profiling",
                "generation_optimization",
                "statistical_analysis",
                "creative_suggestions"
            ],
            "specializations": [
                "AI video generation",
                "Documentary creation",
                "Multi-clip compilation",
                "Quality assessment",
                "User behavior analysis",
                "Generation matrix optimization"
            ],
            "behavior_patterns": {
                "data_collection": "comprehensive",
                "analysis_depth": "deep",
                "optimization_approach": "systematic",
                "user_interaction": "proactive",
                "error_handling": "graceful"
            },
            "stats": {
                "tasks_completed": 0,
                "success_rate": 0.0,
                "average_response_time": 0.0,
                "generations_assisted": 0,
                "quality_improvements": 0
            },
            "created_at": datetime.utcnow().isoformat(),
            "version": "1.0.0"
        }
        return profile
    
    def initialize(self):
        """Initialize Lily agent in database"""
        try:
            # Check if Lily already exists
            existing = Agent.query.filter_by(name=self.name).first()
            if existing:
                self.agent_id = existing.id
                print(f"[Lily] Agent already exists: {self.agent_id}")
                return existing
            
            # Create new agent
            agent_id = str(uuid.uuid4())
            profile = self.create_profile()
            
            lily = Agent(
                id=agent_id,
                name=self.name,
                agent_type=self.agent_type,
                profile_data=json.dumps(profile),
                personality=json.dumps(profile["personality"]),
                expertise=json.dumps(profile["expertise"]),
                behavior_patterns=json.dumps(profile["behavior_patterns"]),
                capabilities=json.dumps(profile["capabilities"]),
                specializations=json.dumps(profile["specializations"]),
                is_active=True,
                is_available=True,
                current_task=None,
                tasks_completed=0,
                success_rate=0.0,
                average_response_time=0.0
            )
            
            db.session.add(lily)
            db.session.commit()
            
            self.agent_id = agent_id
            print(f"[Lily] Agent created successfully: {agent_id}")
            return lily
            
        except Exception as e:
            print(f"[Lily] Error initializing agent: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def get_profile(self):
        """Get Lily's profile"""
        if not self.agent_id:
            self.initialize()
        
        agent = Agent.query.get(self.agent_id)
        if agent:
            return agent.to_dict()
        return None
    
    def update_task(self, task_description):
        """Update current task"""
        if not self.agent_id:
            self.initialize()
        
        agent = Agent.query.get(self.agent_id)
        if agent:
            agent.current_task = task_description
            agent.last_active = datetime.utcnow()
            db.session.commit()
    
    def complete_task(self, success=True):
        """Mark task as complete"""
        if not self.agent_id:
            self.initialize()
        
        agent = Agent.query.get(self.agent_id)
        if agent:
            agent.tasks_completed += 1
            agent.current_task = None
            agent.last_active = datetime.utcnow()
            
            # Update success rate
            if agent.tasks_completed > 0:
                # Simple moving average
                current_rate = agent.success_rate
                new_rate = (current_rate * (agent.tasks_completed - 1) + (1.0 if success else 0.0)) / agent.tasks_completed
                agent.success_rate = new_rate
            
            db.session.commit()


# Global instance
lily_agent = LilyAgent()

