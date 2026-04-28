"""
System Skills Definition
Defines all system skills with bridges, limits, and empty spaces for missing skills
"""
from typing import Dict, List, Optional
from datetime import datetime
import json
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class SystemSkillsDefinition:
    """System-wide skills definition with bridges and limits"""
    
    def __init__(self, base_dir: Optional[str] = None):
        self.base_dir = base_dir or BASE_DIR
        self.skills_file = os.path.join(self.base_dir, 'logs', 'system_skills', 'skills_definition.json')
        self.load_skills()
    
    def load_skills(self):
        """Load skills definition"""
        os.makedirs(os.path.dirname(self.skills_file), exist_ok=True)
        
        if os.path.exists(self.skills_file):
            try:
                with open(self.skills_file, 'r') as f:
                    self.skills = json.load(f)
            except:
                self.skills = self._default_skills_definition()
        else:
            self.skills = self._default_skills_definition()

        self._ensure_super_update_defaults()
        self.save_skills()

    def _ensure_super_update_defaults(self):
        """Backfill super update fields for old skill definition files."""
        if 'super_upgrade_blocks' not in self.skills:
            self.skills['super_upgrade_blocks'] = self._default_super_upgrade_blocks()
        else:
            # Keep legacy files aligned with current block schema/linkboxes.
            for block in self.skills.get('super_upgrade_blocks', []):
                block.setdefault('title', 'Super Upgrade Block')
                block.setdefault('description', 'Boosts system skills by +10 and enables autonomous recovery links.')
                block.setdefault('skill_boost', {'level_delta': 0, 'power_delta': 10, 'limit_delta': 10})
                block.setdefault('enabled', True)
                links = block.setdefault('link_boxes', [])
                expected_links = [
                    {'label': 'System Skills Definition', 'url': '/api/system-skills/definition'},
                    {'label': 'Apply Super Upgrade', 'url': '/api/system-skills/super-upgrade/apply'},
                    {'label': 'Apply All Super Upgrades', 'url': '/api/system-skills/super-upgrade/apply-all'},
                    {'label': 'Self-Heal Status', 'url': '/api/system-skills/self-heal/status'},
                ]
                existing_urls = {str(link.get('url')) for link in links if isinstance(link, dict)}
                for item in expected_links:
                    if item['url'] not in existing_urls:
                        links.append(item)
        if 'applied_super_upgrades' not in self.skills:
            self.skills['applied_super_upgrades'] = []
        if 'self_heal_policy' not in self.skills:
            self.skills['self_heal_policy'] = {
                'enabled': True,
                'auto_activate_on_offline': True,
                'auto_repair_on_error': True,
                'max_retries': 3,
            }
    
    def _default_skills_definition(self) -> Dict:
        """Default skills definition with all skills, bridges, and limits"""
        return {
            'skill_lines': {
                'ai_skills_line': {
                    'name': 'AI Skills Line',
                    'description': 'Core AI capabilities',
                    'skills': [
                        {'name': 'decision_making', 'level': 1, 'max_level': 10, 'power': 10, 'limit': 100, 'bridgeable': True},
                        {'name': 'pattern_recognition', 'level': 1, 'max_level': 10, 'power': 10, 'limit': 100, 'bridgeable': True},
                        {'name': 'prediction', 'level': 1, 'max_level': 10, 'power': 10, 'limit': 100, 'bridgeable': True},
                        {'name': 'content_generation', 'level': 1, 'max_level': 10, 'power': 10, 'limit': 50, 'bridgeable': True},
                        {'name': 'optimization', 'level': 1, 'max_level': 10, 'power': 10, 'limit': 50, 'bridgeable': True},
                        {'name': 'learning', 'level': 1, 'max_level': 10, 'power': 10, 'limit': 100, 'bridgeable': True},
                        {'name': 'risk_assessment', 'level': 1, 'max_level': 10, 'power': 10, 'limit': 100, 'bridgeable': True},
                        {'name': 'strategy_development', 'level': 1, 'max_level': 10, 'power': 10, 'limit': 50, 'bridgeable': True},
                        {'name': 'context_understanding', 'level': 1, 'max_level': 10, 'power': 10, 'limit': 100, 'bridgeable': True, 'placeholder': False},
                        {'name': 'natural_language', 'level': 1, 'max_level': 10, 'power': 10, 'limit': 50, 'bridgeable': True, 'placeholder': False},
                        {'name': 'image_processing', 'level': 1, 'max_level': 10, 'power': 10, 'limit': 50, 'bridgeable': True, 'placeholder': False},
                        {'name': 'audio_processing', 'level': 1, 'max_level': 10, 'power': 10, 'limit': 50, 'bridgeable': True, 'placeholder': False}
                    ]
                },
                'system_skills_line': {
                    'name': 'System Skills Line',
                    'description': 'System operation capabilities',
                    'skills': [
                        {'name': 'debugging', 'level': 1, 'max_level': 10, 'power': 10, 'limit': 50, 'bridgeable': True, 'placeholder': False},
                        {'name': 'monitoring', 'level': 1, 'max_level': 10, 'power': 10, 'limit': 50, 'bridgeable': True, 'placeholder': False},
                        {'name': 'content_creation', 'level': 1, 'max_level': 10, 'power': 10, 'limit': 50, 'bridgeable': True, 'placeholder': False},
                        {'name': 'data_analysis', 'level': 1, 'max_level': 10, 'power': 10, 'limit': 50, 'bridgeable': True, 'placeholder': False},
                        {'name': 'automation', 'level': 1, 'max_level': 10, 'power': 10, 'limit': 50, 'bridgeable': True, 'placeholder': False},
                        {'name': 'security', 'level': 1, 'max_level': 10, 'power': 10, 'limit': 50, 'bridgeable': True, 'placeholder': False},
                        {'name': 'performance', 'level': 1, 'max_level': 10, 'power': 10, 'limit': 50, 'bridgeable': True, 'placeholder': False},
                        {'name': 'integration', 'level': 1, 'max_level': 10, 'power': 10, 'limit': 50, 'bridgeable': True, 'placeholder': False},
                        {'name': 'testing', 'level': 1, 'max_level': 10, 'power': 10, 'limit': 50, 'bridgeable': True, 'placeholder': False},
                        {'name': 'deployment', 'level': 1, 'max_level': 10, 'power': 10, 'limit': 50, 'bridgeable': True, 'placeholder': False},
                        {'name': 'scaling', 'level': 1, 'max_level': 10, 'power': 10, 'limit': 50, 'bridgeable': True, 'placeholder': False},
                        {'name': 'maintenance', 'level': 1, 'max_level': 10, 'power': 10, 'limit': 50, 'bridgeable': True, 'placeholder': False}
                    ]
                },
                'content_skills_line': {
                    'name': 'Content Skills Line',
                    'description': 'Content creation and generation',
                    'skills': [
                        {'name': 'text_generation', 'level': 1, 'max_level': 10, 'power': 10, 'limit': 50, 'bridgeable': True, 'placeholder': False},
                        {'name': 'code_generation', 'level': 1, 'max_level': 10, 'power': 10, 'limit': 50, 'bridgeable': True, 'placeholder': False},
                        {'name': 'image_generation', 'level': 1, 'max_level': 10, 'power': 10, 'limit': 50, 'bridgeable': True, 'placeholder': False},
                        {'name': 'video_generation', 'level': 1, 'max_level': 10, 'power': 10, 'limit': 50, 'bridgeable': True, 'placeholder': False},
                        {'name': 'audio_generation', 'level': 1, 'max_level': 10, 'power': 10, 'limit': 50, 'bridgeable': True, 'placeholder': False},
                        {'name': 'template_creation', 'level': 1, 'max_level': 10, 'power': 10, 'limit': 50, 'bridgeable': True, 'placeholder': False},
                        {'name': 'content_optimization', 'level': 1, 'max_level': 10, 'power': 10, 'limit': 50, 'bridgeable': True, 'placeholder': False},
                        {'name': 'content_analysis', 'level': 1, 'max_level': 10, 'power': 10, 'limit': 50, 'bridgeable': True, 'placeholder': False}
                    ]
                }
            },
            'skill_bridges': [
                {
                    'bridge_id': 'ai_content_bridge',
                    'skill1': 'content_generation',
                    'skill2': 'text_generation',
                    'bridge_type': 'complementary',
                    'power_multiplier': 1.5,
                    'limit_multiplier': 1.2
                },
                {
                    'bridge_id': 'ai_optimization_bridge',
                    'skill1': 'optimization',
                    'skill2': 'performance',
                    'bridge_type': 'synergistic',
                    'power_multiplier': 1.8,
                    'limit_multiplier': 1.3
                },
                {
                    'bridge_id': 'prediction_risk_bridge',
                    'skill1': 'prediction',
                    'skill2': 'risk_assessment',
                    'bridge_type': 'complementary',
                    'power_multiplier': 1.6,
                    'limit_multiplier': 1.2
                }
            ],
            'class_limits': {
                'ai_agent': {'power': 100, 'actions_per_hour': 100, 'content_per_day': 50},
                'debugging_agent': {'power': 50, 'actions_per_hour': 50, 'content_per_day': 10},
                'content_agent': {'power': 75, 'actions_per_hour': 75, 'content_per_day': 100},
                'monitoring_agent': {'power': 40, 'actions_per_hour': 40, 'content_per_day': 5},
                'system_agent': {'power': 60, 'actions_per_hour': 60, 'content_per_day': 20}
            },
            'bridged_limits': {
                'ai_content_bridge': {'power': 150, 'actions': 120},
                'ai_optimization_bridge': {'power': 180, 'actions': 130},
                'prediction_risk_bridge': {'power': 160, 'actions': 120}
            },
            'super_upgrade_blocks': self._default_super_upgrade_blocks(),
            'applied_super_upgrades': [],
            'self_heal_policy': {
                'enabled': True,
                'auto_activate_on_offline': True,
                'auto_repair_on_error': True,
                'max_retries': 3,
            },
            'missing_skills': [],
            'last_updated': datetime.now().isoformat()
        }

    def _default_super_upgrade_blocks(self) -> List[Dict]:
        """Super upgrades with link boxes and +10 boost plans."""
        return [
            {
                'upgrade_id': f'super_upgrade_{i}',
                'title': f'Super Upgrade Block {i}',
                'description': 'Boosts system skills by +10 and enables autonomous recovery links.',
                'skill_boost': {'level_delta': 0, 'power_delta': 10, 'limit_delta': 10},
                'link_boxes': [
                    {'label': 'System Skills Definition', 'url': '/api/system-skills/definition'},
                    {'label': 'Apply Super Upgrade', 'url': '/api/system-skills/super-upgrade/apply'},
                    {'label': 'Apply All Super Upgrades', 'url': '/api/system-skills/super-upgrade/apply-all'},
                    {'label': 'Self-Heal Status', 'url': '/api/system-skills/self-heal/status'},
                ],
                'enabled': True,
            }
            for i in range(1, 11)
        ]
    
    def save_skills(self):
        """Save skills definition"""
        try:
            self.skills['last_updated'] = datetime.now().isoformat()
            with open(self.skills_file, 'w') as f:
                json.dump(self.skills, f, indent=2, default=str)
        except Exception as e:
            print(f"Error saving skills: {e}")
    
    def get_skill_line(self, line_name: str) -> Dict:
        """Get a skill line definition"""
        return self.skills['skill_lines'].get(line_name, {})
    
    def get_all_skill_lines(self) -> Dict:
        """Get all skill lines"""
        return self.skills['skill_lines']
    
    def create_skill_bridge(self, skill1: str, skill2: str, bridge_type: str = 'complementary') -> Dict:
        """Create a new skill bridge"""
        bridge_id = f"bridge_{skill1}_{skill2}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # Determine multipliers based on bridge type
        multipliers = {
            'complementary': {'power': 1.5, 'limit': 1.2},
            'synergistic': {'power': 1.8, 'limit': 1.3},
            'amplifying': {'power': 2.0, 'limit': 1.5},
            'supporting': {'power': 1.3, 'limit': 1.1}
        }
        
        mult = multipliers.get(bridge_type, multipliers['complementary'])
        
        bridge = {
            'bridge_id': bridge_id,
            'skill1': skill1,
            'skill2': skill2,
            'bridge_type': bridge_type,
            'power_multiplier': mult['power'],
            'limit_multiplier': mult['limit'],
            'created_at': datetime.now().isoformat()
        }
        
        self.skills['skill_bridges'].append(bridge)
        
        # Create bridged limit
        self.skills['bridged_limits'][bridge_id] = {
            'power': 100 * mult['power'],
            'actions': 100 * mult['limit']
        }
        
        self.save_skills()
        
        return bridge
    
    def get_class_limits(self, agent_class: str) -> Dict:
        """Get limits for an agent class"""
        return self.skills['class_limits'].get(agent_class, {
            'power': 50,
            'actions_per_hour': 50,
            'content_per_day': 10
        })
    
    def set_class_limit(self, agent_class: str, limits: Dict):
        """Set limits for an agent class"""
        if 'class_limits' not in self.skills:
            self.skills['class_limits'] = {}
        
        self.skills['class_limits'][agent_class] = limits
        self.save_skills()
    
    def add_missing_skill(self, skill_line: str, skill_name: str, skill_data: Dict):
        """Add a missing skill to a skill line"""
        if skill_line not in self.skills['skill_lines']:
            self.skills['skill_lines'][skill_line] = {
                'name': skill_line,
                'description': '',
                'skills': []
            }
        
        skill_entry = {
            'name': skill_name,
            'level': skill_data.get('level', 0),
            'max_level': skill_data.get('max_level', 10),
            'power': skill_data.get('power', 0),
            'limit': skill_data.get('limit', 50),
            'bridgeable': skill_data.get('bridgeable', True),
            'placeholder': skill_data.get('placeholder', False)
        }
        
        # Check if skill already exists
        existing = [s for s in self.skills['skill_lines'][skill_line]['skills'] if s['name'] == skill_name]
        if not existing:
            self.skills['skill_lines'][skill_line]['skills'].append(skill_entry)
            self.save_skills()
        
        return skill_entry
    
    def get_skill_definitions_with_placeholders(self) -> Dict:
        """Get all skill definitions including placeholders for missing skills"""
        definitions = {
            'skill_lines': {},
            'bridges': self.skills['skill_bridges'],
            'class_limits': self.skills['class_limits'],
            'bridged_limits': self.skills['bridged_limits'],
            'super_upgrade_blocks': self.skills.get('super_upgrade_blocks', []),
            'applied_super_upgrades': self.skills.get('applied_super_upgrades', []),
            'self_heal_policy': self.skills.get('self_heal_policy', {}),
        }
        
        # Add all skill lines with placeholders
        for line_name, line_data in self.skills['skill_lines'].items():
            definitions['skill_lines'][line_name] = {
                'name': line_data['name'],
                'description': line_data['description'],
                'skills': line_data['skills'],
                'missing_skills': [s for s in line_data['skills'] if s.get('placeholder', False)]
            }
        
        return definitions

    def apply_super_upgrade(self, upgrade_id: str) -> Dict:
        """Apply a super upgrade (+10 power/limit) across all skill lines."""
        blocks = self.skills.get('super_upgrade_blocks', [])
        block = next((b for b in blocks if b.get('upgrade_id') == upgrade_id), None)
        if not block:
            return {'success': False, 'error': 'upgrade_not_found'}
        if not block.get('enabled', True):
            return {'success': False, 'error': 'upgrade_disabled'}
        if upgrade_id in self.skills.get('applied_super_upgrades', []):
            return {'success': False, 'error': 'upgrade_already_applied'}

        boost = block.get('skill_boost', {})
        power_delta = int(boost.get('power_delta', 10))
        limit_delta = int(boost.get('limit_delta', 10))
        level_delta = int(boost.get('level_delta', 0))
        changed = 0

        for line_data in self.skills.get('skill_lines', {}).values():
            for skill in line_data.get('skills', []):
                skill['power'] = int(skill.get('power', 0)) + power_delta
                skill['limit'] = int(skill.get('limit', 0)) + limit_delta
                skill['level'] = min(
                    int(skill.get('max_level', 10)),
                    int(skill.get('level', 0)) + level_delta,
                )
                changed += 1

        self.skills.setdefault('applied_super_upgrades', []).append(upgrade_id)
        self.save_skills()
        return {
            'success': True,
            'upgrade_id': upgrade_id,
            'skills_updated': changed,
            'power_delta': power_delta,
            'limit_delta': limit_delta,
            'level_delta': level_delta,
        }

    def apply_all_super_upgrades(self) -> Dict:
        """
        Apply all enabled super upgrades with rollback safety.
        If any apply step fails unexpectedly, restore the pre-run snapshot.
        """
        # Deep-copy snapshot via JSON to keep it simple/serializable.
        snapshot = json.loads(json.dumps(self.skills, default=str))
        blocks = [b for b in self.get_super_upgrade_blocks() if b.get('enabled', True)]
        applied = []
        skipped = []

        try:
            for block in blocks:
                upgrade_id = block.get('upgrade_id')
                result = self.apply_super_upgrade(upgrade_id)
                if result.get('success'):
                    applied.append(upgrade_id)
                else:
                    skipped.append({
                        'upgrade_id': upgrade_id,
                        'reason': result.get('error', 'unknown'),
                    })

            return {
                'success': True,
                'total_blocks': len(blocks),
                'applied_count': len(applied),
                'skipped_count': len(skipped),
                'applied': applied,
                'skipped': skipped,
            }
        except Exception as e:
            # Rollback on unexpected failure.
            self.skills = snapshot
            self.save_skills()
            return {
                'success': False,
                'error': str(e),
                'rolled_back': True,
                'applied_before_failure': applied,
            }

    def get_super_upgrade_blocks(self) -> List[Dict]:
        """Return configured super upgrade blocks with link boxes."""
        return self.skills.get('super_upgrade_blocks', [])

    def get_self_heal_policy(self) -> Dict:
        """Return configured self-heal policy."""
        return self.skills.get('self_heal_policy', {})


# Global instance
system_skills_definition = SystemSkillsDefinition()
