"""
Content Generation Agent
Specialized agent for content creation and generation
"""
import os
import json
from typing import Dict, List, Optional
from datetime import datetime
import uuid

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_CONTENT_GEN_JOBS: Dict[str, Dict] = {}


def get_llm_service():
    """Lazy import to avoid hard dependency at import time."""
    from backend.services.llm_service import llm_service
    return llm_service

class AgentContentGenerator:
    """Content generation agent"""
    
    def __init__(self, base_dir: Optional[str] = None):
        self.base_dir = base_dir or BASE_DIR
        self.agent_id = 'content_generator_agent'
        self.agent_name = 'Content Generator Agent'
        self.data_file = os.path.join(self.base_dir, 'logs', 'agents', 'content_generator.json')
        self.load_data()
    
    def load_data(self):
        """Load agent data"""
        os.makedirs(os.path.dirname(self.data_file), exist_ok=True)
        if os.path.exists(self.data_file):
            try:
                with open(self.data_file, 'r') as f:
                    self.data = json.load(f)
            except:
                self.data = self._default_data()
        else:
            self.data = self._default_data()
            self.save_data()
    
    def _default_data(self) -> Dict:
        """Default agent data"""
        return {
            'agent_id': self.agent_id,
            'agent_name': self.agent_name,
            'level': 1,
            'experience': 0,
            'skills': [
                'generate_video',
                'generate_clip',
                'generate_image',
                'generate_audio',
                'generate_text',
                'optimize_content',
                'analyze_trends',
                'create_template'
            ],
            'content_generated': 0,
            'templates_created': 0,
            'trends_analyzed': 0,
            'last_activity': None
        }
    
    def save_data(self):
        """Save agent data"""
        try:
            with open(self.data_file, 'w') as f:
                json.dump(self.data, f, indent=2, default=str)
        except Exception as e:
            print(f"Error saving content generator data: {e}")
    
    def generate_content(self, content_type: str, parameters: Dict, user_id: str = 'agent_user') -> Dict:
        """Generate content"""
        try:
            from backend.services.agent_point_creator import agent_point_creator
            
            # Award points via trigger
            from backend.services.agent_trigger_system import agent_trigger_system
            trigger_map = {
                'video': 'video_generation',
                'clip': 'clip_generation',
                'image': 'image_generation',
                'audio': 'audio_generation',
                'text': 'text_generation'
            }
            trigger_id = trigger_map.get(content_type, 'skill_execution')
            agent_trigger_system.award_points(trigger_id, self.agent_id, {
                'content_type': content_type,
                'parameters': parameters
            })
            
            # Award points for content generation - creates real value
            point_result = agent_point_creator.award_points_for_agent_action(
                agent_id=self.agent_id,
                action=f'generate_{content_type}',
                user_id=user_id
            )
            
            self.data['content_generated'] += 1
            self.data['last_activity'] = datetime.now().isoformat()
            self.save_data()
            
            result = {
                'success': True,
                'content_type': content_type,
                'agent_id': self.agent_id,
                'total_generated': self.data['content_generated'],
                'points_awarded': point_result.get('points_awarded', {}),
                'value_created': point_result.get('total_value', 0)
            }
            normalized = str(content_type or '').strip().lower()
            if normalized == 'video':
                result['generation'] = self._start_video_generation(parameters, user_id, short_clip=False)
            elif normalized in ('clip', 'clips'):
                result['generation'] = self._start_video_generation(parameters, user_id, short_clip=True)
            return result
        except Exception as e:
            return {'success': False, 'error': str(e)}

    def _get_job(self, job_id: str) -> Optional[Dict]:
        return _CONTENT_GEN_JOBS.get(job_id)

    def _set_job(self, job_id: str, job: Dict):
        _CONTENT_GEN_JOBS[job_id] = job

    def get_generation_job(self, job_id: str) -> Dict:
        """Get generated video/clip job status from content agent job store."""
        job = self._get_job(job_id)
        if not job:
            return {'success': False, 'error': 'Job not found', 'job_id': job_id}
        return {'success': True, 'job': job}

    def _start_video_generation(self, parameters: Dict, user_id: str, short_clip: bool = False) -> Dict:
        """
        Start AI-backed video/clip generation.
        Uses video_generator_service AI planning flow and returns job metadata.
        """
        job_id = str(uuid.uuid4())
        prompt = (
            parameters.get('prompt')
            or parameters.get('title')
            or parameters.get('topic')
            or 'Untitled generated content'
        )
        resolution = parameters.get('resolution', '1280x768')
        duration_default = 45 if short_clip else 180
        duration = int(parameters.get('duration', duration_default))
        clip_count = int(parameters.get('clip_count', 3))
        title = parameters.get('title') or str(prompt)[:100]

        llm_available = False
        try:
            llm_available = get_llm_service().is_available()
        except Exception:
            llm_available = False

        config = {
            'prompt': prompt,
            'title': title,
            'description': prompt,
            'user_id': user_id,
            'duration': duration,
            'resolution': resolution,
            'short_clip': short_clip,
            'clip_count': max(1, min(10, clip_count)),
            'use_context': True,  # Enables profile+prompt AI planning for scenes.
            'include_points_in_clip': parameters.get('include_points_in_clip', True),
            'content_category': (parameters.get('content_category') or 'general').strip().lower(),
            'template': parameters.get('template', 'default'),
        }

        self._set_job(job_id, {
            'id': job_id,
            'status': 'processing',
            'progress': 0,
            'message': 'Starting AI generation...',
            'type': 'clip' if short_clip else 'video',
            'config': config,
            'created_at': datetime.utcnow().isoformat(),
            'updated_at': datetime.utcnow().isoformat(),
        })

        from backend.services.video_generator_service import (
            generate_ai_clips_background,
            generate_video_background,
        )
        if short_clip:
            generate_ai_clips_background(job_id, config, self._get_job, self._set_job)
        else:
            generate_video_background(job_id, config, self._get_job, self._set_job)

        return {
            'job_id': job_id,
            'status': 'processing',
            'type': 'clip' if short_clip else 'video',
            'ai_planning_enabled': True,
            'llm_available': llm_available,
        }
    
    def analyze_trends(self) -> Dict:
        """Analyze content trends"""
        try:
            self.data['trends_analyzed'] += 1
            self.data['last_activity'] = datetime.now().isoformat()
            self.save_data()
            
            return {
                'success': True,
                'trends': ['video', 'short_form', 'ai_generated', 'interactive'],
                'total_analyzed': self.data['trends_analyzed']
            }
        except Exception as e:
            return {'success': False, 'error': str(e)}
    
    def get_status(self) -> Dict:
        """Get agent status"""
        return {
            'agent_id': self.agent_id,
            'agent_name': self.agent_name,
            'level': self.data.get('level', 1),
            'experience': self.data.get('experience', 0),
            'content_generated': self.data.get('content_generated', 0),
            'templates_created': self.data.get('templates_created', 0),
            'trends_analyzed': self.data.get('trends_analyzed', 0),
            'skills': self.data.get('skills', [])
        }

# Global instance
agent_content_generator = AgentContentGenerator()
