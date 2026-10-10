"""
Technology Intelligence Battle System
Downloads and integrates future technology intelligence into battle tech logic
"""
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from collections import defaultdict
import random
import uuid
import json

try:
    from backend.services.creative_timemashine_500plus import creative_timemashine_500plus
    from backend.services.advanced_intelligent_calculator import advanced_intelligent_calculator
    from backend.services.unified_point_counter import unified_point_counter
    from backend.services.battle_v3_ultimate import battle_v3_ultimate
except ImportError:
    creative_timemashine_500plus = None
    advanced_intelligent_calculator = None
    unified_point_counter = None
    battle_v3_ultimate = None


class TechnologyIntelligenceBattle:
    """
    Technology Intelligence Battle System
    Integrates future technology intelligence into battle logic
    """
    
    def __init__(self):
        self.downloaded_tech = {}  # {tech_id: tech_data}
        self.integrated_battles = defaultdict(list)  # {battle_id: [tech_ids]}
        self.tech_battle_logic = {}  # {battle_id: logic_data}
        self.intelligence_cache = {}  # Cache for intelligence calculations
    
    def download_tech_intelligence(self, user_id: str, projection_id: str, 
                                  tech_id: str) -> Dict[str, Any]:
        """
        Download technology intelligence from future projection
        """
        if not creative_timemashine_500plus:
            return {'success': False, 'error': 'Time machine system not available'}
        
        # Download from time machine
        download_result = creative_timemashine_500plus.download_future_tech(
            user_id, projection_id, tech_id
        )
        
        if not download_result.get('success'):
            return download_result
        
        download_package = download_result['download']
        tech_data = download_package['tech_data']
        
        # Process technology intelligence
        intelligence_data = self._extract_intelligence(tech_data, download_package)
        
        # Store downloaded tech
        tech_storage_id = f"tech_{uuid.uuid4().hex[:12]}"
        self.downloaded_tech[tech_storage_id] = {
            'tech_storage_id': tech_storage_id,
            'original_tech_id': tech_id,
            'user_id': user_id,
            'download_package': download_package,
            'intelligence_data': intelligence_data,
            'downloaded_at': datetime.utcnow().isoformat(),
            'integrated': False
        }
        
        return {
            'success': True,
            'tech_storage_id': tech_storage_id,
            'tech_name': tech_data['name'],
            'intelligence': intelligence_data,
            'download': download_package
        }
    
    def _extract_intelligence(self, tech_data: Dict[str, Any], 
                             download_package: Dict[str, Any]) -> Dict[str, Any]:
        """Extract intelligence data from technology"""
        compatibility = download_package.get('compatibility_level', 0.5)
        power_scaling = download_package.get('power_scaling', 0.5)
        
        return {
            'battle_power': int(tech_data.get('power_level', 0) * power_scaling),
            'tactical_intelligence': self._calculate_tactical_intelligence(tech_data),
            'strategic_advantage': self._calculate_strategic_advantage(tech_data),
            'capabilities': tech_data.get('capabilities', []),
            'compatibility': compatibility,
            'power_scaling': power_scaling,
            'intelligence_score': int((tech_data.get('power_level', 0) / 100) * compatibility)
        }
    
    def _calculate_tactical_intelligence(self, tech_data: Dict[str, Any]) -> float:
        """Calculate tactical intelligence from technology capabilities"""
        capabilities = tech_data.get('capabilities', [])
        base_score = len(capabilities) * 10
        
        # Advanced capabilities add more
        advanced_keywords = ['quantum', 'reality', 'consciousness', 'multiverse', 'existence']
        for cap in capabilities:
            for keyword in advanced_keywords:
                if keyword.lower() in str(cap).lower():
                    base_score += 50
        
        return min(100, base_score)
    
    def _calculate_strategic_advantage(self, tech_data: Dict[str, Any]) -> float:
        """Calculate strategic advantage from technology"""
        power_level = tech_data.get('power_level', 0)
        
        # Scale strategic advantage (0-100)
        if power_level >= 50000:
            return 100.0  # God-level
        elif power_level >= 25000:
            return 90.0   # Reality-level
        elif power_level >= 15000:
            return 75.0   # Advanced
        elif power_level >= 10000:
            return 60.0   # High
        elif power_level >= 5000:
            return 40.0   # Medium
        else:
            return 25.0   # Basic
    
    def integrate_to_battle_logic(self, user_id: str, tech_storage_id: str, 
                                 battle_id: str) -> Dict[str, Any]:
        """
        Integrate downloaded technology intelligence into battle logic
        """
        if tech_storage_id not in self.downloaded_tech:
            return {'success': False, 'error': 'Technology not downloaded'}
        
        tech_data = self.downloaded_tech[tech_storage_id]
        intelligence = tech_data['intelligence_data']
        
        # Get battle if available
        battle_data = None
        if battle_v3_ultimate and battle_id in battle_v3_ultimate.battles:
            battle_data = battle_v3_ultimate.battles[battle_id]
        
        # Create battle logic enhancement
        logic_enhancement = {
            'tech_storage_id': tech_storage_id,
            'tech_name': tech_data['download_package']['tech_name'],
            'intelligence': intelligence,
            'battle_id': battle_id,
            'user_id': user_id,
            'logic_updates': self._generate_logic_updates(intelligence, battle_data),
            'integrated_at': datetime.utcnow().isoformat()
        }
        
        # Store logic enhancement
        if battle_id not in self.tech_battle_logic:
            self.tech_battle_logic[battle_id] = []
        
        self.tech_battle_logic[battle_id].append(logic_enhancement)
        self.integrated_battles[battle_id].append(tech_storage_id)
        
        # Mark tech as integrated
        tech_data['integrated'] = True
        tech_data['integrated_battle_id'] = battle_id
        
        return {
            'success': True,
            'integration': logic_enhancement,
            'message': f"Technology intelligence integrated into battle {battle_id}"
        }
    
    def _generate_logic_updates(self, intelligence: Dict[str, Any], 
                                battle_data: Optional[Dict] = None) -> Dict[str, Any]:
        """Generate logic updates based on intelligence"""
        updates = {
            'power_multiplier': 1.0 + (intelligence.get('battle_power', 0) / 10000),
            'tactical_bonus': intelligence.get('tactical_intelligence', 0) / 100,
            'strategic_bonus': intelligence.get('strategic_advantage', 0) / 100,
            'intelligence_boost': intelligence.get('intelligence_score', 0) / 1000,
            'capabilities': intelligence.get('capabilities', []),
            'logic_modifications': []
        }
        
        # Add logic modifications based on capabilities
        capabilities = intelligence.get('capabilities', [])
        for cap in capabilities:
            cap_str = str(cap).lower()
            if 'quantum' in cap_str:
                updates['logic_modifications'].append({
                    'type': 'quantum_logic',
                    'effect': 'Multiple simultaneous battle outcomes',
                    'modifier': 2.0
                })
            elif 'reality' in cap_str:
                updates['logic_modifications'].append({
                    'type': 'reality_logic',
                    'effect': 'Physics manipulation in battle',
                    'modifier': 3.0
                })
            elif 'consciousness' in cap_str:
                updates['logic_modifications'].append({
                    'type': 'consciousness_logic',
                    'effect': 'Mind-based battle tactics',
                    'modifier': 2.5
                })
            elif 'multiverse' in cap_str:
                updates['logic_modifications'].append({
                    'type': 'multiverse_logic',
                    'effect': 'Cross-universe battle strategies',
                    'modifier': 5.0
                })
        
        return updates
    
    def get_battle_logic(self, battle_id: str) -> Dict[str, Any]:
        """Get enhanced battle logic for a battle"""
        logic_updates = self.tech_battle_logic.get(battle_id, [])
        
        # Combine all logic updates
        combined_logic = {
            'battle_id': battle_id,
            'total_tech_integrations': len(logic_updates),
            'combined_updates': self._combine_logic_updates(logic_updates),
            'integrated_technologies': [
                {
                    'tech_name': update['tech_name'],
                    'intelligence': update['intelligence']
                }
                for update in logic_updates
            ]
        }
        
        return {
            'success': True,
            'battle_logic': combined_logic
        }
    
    def _combine_logic_updates(self, logic_updates: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Combine multiple logic updates"""
        if not logic_updates:
            return {}
        
        combined = {
            'power_multiplier': 1.0,
            'tactical_bonus': 0.0,
            'strategic_bonus': 0.0,
            'intelligence_boost': 0.0,
            'all_capabilities': [],
            'all_logic_modifications': []
        }
        
        for update in logic_updates:
            logic = update.get('logic_updates', {})
            combined['power_multiplier'] *= logic.get('power_multiplier', 1.0)
            combined['tactical_bonus'] += logic.get('tactical_bonus', 0.0)
            combined['strategic_bonus'] += logic.get('strategic_bonus', 0.0)
            combined['intelligence_boost'] += logic.get('intelligence_boost', 0.0)
            combined['all_capabilities'].extend(logic.get('capabilities', []))
            combined['all_logic_modifications'].extend(logic.get('logic_modifications', []))
        
        # Average bonuses
        if logic_updates:
            combined['tactical_bonus'] /= len(logic_updates)
            combined['strategic_bonus'] /= len(logic_updates)
            combined['intelligence_boost'] /= len(logic_updates)
        
        return combined
    
    def apply_logic_to_battle(self, battle_id: str, user_id: str) -> Dict[str, Any]:
        """
        Apply downloaded technology logic to an active battle
        """
        battle_logic = self.get_battle_logic(battle_id)
        if not battle_logic.get('success'):
            return battle_logic
        
        combined = battle_logic['battle_logic']['combined_updates']
        
        # Apply to battle if available
        if battle_v3_ultimate and battle_id in battle_v3_ultimate.battles:
            battle = battle_v3_ultimate.battles[battle_id]
            
            # Apply multipliers
            if 'tech_intelligence' not in battle:
                battle['tech_intelligence'] = {}
            
            battle['tech_intelligence'].update({
                'power_multiplier': combined.get('power_multiplier', 1.0),
                'tactical_bonus': combined.get('tactical_bonus', 0.0),
                'strategic_bonus': combined.get('strategic_bonus', 0.0),
                'intelligence_boost': combined.get('intelligence_boost', 0.0),
                'capabilities': combined.get('all_capabilities', []),
                'logic_modifications': combined.get('all_logic_modifications', []),
                'applied_at': datetime.utcnow().isoformat()
            })
        
        return {
            'success': True,
            'battle_id': battle_id,
            'applied_logic': combined,
            'message': 'Technology intelligence logic applied to battle'
        }
    
    def get_downloaded_tech(self, user_id: str) -> Dict[str, Any]:
        """Get all downloaded technologies for a user"""
        user_tech = [
            tech for tech in self.downloaded_tech.values()
            if tech['user_id'] == user_id
        ]
        
        return {
            'success': True,
            'user_id': user_id,
            'downloaded_technologies': user_tech,
            'count': len(user_tech)
        }


# Global instance
technology_intelligence_battle = TechnologyIntelligenceBattle()

