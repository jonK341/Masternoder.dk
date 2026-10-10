"""
Death Portal Manager - Manages Two Death Portals
Enhanced with technology integration and placement logic
"""
from datetime import datetime
from typing import Dict, Any, List, Optional
from collections import defaultdict
import hashlib

class DeathPortalManager:
    """Manages two Death Portals with technology integration"""
    
    def __init__(self):
        # Common Mind Generator location (where they were stolen from)
        self.common_mind_generator_location = {
            'x': -500,
            'y': 0,
            'z': -750,
            'name': 'Common Mind Generator Site',
            'description': 'Location where previous Common Mind generators were stolen',
            'stolen_at': '2024-12-15T00:00:00Z',  # When they were stolen
            'status': 'recovered'
        }
        
        # Portal 1: Reinstall at Common Mind Generator location
        self.portals = {
            'portal_1': {
                'portal_id': 'portal_1',
                'name': 'Death Portal Alpha',
                'location': self.common_mind_generator_location.copy(),
                'status': 'active',
                'created_at': datetime.utcnow().isoformat(),
                'bugs_killed': 0,
                'purpose': 'Primary bug killing portal - Reinstalled at Common Mind Generator site',
                'installation_reason': 'Reinstall at same place where Common Mind generators were stolen',
                'tech_integration': {
                    'enabled': True,
                    'tech_level': 1,
                    'unlocked_tech': [],
                    'tech_boosts': {}
                },
                'last_word': None  # Will be set to "Phyko" if confirmed
            },
            'portal_2': {
                'portal_id': 'portal_2',
                'name': 'Death Portal Beta',
                'location': {'x': 1000, 'y': 0, 'z': -500},
                'status': 'pending_placement',
                'created_at': datetime.utcnow().isoformat(),
                'bugs_killed': 0,
                'purpose': 'Secondary portal - Placement to be determined',
                'tech_integration': {
                    'enabled': True,
                    'tech_level': 1,
                    'unlocked_tech': [],
                    'tech_boosts': {}
                },
                'last_word': None
            }
        }
        self.bugs = {}  # {bug_id: bug_data}
        self.bug_history = defaultdict(list)
        self.available_tech = self._initialize_portal_tech()
        self.phyko_confirmed = False  # Whether "Phyko" should be the last word
    
    def get_portals(self) -> Dict[str, Any]:
        """Get all death portals"""
        return {
            'success': True,
            'portals': list(self.portals.values()),
            'total': len(self.portals)
        }
    
    def get_portal(self, portal_id: str) -> Dict[str, Any]:
        """Get specific portal"""
        if portal_id not in self.portals:
            return {
                'success': False,
                'error': 'Portal not found'
            }
        
        return {
            'success': True,
            'portal': self.portals[portal_id]
        }
    
    def report_bug(
        self,
        portal_id: str,
        bug_type: str,
        description: str,
        severity: str = 'medium'
    ) -> Dict[str, Any]:
        """Report bug to specific portal"""
        if portal_id not in self.portals:
            return {
                'success': False,
                'error': 'Portal not found'
            }
        
        bug_id = f"bug_{hashlib.sha256(f'{portal_id}{datetime.utcnow().isoformat()}'.encode()).hexdigest()[:16]}"
        
        bug_data = {
            'bug_id': bug_id,
            'portal_id': portal_id,
            'bug_type': bug_type,
            'description': description,
            'severity': severity,
            'status': 'reported',
            'reported_at': datetime.utcnow().isoformat()
        }
        
        self.bugs[bug_id] = bug_data
        self.bug_history[portal_id].append(bug_data)
        
        return {
            'success': True,
            'bug': bug_data,
            'portal': self.portals[portal_id]
        }
    
    def kill_bug(
        self,
        portal_id: str,
        bug_id: str,
        method: str = 'execution'
    ) -> Dict[str, Any]:
        """Kill bug via specific portal"""
        if portal_id not in self.portals:
            return {
                'success': False,
                'error': 'Portal not found'
            }
        
        if bug_id not in self.bugs:
            return {
                'success': False,
                'error': 'Bug not found'
            }
        
        bug = self.bugs[bug_id]
        
        if bug['portal_id'] != portal_id:
            return {
                'success': False,
                'error': 'Bug belongs to different portal'
            }
        
        bug['status'] = 'killed'
        bug['killed_at'] = datetime.utcnow().isoformat()
        bug['kill_method'] = method
        
        self.portals[portal_id]['bugs_killed'] += 1
        
        return {
            'success': True,
            'bug': bug,
            'portal': self.portals[portal_id],
            'message': f'Bug killed via {method}'
        }
    
    def get_portal_bugs(self, portal_id: str, status: Optional[str] = None) -> Dict[str, Any]:
        """Get bugs for specific portal"""
        if portal_id not in self.portals:
            return {
                'success': False,
                'error': 'Portal not found'
            }
        
        bugs = [
            b for b in self.bugs.values()
            if b.get('portal_id') == portal_id
        ]
        
        if status:
            bugs = [b for b in bugs if b.get('status') == status]
        
        return {
            'success': True,
            'bugs': bugs,
            'portal': self.portals[portal_id],
            'total': len(bugs)
        }
    
    def _initialize_portal_tech(self) -> Dict[str, Dict[str, Any]]:
        """Initialize technology available for death portals"""
        return {
            'quantum_bug_detection': {
                'name': 'Quantum Bug Detection',
                'description': 'Advanced quantum-based bug detection system',
                'power_boost': 30,
                'force_boost': 25,
                'unlocked': False,
                'portal_benefit': 'Increases bug detection rate by 50%'
            },
            'ai_bug_analysis': {
                'name': 'AI Bug Analysis',
                'description': 'AI-powered bug analysis and classification',
                'power_boost': 25,
                'force_boost': 30,
                'unlocked': False,
                'portal_benefit': 'Automatically categorizes bugs by severity'
            },
            'portal_teleportation': {
                'name': 'Portal Teleportation',
                'description': 'Teleport bugs directly to death portal',
                'power_boost': 40,
                'force_boost': 35,
                'unlocked': False,
                'portal_benefit': 'Instant bug teleportation to portal'
            },
            'energy_shield_portal': {
                'name': 'Portal Energy Shield',
                'description': 'Protective energy shield around portal',
                'power_boost': 35,
                'force_boost': 40,
                'unlocked': False,
                'portal_benefit': 'Protects portal from bug attacks'
            },
            'common_mind_integration': {
                'name': 'Common Mind Integration',
                'description': 'Integration with Common Mind generator technology',
                'power_boost': 50,
                'force_boost': 45,
                'unlocked': False,
                'portal_benefit': 'Enhanced portal capabilities using Common Mind tech',
                'requires_location': 'common_mind_generator_site'
            }
        }
    
    def unlock_portal_tech(
        self,
        portal_id: str,
        tech_name: str
    ) -> Dict[str, Any]:
        """Unlock technology for specific portal"""
        if portal_id not in self.portals:
            return {
                'success': False,
                'error': 'Portal not found'
            }
        
        if tech_name not in self.available_tech:
            return {
                'success': False,
                'error': f'Technology {tech_name} not found'
            }
        
        tech = self.available_tech[tech_name]
        portal = self.portals[portal_id]
        
        # Check location requirement
        if tech.get('requires_location') == 'common_mind_generator_site':
            if portal['location'] != self.common_mind_generator_location:
                return {
                    'success': False,
                    'error': 'This technology requires Common Mind Generator site location'
                }
        
        if tech.get('unlocked'):
            return {
                'success': False,
                'error': f'Technology {tech_name} already unlocked'
            }
        
        tech['unlocked'] = True
        tech['unlocked_at'] = datetime.utcnow().isoformat()
        tech['unlocked_for_portal'] = portal_id
        
        # Add to portal's unlocked tech
        portal['tech_integration']['unlocked_tech'].append(tech_name)
        portal['tech_integration']['tech_boosts'][tech_name] = {
            'power_boost': tech['power_boost'],
            'force_boost': tech['force_boost']
        }
        
        # Increase portal tech level
        portal['tech_integration']['tech_level'] += 1
        
        return {
            'success': True,
            'tech': tech,
            'portal': portal,
            'message': f'Technology {tech_name} unlocked for {portal["name"]}'
        }
    
    def get_portal_tech(self, portal_id: str) -> Dict[str, Any]:
        """Get technology for specific portal"""
        if portal_id not in self.portals:
            return {
                'success': False,
                'error': 'Portal not found'
            }
        
        portal = self.portals[portal_id]
        
        return {
            'success': True,
            'portal': portal,
            'tech_integration': portal['tech_integration'],
            'available_tech': self.available_tech,
            'unlocked_tech': portal['tech_integration']['unlocked_tech']
        }
    
    def place_portal_2(
        self,
        location: Optional[Dict[str, float]] = None,
        reason: Optional[str] = None
    ) -> Dict[str, Any]:
        """Place Portal 2 at specified location"""
        portal_2 = self.portals['portal_2']
        
        if location:
            portal_2['location'] = location
        else:
            # Default placement: Strategic location for timepocket operations
            portal_2['location'] = {
                'x': 1000,
                'y': 0,
                'z': -500,
                'name': 'Strategic Timepocket Location',
                'description': 'Secondary portal location for timepocket operations'
            }
        
        portal_2['status'] = 'active'
        portal_2['placed_at'] = datetime.utcnow().isoformat()
        portal_2['placement_reason'] = reason or 'Strategic placement for secondary operations'
        
        return {
            'success': True,
            'portal': portal_2,
            'message': f'Portal 2 placed at {portal_2["location"]}'
        }
    
    def confirm_phyko_last_word(self, confirm: bool = True) -> Dict[str, Any]:
        """Confirm if Phyko should be the last word"""
        self.phyko_confirmed = confirm
        
        if confirm:
            # Set Phyko as last word for both portals
            self.portals['portal_1']['last_word'] = 'Phyko'
            self.portals['portal_2']['last_word'] = 'Phyko'
            
            return {
                'success': True,
                'confirmed': True,
                'message': 'Phyko confirmed as the last word for both portals',
                'portals_updated': ['portal_1', 'portal_2']
            }
        else:
            # Clear last word
            self.portals['portal_1']['last_word'] = None
            self.portals['portal_2']['last_word'] = None
            
            return {
                'success': True,
                'confirmed': False,
                'message': 'Phyko not confirmed as last word',
                'portals_updated': ['portal_1', 'portal_2']
            }
    
    def get_common_mind_location(self) -> Dict[str, Any]:
        """Get Common Mind Generator location"""
        return {
            'success': True,
            'location': self.common_mind_generator_location,
            'portal_1_location': self.portals['portal_1']['location'],
            'message': 'Portal 1 reinstalled at Common Mind Generator site'
        }
    
    def get_available_portal_tech(self) -> Dict[str, Any]:
        """Get all available portal technology"""
        return {
            'success': True,
            'tech': self.available_tech,
            'total': len(self.available_tech),
            'unlocked_count': sum(1 for t in self.available_tech.values() if t.get('unlocked'))
        }


# Global instance
death_portal_manager = DeathPortalManager()

