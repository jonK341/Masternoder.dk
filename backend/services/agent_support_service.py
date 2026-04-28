"""
Agent Support Service
Support and service capabilities for agents
"""
import os
import json
from typing import Dict, List, Optional
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Signup/API key URLs for each LLM provider (keys must match backend.services.llm_service.PROVIDERS)
LLM_PROVIDER_URLS: Dict[str, str] = {
    "openai": "https://platform.openai.com/api-keys",
    "groq": "https://console.groq.com/keys",
    "gemini": "https://aistudio.google.com/apikey",
    "openrouter": "https://openrouter.ai/keys",
    "cerebras": "https://cloud.cerebras.ai/",
    "deepseek": "https://platform.deepseek.com/api_keys",
    "mistral": "https://console.mistral.ai/api-keys/",
    "together": "https://api.together.xyz/settings/api-keys",
    "anthropic": "https://console.anthropic.com/settings/keys",
    "azure": "https://portal.azure.com/",
    "cohere": "https://dashboard.cohere.com/api-keys",
}


def _build_ai_api_providers_collection() -> List[Dict[str, str]]:
    """Build AI API providers list from llm_service.PROVIDERS (api_key_env) plus video/TTS/optional."""
    result: List[Dict[str, str]] = []
    try:
        from backend.services.llm_service import PROVIDERS
        for pname, cfg in PROVIDERS.items():
            if not isinstance(cfg, dict):
                continue
            api_key_env = cfg.get("api_key_env")
            if not api_key_env:
                continue
            label = cfg.get("label") or pname.replace("_", " ").title()
            url = LLM_PROVIDER_URLS.get(pname, "#")
            result.append({"name": label, "url": url, "env": api_key_env})
    except Exception:
        pass
    # Non-LLM providers (video, image, TTS, optional)
    result.extend([
        {"name": "Runway (video)", "url": "https://app.runwayml.com/settings/api", "env": "RUNWAYML_API_KEY"},
        {"name": "Pika (video)", "url": "https://pika.art/", "env": "PIKA_LABS_API_KEY"},
        {"name": "Stability AI", "url": "https://platform.stability.ai/account/keys", "env": "STABILITY_AI_API_KEY"},
        {"name": "ModelsLab", "url": "https://modelslab.com/dashboard/api-keys", "env": "MODELSLAB_API_KEY"},
        {"name": "ElevenLabs (TTS)", "url": "https://elevenlabs.io/app/settings/api-keys", "env": "ELEVENLABS_API_KEY"},
        {"name": "Replicate (optional)", "url": "https://replicate.com/account/api-tokens", "env": "REPLICATE_API_TOKEN"},
        {"name": "HeyGen (Avatar/Video)", "url": "https://app.heygen.com/settings/api", "env": "HEYGEN_API_KEY"},
        {"name": "Google Gemini (alt key)", "url": "https://aistudio.google.com/apikey", "env": "GOOGLE_GEMINI_API_KEY"},
    ])
    return result


class AgentSupportService:
    """Support and service management for agents"""
    
    def __init__(self, base_dir: Optional[str] = None):
        self.base_dir = base_dir or BASE_DIR
        self.support_file = os.path.join(self.base_dir, 'logs', 'agent_support', 'support.json')
        self.load_support()
    
    def load_support(self):
        """Load support data"""
        os.makedirs(os.path.dirname(self.support_file), exist_ok=True)
        if os.path.exists(self.support_file):
            try:
                with open(self.support_file, 'r') as f:
                    self.support_data = json.load(f)
            except:
                self.support_data = self._default_support()
        else:
            self.support_data = self._default_support()
            self.save_support()
    
    def _default_support(self) -> Dict:
        """Default support configuration"""
        return {
            'support_tickets': [],
            'services': {
                'maintenance': {
                    'name': 'Maintenance Service',
                    'status': 'active',
                    'agents': ['master_fix_agent', 'monitoring_agent'],
                    'capabilities': ['health_check', 'diagnostic', 'auto_fix']
                },
                'monitoring': {
                    'name': 'Monitoring Service',
                    'status': 'active',
                    'agents': ['monitoring_agent', 'scanner_agent'],
                    'capabilities': ['system_monitoring', 'performance_tracking', 'alerting']
                },
                'development': {
                    'name': 'Development Service',
                    'status': 'active',
                    'agents': ['scanner_agent'],
                    'capabilities': ['code_generation', 'api_scanning', 'method_generation']
                },
                'support': {
                    'name': 'Support Service',
                    'status': 'active',
                    'agents': ['master_fix_agent'],
                    'capabilities': ['ticket_management', 'issue_resolution', 'documentation']
                }
            },
            'support_resources': {
                'ai_api_providers': _build_ai_api_providers_collection(),
                'useful_docs': [
                    {'label': 'PayPal developer dashboard', 'url': 'https://developer.paypal.com/dashboard/'},
                    {'label': 'GitHub OAuth apps', 'url': 'https://github.com/settings/developers'},
                    {'label': 'arXiv API (intelligence aggregator)', 'url': 'https://info.arxiv.org/help/api/'},
                    {'label': 'Project: Checkpoints recheck (docs/CHECKPOINTS_RECHECK.md)', 'url': '#'},
                    {'label': 'Project: AI systems & env links (docs/RESEARCH_AI_SYSTEMS.md)', 'url': '#'},
                ],
                'api_endpoints': [
                    '/api/agent/master-fix/*',
                    '/api/agent/automation/*',
                    '/api/agent/skillset/all',
                    '/api/agent/support/tickets',
                    '/api/agent/support/resources',
                ],
                'tools': [
                    {'label': 'Debugger', 'url': '/vidgenerator/debugger'},
                    {'label': 'AI Agents', 'url': '/vidgenerator/agents'},
                    {'label': 'Aggregator', 'url': '/vidgenerator/aggregator'},
                ]
            }
        }
    
    def save_support(self):
        """Save support data"""
        try:
            with open(self.support_file, 'w') as f:
                json.dump(self.support_data, f, indent=2, default=str)
        except Exception as e:
            print(f"Error saving support data: {e}")
    
    def create_support_ticket(self, title: str, description: str, priority: str = 'medium', agent_id: Optional[str] = None) -> Dict:
        """Create a support ticket"""
        ticket = {
            'id': f"ticket_{len(self.support_data['support_tickets']) + 1}",
            'title': title,
            'description': description,
            'priority': priority,
            'status': 'open',
            'agent_id': agent_id,
            'created_at': datetime.now().isoformat(),
            'updated_at': datetime.now().isoformat(),
            'resolved_at': None
        }
        
        self.support_data['support_tickets'].append(ticket)
        self.save_support()
        
        return {
            'success': True,
            'ticket': ticket
        }
    
    def get_support_tickets(self, status: Optional[str] = None) -> Dict:
        """Get support tickets"""
        tickets = self.support_data.get('support_tickets', [])
        
        if status:
            tickets = [t for t in tickets if t.get('status') == status]
        
        return {
            'success': True,
            'tickets': tickets,
            'count': len(tickets)
        }
    
    def resolve_ticket(self, ticket_id: str) -> Dict:
        """Resolve a support ticket"""
        tickets = self.support_data.get('support_tickets', [])
        
        for ticket in tickets:
            if ticket.get('id') == ticket_id:
                ticket['status'] = 'resolved'
                ticket['resolved_at'] = datetime.now().isoformat()
                ticket['updated_at'] = datetime.now().isoformat()
                self.save_support()
                
                return {
                    'success': True,
                    'ticket': ticket
                }
        
        return {
            'success': False,
            'error': 'Ticket not found'
        }
    
    def get_services(self) -> Dict:
        """Get all services"""
        return {
            'success': True,
            'services': self.support_data.get('services', {}),
            'count': len(self.support_data.get('services', {}))
        }
    
    def get_service(self, service_id: str) -> Dict:
        """Get a specific service"""
        services = self.support_data.get('services', {})
        service = services.get(service_id)
        
        if service:
            return {
                'success': True,
                'service': service
            }
        else:
            return {
                'success': False,
                'error': 'Service not found'
            }
    
    def get_support_resources(self) -> Dict:
        """Get support resources (merge defaults so AI API provider links always present)."""
        saved = self.support_data.get('support_resources', {})
        defaults = self._default_support().get('support_resources', {})
        merged = dict(defaults)
        for k, v in saved.items():
            if v is None:
                continue
            if k in ('ai_api_providers', 'useful_docs') and isinstance(v, list) and len(v) == 0:
                continue
            merged[k] = v
        return {
            'success': True,
            'resources': merged
        }
    
    def add_service(self, service_id: str, service_data: Dict):
        """Add a new service"""
        if 'services' not in self.support_data:
            self.support_data['services'] = {}
        
        self.support_data['services'][service_id] = service_data
        self.save_support()
        
        return {
            'success': True,
            'service': service_data
        }

# Global instance
agent_support_service = AgentSupportService()
