"""
Technology Tree Galactic Upgrade System
Upgrades all technology and techtree with future tech from other galactic races
Includes Proxima B, Andromeda, Sirius, and other galactic civilizations
"""
import os
import json
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

class TechTreeGalacticUpgrade:
    """
    Upgrades technology tree with future tech from other galactic races
    """
    
    def __init__(self):
        self.galactic_tech_file = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            'data', 'galactic_tech_tree.json'
        )
        os.makedirs(os.path.dirname(self.galactic_tech_file), exist_ok=True)
        self.galactic_technologies = self._load_galactic_tech()
        self._initialize_galactic_technologies()
    
    def _load_galactic_tech(self) -> Dict[str, Any]:
        """Load galactic technologies"""
        try:
            if os.path.exists(self.galactic_tech_file):
                with open(self.galactic_tech_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            logger.error(f"Error loading galactic tech: {e}")
        return {'technologies': {}, 'races': {}}
    
    def _save_galactic_tech(self):
        """Save galactic technologies"""
        try:
            with open(self.galactic_tech_file, 'w', encoding='utf-8') as f:
                json.dump(self.galactic_tech, f, indent=2, default=str)
        except Exception as e:
            logger.error(f"Error saving galactic tech: {e}")
    
    def _initialize_galactic_technologies(self):
        """Initialize technologies from other galactic races"""
        if self.galactic_technologies.get('technologies'):
            return  # Already initialized
        
        self.galactic_technologies['technologies'] = {
            'proxima_b_insectoid_tech': {
                'name': 'Proxima B Insectoid Technology',
                'race': 'Proxima B Insectoid',
                'planet': 'Proxima Centauri b',
                'tech_level': 12.5,
                'category': 'biological',
                'technologies': [
                    {
                        'name': 'Hive Mind Network',
                        'description': 'Direct neural connection between all members',
                        'power': 15000,
                        'intelligence_required': 10.0
                    },
                    {
                        'name': 'Exoskeleton Enhancement',
                        'description': 'Self-repairing exoskeleton technology',
                        'power': 12000,
                        'intelligence_required': 8.0
                    },
                    {
                        'name': 'Adaptive Evolution Engine',
                        'description': 'Rapid biological adaptation to environment',
                        'power': 18000,
                        'intelligence_required': 12.0
                    }
                ],
                'unlocked_at': datetime.now().isoformat()
            },
            'andromeda_construct_tech': {
                'name': 'Andromeda Construct Technology',
                'race': 'Andromeda Construct',
                'galaxy': 'Andromeda',
                'tech_level': 15.0,
                'category': 'mechanical',
                'technologies': [
                    {
                        'name': 'Nano-Machine Integration',
                        'description': 'Molecular-level machine integration',
                        'power': 25000,
                        'intelligence_required': 15.0
                    },
                    {
                        'name': 'Quantum DNA Processing',
                        'description': 'Quantum-enhanced genetic computing',
                        'power': 30000,
                        'intelligence_required': 18.0
                    },
                    {
                        'name': 'Self-Repair Matrix',
                        'description': 'Automatic repair at cellular level',
                        'power': 22000,
                        'intelligence_required': 12.0
                    }
                ],
                'unlocked_at': datetime.now().isoformat()
            },
            'sirius_crystalline_tech': {
                'name': 'Sirius Crystalline Technology',
                'race': 'Sirius Crystalline',
                'star_system': 'Sirius',
                'tech_level': 14.0,
                'category': 'energy',
                'technologies': [
                    {
                        'name': 'Crystalline Energy Matrix',
                        'description': 'Infinite energy storage in crystal structures',
                        'power': 28000,
                        'intelligence_required': 14.0
                    },
                    {
                        'name': 'Light Manipulation Array',
                        'description': 'Control over light at quantum level',
                        'power': 26000,
                        'intelligence_required': 16.0
                    },
                    {
                        'name': 'Crystal Regeneration',
                        'description': 'Self-replicating crystal structures',
                        'power': 24000,
                        'intelligence_required': 13.0
                    }
                ],
                'unlocked_at': datetime.now().isoformat()
            }
        }
        
        self.galactic_technologies['races'] = {
            'proxima_b_insectoid': {
                'name': 'Proxima B Insectoid',
                'status': 'contacted',
                'technology_shared': True
            },
            'andromeda_construct': {
                'name': 'Andromeda Construct',
                'status': 'contacted',
                'technology_shared': True
            },
            'sirius_crystalline': {
                'name': 'Sirius Crystalline',
                'status': 'contacted',
                'technology_shared': True
            }
        }
        
        # Update the instance variable
        self.galactic_tech = self.galactic_technologies
        
        # Update instance variable
        self.galactic_tech = self.galactic_technologies
        
        try:
            with open(self.galactic_tech_file, 'w', encoding='utf-8') as f:
                json.dump(self.galactic_technologies, f, indent=2, default=str)
        except:
            pass
    
    def upgrade_all_tech_with_galactic(self) -> Dict[str, Any]:
        """Upgrade all technology with galactic race technologies"""
        try:
            # Get existing future tech
            try:
                from backend.services.future_tech_intelligence_upgrade import future_tech_intelligence_upgrade
                existing_tech = future_tech_intelligence_upgrade.get_future_technologies_enhanced()
            except:
                existing_tech = {'technologies': []}
            
            # Merge galactic technologies
            upgraded_technologies = existing_tech.get('technologies', []).copy()
            
            # Add galactic race technologies
            for race_tech_key, race_tech in self.galactic_technologies['technologies'].items():
                for tech in race_tech['technologies']:
                    upgraded_tech = {
                        'id': f"galactic_{race_tech_key}_{tech['name'].lower().replace(' ', '_')}",
                        'name': tech['name'],
                        'description': tech['description'],
                        'category': race_tech['category'],
                        'power': tech['power'],
                        'years_ahead': 500 + int(race_tech['tech_level'] * 100),
                        'source_race': race_tech['race'],
                        'source_planet': race_tech.get('planet', race_tech.get('star_system', race_tech.get('galaxy', 'Unknown'))),
                        'intelligence_required': tech['intelligence_required'],
                        'galactic_tech': True,
                        'unlocked_at': datetime.now().isoformat()
                    }
                    upgraded_technologies.append(upgraded_tech)
            
            return {
                'success': True,
                'total_technologies': len(upgraded_technologies),
                'galactic_technologies_added': len(self.galactic_technologies['technologies']),
                'technologies': upgraded_technologies
            }
        except Exception as e:
            logger.error(f"Error upgrading tech with galactic: {e}")
            return {'success': False, 'error': str(e)}
    
    def get_galactic_technologies(self) -> Dict[str, Any]:
        """Get all galactic race technologies"""
        return {
            'success': True,
            'technologies': self.galactic_technologies.get('technologies', {}),
            'races': self.galactic_technologies.get('races', {}),
            'total_technologies': sum(
                len(race['technologies']) 
                for race in self.galactic_technologies.get('technologies', {}).values()
            )
        }


# Global instance
tech_tree_galactic_upgrade = TechTreeGalacticUpgrade()

