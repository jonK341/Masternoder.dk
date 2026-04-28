"""
Agent Groups System
Groups with service workers, agents, models, managers, secretary, and more
"""
import os
import json
from typing import Dict, List, Optional
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

class AgentGroups:
    """Agent groups management"""
    
    def __init__(self, base_dir: Optional[str] = None):
        self.base_dir = base_dir or BASE_DIR
        self.groups_file = os.path.join(self.base_dir, 'logs', 'agent_groups', 'groups.json')
        self.load_groups()
    
    def load_groups(self):
        """Load groups"""
        os.makedirs(os.path.dirname(self.groups_file), exist_ok=True)
        if os.path.exists(self.groups_file):
            try:
                with open(self.groups_file, 'r') as f:
                    self.groups = json.load(f)
            except:
                self.groups = self._default_groups()
        else:
            self.groups = self._default_groups()
            self.save_groups()
    
    def _default_groups(self) -> Dict:
        """Default groups"""
        return {
            'maintenance_team': {
                'name': 'Maintenance Team',
                'description': 'Handles system maintenance and monitoring',
                'members': {
                    'service_workers': [
                        {
                            'id': 'sw_maintenance',
                            'name': 'Maintenance Service Worker',
                            'role': 'background_tasks',
                            'status': 'active'
                        },
                        {
                            'id': 'sw_monitoring',
                            'name': 'Monitoring Service Worker',
                            'role': 'monitoring',
                            'status': 'active'
                        }
                    ],
                    'agents': [
                        {
                            'id': 'agent_master_fix',
                            'name': 'Master Fix Agent',
                            'role': 'maintenance',
                            'status': 'active'
                        },
                        {
                            'id': 'agent_monitoring',
                            'name': 'Monitoring Agent',
                            'role': 'monitoring',
                            'status': 'active'
                        }
                    ],
                    'models': [
                        {
                            'id': 'model_diagnostic',
                            'name': 'Diagnostic Model',
                            'role': 'analysis',
                            'status': 'active'
                        }
                    ],
                    'managers': [
                        {
                            'id': 'manager_maintenance',
                            'name': 'Maintenance Manager',
                            'role': 'coordination',
                            'status': 'active'
                        }
                    ],
                    'secretary': [
                        {
                            'id': 'secretary_maintenance',
                            'name': 'Maintenance Secretary',
                            'role': 'documentation',
                            'status': 'active'
                        }
                    ]
                }
            },
            'development_team': {
                'name': 'Development Team',
                'description': 'Handles development and code generation',
                'members': {
                    'service_workers': [
                        {
                            'id': 'sw_codegen',
                            'name': 'Code Generation Service Worker',
                            'role': 'code_generation',
                            'status': 'active'
                        }
                    ],
                    'agents': [
                        {
                            'id': 'agent_scanner',
                            'name': 'Scanner Agent',
                            'role': 'scanning',
                            'status': 'active'
                        }
                    ],
                    'models': [
                        {
                            'id': 'model_codegen',
                            'name': 'Code Generation Model',
                            'role': 'generation',
                            'status': 'active'
                        }
                    ],
                    'managers': [
                        {
                            'id': 'manager_dev',
                            'name': 'Development Manager',
                            'role': 'coordination',
                            'status': 'active'
                        }
                    ],
                    'secretary': [
                        {
                            'id': 'secretary_dev',
                            'name': 'Development Secretary',
                            'role': 'documentation',
                            'status': 'active'
                        }
                    ]
                }
            },
            'analytics_team': {
                'name': 'Analytics Team',
                'description': 'Handles analytics and reporting',
                'members': {
                    'service_workers': [
                        {
                            'id': 'sw_analytics',
                            'name': 'Analytics Service Worker',
                            'role': 'data_processing',
                            'status': 'active'
                        }
                    ],
                    'agents': [
                        {
                            'id': 'agent_analytics',
                            'name': 'Analytics Agent',
                            'role': 'analysis',
                            'status': 'active'
                        }
                    ],
                    'models': [
                        {
                            'id': 'model_analytics',
                            'name': 'Analytics Model',
                            'role': 'prediction',
                            'status': 'active'
                        }
                    ],
                    'managers': [
                        {
                            'id': 'manager_analytics',
                            'name': 'Analytics Manager',
                            'role': 'coordination',
                            'status': 'active'
                        }
                    ],
                    'secretary': [
                        {
                            'id': 'secretary_analytics',
                            'name': 'Analytics Secretary',
                            'role': 'reporting',
                            'status': 'active'
                        }
                    ]
                }
            },
            'security_team': {
                'name': 'Security Team',
                'description': 'Handles security and integrity checks',
                'members': {
                    'service_workers': [
                        {
                            'id': 'sw_security',
                            'name': 'Security Service Worker',
                            'role': 'monitoring',
                            'status': 'active'
                        }
                    ],
                    'agents': [
                        {
                            'id': 'agent_security',
                            'name': 'Security Agent',
                            'role': 'security',
                            'status': 'active'
                        }
                    ],
                    'models': [
                        {
                            'id': 'model_security',
                            'name': 'Security Model',
                            'role': 'threat_detection',
                            'status': 'active'
                        }
                    ],
                    'managers': [
                        {
                            'id': 'manager_security',
                            'name': 'Security Manager',
                            'role': 'coordination',
                            'status': 'active'
                        }
                    ],
                    'secretary': [
                        {
                            'id': 'secretary_security',
                            'name': 'Security Secretary',
                            'role': 'documentation',
                            'status': 'active'
                        }
                    ]
                }
            },
            'content_team': {
                'name': 'Content Team',
                'description': 'Handles content generation and optimization',
                'members': {
                    'agents': [
                        {
                            'id': 'agent_content_generator',
                            'name': 'Content Generator Agent',
                            'role': 'content_creation',
                            'status': 'active'
                        }
                    ]
                }
            },
            'battle_team': {
                'name': 'Battle Team',
                'description': 'Handles battle strategies and tactics',
                'members': {
                    'agents': [
                        {
                            'id': 'agent_battle_strategy',
                            'name': 'Battle Strategy Agent',
                            'role': 'strategy',
                            'status': 'active'
                        }
                    ]
                }
            },
            'social_team': {
                'name': 'Social Team',
                'description': 'Handles social engagement and community',
                'members': {
                    'agents': [
                        {
                            'id': 'agent_social_engagement',
                            'name': 'Social Engagement Agent',
                            'role': 'engagement',
                            'status': 'active'
                        }
                    ]
                }
            },
            'analytics_team': {
                'name': 'Analytics Team',
                'description': 'Handles data analysis and insights',
                'members': {
                    'agents': [
                        {
                            'id': 'agent_analytics',
                            'name': 'Analytics Agent',
                            'role': 'analytics',
                            'status': 'active'
                        }
                    ]
                }
            },
            'performance_team': {
                'name': 'Performance Team',
                'description': 'Handles performance optimization',
                'members': {
                    'agents': [
                        {
                            'id': 'agent_performance_optimizer',
                            'name': 'Performance Optimizer Agent',
                            'role': 'optimization',
                            'status': 'active'
                        }
                    ]
                }
            },
            'ux_team': {
                'name': 'UX Team',
                'description': 'Handles user experience optimization',
                'members': {
                    'agents': [
                        {
                            'id': 'agent_user_experience',
                            'name': 'User Experience Agent',
                            'role': 'ux',
                            'status': 'active'
                        }
                    ]
                }
            },
            'integration_team': {
                'name': 'Integration Team',
                'description': 'Handles system integrations',
                'members': {
                    'agents': [
                        {
                            'id': 'agent_integration',
                            'name': 'Integration Agent',
                            'role': 'integration',
                            'status': 'active'
                        }
                    ]
                }
            },
            'management_team': {
                'name': 'Management Team',
                'description': 'Manages and coordinates all agents',
                'members': {
                    'agents': [
                        {
                            'id': 'agent_manager',
                            'name': 'Agent Manager',
                            'role': 'manager',
                            'status': 'active'
                        },
                        {
                            'id': 'agent_secretary',
                            'name': 'Agent Secretary',
                            'role': 'secretary',
                            'status': 'active'
                        },
                        {
                            'id': 'agent_judge',
                            'name': 'Agent Judge',
                            'role': 'judge',
                            'status': 'active'
                        }
                    ]
                }
            },
            'quality_team': {
                'name': 'Quality Team',
                'description': 'Handles quality assurance and testing',
                'members': {
                    'service_workers': [
                        {
                            'id': 'sw_testing',
                            'name': 'Testing Service Worker',
                            'role': 'testing',
                            'status': 'active'
                        }
                    ],
                    'agents': [
                        {
                            'id': 'agent_qa',
                            'name': 'QA Agent',
                            'role': 'quality',
                            'status': 'active'
                        }
                    ],
                    'models': [
                        {
                            'id': 'model_qa',
                            'name': 'QA Model',
                            'role': 'validation',
                            'status': 'active'
                        }
                    ],
                    'managers': [
                        {
                            'id': 'manager_qa',
                            'name': 'QA Manager',
                            'role': 'coordination',
                            'status': 'active'
                        }
                    ],
                    'secretary': [
                        {
                            'id': 'secretary_qa',
                            'name': 'QA Secretary',
                            'role': 'documentation',
                            'status': 'active'
                        }
                    ]
                }
            }
        }
    
    def save_groups(self):
        """Save groups"""
        try:
            with open(self.groups_file, 'w') as f:
                json.dump(self.groups, f, indent=2, default=str)
        except Exception as e:
            print(f"Error saving groups: {e}")
    
    def get_group(self, group_id: str) -> Dict:
        """Get a group"""
        return self.groups.get(group_id, {})
    
    def get_all_groups(self) -> Dict:
        """Get all groups"""
        return self.groups
    
    def add_member(self, group_id: str, member_type: str, member: Dict):
        """Add member to group"""
        if group_id not in self.groups:
            self.groups[group_id] = {
                'name': group_id,
                'description': '',
                'members': {}
            }
        
        if 'members' not in self.groups[group_id]:
            self.groups[group_id]['members'] = {}
        
        if member_type not in self.groups[group_id]['members']:
            self.groups[group_id]['members'][member_type] = []
        
        self.groups[group_id]['members'][member_type].append(member)
        self.save_groups()
    
    def remove_member(self, group_id: str, member_type: str, member_id: str):
        """Remove member from group"""
        if group_id in self.groups:
            members = self.groups[group_id].get('members', {}).get(member_type, [])
            self.groups[group_id]['members'][member_type] = [
                m for m in members if m.get('id') != member_id
            ]
            self.save_groups()
    
    def get_group_stats(self, group_id: str) -> Dict:
        """Get statistics for a group"""
        group = self.get_group(group_id)
        if not group:
            return {}
        
        stats = {
            'total_members': 0,
            'by_type': {}
        }
        
        for member_type, members in group.get('members', {}).items():
            count = len(members)
            stats['by_type'][member_type] = count
            stats['total_members'] += count
        
        return stats

# Global instance
agent_groups = AgentGroups()
