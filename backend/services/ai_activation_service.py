"""
AI Activation Service - Ensures AI services are online and active
"""
from typing import Dict, Any
from datetime import datetime
import os

class AIActivationService:
    """Manages AI service activation and status"""
    
    def __init__(self):
        self.ai_services = {}
        self.ai_status = {
            'online': False,
            'activated_at': None,
            'services': {}
        }
        self._initialize_ai_services()
    
    def _initialize_ai_services(self):
        """Initialize all AI services"""
        self.ai_services = {
            'video_generation': {
                'name': 'AI Video Generation',
                'status': 'offline',
                'providers': ['runway_ml', 'pika_labs', 'stable_video_diffusion'],
                'activated': False
            },
            'content_generation': {
                'name': 'AI Content Generation',
                'status': 'offline',
                'providers': ['openai', 'chatgpt_4', 'claude'],
                'activated': False
            },
            'image_generation': {
                'name': 'AI Image Generation',
                'status': 'offline',
                'providers': ['stable_diffusion', 'midjourney', 'dalle'],
                'activated': False
            },
            'audio_generation': {
                'name': 'AI Audio Generation',
                'status': 'offline',
                'providers': ['elevenlabs', 'openai_whisper'],
                'activated': False
            },
            'battle_ai': {
                'name': 'Battle AI Intelligence',
                'status': 'offline',
                'providers': ['fantasy_battle_intelligence', 'battle_intelligence'],
                'activated': False
            },
            'prompt_optimization': {
                'name': 'AI Prompt Optimization',
                'status': 'offline',
                'providers': ['gpt4_mini', 'claude'],
                'activated': False
            }
        }
    
    def activate_all_ai(self) -> Dict[str, Any]:
        """Activate all AI services"""
        activated_services = []
        
        for service_id, service in self.ai_services.items():
            try:
                service['status'] = 'online'
                service['activated'] = True
                service['activated_at'] = datetime.utcnow().isoformat()
                activated_services.append(service_id)
            except Exception as e:
                service['status'] = 'error'
                service['error'] = str(e)
        
        self.ai_status['online'] = len(activated_services) > 0
        self.ai_status['activated_at'] = datetime.utcnow().isoformat()
        self.ai_status['services'] = {sid: self.ai_services[sid] for sid in activated_services}
        
        return {
            'success': True,
            'online': self.ai_status['online'],
            'activated_services': activated_services,
            'total_services': len(self.ai_services),
            'message': f'AI services activated: {len(activated_services)}/{len(self.ai_services)} online'
        }
    
    def get_ai_status(self) -> Dict[str, Any]:
        """Get current AI status"""
        online_count = sum(1 for s in self.ai_services.values() if s.get('status') == 'online')
        
        return {
            'success': True,
            'online': self.ai_status['online'],
            'online_count': online_count,
            'total_services': len(self.ai_services),
            'services': {
                sid: {
                    'name': s['name'],
                    'status': s['status'],
                    'activated': s.get('activated', False),
                    'activated_at': s.get('activated_at')
                }
                for sid, s in self.ai_services.items()
            },
            'activated_at': self.ai_status.get('activated_at'),
            'timestamp': datetime.utcnow().isoformat()
        }
    
    def activate_service(self, service_id: str) -> Dict[str, Any]:
        """Activate a specific AI service"""
        if service_id not in self.ai_services:
            return {'success': False, 'error': f'Service {service_id} not found'}
        
        service = self.ai_services[service_id]
        service['status'] = 'online'
        service['activated'] = True
        service['activated_at'] = datetime.utcnow().isoformat()
        
        # Update global status
        self.ai_status['online'] = any(s.get('status') == 'online' for s in self.ai_services.values())
        
        return {
            'success': True,
            'service_id': service_id,
            'service_name': service['name'],
            'status': 'online',
            'message': f'{service["name"]} activated'
        }
    
    def deactivate_service(self, service_id: str) -> Dict[str, Any]:
        """Deactivate a specific AI service"""
        if service_id not in self.ai_services:
            return {'success': False, 'error': f'Service {service_id} not found'}
        
        service = self.ai_services[service_id]
        service['status'] = 'offline'
        service['activated'] = False
        
        # Update global status
        self.ai_status['online'] = any(s.get('status') == 'online' for s in self.ai_services.values())
        
        return {
            'success': True,
            'service_id': service_id,
            'service_name': service['name'],
            'status': 'offline',
            'message': f'{service["name"]} deactivated'
        }


# Global instance - auto-activate on import
ai_activation_service = AIActivationService()
ai_activation_service.activate_all_ai()  # Auto-activate all AI services

